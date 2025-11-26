from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from random import Random
from typing import Optional

from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side
from intraday_abm.core.order import Order
from intraday_abm.agents.pricing_strategies import PricingStrategy


@dataclass
class Agent(ABC):
    """
    Abstrakte Basisklasse für alle Agenten.

    - id: eindeutige Agenten-ID
    - private_info: enthält Kapazität, Position, Erlöse, Imbalance etc.
    - rng: Agent-lokaler Zufallszahlengenerator
    - pricing_strategy: optionale Preisstrategie (naiv / MTAA nach Shinde)
    """

    id: int
    private_info: AgentPrivateInfo
    rng: Random = field(repr=False)

    # WICHTIG:
    # - init=False → dieses Feld taucht NICHT als Parameter im __init__ auf.
    #   Damit kollidiert es NICHT mit den Feldern der Kindklassen.
    # - Default = None → wir können später optional eine Strategy zuweisen.
    pricing_strategy: Optional[PricingStrategy] = field(
        default=None,
        repr=False,
        init=False,
    )

    @abstractmethod
    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft zum Zeitpunkt t eine Handelsentscheidung.
        Gibt eine Order zurück oder None (keine Aktivität in diesem Schritt).
        """
        ...

    def update_imbalance(self, t: int) -> None:
        """
        Standard-Imbalance-Definition (für nicht-physische Agents):

        δ_{i,t} = da_position_i - market_position_i

        Für Random/Trend/Dispatchable ist das „physische Ziel“ die
        Day-Ahead-Position (Default 0). VariableAgent überschreibt
        diese Methode und nutzt Forecast(t).
        """
        pi = self.private_info
        pi.imbalance = pi.da_position - pi.market_position

    def compute_order_price(
        self,
        *,
        public_info: PublicInfo,
        side: Side,
        volume: float,
    ) -> float:
        """
        Zentraler Zugriffspunkt für Preisstrategien nach Shinde.

        Falls eine PricingStrategy gesetzt ist, wird deren compute_price(...)
        verwendet. Andernfalls wird ein einfacher Fallback genutzt
        (derzeit: Day-Ahead-Preis).
        """
        if self.pricing_strategy is None:
            # Fallback, damit existierender Code weiterläuft,
            # solange Agenten noch nicht explizit Strategien zugewiesen bekommen.
            return public_info.da_price

        return self.pricing_strategy.compute_price(
            agent=self,
            public_info=public_info,
            side=side,
            volume=volume,
        )

    def on_trade(self, volume: float, price: float, side: Side) -> None:
        """
        Aktualisiert Marktposition und Erlöse nach einem Trade.

        Orientierung an Shinde:
        - market_position p_mar erhöht sich bei Verkäufen, verringert sich bei Käufen
        - revenue r_{i,t} steigt bei Verkäufen und fällt bei Käufen
        """
        if side == Side.SELL:
            # Verkauft: Position steigt, Erlöse steigen
            self.private_info.market_position += volume
            self.private_info.revenue += volume * price
        else:  # BUY
            # Gekauft: Position sinkt, „Erlös“ wird negativer (Kosten)
            self.private_info.market_position -= volume
            self.private_info.revenue -= volume * price
