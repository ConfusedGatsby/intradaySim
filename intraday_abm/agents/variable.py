from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class VariableAgent(Agent):
    """
    Skeleton für einen variablen Agenten (z.B. Wind/PV-Erzeuger).
    Angelehnt an Shinde: besitzt private Forecast-Information etc.

    Aktuell ist die Strategie ein Platzhalter (gibt None zurück).
    Die konkrete Entscheidungslogik wird später (textnah) aus Shinde übernommen.
    """

    # Platzhalter für spätere Erweiterungen, z.B.:
    # forecast: list[float] | None = None
    # forecast_error: float = 0.0

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        # TODO: Shinde-nahe Entscheidungslogik implementieren
        return None

    @classmethod
    def create(cls, id: int, rng, capacity: float) -> "VariableAgent":
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
        )
