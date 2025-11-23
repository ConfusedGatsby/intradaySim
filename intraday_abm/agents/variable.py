from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side
from intraday_abm.core.order import Order


@dataclass
class VariableAgent(Agent):
    """
    Shinde-inspirierter „variable agent“ (z.B. Wind/PV/variable Last).

    Vereinfachte Struktur:
    - besitzt ein Forecast-Profil (Erzeugung/Last) als Funktion f(t)
      oder konstante Basisgröße (base_forecast)
    - Imbalance = forecast(t) - market_position
    - bei positiver Imbalance (Überproduktion): SELL
    - bei negativer Imbalance (Defizit): BUY
    - Preiswahl nahe am Midprice / DA-Preis (Naive-artig)
    """

    base_forecast: float = 20.0
    forecast_fn: Optional[Callable[[int], float]] = None
    base_volume: float = 5.0
    imbalance_tolerance: float = 1.0  # bis zu dieser Imbalance passiert nichts

    def _forecast(self, t: int) -> float:
        """Liefert den Forecast-Wert für Zeitpunkt t."""
        if self.forecast_fn is not None:
            return self.forecast_fn(t)
        return self.base_forecast

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Entscheidet anhand der Imbalance über BUY/SELL.

        - δ = forecast(t) - market_position
        - δ >> 0  -> SELL (Überproduktion)
        - δ << 0  -> BUY  (Defizit)
        - Volumen ∝ |δ|, begrenzt durch Kapazität
        """

        bb = public_info.tob.best_bid_price
        ba = public_info.tob.best_ask_price

        if bb is None and ba is None:
            return None

        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
        else:
            mid = bb if bb is not None else ba
        if mid is None:
            mid = public_info.da_price

        # Forecast und Imbalance
        forecast = self._forecast(t)
        mar_pos = self.private_info.market_position

        imbalance = forecast - mar_pos
        self.private_info.imbalance = imbalance

        if abs(imbalance) <= self.imbalance_tolerance:
            return None

        # Kapazitätsgrenzen
        cap = self.private_info.effective_capacity
        available_capacity = max(0.0, cap - abs(mar_pos))
        if available_capacity <= 0.0:
            return None

        desired_volume = min(abs(imbalance), self.base_volume, available_capacity)
        if desired_volume <= 0.0:
            return None

        # Richtung
        if imbalance > 0:
            side = Side.SELL
        else:
            side = Side.BUY

        # Preiswahl Naive-artig um den Midprice herum
        price_spread = 2.0  # kleine Spanne um mid
        if side == Side.SELL:
            price = mid + self.rng.uniform(0.0, price_spread)
        else:
            price = mid - self.rng.uniform(0.0, price_spread)

        return Order(
            id=-1,
            agent_id=self.id,
            side=side,
            price=price,
            volume=desired_volume,
            product_id=0,
        )

    @classmethod
    def create(
        cls,
        id: int,
        rng,
        capacity: float,
        base_forecast: float = 20.0,
        base_volume: float = 5.0,
        imbalance_tolerance: float = 1.0,
        forecast_fn: Optional[Callable[[int], float]] = None,
    ) -> "VariableAgent":
        """
        Convenience-Factory:
        erzeugt einen VariableAgent mit AgentPrivateInfo.
        """
        priv = AgentPrivateInfo(effective_capacity=capacity)
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            base_forecast=base_forecast,
            base_volume=base_volume,
            imbalance_tolerance=imbalance_tolerance,
            forecast_fn=forecast_fn,
        )
