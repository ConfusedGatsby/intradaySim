from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Einfacher Hilfsagent zur Erzeugung zufälliger Liquidität.

    Shinde-inspirierte Interpretation:
    - Dieser Agent repräsentiert einen „naive trader“, der stetig
      Orders um den aktuellen Marktpreis herum stellt und damit
      Basis-Liquidität bereitstellt.
    """

    # Zusätzliche Parameter gegenüber der Basisklasse Agent:
    min_price: float
    max_price: float
    min_volume: float
    max_volume: float

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft eine einfache, zufällige Handelsentscheidung:

        - mit einer gewissen Wahrscheinlichkeit in diesem Tick inaktiv
        - sonst: zufällige Wahl BUY/SELL
        - Volumen zufällig in [min_volume, max_volume]
        - Preis über die PricingStrategy (NaivePricingStrategy) bestimmt
        """

        # Einfache Wahrscheinlichkeit, in diesem Tick nichts zu tun
        if self.rng.random() < 0.3:
            return None

        # Zufällige Orderrichtung
        side = Side.BUY if self.rng.random() < 0.5 else Side.SELL

        # Zufälliges Volumen im erlaubten Band
        volume = self.rng.uniform(self.min_volume, self.max_volume)

        # Preisbestimmung über die (naive) PricingStrategy
        price = self.compute_order_price(
            public_info=public_info,
            side=side,
            volume=volume,
        )

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
        *,
        id: int,
        rng,
        capacity: float,
        min_price: float,
        max_price: float,
        min_volume: float,
        max_volume: float,
    ) -> "RandomLiquidityAgent":
        """
        Convenience-Factory zum Erzeugen eines RandomLiquidityAgent.

        - capacity: effektive Kapazität (wird im AgentPrivateInfo hinterlegt)
        - min_price / max_price: erlaubtes Preisband für Orders
        - min_volume / max_volume: Volumenband für Orders

        Zusätzlich wird hier direkt eine NaivePricingStrategy zugewiesen,
        die auf dem gleichen Preisband basiert.
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
        )

        # NaivePricingStrategy zuweisen (Shinde-nahe naive Trader)
        agent.pricing_strategy = NaivePricingStrategy(
            rng=rng,
            min_price=min_price,
            max_price=max_price,
            spread_band=max_price - min_price,  # grobes Band, kann später kalibriert werden
        )

        return agent
