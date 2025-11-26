from __future__ import annotations

from abc import ABC, abstractmethod
from random import Random
from typing import Optional, TYPE_CHECKING, List, Tuple

from intraday_abm.core.types import Side, PublicInfo

if TYPE_CHECKING:
    from intraday_abm.agents.base import Agent


class PricingStrategy(ABC):
    """
    Abstrakte Basisklasse für Preisstrategien.

    Wichtig:
    - RandomLiquidityAgent nutzt build_price_volume_curve(...)
    - DispatchableAgent / VariableAgent nutzen compute_price(...)
      (über Agent.compute_order_price).
    """

    def __init__(self, rng: Random):
        self.rng = rng

    @abstractmethod
    def build_price_volume_curve(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> List[Tuple[float, float]]:
        """
        Erzeugt eine diskrete Price-Volume-Kurve:
        Rückgabe: Liste von (price, volume)-Tupeln.
        """
        ...

    # NICHT abstract: Default-Implementation, kann von Subklassen
    # überschrieben werden
    def compute_price(
        self,
        *,
        agent: Optional["Agent"] = None,
        public_info: PublicInfo,
        side: Side,
        volume: float,
        **kwargs,
    ) -> float:
        """
        Default-Fallback: nutzt die Marktinformation (TOB/DA-Preis),
        um einen einfachen Preis zu bestimmen.

        DispatchableAgent / VariableAgent rufen diese Methode über
        Agent.compute_order_price(...) auf.
        """
        tob = public_info.tob
        bb = tob.best_bid_price
        ba = tob.best_ask_price

        if bb is not None and ba is not None:
            return 0.5 * (bb + ba)
        elif bb is not None:
            return bb
        elif ba is not None:
            return ba
        else:
            return public_info.da_price


class NaivePricingStrategy(PricingStrategy):
    """
    Shinde-nahe naive Preisstrategie.

    Idee:
    - Bestimme einen Referenzpreis p* (Midprice, falls verfügbar,
      sonst best_bid/best_ask oder DA-Preis).
    - Erzeuge ein Preisintervall um p* mit Breite pi_range.
    - Für RandomLiquidityAgent:
      * baue eine diskrete Price-Volume-Kurve über dieses Intervall.
    - Für Dispatchable/VariableAgent:
      * compute_price(...) zieht einen einzelnen Preis aus dem
        betreffenden Intervall [p* - pi_range, p* + pi_range],
        ggf. leicht asymmetrisch nach BUY/SELL.
    """

    def __init__(
        self,
        rng: Random,
        pi_range: float,
        n_segments: int,
        n_orders: int,
        min_price: float,
        max_price: float,
    ):
        super().__init__(rng)
        self.pi_range = pi_range
        self.n_segments = max(1, n_segments)
        self.n_orders = max(1, n_orders)
        self.min_price = min_price
        self.max_price = max_price

    # -------------------------------------------------------------
    # Hilfsfunktionen
    # -------------------------------------------------------------
    def _reference_price(self, public_info: PublicInfo) -> float:
        tob = public_info.tob
        bb = tob.best_bid_price
        ba = tob.best_ask_price

        # Mid als Signal nur nutzen, solange beide Seiten existieren.
        # Zusätzlich dämpfen wir mit dem DA-Preis, damit sich der Referenzpreis
        # nicht selbst hochschaukelt, wenn das Buch auf einer Seite dünn ist.
        da = public_info.da_price

        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
            return 0.5 * mid + 0.5 * da  # Mittelwert aus Mid und DA
        # Nur eine Seite vorhanden -> stabiler Anker am DA-Preis
        return da

    def _clip_price(self, p: float) -> float:
        return max(self.min_price, min(self.max_price, p))

    # -------------------------------------------------------------
    # Für RandomLiquidityAgent (Price-Volume-Kurve)
    # -------------------------------------------------------------
    def build_price_volume_curve(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> List[Tuple[float, float]]:
        """
        Erzeugt eine einfache diskrete Price-Volume-Kurve über ein
        Intervall um den Referenzpreis.

        - total_volume wird gleichmäßig auf n_segments verteilt
        - Preise werden linear im Intervall verteilt + leichtes Jitter
        """

        if total_volume <= 0.0:
            return []

        ref = self._reference_price(public_info)

        # Intervall um den Referenzpreis
        half_range = 0.5 * self.pi_range
        p_min = self._clip_price(ref - half_range)
        p_max = self._clip_price(ref + half_range)

        if p_max <= p_min:
            # degeneriertes Intervall → alles auf einen Preis
            return [(p_min, total_volume)]

        vol_per_segment = total_volume / float(self.n_segments)
        curve: List[Tuple[float, float]] = []

        for i in range(self.n_segments):
            # lineare Position im Intervall
            frac = (i + 0.5) / self.n_segments
            base_price = p_min + frac * (p_max - p_min)

            # kleiner Zufalls-Jitter, um die Preise zu streuen
            jitter = self.rng.uniform(-0.2, 0.2)
            price = self._clip_price(base_price + jitter)

            curve.append((price, vol_per_segment))

        return curve

    # -------------------------------------------------------------
    # Für DispatchableAgent / VariableAgent (einzelner Preis)
    # -------------------------------------------------------------
    def compute_price(
        self,
        *,
        agent: Optional["Agent"] = None,
        public_info: PublicInfo,
        side: Side,
        volume: float,
        **kwargs,
    ) -> float:
        """
        Einzelpreis für eine Order.

        - Referenzpreis p* wie oben
        - BUY:  Preis aus [p* - pi_range, p*]
        - SELL: Preis aus [p*, p* + pi_range]
        - alles geclippt auf [min_price, max_price]
        """
        ref = self._reference_price(public_info)
        half_range = self.pi_range

        if side == Side.BUY:
            low = self._clip_price(ref - half_range)
            high = self._clip_price(ref)
        else:  # SELL
            low = self._clip_price(ref)
            high = self._clip_price(ref + half_range)

        if high < low:
            low, high = high, low

        if high == low:
            return low

        return self.rng.uniform(low, high)


class MTAAPricingStrategy(PricingStrategy):
    """
    Platzhalter für MTAA-Strategie (Modified Trader Adaptive Aggressiveness).
    Noch nicht implementiert.
    """

    def build_price_volume_curve(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> List[Tuple[float, float]]:
        """
        Hier könnten die Formeln für MTAA (Shinde) implementiert werden.
        Aktuell nicht implementiert.
        """
        raise NotImplementedError("MTAA-Strategie ist noch nicht implementiert.")
