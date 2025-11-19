from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional


class Side(Enum):
    """Orderrichtung im Orderbuch."""
    BUY = auto()
    SELL = auto()


class TimeInForce(Enum):
    """Gültigkeitsdauer einer Order."""
    GTC = auto()  # Good till cancelled
    IOC = auto()  # Immediate or cancel


@dataclass
class PublicInfo:
    """
    Öffentliche Marktinformation, die allen Agenten zugänglich ist.
    Angelehnt an Shinde: TOB + Day-Ahead-Preis.
    """
    best_bid: Optional[float]
    best_ask: Optional[float]
    da_price: float


@dataclass
class AgentPrivateInfo:
    """
    Agentenspezifische, nicht öffentliche Information.
    Hier zunächst nur Kapazität, später erweiterbar (Kosten, Forecasts, etc.).
    """
    capacity: float
