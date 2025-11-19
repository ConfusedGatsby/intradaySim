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

    - hält eine Agenten-ID
    - besitzt private Informationen (z.B. Kapazität)
    - trifft Entscheidungen nur auf Basis von PublicInfo + eigener PrivateInfo
    """
    id: int
    private_info: AgentPrivateInfo
    rng: Random = field(repr=False)

    @abstractmethod
    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft zum Zeitpunkt t eine Handelsentscheidung.

        Gibt eine neue Order zurück oder None, wenn der Agent in diesem
        Zeitschritt nicht aktiv ist.
        """
        ...
