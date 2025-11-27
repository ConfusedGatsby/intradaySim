from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.core.types import Side, TimeInForce


@dataclass
class Order:
    """
    Repräsentiert eine Limit-Order im Orderbuch.

    Im Multi-Produkt-Setting ist eine Order eindeutig durch
    (product_id, id) und ihren Zeitindex (timestamp) identifiziert.

    Attribute
    ---------
    id:
        Laufende Order-ID, wird vom MarketOperator vergeben.
    agent_id:
        ID des Agenten, der die Order eingestellt hat.
    side:
        BUY oder SELL.
    price:
        Limitpreis in €/MWh (Pay-as-Bid).
    volume:
        Volumen in MW (bzw. MWh je Zeitschritt – je nach Modellierung).
    product_id:
        Produkt / Lieferperiode, auf die sich die Order bezieht.
    time_in_force:
        Gültigkeitsdauer (z.B. GTC = good till cancelled).
    timestamp:
        Globaler Zeitschritt t, zu dem die Order erzeugt wurde.
    """
    id: int
    agent_id: int
    side: Side
    price: float
    volume: float
    product_id: int
    time_in_force: Optional[TimeInForce] = None
    timestamp: Optional[int] = None


@dataclass
class Trade:
    """
    Ausgeführter Handel zwischen zwei Orders (Pay-as-Bid).

    Im Multi-Produkt-Fall ist jeder Trade ebenfalls einem Produkt
    eindeutig zugeordnet.

    Attribute
    ---------
    product_id:
        Produkt / Lieferperiode des Trades.
    price:
        Ausführungspreis (Preis der liegenden Order, Pay-as-Bid).
    volume:
        Gehandeltes Volumen.
    buy_order_id / sell_order_id:
        IDs der beteiligten Orders.
    buy_agent_id / sell_agent_id:
        IDs der beteiligten Agenten (für PnL / Logging).
    time:
        Globaler Simulationszeitpunkt t des Trades.
    """
    product_id: int
    price: float
    volume: float
    buy_order_id: int
    sell_order_id: int
    buy_agent_id: int
    sell_agent_id: int
    time: int
