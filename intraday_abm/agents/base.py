from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from random import Random
from typing import Optional

from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side
from intraday_abm.core.order import Order


@dataclass
class Agent(ABC):
    """
    Abstrakte Basisklasse für alle Agenten.

    - id: eindeutige Agenten-ID
    - private_info: enthält Kapazität, Position, Erlöse, Imbalance etc.
    - rng: Agent-lokaler Zufallszahlengenerator
    """
    id: int
    private_info: AgentPrivateInfo
    rng: Random = field(repr=False)

    @abstractmethod
    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft zum Zeitpunkt t eine Handelsentscheidung.
        Gibt eine Order zurück oder None (keine Aktivität in diesem Schritt).
        """
        ...

    def on_trade(self, volume: float, price: float, side: Side) -> None:
        """
        Aktualisiert Marktposition und Erlöse nach einem Trade.

        Orientierung an Shinde:
        - market_position p_mar erhöht sich bei Verkäufen, verringert sich bei Käufen
        - revenue r_i,t steigt bei Verkäufen und fällt bei Käufen
        """
        if side == Side.SELL:
            # Verkauft: Position steigt, Erlöse steigen
            self.private_info.market_position += volume
            self.private_info.revenue += volume * price
        else:  # BUY
            # Gekauft: Position sinkt, „Erlös“ wird negativer (Kosten)
            self.private_info.market_position -= volume
            self.private_info.revenue -= volume * price
