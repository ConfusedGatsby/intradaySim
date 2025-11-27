from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Callable, Dict, Union, List

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side, TimeInForce
from intraday_abm.core.order import Order


@dataclass
class VariableAgent(Agent):
    """
    Shinde-inspirierter „variable agent" (z.B. Wind/PV/variable Last).
    
    Unterstützt BEIDE Modi:
    - Single-Product: forecast(t) für EIN Produkt
    - Multi-Product: forecast(t, product_id) für MEHRERE Produkte
    
    Vereinfachte Struktur:
    - besitzt ein Forecast-Profil (Erzeugung/Last) als Funktion f(t) oder f(t, product_id)
      oder konstante Basisgröße (base_forecast).
    - Imbalance wird definiert als
          δ_t = forecast(t) - market_position          (single-product)
          δ_{t,d} = forecast(t, d) - position_d        (multi-product)
      d.h.:
        * δ > 0 → erwartete Einspeisung > bisher gehandelte Position
                  → Überproduktion → SELL
        * δ < 0 → erwartete Einspeisung < bisher gehandelte Position
                  → Defizit → BUY
    - Erst wenn |δ| über einer Toleranz (imbalance_tolerance) liegt, wird
      im CID gehandelt.
    - Volumen ist durch |δ|, base_volume und Kapazität begrenzt.
    - Der Preis wird über compute_order_price bestimmt, so dass optional eine
      PricingStrategy genutzt werden kann.
    
    **Multi-Product Verhalten:**
    - Forecasts entwickeln sich UNABHÄNGIG pro Produkt
    - Jedes Produkt kann eigenen Forecast-Fehler haben
    - Agent handelt JEDES Produkt separat (keine Kopplung außer Kapazität)
    """

    base_forecast: float = 20.0
    forecast_fn: Optional[Callable[[int], float]] = None
    base_volume: float = 5.0
    imbalance_tolerance: float = 1.0  # bis zu dieser Imbalance passiert nichts

    def _forecast(self, t: int, product_id: Optional[int] = None) -> float:
        """
        Liefert den Forecast-Wert für Zeitpunkt t (und optional product_id).

        **Single-Product Mode:**
        - Falls eine forecast_fn gesetzt ist, wird diese genutzt: forecast_fn(t)
        - Andernfalls wird eine konstante Basisgröße (base_forecast) zurückgegeben.
        
        **Multi-Product Mode:**
        - Nutzt private_info.forecasts[product_id]
        - Forecasts werden pro Produkt gespeichert und können sich unabhängig entwickeln
        
        Args:
            t: Current simulation time
            product_id: Product to forecast (Multi-Product only)
            
        Returns:
            Forecast value
        """
        if self.is_multi_product:
            if product_id is None:
                raise ValueError("product_id required in multi-product mode")
            # Multi-Product: nutze gespeicherten Forecast
            return self.private_info.forecasts.get(product_id, self.base_forecast)
        else:
            # Single-Product: nutze forecast_fn oder base_forecast
            if self.forecast_fn is not None:
                return self.forecast_fn(t)
            return self.base_forecast

    def update_forecast(self, t: int, product_id: int, delta: float = 0.0) -> None:
        """
        Update forecast für ein spezifisches Produkt (Multi-Product only).
        
        Diese Methode ermöglicht Forecast-Evolution über Zeit, z.B.:
        - Random Walk: delta = rng.gauss(0, sigma)
        - Mean Reversion: delta = alpha * (base_forecast - current_forecast)
        - Externes Update: delta aus externer Quelle
        
        Args:
            t: Current simulation time
            product_id: Product to update
            delta: Change to apply to forecast
        
        Example:
            # Random walk mit mean reversion
            current = agent.private_info.forecasts[product_id]
            error = agent.rng.gauss(0, 2.0)
            reversion = 0.1 * (agent.base_forecast - current)
            agent.update_forecast(t, product_id, error + reversion)
        """
        if not self.is_multi_product:
            return  # Ignore in single-product mode
        
        current = self.private_info.forecasts.get(product_id, self.base_forecast)
        new_forecast = current + delta
        
        # Optional: Clipping auf sinnvolle Grenzen
        # new_forecast = max(0.0, min(self.private_info.capacities[product_id], new_forecast))
        
        self.private_info.forecasts[product_id] = new_forecast

    def update_imbalance(self, t: int, product_id: Optional[int] = None) -> None:
        """
        Aktualisiert die Imbalance δ_t für VariableAgent.
        
        **Single-Product Mode:**
        δ_t = forecast(t) - market_position

        **Multi-Product Mode:**
        δ_{t,d} = forecast(t, d) - position_d
        
        Diese Definition ist konsistent mit der Idee:
        - forecast(t) repräsentiert zu erwartende Erzeugung/Last,
        - market_position repräsentiert die bisher über DA/CID verkaufte/gekaufte
          Energiemenge (Netto).
        
        Args:
            t: Current simulation time
            product_id: Product to update (Multi-Product only)
        """
        if self.is_multi_product:
            if product_id is None:
                raise ValueError("product_id required in multi-product mode")
            
            forecast = self._forecast(t, product_id)
            position = self.private_info.positions.get(product_id, 0.0)
            self.private_info.set_imbalance(product_id, forecast - position)
        else:
            # Single-Product Mode (original)
            forecast = self._forecast(t)
            pi = self.private_info
            pi.imbalance = forecast - pi.market_position

    def decide_order(
        self,
        t: int,
        public_info: PublicInfo,
    ) -> Optional[Order]:
        """
        Bestimme eine Order für den VariableAgent (Single-Product).

        1. Forecast(t) und δ_t = forecast - market_position bestimmen.
        2. Wenn |δ_t| <= imbalance_tolerance → keine Order.
        3. Kapazität & aktuelle Marktposition begrenzen das Ordervolumen.
        4. Side:
           - δ_t > 0  → SELL (Überproduktion)
           - δ_t < 0  → BUY  (Defizit)
        5. Preis über compute_order_price bestimmen.
        
        Args:
            t: Current simulation time
            public_info: Public market information
            
        Returns:
            Order or None
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

        # Symmetrische Kapazität um 0: je weiter wir schon „ausgelenkt" sind,
        # desto weniger ist noch verfügbar.
        available_capacity = max(0.0, cap - abs(mar_pos))
        if available_capacity <= 0.0:
            return None

        # --- 3) Volumen aus Imbalance ableiten ------------------------------
        volume = min(abs(delta), self.base_volume, available_capacity)
        if volume <= 0.0:
            return None

        # --- 4) Side bestimmen ----------------------------------------------
        # δ_t > 0: forecast > market_position → wir haben zu viel „physisch"
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
            time_in_force=TimeInForce.GTC,
            timestamp=t,
        )

    def decide_orders(
        self, 
        t: int, 
        public_info: Dict[int, PublicInfo]
    ) -> Dict[int, Union[Order, List[Order]]]:
        """
        Multi-Product: Entscheide Orders für mehrere Produkte.
        
        Strategie:
        1. Für jedes offene Produkt: update_imbalance()
        2. Für jedes Produkt mit signifikanter Imbalance: erstelle Order
        3. Nutze gleiche Logik wie decide_order(), aber pro Produkt
        
        Args:
            t: Current simulation time
            public_info: Dict mapping product_id to PublicInfo
            
        Returns:
            Dict mapping product_id to Order(s)
        """
        if not self.is_multi_product:
            # Fallback to single-product
            return super().decide_orders(t, public_info)
        
        orders = {}
        
        for product_id, pub_info in public_info.items():
            order = self._decide_for_product(t, product_id, pub_info)
            if order:
                orders[product_id] = order
        
        return orders

    def _decide_for_product(
        self, 
        t: int, 
        product_id: int, 
        public_info: PublicInfo
    ) -> Optional[Order]:
        """
        Hilfsmethode: Entscheide Order für ein spezifisches Produkt.
        
        Nutzt die gleiche Logik wie decide_order(), aber mit produkt-spezifischem State.
        
        Args:
            t: Current simulation time
            product_id: Product to trade
            public_info: Public info for this product
            
        Returns:
            Order or None
        """
        # --- 1) Forecast & Imbalance ----------------------------------------
        self.update_imbalance(t, product_id)
        delta = self.private_info.imbalances.get(product_id, 0.0)

        # Kleine Imbalance ignorieren (Totzone)
        if abs(delta) <= self.imbalance_tolerance:
            return None

        # --- 2) Kapazitätsgrenzen -------------------------------------------
        cap = self.private_info.capacities.get(product_id, 0.0)
        position = self.private_info.positions.get(product_id, 0.0)

        if cap <= 0.0:
            return None

        # Symmetrische Kapazität um 0
        available_capacity = max(0.0, cap - abs(position))
        if available_capacity <= 0.0:
            return None

        # --- 3) Volumen aus Imbalance ableiten ------------------------------
        volume = min(abs(delta), self.base_volume, available_capacity)
        if volume <= 0.0:
            return None

        # --- 4) Side bestimmen ----------------------------------------------
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
            product_id=product_id,
            time_in_force=TimeInForce.GTC,
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
        Convenience-Factory: erzeugt einen VariableAgent mit AgentPrivateInfo (Single-Product).
        
        Args:
            id: Agent ID
            rng: Random number generator
            capacity: Agent capacity
            base_forecast: Base forecast value
            base_volume: Base order volume
            imbalance_tolerance: Minimum imbalance to trade
            forecast_fn: Optional forecast function
            
        Returns:
            VariableAgent instance
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