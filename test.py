from pytoncenter import get_client, AsyncTonCenterClientV3
from pytoncenter.v3.models import *
from pytoncenter.extension.message import BaseMessage, JettonMessage
from pytoncenter.address import Address
from pytoncenter.utils import get_opcode
from typing import Optional, Callable
from tonpy import CellSlice
import asyncio
from test_parser import TicTonMessage
from pydantic import BaseModel


class OnTickSuccessParams(BaseModel):
    pass


class OnWindSuccessParams(BaseModel):
    pass


class OnRingSuccessParams(BaseModel):
    pass


async def _handle_tick(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    tock_msg: TicTonMessage.Tock,
    on_tick_success: Callable[[OnTickSuccessParams], None],
    **kwargs,
):
    tick_msg = TicTonMessage.Tick.parse(body)
    pass


async def _handle_chime(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    tock_msg: TicTonMessage.Tock,
    on_wind_success: Callable[[OnWindSuccessParams], None],
    **kwargs,
):
    wind_msg = TicTonMessage.Chime.parse(body)
    pass


async def _handle_chronoshift(
    client: AsyncTonCenterClientV3,
    body: CellSlice,
    tx: Transaction,
    jetton_mint_msg: TicTonMessage.JettonMint,
    on_ring_success: Callable[[OnRingSuccessParams], None],
    **kwargs
):
    chronoshift_msg = TicTonMessage.Chronoshift.parse(body)
    pass


async def handle_tock(
    client: AsyncTonCenterClientV3, 
    body: CellSlice, 
    tx: Transaction,
    on_tick_success: Callable[[OnTickSuccessParams],None], 
    on_wind_success: Callable[[OnWindSuccessParams],None], 
    **kwargs,
):
    tock_msg = TicTonMessage.Tock.parse(body)
    if tx.in_msg is None:
        return
    txs = await client.get_adjacent_transactions(
        GetAdjacentTransactionsRequest(
            hash=tx.in_msg.hash,
            direction="in",
            limit=1,
        )
    )
    if len(txs) == 0:
        return
    prev_tx = txs[0]
    if prev_tx.in_msg is None:
        return
    if prev_tx.in_msg.message_content is None:
        return
    prev_cs = CellSlice(prev_tx.in_msg.message_content.body)
    opcode = get_opcode(prev_cs.preload_uint(32))
    if opcode == TicTonMessage.Tick.OPCODE:
        await _handle_tick(client, prev_cs, prev_tx, tock_msg,on_tick_success, **kwargs)
        return
    if opcode == TicTonMessage.Chime.OPCODE:
        await _handle_chime(client, prev_cs, prev_tx, tock_msg,on_wind_success, **kwargs)
        return


async def handle_jetton_mint(
    client: AsyncTonCenterClientV3, body: CellSlice, tx: Transaction,on_ring_success: Callable[[OnRingSuccessParams], None], **kwargs
):
    jetton_mint_msg = TicTonMessage.JettonMint.parse(body)
    if tx.in_msg is None:
        return
    txs = await client.get_adjacent_transactions(
        GetAdjacentTransactionsRequest(
            hash=tx.in_msg.hash,
            direction="in",
            limit=1,
        )
    )
    if len(txs) == 0:
        return
    prev_tx = txs[0]
    if prev_tx.in_msg is None:
        return
    if prev_tx.in_msg.message_content is None:
        return
    prev_cs = CellSlice(prev_tx.in_msg.message_content.body)
    opcode = get_opcode(prev_cs.preload_uint(32))
    if opcode == TicTonMessage.Chronoshift.OPCODE:
        await _handle_chronoshift(client, prev_cs, prev_tx, jetton_mint_msg, on_ring_success, **kwargs)


async def handle_chronoshift_without_jetton_mint(
    client: AsyncTonCenterClientV3, body: CellSlice, tx: Transaction,on_ring_success: Callable[[OnRingSuccessParams], None], **kwargs
):
    chronoshift_msg = TicTonMessage.Chronoshift.parse(body)
    for msg in tx.out_msgs:
        if msg.message_content is None:
            continue
        cs = CellSlice(msg.message_content.body)
        opcode = get_opcode(cs.preload_uint(32))
        if opcode == TicTonMessage.JettonMint:
            # These transactions will be handled by handle_jetton_mint
            # so we don't need to handle them here
            return
    # TODO:


# async def handle_jetton_internal_transfer(client: AsyncTonCenterClientV3,body: CellSlice, tx: Transaction, **kwargs) -> None:
#     msg = JettonMessage.InternalTransfer.parse(body)
#     if msg.forward_payload is None: # donate, thanks daddy
#         return
#     opcode = get_opcode(msg.forward_payload.preload_uint(32))
#     if opcode == TicTonMessage.Tick.OPCODE:
#         await handle_tick(msg.forward_payload, tx, **kwargs)
#         if len(tx.out_msgs)== 0:
#             return
#         for out_msg in tx.out_msgs:
#             if out_msg.message_content is None:
#                 continue
#             cs = CellSlice(out_msg.message_content.body)
#             tock_opcode = get_opcode(cs.preload_uint(32))
#             if tock_opcode == TicTonMessage.Tock.OPCODE:
#                 # get transaction
#                 tock_tx = await client.get_transaction_by_message(GetTransactionByMessageRequest(
#                     direction="in",
#                     msg_hash=out_msg.message_content.hash,
#                     limit=1,
#                 ))
#                 if len(tock_tx) == 0:
#                     continue
#                 await handle_tock(client, cs, tock_tx[0], **kwargs)
#                 return


async def main():
    client = get_client(version="v3", network="testnet")
    txs = await client.get_transactions(
        GetTransactionRequest(
            account="EQBENmfrJP6KwfBBtcHaixDHYCnBcD3QGBJ6NJtY3dwXI0go"
        )
    )
    for tx in txs:
        if tx.in_msg is not None:
            print(tx.in_msg.hash)


if __name__ == "__main__":
    asyncio.run(main())
