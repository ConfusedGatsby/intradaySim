from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side
from intraday_abm.core.order import Order


@dataclass
class DispatchableAgent(Agent):
    """
    Shinde-inspirierter „dispatchable agent“ (z.B. thermisches Kraftwerk).

    Vereinfachte, aber Shinde-nahe Idee:

    - Der Agent hat eine Day-Ahead-Position (private_info.da_position)
      und eine effektive Kapazität (private_info.effective_capacity).
    - Er kennt seine Grenzkosten (marginal_cost).
    - Er hat ein typisches Ordervolumen pro Tick (base_volume).
    - Er betrachtet, ob der aktuelle Marktpreis (Midprice, TOB) deutlich
      über/unter den Grenzkosten liegt (epsilon_price als Mindestmarge).
    - Die Imbalance wird als
          δ_t = da_position - market_position
      definiert. Sie gibt an, wie weit die aktuelle Marktposition von der
      DA-Position entfernt ist.

    Entscheidungslogik (heuristisch, Shinde-nah):

    1. δ_t bestimmen (DA-Lücke):
       - δ_t > 0  → unterverkauft relativ zur DA-Position
       - δ_t < 0  → überverkauft relativ zur DA-Position

    2. Kapazität prüfen:
       - effektive Kapazität C und aktuelle Marktposition p_mar begrenzen
         das noch handelbare Volumen.

    3. Zielvolumen:
       - Volumen proportional zur Größe der DA-Lücke,
         begrenzt durch base_volume und verfügbare Kapazität.

    4. Profitchance:
       - SELL ist attraktiv, wenn Midprice deutlich über marginal_cost liegt.
       - BUY ist attraktiv, wenn Midprice deutlich unter marginal_cost liegt.
       - Die Marge wird über epsilon_price gesteuert.

    5. Side-Wahl:
       - Primär: in Richtung DA-Position gehen, sofern profitabel.
       - Fallback: wenn nur eine Richtung profitabel ist, folge dieser.
       - Sonst: keine Order.

    6. Preis:
       - Nutzung von Agent.compute_order_price(), d.h.:
         * falls eine PricingStrategy gesetzt ist → Strategy entscheidet,
         * sonst Fallback: Day-Ahead-Preis.
       - Damit sind wir kompatibel mit einer späteren MTAA-/Naive-Strategie.
    """

    # Modellparameter
    marginal_cost: float            # Grenzkosten [€/MWh]
    base_volume: float = 5.0        # typisches Ordervolumen pro Tick
    epsilon_price: float = 1.0      # Mindest-Marge in €/MWh
    imbalance_penalty: float = 0.0  # (aktuell nur Dokumentation, Kosten in simulation.py)

    def decide_order(
        self,
        t: int,
        public_info: PublicInfo,
    ) -> Optional[Order]:
        """
        Bestimme eine (ggf. leere) Order basierend auf:

        - aktueller Imbalance δ_t = da_position - market_position,
        - Kapazitätsrestriktionen,
        - Midprice vs. Grenzkosten,
        - Mindestmarge epsilon_price.

        Die konkrete Preisfindung wird an compute_order_price delegiert,
        wodurch eine zentrale PricingStrategy genutzt werden kann.
        """

        tob = public_info.tob
        bb = tob.best_bid_price
        ba = tob.best_ask_price

        # Wenn überhaupt kein Marktpreis vorliegt, nutzen wir DA-Preis.
        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
        elif bb is not None:
            mid = bb
        elif ba is not None:
            mid = ba
        else:
            mid = public_info.da_price

        # --- 2) Kapazität, Position & Imbalance -----------------------------
        pi = self.private_info
        cap = pi.effective_capacity
        da_pos = pi.da_position
        mar_pos = pi.market_position

        # Imbalance nach Shinde-Logik:
        # δ_t = da_position - market_position
        # δ_t > 0: unterverkauft relativ zur DA-Position
        # δ_t < 0: überverkauft relativ zur DA-Position
        delta = da_pos - mar_pos
        pi.imbalance = delta

        # Wenn praktisch keine DA-Lücke besteht oder keine Kapazität vorhanden
        if abs(delta) <= 1e-6 or cap <= 0.0:
            return None

        # Frei verfügbare „Restkapazität“ um die aktuelle Marktposition herum
        available_capacity = max(0.0, cap - abs(mar_pos))
        if available_capacity <= 0.0:
            return None

        # Volumen an Lücke und Kapazität koppeln (verhindert große Sprünge)
        volume = min(abs(delta), self.base_volume, available_capacity)
        if volume <= 0.0:
            return None

        # --- 3) Profitchancen relativ zu Grenzkosten prüfen -----------------
        spread_to_cost = mid - self.marginal_cost
        sell_profitable = spread_to_cost >= self.epsilon_price
        buy_profitable = spread_to_cost <= -self.epsilon_price

        # --- 4) Handelsrichtung bestimmen -----------------------------------
        side: Optional[Side] = None

        # Primär: Richtung, die die DA-Lücke schließt, falls profitabel
        if delta > 0.0:
            # Unterverkauft: wir müssen Marktposition erhöhen → SELL
            if sell_profitable:
                side = Side.SELL
        elif delta < 0.0:
            # Überverkauft: wir müssen Marktposition verringern → BUY
            if buy_profitable:
                side = Side.BUY

        # Fallback: wenn nur eine Richtung profitabel ist, nimm diese
        if side is None:
            if sell_profitable and not buy_profitable:
                side = Side.SELL
            elif buy_profitable and not sell_profitable:
                side = Side.BUY
            else:
                # Weder klare Marge noch sinnvolle DA-Korrektur → keine Order
                return None

        # --- 5) Limitpreis über PricingStrategy / Fallback bestimmen --------
        price = self.compute_order_price(
            public_info=public_info,
            side=side,
            volume=volume,
        )

        # --- 6) Order erzeugen ----------------------------------------------
        return Order(
            id=-1,  # wird vom MarketOperator gesetzt
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
        da_position: float,
        marginal_cost: float,
        base_volume: float,
        epsilon_price: float,
    ) -> "DispatchableAgent":
        """
        Convenience-Factory, um einen DispatchableAgent mit AgentPrivateInfo
        zu erzeugen.

        Hinweis: imbalance_penalty wird aktuell nicht direkt im Agenten
        genutzt, sondern die Imbalance-Kosten werden in simulation.py
        auf Basis der System-λ_up/λ_down berechnet.
        """
        priv = AgentPrivateInfo(
            effective_capacity=capacity,
            da_position=da_position,
        )
        return cls(
            id=id,
            private_info=priv,
            rng=rng,
            marginal_cost=marginal_cost,
            base_volume=base_volume,
            epsilon_price=epsilon_price,
            imbalance_penalty=0.0,
        )
