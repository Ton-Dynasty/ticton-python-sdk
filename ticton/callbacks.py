from typing import Callable, Coroutine, Optional

from pydantic import BaseModel, Field
from pytoncenter import AsyncTonCenterClientV3
from pytoncenter.extension.message import JettonMessage
from pytoncenter.utils import get_opcode
from pytoncenter.v3.models import *
from tonpy import CellSlice

from .arithmetic import FixedFloat
from .parser import TicTonMessage


class OnTickSuccessParams(BaseModel):
    tx: Transaction
    watchmaker: AddressLike
    base_asset_price: float
    new_alarm_id: int
    created_at: int

    def __str__(self):
        return f"Tick success: new_alarm_id={self.new_alarm_id}, watchmaker={self.watchmaker}, base_asset_price={self.base_asset_price}, created_at={self.created_at}"


class OnWindSuccessParams(BaseModel):
    tx: Transaction
    timekeeper: AddressLike
    alarm_id: int
    new_base_asset_price: float
    remain_scale: int
    new_alarm_id: int
    created_at: int

    def __str__(self):
        return f"Wind success: new_alarm_id={self.new_alarm_id}, alarm_id={self.alarm_id}, timekeeper={self.timekeeper}, new_base_asset_price={self.new_base_asset_price}, remain_scale={self.remain_scale}, created_at={self.created_at}"


class OnRingSuccessParams(BaseModel):
    tx: Transaction
    alarm_id: int = Field(..., description="alarm index")
    created_at: int = Field(..., description="created at")
    origin: Optional[AddressLike] = Field(None, description="origin address, maybe empty if no reward")
    receiver: Optional[AddressLike] = Field(None, description="receiver address, maybe empty if no reward")
    reward: float = Field(0.0, description="reward amount")

    def __str__(self):
        return f"Ring success: alarm_id={self.alarm_id}, origin={self.origin}, receiver={self.receiver}, reward={self.reward}, created_at={self.created_at}"


async def handle_noop(*args, **kwargs): ...


async def handle_notification(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    on_tick_success: Callable[[OnTickSuccessParams], Coroutine[Any, Any, None]],
    **kwargs,
):
    msg = JettonMessage.TransferNotification.parse(body)
    if msg.forward_payload is None:  # donate, thanks daddy
        return
    opcode = get_opcode(msg.forward_payload.preload_uint(8))
    if opcode == TicTonMessage.Tick.OPCODE:
        await _handle_tick(
            client,
            msg.forward_payload,
            tx,
            on_tick_success=on_tick_success,
            **kwargs,
        )
        return


async def _handle_tick(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    on_tick_success: Callable[[OnTickSuccessParams], Coroutine[Any, Any, None]],
    **kwargs,
):
    try:
        tick_msg = TicTonMessage.Tick.parse(body)
    except Exception as e:
        print(f"Handle tick failed: {e} ")
        return
    for candidate in tx.out_msgs:
        if candidate.message_content is None:
            continue
        out_msg_cs = CellSlice(candidate.message_content.body)
        out_opcode = get_opcode(out_msg_cs.preload_uint(32))
        if out_opcode == TicTonMessage.Tock.OPCODE:
            txs, _ = await client.get_transaction_by_message(GetTransactionByMessageRequest(direction="in", msg_hash=candidate.hash))
            assert len(txs) == 1
            tock_tx = txs[0]
            assert tock_tx.in_msg.message_content is not None
            tock_cs = CellSlice(tock_tx.in_msg.message_content.body)
            tock_msg = TicTonMessage.Tock.parse(tock_cs)
            base_asset_price = float(FixedFloat(tick_msg.base_asset_price, skip_scale=True).to_float()) * 1e3
            await on_tick_success(
                OnTickSuccessParams(
                    tx=tx,
                    watchmaker=tock_msg.watchmaker,  # type: ignore
                    base_asset_price=base_asset_price,
                    new_alarm_id=tock_msg.alarm_index,
                    created_at=tock_msg.created_at,
                )
            )
            return


async def handle_chime(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    on_wind_success: Callable[[OnWindSuccessParams], None],
    **kwargs,
):
    wind_msg = TicTonMessage.Chime.parse(body)
    new_alarm_index = None
    for candidate in tx.out_msgs:
        if candidate.message_content is None:
            continue
        out_msg_cs = CellSlice(candidate.message_content.body)
        out_opcode = get_opcode(out_msg_cs.preload_uint(32))
        if out_opcode == TicTonMessage.Tock.OPCODE:
            txs, _ = await client.get_transaction_by_message(GetTransactionByMessageRequest(direction="in", msg_hash=candidate.hash))
            if len(txs) == 0:
                return
            assert len(txs) == 1
            tock_tx = txs[0]
            if tock_tx.in_msg.message_content is None:
                continue
            tock_cs = CellSlice(tock_tx.in_msg.message_content.body)
            tock_msg = TicTonMessage.Tock.parse(tock_cs)
            new_alarm_index = tock_msg.alarm_index
            break

    if new_alarm_index is None:
        return

    await on_wind_success(
        OnWindSuccessParams(
            tx=tx,
            timekeeper=tock_msg.watchmaker,  # type: ignore
            alarm_id=wind_msg.alarm_index,
            new_base_asset_price=float(FixedFloat(wind_msg.new_base_asset_price, skip_scale=True).to_float()) * 1e3,
            remain_scale=wind_msg.remain_scale,
            new_alarm_id=new_alarm_index,
            created_at=tock_msg.created_at,
        )
    )


async def handle_chronoshift(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    on_ring_success: Callable[[OnRingSuccessParams], None],
    **kwargs,
):
    chronoshift_msg = TicTonMessage.Chronoshift.parse(body)

    reward = 0.0
    origin = None
    receiver = None
    for candidate in tx.out_msgs:
        if candidate.message_content is None:
            continue
        out_msg_cs = CellSlice(candidate.message_content.body)
        out_opcode = get_opcode(out_msg_cs.preload_uint(32))
        if out_opcode == TicTonMessage.JettonMintPartial.OPCODE:
            txs, _ = await client.get_transaction_by_message(GetTransactionByMessageRequest(direction="in", msg_hash=candidate.hash))
            assert len(txs) == 1
            jetton_mint_tx = txs[0]
            if jetton_mint_tx.in_msg.message_content is None:
                break
            jetton_mint_cs = CellSlice(jetton_mint_tx.in_msg.message_content.body)
            jetton_mint_msg = TicTonMessage.JettonMintPartial.parse(jetton_mint_cs)
            origin = jetton_mint_msg.origin
            receiver = jetton_mint_msg.receiver
            reward = float(jetton_mint_msg.amount) / 1e9

    await on_ring_success(
        OnRingSuccessParams(
            tx=tx,
            alarm_id=chronoshift_msg.alarm_index,
            created_at=chronoshift_msg.created_at,
            origin=origin,  # type: ignore
            receiver=receiver,  # type: ignore
            reward=reward,
        )
    )
