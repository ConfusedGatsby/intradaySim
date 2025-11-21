from __future__ import annotations

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
class TopOfBook:
    """
    Top-of-Book-Information (TOB) eines Produkts.

    - best_bid_price / best_ask_price: beste Preise
    - best_bid_volume / best_ask_volume: Volumen auf dem besten Level (optional)
    """
    best_bid_price: Optional[float]
    best_bid_volume: Optional[float]
    best_ask_price: Optional[float]
    best_ask_volume: Optional[float]


@dataclass
class PublicInfo:
    """
    Öffentliche Marktinformation für alle Agenten.

    Entspricht konzeptionell s_public = (TOB, DA-Preis):
    - tob: Top-of-Book (Preis/Volumen)
    - da_price: Day-Ahead-Preis für dieses Produkt
    """
    tob: TopOfBook
    da_price: float


@dataclass
class AgentPrivateInfo:
    """
    Agentenspezifische, nicht öffentliche Information.

    Orientiert sich an den im Paper genannten Größen:
    - effective_capacity: C_{i,t}, aktuell nutzbare Kapazität
    - da_position:      p_i^{DA}, Day-Ahead-Position
    - market_position:  p^{mar}_{i,t}, laufende Intraday-Marktposition
    - revenue:          r_{i,t}, kumulierte Erlöse aus Intraday-Trades
    - imbalance:        δ_{i,t}, Imbalance (z.B. Forecast - Position)
    - est_imb_price_up / est_imb_price_down: Schätzungen von Imbalance-Preisen

    Für einfache Agents (Random/Trend) werden nur Teile davon benutzt, der Rest
    bleibt bei den Defaultwerten.
    """
    effective_capacity: float
    da_position: float = 0.0
    market_position: float = 0.0
    revenue: float = 0.0
    imbalance: float = 0.0
    est_imb_price_up: float = 0.0
    est_imb_price_down: float = 0.0
