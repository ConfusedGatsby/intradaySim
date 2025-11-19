from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class VariableAgent(Agent):
    """
    Skeleton für einen variablen Agenten (z.B. Wind/PV).

    Aktuell keine Strategie implementiert.
    Später können Forecast-Profile und Imbalance-Information ergänzt werden.
    """

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """Derzeit keine Handelsaktivität (wird später implementiert)."""
        return None

    @classmethod
    def create(cls, id: int, rng, capacity: float) -> "VariableAgent":
        """Convenience-Factory zum Erzeugen mit AgentPrivateInfo."""
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
        )
