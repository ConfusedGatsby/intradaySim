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
    Basisklasse für alle Agenten im Intraday-Marktmodell.

    - Hält eine ID und private Information (Kapazität etc.).
    - Bekommt pro Entscheidungsschritt nur PublicInfo (TOB + DA-Preis).
    - Die konkrete Strategie wird in Subklassen implementiert.
    """
    id: int
    private_info: AgentPrivateInfo
    rng: Random = field(repr=False)

    @abstractmethod
    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft eine Handelsentscheidung zum Zeitpunkt t auf Basis von
        öffentlicher Information (TOB + DA-Preis) und eigener privater Information.

        Gibt eine neue Order zurück oder None, wenn keine Order platziert werden soll.
        """
        ...
