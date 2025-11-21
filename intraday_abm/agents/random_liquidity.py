from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Einfacher Hilfsagent zur Erzeugung zufälliger Liquidität.
    Dient nur als synthetischer Order-Flow, nicht als Shinde-Agent.
    """
    min_price: float = 10.0
    max_price: float = 90.0
    min_volume: float = 1.0
    max_volume: float = 10.0

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """Plaziert zufällig eine BUY- oder SELL-Limit-Order."""
        side = self.rng.choice([Side.BUY, Side.SELL])
        volume = self.rng.uniform(self.min_volume, self.max_volume)
        price = self.rng.uniform(self.min_price, self.max_price)

        return Order(
            id=-1,  # ID wird im MarketOperator vergeben
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=0,
        )

    @classmethod
    def create(
        cls,
        id: int,
        rng,
        capacity: float,
        min_price: float,
        max_price: float,
        min_volume: float,
        max_volume: float,
    ) -> "RandomLiquidityAgent":
        """Convenience-Factory zum Erzeugen mit AgentPrivateInfo."""
        priv = AgentPrivateInfo(effective_capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            max_volume=max_volume,
        )
