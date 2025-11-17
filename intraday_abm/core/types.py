from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional



class Side(str, Enum):
    """Order-Seite im LOB."""
    BUY = "BUY"
    SELL = "SELL"


class TimeInForce(str, Enum):
    """
    Time-In-Force:
    - GTC (Good Till Cancelled): Shinde-Verhalten (Order bleibt im Buch,
      bis der Agent beim nächsten Schritt cancelt).
    - IOC (Immediate-Or-Cancel): Projekteigene Erweiterung für Tests.
    """
    GTC = "GTC"
    IOC = "IOC"


class OrderStatus(str, Enum):
    """Status einer Order während ihres Lebenszyklus."""
    ACTIVE = "ACTIVE"               # liegend im Orderbuch
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"               # vollständig ausgeführt
    CANCELLED = "CANCELLED"         # durch Agent/IOC gestrichen

@dataclass
class PublicInfo:
    """
    Öffentliche Marktinformation, die allen Agenten zur Verfügung steht.
    Angelehnt an Shinde: TOB + Day-Ahead-Preis.
    """
    best_bid: Optional[float]
    best_ask: Optional[float]
    # Optional kannst du später noch Volume/VWAP ergänzen
    da_price: float


@dataclass
class AgentPrivateInfo:
    """
    Private Information eines Agenten (agentenspezifisch, nicht öffentlich).
    Hier nur generisch angelegt; konkrete Felder können je Agententyp variieren.
    """
    capacity: float  # z.B. verfügbare Leistung/Energie

    # Platzhalter für spätere Erweiterungen:
    # marginal_cost: float | None = None
    # forecast_error: float | None = None
    # imbalance_info_quality: float | None = None
