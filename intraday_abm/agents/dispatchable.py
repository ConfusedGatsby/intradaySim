from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class DispatchableAgent(Agent):
    """
    Skeleton für einen dispatchbaren Agenten (z.B. konventionelles Kraftwerk).

    Aktuell gibt die Strategie keine Orders zurück (Stub).
    Dient als strukturelle Vorbereitung für eine spätere Shinde-nahe Implementierung.
    """

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """Derzeit keine Handelsaktivität (wird später implementiert)."""
        return None

    @classmethod
    def create(cls, id: int, rng, capacity: float) -> "DispatchableAgent":
        """Convenience-Factory zum Erzeugen mit AgentPrivateInfo."""
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
        )
