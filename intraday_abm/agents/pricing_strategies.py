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

    In Anlehnung an Shinde wird die Bietlogik (naiv vs. MTAA)
    vom Agententyp getrennt. Agenten besitzen eine PricingStrategy-
    Instanz und rufen compute_price(...) auf, um den Limitpreis
    ihrer Order zu bestimmen.
    """

    def __init__(self, rng: Optional[Random] = None) -> None:
        # Eigener RNG pro Strategieinstanz (reproduzierbar, agent-lokal)
        self.rng: Random = rng or Random()

    @abstractmethod
    def compute_price(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        volume: float,
    ) -> float:
        """
        Berechnet den Limitpreis für eine neue Order.

        Parameter
        ----------
        agent : Agent
            Der Agent, der die Order platziert.
        public_info : PublicInfo
            Öffentliche Marktinformationen (Top-of-Book, DA-Preis, Zeit t).
        side : Side
            BUY oder SELL.
        volume : float
            Volumen der Order.

        Returns
        -------
        float : Limitpreis
        """
        raise NotImplementedError


class NaivePricingStrategy(PricingStrategy):
    """
    Naive Preisstrategie – analog zu den „naive traders“ in Shinde.

    Verhält sich wie ein einfacher Market-Maker:

    - nimmt Midprice (falls vorhanden), sonst DA-Preis, sonst best_ask/best_bid
    - erzeugt einen zufälligen Preis innerhalb eines symmetrischen Bandes
    - stellt damit robuste Liquidität bereit
    """

    def __init__(
        self,
        rng: Optional[Random] = None,
        spread_band: float = 10.0,
        min_price: float = 0.0,
        max_price: float = 1000.0,
    ) -> None:
        super().__init__(rng=rng)
        self.spread_band = spread_band
        self.min_price = min_price
        self.max_price = max_price

    def _reference_price(self, public_info: PublicInfo, side: Side) -> float:
        """
        Bestimme den Referenzpreis:
        1) Midprice, falls beidseitig Order
        2) Für BUY: best_ask_price
           Für SELL: best_bid_price
        3) Fallback: da_price
        """
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

    def compute_price(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        volume: float,
    ) -> float:
        ref = self._reference_price(public_info, side)

        half_band = 0.5 * self.spread_band
        offset = self.rng.uniform(-half_band, half_band)
        price = ref + offset

        return max(self.min_price, min(self.max_price, price))


class MTAAPricingStrategy(PricingStrategy):
    """
    Platzhalter für eine MTAA-ähnliche Strategie
    (Modified Trader Adaptive Aggressiveness),
    wie in Shinde beschrieben.

    Aktuell nur das Grundgerüst:

    - aggressiveness in [-1, 1]
    - BUY: aggressiver -> Preis höher (näher an ask)
    - SELL: aggressiver -> Preis tiefer (näher an bid)
    - tatsächliche Lernlogik (Update-Regeln) folgt später
    """

    def __init__(
        self,
        rng: Optional[Random] = None,
        initial_aggressiveness: float = 0.0,
        min_aggressiveness: float = -1.0,
        max_aggressiveness: float = 1.0,
        base_spread: float = 4.0,
        min_price: float = 0.0,
        max_price: float = 1000.0,
    ) -> None:
        super().__init__(rng=rng)
        self.aggressiveness = initial_aggressiveness
        self.min_aggressiveness = min_aggressiveness
        self.max_aggressiveness = max_aggressiveness
        self.base_spread = base_spread
        self.min_price = min_price
        self.max_price = max_price

    def _clamp(self) -> None:
        """Clamp aggressiveness in [min_aggressiveness, max_aggressiveness]."""
        self.aggressiveness = max(
            self.min_aggressiveness,
            min(self.max_aggressiveness, self.aggressiveness),
        )

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

    def compute_price(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        volume: float,
    ) -> float:
        """
        Platzhalterimplementierung:
        - Aggressiveness beeinflusst die Abweichung vom Referenzpreis
        - Noise sorgt für leichte Variation
        """
        self._clamp()
        ref = self._reference_price(public_info, side)

        direction = 1.0 if side is Side.BUY else -1.0

        factor = 1.0 - 0.5 * self.aggressiveness
        half_base = 0.5 * self.base_spread
        offset_magnitude = factor * half_base

        noise = self.rng.uniform(-0.1 * offset_magnitude, 0.1 * offset_magnitude)
        price = ref + direction * offset_magnitude + noise

        return max(self.min_price, min(self.max_price, price))

    def update_after_feedback(
        self,
        *,
        was_executed: bool,
        spread: Optional[float] = None,
    ) -> None:
        """
        Erweiterungspunkt für die echte MTAA-Lernlogik.
        Wird später implementiert.

        - Wenn Order zu selten gefüllt wird → aggressiveness erhöhen
        - Wenn Order zu leicht gefüllt wird → aggressiveness senken
        """
        pass
