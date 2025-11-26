from __future__ import annotations

from abc import ABC, abstractmethod
from random import Random
from typing import Optional, TYPE_CHECKING

from intraday_abm.core.types import Side, PublicInfo

if TYPE_CHECKING:
    from intraday_abm.agents.base import Agent


class PricingStrategy(ABC):
    """
    Abstrakte Basisklasse für Preisstrategien.
    """

    def __init__(self, rng: Optional[Random] = None) -> None:
        self.rng: Random = rng or Random()

    @abstractmethod
    def build_price_volume_curve(
        self,
        *,
        agent: Agent,
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> list[tuple[float, float]]:
        """
        Gibt eine Liste von Preis-Volumen-Paaren für Orders zurück.
        """
        raise NotImplementedError


class NaivePricingStrategy(PricingStrategy):
    """
    Shinde-nahe naive Preisstrategie:

    - Symmetrisches Preisband um Midprice oder DA-Preis
    - Diskret segmentiert (z.B. in 20 Preisstufen)
    - Liefert n zufällig ausgewählte Preisstufen für Orders
    """

    def __init__(
        self,
        rng: Optional[Random] = None,
        pi_range: float = 10.0,         # Breite des Preisbands (±)
        n_segments: int = 20,           # Anzahl diskreter Preisstufen im Band
        n_orders: int = 5,              # Anzahl Orders, die pro Tick erzeugt werden
        min_price: float = 0.0,
        max_price: float = 1000.0,
    ) -> None:
        super().__init__(rng=rng)
        self.pi_range = pi_range
        self.n_segments = n_segments
        self.n_orders = n_orders
        self.min_price = min_price
        self.max_price = max_price

    def _reference_price(self, public_info: PublicInfo, side: Side) -> float:
        tob = public_info.tob
        bid = tob.best_bid_price
        ask = tob.best_ask_price

        if bid is not None and ask is not None:
            return 0.5 * (bid + ask)
        if side is Side.BUY and ask is not None:
            return ask
        if side is Side.SELL and bid is not None:
            return bid
        return public_info.da_price

    def build_price_volume_curve(
        self,
        *,
        agent: Agent,
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> list[tuple[float, float]]:
        """
        Gibt n Preis-Volumen-Paare zurück, gleichmäßig verteilt im Preisband.
        """

        ref_price = self._reference_price(public_info, side)

        delta = self.pi_range / self.n_segments
        lower = max(self.min_price, ref_price - 0.5 * self.pi_range)
        upper = min(self.max_price, ref_price + 0.5 * self.pi_range)

        grid = [lower + i * delta for i in range(self.n_segments + 1)]
        prices = self.rng.sample(grid, k=min(self.n_orders, len(grid)))

        volume = total_volume / len(prices)
        return [(p, volume) for p in prices]


class MTAAPricingStrategy(PricingStrategy):
    """
    Platzhalter für MTAA-Strategie (Modified Trader Adaptive Aggressiveness).
    Noch nicht implementiert.
    """

    def build_price_volume_curve(
        self,
        *,
        agent: Agent,
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> list[tuple[float, float]]:
        raise NotImplementedError("MTAA-Strategie ist noch nicht implementiert.")
