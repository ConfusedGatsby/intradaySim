from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .types import Side, TimeInForce


@dataclass
class Order:
    """
    Limit Order im Intraday-Markt.

    id           – eindeutige Order-ID (wird vom MarketOperator vergeben)
    agent_id     – ID des Agenten, der die Order platziert
    side         – BUY oder SELL
    price        – Limitpreis
    volume       – verbleibendes Volumen
    product_id   – Produkt (z.B. 15-Minuten-Slot)
    time         – Ankunftszeit im Markt (für FIFO auf Preislevel)
    tif          – Time-in-Force (GTC oder IOC)
    """
    id: int
    agent_id: int
    side: Side
    price: float
    volume: float
    product_id: int
    time: Optional[int] = None
    tif: TimeInForce = TimeInForce.GTC
