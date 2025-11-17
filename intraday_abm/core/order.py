from dataclasses import dataclass
from typing import Optional
from .types import Side, TimeInForce, OrderStatus


@dataclass
class Order:
    """
    Repräsentiert eine Limit-Order im kontinuierlichen Intraday-Markt.
    Diese Struktur ist Shinde-nah und minimal für unser Mini-Modell.

    - id:        eindeutige Order-ID
    - agent_id:  Agent, der diese Order submitted hat
    - side:      BUY oder SELL
    - product_id: Produktindex (Phase 1 = immer 0, später 0..95)
    - volume:    verbleibendes Volumen (wird durch Matching reduziert)
    - price:     Limitpreis (Pay-as-Bid → Preis der liegenden Gegenseite)
    - time:      Zeitschritt t, an dem die Order aufgegeben wurde
    - tif:       Time-in-force (GTC/IOC)
    - status:    aktueller Status der Order
    """
    id: int
    agent_id: int
    side: Side

    product_id: int = 0
    volume: float = 0.0
    price: float = 0.0

    time: int = 0
    tif: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.ACTIVE

    def __repr__(self) -> str:
        """Kurze, klare Darstellung für Debugging und Logs."""
        return (f"Order(id={self.id}, agent={self.agent_id}, side={self.side}, "
                f"vol={self.volume:.2f}, price={self.price:.2f}, "
                f"time={self.time}, tif={self.tif}, status={self.status})")


@dataclass
class Trade:
    """
    Repräsentiert einen ausgeführten Trade zwischen zwei Orders.
    - buy_order_id:  ID der beteiligten Kauforder
    - sell_order_id: ID der beteiligten Verkauforder
    - product_id:    Produkt (Phase 1 = 0)
    - price:         Ausführungspreis (Shinde: Preis der älteren Order)
    - volume:        gehandelte Menge
    - time:          Zeitschritt t
    """
    id: int
    buy_order_id: int
    sell_order_id: int

    product_id: int
    price: float
    volume: float
    time: int

    def __repr__(self) -> str:
        return (f"Trade(id={self.id}, buy={self.buy_order_id}, "
                f"sell={self.sell_order_id}, vol={self.volume:.2f}, "
                f"price={self.price:.2f}, time={self.time})")
