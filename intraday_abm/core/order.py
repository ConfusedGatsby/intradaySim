from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.core.types import Side, TimeInForce


@dataclass
class Order:
    """
    Repräsentiert eine Limit-Order im Orderbuch.
    """
    id: int
    agent_id: int
    side: Side
    price: float
    volume: float
    product_id: int
    time_in_force: TimeInForce = TimeInForce.GTC
    timestamp: Optional[int] = None  # wird vom MarketOperator gesetzt


@dataclass
class Trade:
    """
    Repräsentiert einen ausgeführten Handel.

    - price: Ausführungspreis (Pay-as-Bid -> Preis der liegenden Order)
    - volume: gehandeltes Volumen
    - buy_order_id / sell_order_id: Order-IDs
    - buy_agent_id / sell_agent_id: Agenten-IDs (für A2 wichtig)
    - time: Simulationszeitpunkt des Trades
    """
    price: float
    volume: float
    buy_order_id: int
    sell_order_id: int
    buy_agent_id: int
    sell_agent_id: int
    time: int
