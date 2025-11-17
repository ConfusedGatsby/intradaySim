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
    Angelehnt an Shinde: hat private Kapazitäts- und Kosteninformationen.

    Aktuell ist die Strategie ein Platzhalter (gibt None zurück).
    Die konkrete Entscheidungslogik wird später (textnah) aus Shinde übernommen.
    """

    # Platzhalter für spätere Erweiterungen, z.B.:
    # marginal_cost: float = 50.0
    # ramp_limit: float = 10.0

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        # TODO: Shinde-nahe Entscheidungslogik implementieren
        # Aktuell kein Handel -> None
        return None

    @classmethod
    def create(cls, id: int, rng, capacity: float) -> "DispatchableAgent":
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
        )
