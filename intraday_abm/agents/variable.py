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
      oder konstante Basisgröße (base_forecast).
    - Imbalance wird definiert als
          δ_t = forecast(t) - market_position
      d.h.:
        * δ_t > 0 → erwartete Einspeisung > bisher gehandelte Position
                    → Überproduktion → SELL
        * δ_t < 0 → erwartete Einspeisung < bisher gehandelte Position
                    → Defizit → BUY
    - Erst wenn |δ_t| über einer Toleranz (imbalance_tolerance) liegt, wird
      im CID gehandelt.
    - Volumen ist durch |δ_t|, base_volume und Kapazität begrenzt.
    - Der Preis wird über compute_order_price bestimmt, so dass optional eine
      PricingStrategy genutzt werden kann.
    """

    base_forecast: float = 20.0
    forecast_fn: Optional[Callable[[int], float]] = None
    base_volume: float = 5.0
    imbalance_tolerance: float = 1.0  # bis zu dieser Imbalance passiert nichts

    def _forecast(self, t: int) -> float:
        """
        Liefert den Forecast-Wert für Zeitpunkt t.

        - Falls eine forecast_fn gesetzt ist, wird diese genutzt.
        - Andernfalls wird eine konstante Basisgröße (base_forecast)
          zurückgegeben.
        """
        if self.forecast_fn is not None:
            return self.forecast_fn(t)
        return self.base_forecast

    def update_imbalance(self, t: int) -> None:
        """
        Aktualisiert die Imbalance δ_t für VariableAgent.

        δ_t = forecast(t) - market_position

        Diese Definition ist konsistent mit der Idee:
        - forecast(t) repräsentiert zu erwartende Erzeugung/Last,
        - market_position repräsentiert die bisher über DA/CID verkaufte/gekaufte
          Energiemenge (Netto).
        """
        forecast = self._forecast(t)
        pi = self.private_info
        pi.imbalance = forecast - pi.market_position

    def decide_order(
        self,
        t: int,
        public_info: PublicInfo,
    ) -> Optional[Order]:
        """
        Bestimme eine Order für den VariableAgent:

        1. Forecast(t) und δ_t = forecast - market_position bestimmen.
        2. Wenn |δ_t| <= imbalance_tolerance → keine Order.
        3. Kapazität & aktuelle Marktposition begrenzen das Ordervolumen.
        4. Side:
           - δ_t > 0  → SELL (Überproduktion)
           - δ_t < 0  → BUY  (Defizit)
        5. Preis über compute_order_price bestimmen.
        """

        # --- 1) Forecast & Imbalance ----------------------------------------
        self.update_imbalance(t)
        pi = self.private_info
        delta = pi.imbalance

        # Kleine Imbalance ignorieren (Totzone)
        if abs(delta) <= self.imbalance_tolerance:
            return None

        # --- 2) Kapazitätsgrenzen -------------------------------------------
        cap = pi.effective_capacity
        mar_pos = pi.market_position

        if cap <= 0.0:
            return None

        # Symmetrische Kapazität um 0: je weiter wir schon „ausgelenkt“ sind,
        # desto weniger ist noch verfügbar.
        available_capacity = max(0.0, cap - abs(mar_pos))
        if available_capacity <= 0.0:
            return None

        # --- 3) Volumen aus Imbalance ableiten ------------------------------
        volume = min(abs(delta), self.base_volume, available_capacity)
        if volume <= 0.0:
            return None

        # --- 4) Side bestimmen ----------------------------------------------
        # δ_t > 0: forecast > market_position → wir haben zu viel „physisch“
        #          → SELL, um Imbalance abzubauen.
        # δ_t < 0: forecast < market_position → Defizit → BUY.
        side = Side.SELL if delta > 0.0 else Side.BUY

        # --- 5) Preis bestimmen ---------------------------------------------
        price = self.compute_order_price(
            public_info=public_info,
            side=side,
            volume=volume,
        )

        # --- 6) Order erzeugen ----------------------------------------------
        return Order(
            id=-1,
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=0,
            time_in_force=None,
            timestamp=t,
        )

    @classmethod
    def create(
        cls,
        *,
        id: int,
        rng,
        capacity: float,
        base_forecast: float,
        base_volume: float,
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
