from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class SimpleTrendAgent(Agent):
    """
    Heuristischer Agent, der auf einfache Preis-Trends reagiert.

    Zweck:
    - demonstriert, wie ein Agent PublicInfo nutzt
    - nicht als finale, ökonomisch fundierte Strategie gedacht
    """
    last_midprice: Optional[float] = field(default=None, repr=False)
    base_volume: float = 5.0

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """Kauft bei fallenden und verkauft bei steigenden Midprices."""
        bb = public_info.best_bid
        ba = public_info.best_ask

        if bb is None and ba is None:
            return None

        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
        else:
            mid = bb if bb is not None else ba

        if self.last_midprice is None:
            trend = 0.0
        else:
            trend = mid - self.last_midprice

        self.last_midprice = mid

        if trend > 0:
            side = Side.SELL
        elif trend < 0:
            side = Side.BUY
        else:
            side = self.rng.choice([Side.BUY, Side.SELL])

        price_spread = 2.0
        if side == Side.BUY:
            price = mid - self.rng.uniform(0.0, price_spread)
        else:
            price = mid + self.rng.uniform(0.0, price_spread)

        volume = self.base_volume

        return Order(
            id=-1,
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=0,
        )

    @classmethod
    def create(cls, id: int, rng, capacity: float, base_volume: float = 5.0) -> "SimpleTrendAgent":
        """Convenience-Factory zum Erzeugen mit AgentPrivateInfo."""
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            base_volume=base_volume,
        )
