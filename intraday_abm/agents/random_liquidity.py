from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo, TimeInForce
from intraday_abm.core.order import Order


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Shinde-nahe naive Trader mit diskretem Preisband und mehreren Orders.

    Refaktorisierte Version (Phase 1 + 2):

    - Die eigentliche Preisband- und Preisfindungslogik liegt in einer
      externen PricingStrategy (z.B. NaivePricingStrategy).
    - Der Agent selbst entscheidet nur noch:
        * wie viele Orders er typischerweise platzieren möchte (n_orders)
        * welches Gesamtvolumen er in einem Tick bereitstellen möchte
        * die Orderrichtung (BUY/SELL) pro Order
        * lokale Volumengrenzen pro Order

    Die Strategy wird von außen (in der Simulation) zugewiesen:
    agent.pricing_strategy = <PricingStrategy-Instanz>
    """

    min_price: float
    max_price: float
    min_volume: float
    max_volume: float

    # Shinde-nahe Konfig:
    # price_band_pi und n_segments werden von der Strategy genutzt und sind
    # hier nur noch zur Dokumentation / Konsistenz abgelegt. n_orders wird
    # lokal genutzt, um das Ziel-Gesamtvolumen pro Tick zu bestimmen.
    price_band_pi: float = 10.0
    n_segments: int = 20
    n_orders: int = 5

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order | List[Order]]:
        """
        Platziert mehrere Orders, deren Preise durch eine PricingStrategy
        (z.B. NaivePricingStrategy) bestimmt werden.

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

        # Die Preisstrategie erzeugt eine diskrete Price-Volume-Kurve.
        # Hinweis: Für die Referenzpreis-Bestimmung ist bei vorhandenem Bid & Ask
        # die Side hier irrelevant (Midprice). Wir geben BUY mit.
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
                time_in_force=TimeInForce.GTC,
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
        Factory-Methode zum Erzeugen eines RandomLiquidityAgent.

        WICHTIG (Phase 2):
        - Die eigentliche PricingStrategy (Naive / MTAA / ...) wird NICHT mehr
          hier erzeugt, sondern in der Simulation und anschließend dem Agenten
          zugewiesen:
              agent.pricing_strategy = strategy

        - Die hier übergebenen Parameter (insbesondere n_orders) steuern nur
          das agentenspezifische Verhalten (z.B. Ziel-Gesamtvolumen pro Tick).
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

        return agent
