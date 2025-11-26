from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from intraday_abm.agents.base import Agent
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Shinde-nahe naive Trader mit diskretem Preisband und mehreren Orders.

    Ursprüngliche Implementierung:
    - Preisband-Logik (±π um den DA-Preis) war direkt im Agenten codiert.
    - In jedem Schritt wurden n_orders zufällig über das Band verteilte Orders
      erzeugt (jeweils mit zufälliger Side und zufälligem Volumen).

    Refaktorisierte Version:
    - Die eigentliche Preisband-Logik ist in NaivePricingStrategy gekapselt.
    - Der Agent bestimmt nur noch das Gesamtvolumen, das er in diesem Tick
      bereitstellen möchte, und verteilt dieses über die von der Strategy
      gelieferten Preis-Volumen-Paare.
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
        Platziert mehrere Orders, deren Preise durch eine PricingStrategy
        (NaivePricingStrategy) bestimmt werden.

        Schritte:
        1. Gesamtvolumen abschätzen, das der Agent in diesem Tick bereitstellen
           möchte (auf Basis von min/max_volume und n_orders).
        2. Über die PricingStrategy eine diskrete Price-Volume-Curve erzeugen.
        3. Für jedes Preis-Volumen-Paar eine Order mit zufälliger Side erzeugen.
        """

        # Fallback: wenn keine Strategy gesetzt ist, keine Aktivität
        if self.pricing_strategy is None:
            return None

        if self.n_orders <= 0:
            return None

        # Einfacher Ansatz: Gesamtvolumen = erwarteter Mittelwert aller Orders
        avg_volume = 0.5 * (self.min_volume + self.max_volume)
        total_volume = avg_volume * self.n_orders

        if total_volume <= 0.0:
            return None

        # NaivePricingStrategy erzeugt eine diskrete Price-Volume-Kurve
        # Hinweis: Für die Referenzpreis-Bestimmung ist bei vorhandenem Bid & Ask
        # die Side irrelevant (midprice). Wir geben hier BUY mit.
        curve = self.pricing_strategy.build_price_volume_curve(
            agent=self,
            public_info=public_info,
            side=Side.BUY,
            total_volume=total_volume,
        )

        if not curve:
            return None

        orders: List[Order] = []

        for price, vol in curve:
            # Volumen innerhalb der Agenten-Grenzen halten
            volume = max(self.min_volume, min(self.max_volume, vol))
            if volume <= 0.0:
                continue

            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL

            order = Order(
                id=-1,
                agent_id=self.id,
                side=side,
                price=price,
                volume=volume,
                product_id=0,
            )
            orders.append(order)

        if not orders:
            return None

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
        """
        Factory-Methode zum Erzeugen eines RandomLiquidityAgent inklusive
        seiner NaivePricingStrategy.

        - capacity: effektive Kapazität C_max (wird in PrivateInfo abgelegt)
        - min_price / max_price: global zulässiger Preisrahmen für diesen Agenten
        - min_volume / max_volume: Volumengrenzen pro Order
        - price_band_pi, n_segments, n_orders: Parameter der NaivePricingStrategy
        """
        priv = AgentPrivateInfo(effective_capacity=capacity)

        agent = cls(
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

        # Shinde-nahe naive Preisstrategie an den Agenten hängen.
        agent.pricing_strategy = NaivePricingStrategy(
            rng=rng,
            pi_range=price_band_pi,
            n_segments=n_segments,
            n_orders=n_orders,
            min_price=min_price,
            max_price=max_price,
        )

        return agent
