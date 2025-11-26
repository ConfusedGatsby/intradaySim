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
    - hat eine Grenzkosten-Schätzung (marginal_cost)
    - hat eine Day-Ahead-Position (private_info.da_position)
    - besitzt eine effektive Kapazität (private_info.effective_capacity)
    - beobachtet Day-Ahead-Preis und aktuelles Top-of-Book (PublicInfo)

    Entscheidungslogik (Heuristik):
    - Wenn Marktpreis deutlich über Grenzkosten liegt und noch Volumen
      zu verkaufen ist (DA-Position noch nicht erreicht), dann SELL.
    - Wenn Marktpreis deutlich unter Grenzkosten liegt und die aktuelle
      Marktposition zu hoch ist (Überverkauf), dann BUY.
    - Volumen wird durch Kapazität und Abweichung von der DA-Position begrenzt.

    Imbalance-Definition:
    - δ_t = da_position - market_position
      > 0  => Unterlieferung (wir „hängen hinterher“ → eher SELL)
      < 0  => Überlieferung (zu viel verkauft)       → eher BUY

    Imbalance-Kosten:
    - Die eigentliche finanzielle Abrechnung erfolgt zentral in der
      Simulation (z.B. einmalig am Ende des Zeithorizonts).
    - Diese Klasse setzt nur pi.imbalance als physisches Steuersignal.
    - Das Feld imbalance_penalty ist aktuell nur als Konfig-Parameter
      vorgesehen (für spätere lokale Heuristiken), wird aber NICHT
      mehr benutzt, um Kosten aufzuräumen.
    """

    marginal_cost: float          # Grenzkosten [€/MWh]
    base_volume: float = 5.0      # typisches Ordervolumen
    epsilon_price: float = 1.0    # Mindest-Marge in €/MWh
    imbalance_penalty: float = 0.0  # aktuell nur „Deko“, zentrale Kosten in simulation.py

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft eine Shinde-inspirierte Handelsentscheidung.

        - Nutzt DA-Position und aktuelle Marktposition
        - vergleicht Midprice / TOB-Preise mit Grenzkosten
        - wählt SELL/BUY und Limitpreis innerhalb eines sinnvollen Intervalls
        """

        # --- 1) Preis-Signale rekonstruieren --------------------------------
        bb = public_info.tob.best_bid_price
        ba = public_info.tob.best_ask_price

        if bb is None and ba is None:
            # kein Marktpreis beobachtbar
            return None

        if bb is not None and ba is not None:
            mid = 0.5 * (bb + ba)
        else:
            # fallback: nutze existierenden TOB-Preis oder DA-Preis
            mid = bb if bb is not None else ba
        if mid is None:
            mid = public_info.da_price

        # --- 2) Kapazität, Position & Imbalance -----------------------------
        pi = self.private_info
        cap = pi.effective_capacity
        da_pos = pi.da_position
        mar_pos = pi.market_position

        # Imbalance nach Shinde-Logik:
        # δ_t = da_position - market_position
        imbalance = da_pos - mar_pos
        pi.imbalance = imbalance

        # >>> WICHTIG: keine lokale Akkumulation von Imbalance-Kosten mehr <<<
        # Die eigentliche Abrechnung erfolgt zentral in der Simulation.

        # Wie weit sind wir von der DA-Position entfernt?
        # positive Lücke: wir können noch verkaufen,
        # negative Lücke: wir sind über die DA-Position hinaus verkauft.
        pos_gap = imbalance  # = da_pos - mar_pos

        # frei verfügbare zusätzliche Nutzung (Symmetrie um 0 herum)
        available_capacity = max(0.0, cap - abs(mar_pos))
        if available_capacity <= 0.0:
            return None

        # Volumen an Lücke und Kapazität koppeln
        # (verhindert unrealistisch große Orders)
        raw_volume = min(abs(pos_gap), self.base_volume)
        volume = min(raw_volume, available_capacity)
        if volume <= 0.0:
            return None

        # --- 3) Profitchancen relativ zu Grenzkosten prüfen -----------------
        spread_to_cost = mid - self.marginal_cost

        # SELL profitabel: Marktpreis deutlich über Grenzkosten
        sell_profitable = spread_to_cost >= self.epsilon_price
        # BUY profitabel: Marktpreis deutlich unter Grenzkosten
        buy_profitable = spread_to_cost <= -self.epsilon_price

        # Wenn weder Kauf noch Verkauf eine klare Marge bietet -> abwarten
        if not sell_profitable and not buy_profitable:
            return None

        # --- 4) Handelsrichtung bestimmen -----------------------------------
        # Priorität: DA-Lücke schließen
        if sell_profitable and pos_gap > 0:
            side = Side.SELL
        elif buy_profitable and pos_gap < 0:
            side = Side.BUY
        else:
            # Wenn Richtungen „konflikten“, wähle stärkere Marge
            if sell_profitable and not buy_profitable:
                side = Side.SELL
            elif buy_profitable and not sell_profitable:
                side = Side.BUY
            else:
                # beide profitabel: wähle stärkere Abweichung von den Kosten
                if abs(spread_to_cost) == 0:
                    return None
                if spread_to_cost > 0:
                    side = Side.SELL
                else:
                    side = Side.BUY

        # --- 5) Limitpreis Naive-artig um Mid herum -------------------------
        price_spread = 2.0  # kleine Hilfsspanne, könnte später parametrisierbar werden

        if side == Side.SELL:
            # verkaufen etwas über Mid, aber nicht unter Grenzkosten
            low = max(self.marginal_cost, mid)
            high = max(low, mid + price_spread)
            price = self.rng.uniform(low, high)
        else:  # BUY
            # kaufen etwas unter Mid, aber nicht über Grenzkosten
            high = min(self.marginal_cost, mid)
            low = min(high, mid - price_spread)
            price = self.rng.uniform(low, high)

        return Order(
            id=-1,  # MarketOperator vergibt finale Order-ID
            agent_id=self.id,
            side=side,
            price=price,
            volume=volume,
            product_id=0,
        )

    @classmethod
    def create(
        cls,
        id: int,
        rng,
        capacity: float,
        da_position: float,
        marginal_cost: float,
        base_volume: float = 5.0,
        epsilon_price: float = 1.0,
        imbalance_penalty: float = 0.0,
    ) -> "DispatchableAgent":
        """
        Convenience-Factory:
        erzeugt einen DispatchableAgent mit AgentPrivateInfo.

        - capacity: effektive Kapazität C_max
        - da_position: Day-Ahead-Position p_i^{DA}
        - imbalance_penalty: (derzeit ungenutzt in der Agentenlogik,
          Abrechnung der Imbalance-Kosten erfolgt zentral in simulation.py)
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
            imbalance_penalty=imbalance_penalty,
        )
