from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Shinde-nahe naive Trader mit diskretem Preisband und mehreren Orders.

    - platziert in jedem Schritt mehrere gleichmäßig verteilte Orders
    - nutzt das DA-Preiszentrum und ein Preisband ±π
    - diskretisiert das Band in n Preisstufen
    """

    min_price: float
    max_price: float
    min_volume: float
    max_volume: float

    # Shinde-nahe Konfig:
    price_band_pi: float = 10.0
    n_segments: int = 20
    n_orders: int = 5

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order | List[Order]]:
        """
        Platziert n_orders zufällig über das diskrete Preisband verteilte Orders.

        - Mitte = DA-Preis
        - Bandbreite ±π
        - Preislevel = equidistant auf dem Band
        - Richtung = zufällig BUY / SELL
        - Volumen = zufällig im erlaubten Band
        """
        center = public_info.da_price
        pi = self.price_band_pi
        n = self.n_segments

        # Erzeuge diskrete Preislevel (aufsteigend)
        step = (2 * pi) / (n - 1)
        price_levels = [center - pi + i * step for i in range(n)]

        # n_orders zufällig aus diesen Leveln ziehen (ohne Duplikate)
        if self.rng is None:
            return None

        selected_prices = self.rng.sample(price_levels, min(self.n_orders, len(price_levels)))

        orders = []
        for p in selected_prices:
            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL
            volume = self.rng.uniform(self.min_volume, self.max_volume)

            order = Order(
                id=-1,
                agent_id=self.id,
                side=side,
                price=p,
                volume=volume,
                product_id=0,
            )
            orders.append(order)

        return orders

    @classmethod
    def create(
        cls,
        *,
        id: int,
        rng,
        capacity: float,
        min_price: float,
        max_price: float,
        min_volume: float,
        max_volume: float,
        price_band_pi: float = 10.0,
        n_segments: int = 20,
        n_orders: int = 5,
    ) -> "RandomLiquidityAgent":
        priv = AgentPrivateInfo(effective_capacity=capacity)

        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            max_volume=max_volume,
            price_band_pi=price_band_pi,
            n_segments=n_segments,
            n_orders=n_orders,
        )
