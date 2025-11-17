from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class SimpleTrendAgent(Agent):
    """
    Sehr einfacher, heuristischer Agent, der auf Preis-Trends reagiert.
    Ebenfalls nur als Platzhalter-Agent gedacht, nicht als Shinde-Agent.

    Idee:
    - Wenn letzter Midprice steigt, eher SELL.
    - Wenn letzter Midprice fällt, eher BUY.
    - Wenn keine Info vorhanden, zufällig.
    """

    last_midprice: Optional[float] = field(default=None, repr=False)
    base_volume: float = 5.0

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        best_bid = public_info.best_bid
        best_ask = public_info.best_ask

        # Kein TOB -> keine Entscheidung
        if best_bid is None and best_ask is None:
            return None

        # Midprice, falls möglich
        if best_bid is not None and best_ask is not None:
            mid = 0.5 * (best_bid + best_ask)
        else:
            # fallback: nutze die existierende Seite
            mid = best_bid if best_bid is not None else best_ask

        # Trendbewertung
        if self.last_midprice is None:
            trend = 0.0
        else:
            trend = mid - self.last_midprice

        self.last_midprice = mid

        # Trend > 0 => Preise steigen => eher verkaufen
        # Trend < 0 => Preise fallen => eher kaufen
        if trend > 0:
            side = Side.SELL
        elif trend < 0:
            side = Side.BUY
        else:
            # neutral -> zufällige Entscheidung
            side = self.rng.choice([Side.BUY, Side.SELL])

        # Einfache Preiswahl in Nähe des Midprice
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
    def create(cls, id: int, rng, capacity: float,
               base_volume: float = 5.0) -> "SimpleTrendAgent":
        priv = AgentPrivateInfo(capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            base_volume=base_volume,
        )
