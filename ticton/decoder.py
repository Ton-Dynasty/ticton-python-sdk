from __future__ import annotations

from pydantic import BaseModel
from pytoncenter.address import Address
from pytoncenter.decoder import BaseDecoder, Decoder, GetMethodResultType, Types
from pytoncenter.v3.models import AddressLike


class OracleMetadata(BaseModel):
    base_asset_address: AddressLike
    quote_asset_address: AddressLike
    base_asset_decimals: int
    quote_asset_decimals: int
    min_base_asset_threshold: int
    base_asset_wallet_address: AddressLike
    quote_asset_wallet_address: AddressLike
    is_initialized: bool
    latest_base_asset_price: int
    latest_timestamp: int
    total_alarms: int


class AlarmMetadata(BaseModel):
    watchmaker_address: AddressLike
    base_asset_scale: int
    quote_asset_scale: int
    remain_scale: int
    base_asset_price: int
    base_asset_amount: int
    quote_asset_amount: int
    created_at: int
    alarm_index: int


class EstimateData(BaseModel):
    can_buy: bool
    need_baseAsset_amount: int
    need_quote_asset_amount: int


class JettonWalletAddress(BaseModel):
    wallet_address: AddressLike


class OracleMetadataDecoder(BaseDecoder):
    decoder = Decoder(
        Types.Address("base_asset_address"),
        Types.Address("quote_asset_address"),
        Types.Number("base_asset_decimals"),
        Types.Number("quote_asset_decimals"),
        Types.Number("min_base_asset_threshold"),
        Types.Address("base_asset_wallet_address"),
        Types.Address("quote_asset_wallet_address"),
        Types.Bool("is_initialized"),
        Types.Number("latest_base_asset_price"),
        Types.Number("latest_timestamp"),
        Types.Number("total_alarms"),
    )

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OracleMetadataDecoder, cls).__new__(cls)
        return cls._instance

    def decode(self, data: GetMethodResultType) -> OracleMetadata:
        result = self.decoder.decode(data)
        return OracleMetadata(**result)


class AlarmAddressDecoder(BaseDecoder):
    decoder = Decoder(
        Types.Address("alarm_address"),
    )

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlarmAddressDecoder, cls).__new__(cls)
        return cls._instance

    def decode(self, data: GetMethodResultType) -> Address:
        result = self.decoder.decode(data)
        return result["alarm_address"]


class AlarmMetadataDecoder(BaseDecoder):
    decoder = Decoder(
        Types.Address("watchmaker_address"),
        Types.Number("base_asset_scale"),
        Types.Number("quote_asset_scale"),
        Types.Number("remain_scale"),
        Types.Number("base_asset_price"),
        Types.Number("base_asset_amount"),
        Types.Number("quote_asset_amount"),
        Types.Number("created_at"),
        Types.Number("alarm_index"),
    )

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AlarmMetadataDecoder, cls).__new__(cls)
        return cls._instance

    def decode(self, data: GetMethodResultType) -> AlarmMetadata:
        result = self.decoder.decode(data)
        return AlarmMetadata(**result)


class EstimateDataDecoder(BaseDecoder):
    decoder = Decoder(
        Types.Bool("can_buy"),
        Types.Number("need_baseAsset_amount"),
        Types.Number("need_quote_asset_amount"),
    )

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EstimateDataDecoder, cls).__new__(cls)
        return cls._instance

    def decode(self, data: GetMethodResultType) -> EstimateData:
        result = self.decoder.decode(data)
        return EstimateData(**result)


class JettonWalletAddressDecoder(BaseDecoder):
    decoder = Decoder(
        Types.Address("wallet_address"),
    )

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JettonWalletAddressDecoder, cls).__new__(cls)
        return cls._instance

    def decode(self, data: GetMethodResultType) -> JettonWalletAddress:
        result = self.decoder.decode(data)
        return JettonWalletAddress(**result)
