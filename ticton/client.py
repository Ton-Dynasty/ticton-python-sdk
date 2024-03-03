from __future__ import annotations

import asyncio
import logging
import time
import warnings
from decimal import Decimal
from os import getenv
from typing import (
    Any,
    Callable,
    Coroutine,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    overload,
)

from pydantic import BaseModel, Field
from pytoncenter import AsyncTonCenterClientV3, get_client
from pytoncenter.address import Address as PyAddress
from pytoncenter.extension.message import JettonMessage
from pytoncenter.utils import get_opcode
from pytoncenter.v3.models import (
    AddressLike,
    ExternalMessage,
    GetAccountRequest,
    GetMethodParameterInput,
    GetSpecifiedJettonWalletRequest,
    GetTransactionsRequest,
    GetWalletRequest,
    RunGetMethodRequest,
    SentMessage,
)
from tonpy import CellSlice
from tonsdk.boc import Cell, begin_cell
from tonsdk.contract.wallet import Wallets
from tonsdk.utils import bytes_to_b64str

from .arithmetic import FixedFloat, to_token, token_to_float
from .callbacks import (
    OnRingSuccessParams,
    OnTickSuccessParams,
    OnWindSuccessParams,
    handle_chime,
    handle_chronoshift,
    handle_noop,
    handle_notification,
)
from .decoder import (
    AlarmAddressDecoder,
    AlarmMetadata,
    AlarmMetadataDecoder,
    EstimateDataDecoder,
    JettonWalletAddressDecoder,
    OracleMetadata,
    OracleMetadataDecoder,
)
from .parser import TicTonMessage

__all__ = ["TicTonAsyncClient"]


class SubscribeParam(BaseModel):
    start_lt: Optional[int] = Field(
        default=None,
        description="The lt to start from, if None, the oldest lt will be used",
    )
    interval: float = Field(default=2.0, description="The interval of the subscription in seconds")
    limit: int = Field(default=256, ge=1, le=256, description="The limit of the subscription")
    offset: int = Field(default=0, ge=0, description="The offset of the subscription")
    account: AddressLike = Field(..., description="The account to subscribe to")


class DryRunResult(BaseModel):
    boc: str = Field(..., description="The boc of the message in b64 encoded format")
    desitnation: AddressLike = Field(..., description="The destination address of the message")
    amount: int = Field(..., description="Transfer amount in nanoTON")


class TicTonAsyncClient:
    def __init__(
        self,
        metadata: OracleMetadata,
        toncenter: AsyncTonCenterClientV3,
        oracle_addr: AddressLike,
        mnemonics: Optional[str] = None,
        wallet_version: Literal["v2r1", "v2r2", "v3r1", "v3r2", "v4r1", "v4r2", "hv2"] = "v4r2",
        threshold_price: float = 0.7,
        *,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.wallet = None
        if mnemonics is not None:
            _, _, _, self.wallet = Wallets.from_mnemonics(mnemonics.split(" "), wallet_version)  # type: ignore
        self.oracle = PyAddress(oracle_addr)
        if logger is None:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
            console_handler = logging.StreamHandler()
            self.logger.addHandler(console_handler)
        else:
            self.logger = logger

        self.toncenter = toncenter

        self.threshold_price = threshold_price
        self.metadata = metadata

        self.logger.info("TicTonAsyncClient initialized")

    @classmethod
    async def init(
        cls: Type[TicTonAsyncClient],
        mnemonics: Union[Literal["auto", "unset"], str] = "auto",
        oracle_addr: Optional[str] = None,
        toncenter_api_key: Optional[str] = None,
        wallet_version: Literal["v2r1", "v2r2", "v3r1", "v3r2", "v4r1", "v4r2", "hv2"] = "v4r2",
        threshold_price: float = 0.01,
        *,
        testnet: bool = True,
        logger: Optional[logging.Logger] = None,
        qps: Optional[float] = None,
    ) -> TicTonAsyncClient:
        """
        Parameters
        ----------
        mnemonics : Union[Literal["auto", "unset"], str]
            The mnemonics of the user's wallet, if "auto", the mnemonics will be read from the environment variable TICTON_WALLET_MNEMONICS, if "unset", the mnemonics will be set to None. Otherwise, the mnemonics will be set to the given value.
        oracle_addr : Optional[str]
            The address of the oracle contract
        toncenter_api_key : Optional[str]
            The api key of the toncenter
        wallet_version : Literal["v2r1", "v2r2", "v3r1", "v3r2", "v4r1", "v4r2", "hv2"]
            The version of the wallet
        threshold_price : float
            The threshold price of the position
        testnet : bool
            Whether to use testnet or mainnet
        """
        assert mnemonics in {"auto", "unset"} or isinstance(mnemonics, str), "mnemonics must be a string or 'auto' or 'unset'"
        if mnemonics == "auto":
            phrase = getenv("TICTON_WALLET_MNEMONICS", None)
        elif mnemonics == "unset":
            phrase = None
        else:
            phrase = mnemonics

        wallet_version = getenv("TICTON_WALLET_VERSION", wallet_version)  # type: ignore
        oracle_addr_str = getenv("TICTON_ORACLE_ADDRESS", oracle_addr)
        toncenter_api_key = getenv("TICTON_TONCENTER_API_KEY", toncenter_api_key)
        threshold_price = float(getenv("TICTON_THRESHOLD_PRICE", threshold_price))
        assert oracle_addr_str is not None, "oracle_addr must be provided, you can either pass it as a parameter or set TICTON_ORACLE_ADDRESS environment variable"

        toncenter = get_client(
            version="v3",
            network="testnet" if testnet else "mainnet",
            api_key=toncenter_api_key,
            qps=qps,
        )

        metadata = await cls.get_oracle_metadata(toncenter, oracle_addr_str)

        return cls(
            metadata=metadata,
            toncenter=toncenter,
            mnemonics=phrase,
            oracle_addr=oracle_addr_str,
            wallet_version=wallet_version,
            threshold_price=threshold_price,
            logger=logger,
        )

    @classmethod
    async def get_oracle_metadata(
        cls: Type[TicTonAsyncClient],
        toncenter: AsyncTonCenterClientV3,
        oracle_addr: str,
    ) -> OracleMetadata:
        result = await toncenter.run_get_method(RunGetMethodRequest(address=oracle_addr, method="getOracleData", stack=[]))
        return OracleMetadataDecoder().decode(result)

    async def sync_oracle_metadata(self):
        self.metadata = await self.get_oracle_metadata(self.toncenter, self.oracle.to_string())

    async def _convert_price(self, price: float) -> FixedFloat:
        """
        Adjusts the given price by scaling it to match the decimal difference between the quote and base assets in a token pair.
        """
        assert price > 0, "price must be greater than 0"
        price = float(price)
        return FixedFloat(price) * 10**self.metadata.quote_asset_decimals / 10**self.metadata.base_asset_decimals

    async def _convert_fixedfloat_to_price(self, price: FixedFloat) -> float:
        """
        Adjusts the given price by scaling it to match the decimal difference between the quote and base assets in a token pair.
        """
        assert isinstance(price, FixedFloat), "price must be a FixedFloat"
        return price.to_float() * 10**self.metadata.base_asset_decimals / 10**self.metadata.quote_asset_decimals

    def assert_wallet_exists(self):
        assert self.wallet is not None, "if you want to run tick, ring, or wind, you must provide the mnemonics. Otherwise, only dry_run mode is available."

    async def _get_user_balance(self, owner_address: AddressLike) -> Tuple[Decimal, Decimal]:
        """
        get the user's balance of baseAsset and quoteAsset in nanoTON

        Returns
        -------
        base_asset_balance : Decimal
            The balance of baseAsset in nanoTON
        quote_asset_balance : Decimal
            The balance of quoteAsset in nanoTON
        """

        async def _get_balance(master_address: PyAddress, account_address: PyAddress) -> Decimal:

            if master_address == PyAddress("0:0000000000000000000000000000000000000000000000000000000000000000"):
                account = await self.toncenter.get_account(GetAccountRequest(address=account_address.to_string()))
                return Decimal(account.balance)
            else:
                jetton = await self.toncenter.get_jetton_wallets(
                    GetSpecifiedJettonWalletRequest(
                        owner_address=account_address.to_string(),
                        jetton_address=master_address.to_string(),
                    )
                )
                assert jetton is not None, "jetton wallet does not found"
                return Decimal(jetton.balance)

        base_asset_balance, quote_asset_balance = await self.toncenter.multicall(
            _get_balance(
                self.metadata.base_asset_address,  # type: ignore
                PyAddress(owner_address),
            ),
            _get_balance(
                self.metadata.quote_asset_address,  # type: ignore
                PyAddress(owner_address),
            ),
        )

        if isinstance(base_asset_balance, AssertionError):
            warnings.warn(f"your base asset balance is not found. reason: {base_asset_balance}")
            base_asset_balance = Decimal(0)
        if isinstance(quote_asset_balance, AssertionError):
            warnings.warn(f"your quote asset balance is not found. reason: {quote_asset_balance}")
            quote_asset_balance = Decimal(0)

        return base_asset_balance, quote_asset_balance

    async def _send(
        self,
        to_address: str,
        amount: int,
        seqno: int,
        body: Cell,
    ):
        """
        _send will send the given amount of tokens to to_address, if dry_run is set to True, it will
        call toncenter simulation api, otherwise it will send the transaction to the network directly.

        Parameters
        ----------
        amount : int
            The amount of TON to be sent
        seqno : int
            The seqno of user's wallet
        body : Cell
            The body of the transaction
        dry_run : bool
            Whether to call toncenter simulation api or not
        """
        self.assert_wallet_exists()
        query = self.wallet.create_transfer_message(  # type: ignore
            to_addr=to_address,
            amount=amount,
            seqno=seqno,
            payload=body,
        )
        boc: str = bytes_to_b64str(query["message"].to_boc(False))
        result = await self.toncenter.send_message(ExternalMessage(boc=boc))
        return result

    async def _estimate_from_oracle_get_method(
        self,
        alarm_address: AddressLike,
        buy_num: int,
        new_price: int,
    ):
        result = await self.toncenter.run_get_method(
            RunGetMethodRequest(
                address=alarm_address,
                method="getEstimate",
                stack=[
                    {"type": "num", "value": buy_num},
                    {"type": "num", "value": new_price},
                ],
            )
        )
        estimate_data = EstimateDataDecoder().decode(result)
        return (
            estimate_data.can_buy,
            estimate_data.need_baseAsset_amount,
            estimate_data.need_quote_asset_amount,
        )

    async def get_alarm_address(self, alarm_id: int) -> PyAddress:
        result = await self.toncenter.run_get_method(
            RunGetMethodRequest(
                address=self.oracle.to_string(),
                method="getAlarmAddress",
                stack=[
                    GetMethodParameterInput(type="num", value=alarm_id),
                ],
            )
        )
        return AlarmAddressDecoder().decode(result)

    async def get_address_state(self, address: PyAddress) -> str:
        result = await self.toncenter.get_account(GetAccountRequest(address=address))  # type: ignore
        return result.status

    async def _estimate_wind(self, alarm_id: int, buy_num: int, new_price: float):
        alarm_address = await self.get_alarm_address(alarm_id)
        alarm_status = await self.get_address_state(alarm_address)
        assert alarm_status == "active", "alarm is not active"

        alarm_metadata = await self.get_alarm_metadata(alarm_address)

        new_price_ff = await self._convert_price(new_price)
        old_price_ff = FixedFloat(alarm_metadata.base_asset_price, skip_scale=True)
        price_delta = abs(new_price_ff - old_price_ff)

        if price_delta < self.threshold_price:
            return None, None, alarm_metadata

        (
            can_buy,
            need_base_asset,
            need_quote_asset,
        ) = await self._estimate_from_oracle_get_method(alarm_address.to_string(), buy_num, int(new_price_ff.raw_value))

        return (
            can_buy,
            (Decimal(need_base_asset), Decimal(need_quote_asset)),
            alarm_metadata,
        )

    async def _must_afford(
        self,
        wallet_address: AddressLike,
        need_base_asset: Decimal,
        need_quote_asset: Decimal,
    ):
        base_asset_balance, quote_asset_balance = await self._get_user_balance(wallet_address)
        if need_base_asset > base_asset_balance or need_quote_asset > quote_asset_balance:
            raise Exception(
                f"expected base asset: {need_base_asset / 10 ** self.metadata.base_asset_decimals}, quote asset: {need_quote_asset / 10 ** self.metadata.quote_asset_decimals}, but got base asset: {base_asset_balance/ 10 ** self.metadata.base_asset_decimals}, quote asset: {quote_asset_balance/ 10 ** self.metadata.quote_asset_decimals}"
            )

    async def get_alarm_metadata(self, alarm_address: PyAddress) -> AlarmMetadata:
        """
        get the alarm info
        """
        result = await self.toncenter.run_get_method(RunGetMethodRequest(address=alarm_address.to_string(), method="getAlarmMetadata", stack=[]))
        return AlarmMetadataDecoder().decode(result)  # type: ignore

    async def check_alarms(self, alarm_id_list: List[int]):
        self.logger.info("Checking Alarms State")

        address_list = await self.toncenter.multicall([self.get_alarm_address(alarm_id) for alarm_id in alarm_id_list])

        # get alarm state
        state_list = await self.toncenter.multicall([self.get_address_state(address) for address in address_list])

        # update alarm dict
        alarm_dict = {}
        for alarm_id, alarm_address, alarm_state in zip(alarm_id_list, address_list, state_list):
            alarm_dict[alarm_id] = {}
            alarm_dict[alarm_id]["state"] = alarm_state
            alarm_dict[alarm_id]["address"] = alarm_address

        return alarm_dict

    async def get_jetton_wallet_address(self, owner_address: str, jetton_address: str) -> AddressLike:
        """
        get_jetton_wallet tries to get the jetton wallet info from the oracle contract or toncenter,
        if calculated is True, it will call getJettonWallets method from oracle contract, otherwise it will call getWallet method from toncenter
        """

        result = await self.toncenter.run_get_method(
            RunGetMethodRequest(
                address=jetton_address,
                method="get_wallet_address",
                stack=[{"type": "addr", "value": owner_address}],
            )
        )
        decoded = JettonWalletAddressDecoder().decode(result)
        return decoded.wallet_address

    async def _action_check(self, dry_run: bool, wallet_addr_override: Optional[AddressLike] = None):
        if self.wallet is None and dry_run == False:
            raise Exception("if you want to run tick, ring, or wind, you must provide the mnemonics. Otherwise, only dry_run mode is available.")

        assert (dry_run == False and self.wallet is not None) or (
            dry_run == True and wallet_addr_override is not None and isinstance(wallet_addr_override, (str, PyAddress))
        ), "wallet_addr_override must be provided in dry_run mode"

    @overload
    async def tick(
        self,
        price: float,
        dry_run: Literal[False] = False,
        *,
        timeout: int = 1000,
        extra_ton: float = 0.1,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> SentMessage:
        """
        Sending a tick message to the oracle, return message hash
        """

    @overload
    async def tick(
        self,
        price: float,
        dry_run: Literal[True] = True,
        *,
        timeout: int = 1000,
        extra_ton: float = 0.1,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> DryRunResult:
        """
        Sending a tick message to the oracle in dry_run mode, return message boc
        """

    async def tick(
        self,
        price: float,
        dry_run: bool = False,
        *,
        timeout: int = 1000,
        extra_ton: float = 0.1,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ):
        """
        tick will open a position with the given price and timeout, the total amount
        of baseAsset and quoteAsset will be calculated automatically.

        Parameters
        ----------
        price : float
            The price of the position quoteAsset/baseAsset
        timeout : int
            The timeout of the position in seconds
        extra_ton : float
            The extra ton to be sent to the oracle
        dry_run : bool
            Whether to call toncenter simulation api or not
        wallet_addr_override : Optional[str]
            it is useful when mnemonics is not provided, you can override the wallet address with this parameter
            only works when dry_run is set to True

        Examples
        --------
        Assume the token pair is TON/USDT, the price is 2.5 USDT per TON

        >>> client = TicTonAsyncClient(...)
        >>> await client.init()
        >>> await client.tick(2.5)
        """
        assert extra_ton >= 0.1, "extra_ton must be greater than or equal to 0.1"
        assert price > 0, "price must be greater than 0"
        await self._action_check(dry_run, wallet_addr_override)

        expire_at = int(time.time()) + timeout
        price = round(price, self.metadata.quote_asset_decimals)
        base_asset_price = await self._convert_price(price)
        quote_asset_transfered = FixedFloat(to_token(price, self.metadata.quote_asset_decimals))
        forward_ton_amount = quote_asset_transfered / base_asset_price + to_token(extra_ton, self.metadata.base_asset_decimals)
        base_asset_price = int(base_asset_price.raw_value)
        quote_asset_transfered = quote_asset_transfered.to_float()
        forward_ton_amount = int(round(forward_ton_amount.to_float(), 0))
        gas_fee = int(0.13 * 10**9)

        forward_info = begin_cell().store_uint(0, 8).store_uint(expire_at, 256).store_uint(base_asset_price, 256).end_cell()

        my_wallet_address = PyAddress(self.wallet.address.to_string() if self.wallet is not None else wallet_addr_override)  # type: ignore
        assert my_wallet_address is not None, "wallet address is not found"
        await self._must_afford(my_wallet_address, Decimal(forward_ton_amount + gas_fee), Decimal(quote_asset_transfered))  # type: ignore

        # jetton transfer
        body = (
            begin_cell()
            .store_uint(0xF8A7EA5, 32)
            .store_uint(0, 64)
            .store_coins(quote_asset_transfered)
            .store_address(self.oracle)
            .store_address(my_wallet_address)
            .store_bit(False)
            .store_coins(forward_ton_amount)
            .store_ref(forward_info)
            .end_cell()
        )

        jetton_wallet = await self.toncenter.get_jetton_wallets(
            GetSpecifiedJettonWalletRequest(
                owner_address=my_wallet_address,  # type: ignore
                jetton_address=self.metadata.quote_asset_address,
            )
        )

        wallet_info = await self.toncenter.get_wallet(GetWalletRequest(address=my_wallet_address))  # type: ignore

        assert jetton_wallet is not None, f"jetton wallet does not found, you may need to get some token to initialize the jetton wallet"
        assert wallet_info.seqno is not None, "seqno is not found"

        if dry_run:
            return DryRunResult(
                boc=bytes_to_b64str(body.to_boc(False)),
                desitnation=jetton_wallet.address,
                amount=forward_ton_amount + gas_fee,
            )

        result = await self._send(
            to_address=jetton_wallet.address.to_string(),  # type: ignore
            amount=forward_ton_amount + gas_fee,
            seqno=wallet_info.seqno,
            body=body,
        )

        args = [
            price,
            token_to_float(forward_ton_amount + gas_fee, self.metadata.base_asset_decimals),
            token_to_float(quote_asset_transfered, self.metadata.quote_asset_decimals),
        ]
        log_info = ("Tick message successfully sent, tick price: {}, spend base asset: {}, spend quote asset: {}").format(*args)
        self.logger.info(log_info)

        return result

    @overload
    async def ring(
        self,
        alarm_id: int,
        dry_run: Literal[False] = False,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> SentMessage:
        """
        ring will close the position with the given alarm_id
        """

    @overload
    async def ring(
        self,
        alarm_id: int,
        dry_run: Literal[True] = True,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> DryRunResult:
        """
        ring will close the position with the given alarm_id in dry_run mode
        """

    async def ring(
        self,
        alarm_id: int,
        dry_run: bool = False,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ):
        """
        ring will close the position with the given alarm_id

        Parameters
        ----------
        alarm_id : int
            The alarm_id of the position to be closed
        dry_run : bool
            Whether to call toncenter simulation api or not
        wallet_addr_override : Optional[str]
            it is useful when mnemonics is not provided, you can override the wallet address with this parameter
            only works when dry_run is set to True

        Examples
        --------
        >>> client = TicTonAsyncClient.init(...)
        >>> await client.ring(123)
        """
        await self._action_check(dry_run, wallet_addr_override)
        my_wallet_address = PyAddress(self.wallet.address.to_string() if self.wallet is not None else wallet_addr_override)  # type: ignore

        alarm_address = await self.get_alarm_address(alarm_id)
        alarm_state = await self.get_address_state(alarm_address)
        assert alarm_state == "active", "Ring: alarm is not exist"
        wallet = await self.toncenter.get_wallet(GetWalletRequest(address=my_wallet_address))  # type: ignore
        assert wallet.seqno is not None, "Ring: seqno is not found in wallet info"
        gas_fee = int(0.35 * 10**9)
        body = begin_cell().store_uint(0xC3510A29, 32).store_uint(1, 257).store_uint(alarm_id, 257).end_cell()  # query_id cannot be 0

        if dry_run:
            return DryRunResult(
                boc=bytes_to_b64str(body.to_boc(False)),
                desitnation=self.oracle,  # type: ignore
                amount=gas_fee,
            )
        result = await self._send(
            to_address=self.oracle.to_string(),
            amount=gas_fee,
            seqno=wallet.seqno,
            body=body,
        )

        args = [alarm_id]
        log_info = "Ring message successfully sent, alarm id: {}".format(*args)
        self.logger.info(log_info)

        return result

    @overload
    async def wind(
        self,
        alarm_id: int,
        buy_num: int,
        new_price: float,
        skip_estimate: bool = False,
        need_quote_asset: Optional[Decimal] = None,
        need_base_asset: Optional[Decimal] = None,
        dry_run: Literal[False] = False,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> SentMessage:
        """
        wind will arbitrage the position with the given alarm_id, buy_num and new_price, return message hash
        """

    @overload
    async def wind(
        self,
        alarm_id: int,
        buy_num: int,
        new_price: float,
        skip_estimate: bool = False,
        need_quote_asset: Optional[Decimal] = None,
        need_base_asset: Optional[Decimal] = None,
        dry_run: Literal[True] = True,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ) -> DryRunResult:
        """
        wind will arbitrage the position with the given alarm_id, buy_num and new_price in dry_run mode, return message boc
        """

    async def wind(
        self,
        alarm_id: int,
        buy_num: int,
        new_price: float,
        skip_estimate: float = False,
        need_quote_asset: Optional[Decimal] = None,
        need_base_asset: Optional[Decimal] = None,
        dry_run: bool = False,
        *,
        wallet_addr_override: Optional[AddressLike] = None,
        **kwargs,
    ):
        """
        wind will arbitrage the position with the given alarm_id, buy_num and new_price

        Parameters
        ----------
        alarm_id : int
            The alarm_id of the position to be arbitrage
        buy_num : int
            The number of tokens to be bought, at least 1.
        new_price : float
            The new price of the position quoteAsset/baseAsset
        dry_run : bool
            Whether to call toncenter simulation api or not

        Examples
        --------
        Assume the token pair is TON/USDT, the price is 2.5 USDT per TON. The position is opened with 1 TON and 2.5 USDT with index 123.
        The new price is 5 USDT per TON, the buy_num is 1.

        >>> client = TicTonAsyncClient.init(...)
        >>> await client.wind(123, 1, 5)
        """
        await self._action_check(dry_run, wallet_addr_override)
        assert new_price > 0, "new_price must be greater than 0"
        assert isinstance(buy_num, int), "buy_num must be an int"
        assert buy_num > 0, "buy_num must be greater than 0"

        my_wallet_address = PyAddress(self.wallet.address.to_string() if self.wallet is not None else wallet_addr_override)  # type: ignore

        new_price_ff = await self._convert_price(new_price)

        if skip_estimate:
            assert need_base_asset is not None, "need_base_asset must be provided"
            assert need_quote_asset is not None, "need_quote_asset must be provided"
        else:
            can_buy, need_asset_tup, _ = await self._estimate_wind(alarm_id, buy_num, new_price)
            assert can_buy, "Buy num is too large"
            assert need_asset_tup is not None, "The price difference is smaller than threshold price"

            need_base_asset, need_quote_asset = need_asset_tup

        gas_fee = int(0.5 * 10**9)
        forward_ton_amount = int(need_base_asset) + gas_fee

        await self._must_afford(my_wallet_address, Decimal(need_base_asset + gas_fee), need_quote_asset)  # type: ignore

        forward_info = begin_cell().store_uint(1, 8).store_uint(alarm_id, 256).store_uint(buy_num, 32).store_uint(int(new_price_ff.raw_value), 256).end_cell()

        body = (
            begin_cell()
            .store_uint(0xF8A7EA5, 32)
            .store_uint(0, 64)
            .store_coins(int(need_quote_asset))
            .store_address(self.oracle)
            .store_address(my_wallet_address)
            .store_bit(False)
            .store_coins(forward_ton_amount)
            .store_ref(forward_info)
            .end_cell()
        )

        jetton_wallet = await self.toncenter.get_jetton_wallets(
            GetSpecifiedJettonWalletRequest(
                owner_address=my_wallet_address,  # type: ignore
                jetton_address=self.metadata.quote_asset_address,
            )
        )

        assert jetton_wallet is not None, "jetton wallet does not found"

        if dry_run:
            return DryRunResult(
                boc=bytes_to_b64str(body.to_boc(False)),
                desitnation=jetton_wallet.address,
                amount=forward_ton_amount + gas_fee,
            )

        wallet_info = await self.toncenter.get_wallet(GetWalletRequest(address=my_wallet_address))  # type: ignore
        assert wallet_info.seqno is not None, "seqno is not found in wallet info"

        result = await self._send(
            to_address=jetton_wallet.address.to_string(),  # type: ignore
            amount=forward_ton_amount + gas_fee,
            seqno=wallet_info.seqno,
            body=body,
        )

        args = [
            alarm_id,
            buy_num,
            new_price,
            token_to_float(need_base_asset, self.metadata.base_asset_decimals),
            token_to_float(need_quote_asset, self.metadata.quote_asset_decimals),
        ]
        log_info = ("Wind message successfully sent, alarm id: {}, buy num: {}, wind price: {}, spend base asset: {}, spend quote asset: {}").format(*args)
        self.logger.info(log_info)

        return result

    async def _validate_subscribe_param(
        self,
        start_lt: Union[int, Literal["latest", "oldest"]],
        interval: Union[int, float],
        limit: int,
    ) -> SubscribeParam:
        # Check start_lt
        assert isinstance(start_lt, int) or start_lt in [
            "latest",
            "oldest",
        ], "start_lt must be an int or 'latest' or 'oldest'"
        # Default option is "oldest"
        begin_lt = None
        if isinstance(start_lt, int):
            begin_lt = start_lt
        if start_lt == "latest":
            latest_txs, _ = await self.toncenter.get_transactions(
                GetTransactionsRequest(
                    account=self.oracle.to_string(),
                    limit=1,
                    sort="desc",
                )
            )
            begin_lt = latest_txs[0].lt if len(latest_txs) == 1 else None
        return SubscribeParam(
            start_lt=begin_lt,
            interval=interval,
            limit=limit,
            offset=0,
            account=self.oracle.to_string(),
        )

    async def subscribe(
        self,
        on_tick_success: Callable[[OnTickSuccessParams], Coroutine[Any, Any, None]] = handle_noop,
        on_wind_success: Callable[[OnWindSuccessParams], Coroutine[Any, Any, None]] = handle_noop,
        on_ring_success: Callable[[OnRingSuccessParams], Coroutine[Any, Any, None]] = handle_noop,
        start_lt: Union[int, Literal["latest", "oldest"]] = "oldest",
        interval: Union[int, float] = 2.0,
        *,
        limit: int = 128,
    ):
        """
        subscribe will subscribe to the oracle's notifications and chimes, and call the corresponding callback functions when a notification or chime is received.

        Parameters
        ----------
        on_tick_success : Callable[[OnTickSuccessParams], Coroutine[Any, Any, None]]
            The callback function to be called when a JettonTransferNotification(Tick) is received

        on_wind_success : Callable[[OnWindSuccessParams], Coroutine[Any, Any, None]]
            The callback function to be called when a chronoShift is received

        on_ring_success : Callable[[OnRingSuccessParams], Coroutine[Any, Any, None]]
            The callback function to be called when a chime is received

        start_lt : Optional[int]
            The lt to start from, if None, the oldest lt will be used

        interval : float
            The interval of the subscription in seconds, default is 2.0. If the runtime of the callback function is longer than the interval, the next subscription will run immediately after the callback function is finished.

        limit : int
            The limit of the subscription, default is 128. The maximum value is 128.
        """
        params = await self._validate_subscribe_param(start_lt, interval, limit)

        callbacks = {
            JettonMessage.TransferNotification.OPCODE: handle_notification,
            TicTonMessage.Chronoshift.OPCODE: handle_chronoshift,
            TicTonMessage.Chime.OPCODE: handle_chime,
        }

        while True:
            start_utime = time.monotonic()
            txs, _ = await self.toncenter.get_transactions(
                GetTransactionsRequest(
                    account=self.oracle.to_string(True),
                    start_lt=params.start_lt,
                    limit=params.limit,
                    offset=params.offset,
                    sort="asc",
                )
            )

            params.offset += len(txs)

            for tx in txs:
                try:
                    msg = tx.in_msg
                    if msg.message_content is None:
                        continue
                    cs = CellSlice(msg.message_content.body)
                    opcode = get_opcode(cs.preload_uint(32))
                    if opcode == "0x00000000":  # Comment Message
                        continue

                    handle_func = callbacks.get(opcode, handle_noop)
                    await handle_func(
                        client=self.toncenter,
                        body=cs,
                        tx=tx,
                        on_tick_success=on_tick_success,
                        on_wind_success=on_wind_success,
                        on_ring_success=on_ring_success,
                    )
                except:
                    pass

            end_utime = time.monotonic()
            runtime = end_utime - start_utime
            sleep_time = max(params.interval - runtime, 0)
            self.logger.debug(f"Sleeping for {sleep_time} seconds")
            await asyncio.sleep(sleep_time)
