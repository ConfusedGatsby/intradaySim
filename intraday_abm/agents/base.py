from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from random import Random
from typing import Optional

from intraday_abm.core.types import PublicInfo, AgentPrivateInfo
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
