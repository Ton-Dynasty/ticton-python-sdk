from pytoncenter.extension.message import BaseMessage
from pytoncenter.address import Address
from pytoncenter.utils import get_opcode
from tonpy import CellSlice


class TicTonMessage:
    class Tick(BaseMessage["Tick"]):
        OPCODE = "0x00000000"

        def __init__(
            self,
            expire_at: int,
            base_asset_price: int,
        ):
            self.expire_at = expire_at
            self.base_asset_price = base_asset_price

        @classmethod
        def _preparse(cls, cs: CellSlice) -> CellSlice:
            opcode = get_opcode(cs.load_uint(8))
            assert opcode == cls.OPCODE, f"opcode {opcode} is not {cls.OPCODE}"
            return cs

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            tick#e4366caf expireAt:uint256 baseAssetPrice:uint256 = Tick
            """
            expire_at = body.load_uint(256)
            base_asset_price = body.load_uint(256)
            return cls(
                expire_at=expire_at,
                base_asset_price=base_asset_price,
            )

    class Tock(BaseMessage["Tock"]):
        OPCODE = "0x09c0fafb"

        def __init__(
            self,
            alarm_index: int,
            scale: int,
            created_at: int,
            watchmaker: Address,
            base_asset_price: int,
        ):
            self.alarm_index = alarm_index
            self.scale = scale
            self.created_at = created_at
            self.watchmaker = watchmaker
            self.base_asset_price = base_asset_price

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            tock#09c0fafb alarmIndex:uint256 scale:uint32 createdAt:int257 watchmaker:address baseAssetPrice:int257
            """
            alarm_index = body.load_uint(256)
            scale = body.load_uint(32)
            created_at = body.load_int(257)
            watchmaker = Address(body.load_address())
            body = body.load_ref(as_cs=True)
            base_asset_price = body.load_int(257)
            return cls(
                alarm_index=alarm_index,
                scale=scale,
                created_at=created_at,
                watchmaker=watchmaker,
                base_asset_price=base_asset_price,
            )

    class Ring(BaseMessage["Ring"]):
        OPCODE = "0xc3510a29"

        def __init__(
            self,
            query_id: int,
            alarm_index: int,
        ):
            self.query_id = query_id
            self.alarm_index = alarm_index

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            ring#c3510a29 queryID:int257 alarmIndex:int257
            """
            query_id = body.load_int(257)
            alarm_index = body.load_int(257)
            return cls(
                query_id=query_id,
                alarm_index=alarm_index,
            )

    class Chime(BaseMessage["Chime"]):
        OPCODE = "0x08eb5cd4"

        def __init__(
            self,
            alarm_index: int,
            time_keeper: Address,
            new_base_asset_price: int,
            new_scale: int,
            refund_quote_asset_amount: int,
            base_asset_price: int,
            created_at: int,
            remain_scale: int,
            preserve_base_asset_amount: int,
        ):
            self.alarm_index = alarm_index
            self.time_keeper = time_keeper
            self.new_base_asset_price = new_base_asset_price
            self.new_scale = new_scale
            self.refund_quote_asset_amount = refund_quote_asset_amount
            self.base_asset_price = base_asset_price
            self.created_at = created_at
            self.remain_scale = remain_scale
            self.preserve_base_asset_amount = preserve_base_asset_amount

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            chime#08eb5cd4 alarmIndex:int257 timeKeeper:address newBaseAssetPrice:uint256 newScale:int257 refundQuoteAssetAmount:int257 baseAssetPrice:uint256 createdAt:int257 remainScale:int257 preserveBaseAssetAmount:int257
            """
            alarm_index = body.load_int(257)
            time_keeper = Address(body.load_address())
            new_base_asset_price = body.load_uint(256)
            body = body.load_ref(as_cs=True)
            new_scale = body.load_int(257)
            refund_quote_asset_amount = body.load_int(257)
            base_asset_price = body.load_uint(256)
            body = body.load_ref(as_cs=True)
            created_at = body.load_int(257)
            remain_scale = body.load_int(257)
            preserve_base_asset_amount = body.load_int(257)
            return cls(
                alarm_index=alarm_index,
                time_keeper=time_keeper,
                new_base_asset_price=new_base_asset_price,
                new_scale=new_scale,
                refund_quote_asset_amount=refund_quote_asset_amount,
                base_asset_price=base_asset_price,
                created_at=created_at,
                remain_scale=remain_scale,
                preserve_base_asset_amount=preserve_base_asset_amount,
            )

    class Chronoshift(BaseMessage["Chronoshift"]):
        OPCODE = "0x54451598"

        def __init__(
            self,
            query_id: int,
            alarm_index: int,
            created_at: int,
            watchmaker: Address,
            base_asset_price: int,
            remain_scale: int,
            remain_base_asset_scale: int,
            remain_quote_asset_scale: int,
            extra_base_asset_amount: int,
            extra_quote_asset_amount: int,
        ):
            self.query_id = query_id
            self.alarm_index = alarm_index
            self.created_at = created_at
            self.watchmaker = watchmaker
            self.base_asset_price = base_asset_price
            self.remain_scale = remain_scale
            self.remain_base_asset_scale = remain_base_asset_scale
            self.remain_quote_asset_scale = remain_quote_asset_scale
            self.extra_base_asset_amount = extra_base_asset_amount
            self.extra_quote_asset_amount = extra_quote_asset_amount

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            chronoshift#54451598 queryID:int257 alarmIndex:int257 createdAt:int257 watchmaker:address baseAssetPrice:uint256 remainScale:int257 remainBaseAssetScale:int257 remainQuoteAssetScale:int257 extraBaseAssetAmount:int257 extraQuoteAssetAmount:int257
            """
            query_id = body.load_int(257)
            alarm_index = body.load_int(257)
            created_at = body.load_int(257)
            body = body.load_ref(as_cs=True)
            watchmaker = Address(body.load_address())
            base_asset_price = body.load_uint(256)
            remain_scale = body.load_int(257)
            body = body.load_ref(as_cs=True)
            remain_base_asset_scale = body.load_int(257)
            remain_quote_asset_scale = body.load_int(257)
            extra_base_asset_amount = body.load_int(257)
            body = body.load_ref(as_cs=True)
            extra_quote_asset_amount = body.load_int(257)
            return cls(
                query_id=query_id,
                alarm_index=alarm_index,
                created_at=created_at,
                watchmaker=watchmaker,
                base_asset_price=base_asset_price,
                remain_scale=remain_scale,
                remain_base_asset_scale=remain_base_asset_scale,
                remain_quote_asset_scale=remain_quote_asset_scale,
                extra_base_asset_amount=extra_base_asset_amount,
                extra_quote_asset_amount=extra_quote_asset_amount,
            )

    class JettonMintPartial(BaseMessage["JettonMintPartial"]):
        OPCODE = "0x89b71d09"

        def __init__(
            self,
            origin: Address,
            receiver: Address,
            amount: int,
        ):
            self.origin = origin
            self.receiver = receiver
            self.amount = amount

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            jetton_mint#89b71d09 origin:address receiver:address amount:int257 custom_payload:Maybe ^cell forward_ton_amount:coins forward_payload:remainder<slice>
            """
            origin = Address(body.load_address())
            receiver = Address(body.load_address())
            amount = body.load_int(257)
            return cls(
                origin=origin,
                receiver=receiver,
                amount=amount,
            )
