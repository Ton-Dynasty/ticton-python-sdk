from pytoncenter.extension.message import BaseMessage
from pytoncenter.address import Address
from typing import Optional
from tonpy import CellSlice

class TicTonMessage:
    class Tick(BaseMessage["Tick"]):
        OPCODE = ""
        def __init__(
            self,
            query_id: int,
            amount: int,
            sender: Address,
            response_address: Address,
            forward_ton_amount: int,
            forward_payload: Optional[CellSlice],
        ):
            self.query_id = query_id
            self.amount = amount
            self.sender = sender
            self.response_address = response_address
            self.forward_ton_amount = forward_ton_amount
            self.forward_payload = forward_payload

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            //
            """
            query_id = body.load_uint(64)
            amount = body.load_var_int(16)
            sender = Address(body.load_address())
            response_address = Address(body.load_address())
            forward_ton_amount = body.load_var_uint(16)
            forward_payload = None if body.empty_ext() else body.load_ref(as_cs=True)
            return cls(
                query_id=query_id,
                amount=amount,
                sender=sender,
                response_address=response_address,
                forward_ton_amount=forward_ton_amount,
                forward_payload=forward_payload,
            )

    class Tock(BaseMessage["Tock"]):
        OPCODE = ""
        def __init__(
            self,
            query_id: int,
            amount: int,
            sender: Address,
            response_address: Address,
            forward_ton_amount: int,
            forward_payload: Optional[CellSlice],
        ):
            self.query_id = query_id
            self.amount = amount
            self.sender = sender
            self.response_address = response_address
            self.forward_ton_amount = forward_ton_amount
            self.forward_payload = forward_payload

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            //
            """
            query_id = body.load_uint(64)
            amount = body.load_var_int(16)
            sender = Address(body.load_address())
            response_address = Address(body.load_address())
            forward_ton_amount = body.load_var_uint(16)
            forward_payload = None if body.empty_ext() else body.load_ref(as_cs=True)
            return cls(
                query_id=query_id,
                amount=amount,
                sender=sender,
                response_address=response_address,
                forward_ton_amount=forward_ton_amount,
                forward_payload=forward_payload,
            )

    class Ring(BaseMessage["Ring"]):
        OPCODE = ""
        def __init__(
            self,
            query_id: int,
            amount: int,
            sender: Address,
            response_address: Address,
            forward_ton_amount: int,
            forward_payload: Optional[CellSlice],
        ):
            self.query_id = query_id
            self.amount = amount
            self.sender = sender
            self.response_address = response_address
            self.forward_ton_amount = forward_ton_amount
            self.forward_payload = forward_payload

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            //
            """
            query_id = body.load_uint(64)
            amount = body.load_var_int(16)
            sender = Address(body.load_address())
            response_address = Address(body.load_address())
            forward_ton_amount = body.load_var_uint(16)
            forward_payload = None if body.empty_ext() else body.load_ref(as_cs=True)
            return cls(
                query_id=query_id,
                amount=amount,
                sender=sender,
                response_address=response_address,
                forward_ton_amount=forward_ton_amount,
                forward_payload=forward_payload,
            )

    class Chime(BaseMessage["Chime"]):
        OPCODE = ""
        def __init__(
            self,
            query_id: int,
            amount: int,
            sender: Address,
            response_address: Address,
            forward_ton_amount: int,
            forward_payload: Optional[CellSlice],
        ):
            self.query_id = query_id
            self.amount = amount
            self.sender = sender
            self.response_address = response_address
            self.forward_ton_amount = forward_ton_amount
            self.forward_payload = forward_payload

        @classmethod
        def _parse(cls, body: CellSlice):
            """
            //
            """
            query_id = body.load_uint(64)
            amount = body.load_var_int(16)
            sender = Address(body.load_address())
            response_address = Address(body.load_address())
            forward_ton_amount = body.load_var_uint(16)
            forward_payload = None if body.empty_ext() else body.load_ref(as_cs=True)
            return cls(
                query_id=query_id,
                amount=amount,
                sender=sender,
                response_address=response_address,
                forward_ton_amount=forward_ton_amount,
                forward_payload=forward_payload,
            )

    class Chronoshift(BaseMessage["Chronoshift"]):
        pass
    
    class JettonMint(BaseMessage["JettonMint"]):
        pass