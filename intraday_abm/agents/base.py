from __future__ import annotations

from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from random import Random
from typing import Optional, Union, Dict, List

from intraday_abm.core.types import PublicInfo, AgentPrivateInfo, Side
from intraday_abm.core.order import Order
from intraday_abm.agents.pricing_strategies import PricingStrategy

# Import MultiProductPrivateInfo with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo


@dataclass
class Agent(ABC):
    """
    Abstrakte Basisklasse für alle Agenten - unterstützt Single UND Multi-Product.

    Diese Klasse kann in zwei Modi operieren:
    
    **Single-Product Mode (original):**
    - private_info: AgentPrivateInfo (scalar values)
    - decide_order(t, public_info) → Optional[Order]
    - update_imbalance(t) für ein Produkt
    
    **Multi-Product Mode (neu):**
    - private_info: MultiProductPrivateInfo (dict per product_id)
    - decide_orders(t, public_info: Dict) → Dict[int, Order]
    - update_imbalance(t, product_id) für spezifisches Produkt
    
    Attributes:
        id: eindeutige Agenten-ID
        private_info: AgentPrivateInfo (single) oder MultiProductPrivateInfo (multi)
        rng: Agent-lokaler Zufallszahlengenerator
        pricing_strategy: optionale Preisstrategie (naiv / MTAA nach Shinde)
        is_multi_product: Flag ob Agent im Multi-Product Modus läuft
    
    Example:
        # Single-Product (alt):
        agent = VariableAgent(
            id=1,
            private_info=AgentPrivateInfo(capacity=100.0, ...),
            rng=Random(42)
        )
        order = agent.decide_order(t=100, public_info=...)
        
        # Multi-Product (neu):
        agent = VariableAgent(
            id=1,
            private_info=MultiProductPrivateInfo.initialize(products, ...),
            rng=Random(42)
        )
        orders = agent.decide_orders(t=100, public_info={0: ..., 1: ...})
    """

    id: int
    private_info: Union[AgentPrivateInfo, MultiProductPrivateInfo]
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

    def __post_init__(self):
        """
        Detect if agent is in multi-product mode.
        
        This is done by checking the type of private_info.
        """
        # Avoid circular import by checking class name
        self.is_multi_product = (
            type(self.private_info).__name__ == 'MultiProductPrivateInfo'
        )

    # ------------------------------------------------------------------
    # SINGLE-PRODUCT INTERFACE (Original - bleibt unverändert)
    # ------------------------------------------------------------------

    @abstractmethod
    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order]:
        """
        Trifft zum Zeitpunkt t eine Handelsentscheidung (Single-Product).
        
        Gibt eine Order zurück oder None (keine Aktivität in diesem Schritt).
        
        Args:
            t: Current simulation time
            public_info: Public market information
            
        Returns:
            Order or None
        
        Note:
            Diese Methode ist für Single-Product Mode.
            Für Multi-Product, überschreiben Sie decide_orders().
        """
        ...

    def update_imbalance(self, t: int, product_id: Optional[int] = None) -> None:
        """
        Standard-Imbalance-Definition.
        
        **Single-Product Mode (product_id=None):**
        δ_{i,t} = da_position_i - market_position_i
        
        **Multi-Product Mode (product_id specified):**
        δ_{i,t,d} = da_position_{i,d} - market_position_{i,d}
        
        Args:
            t: Current simulation time
            product_id: Product to update (Multi-Product only)
        
        Note:
            Für Random/Trend/Dispatchable ist das „physische Ziel" die
            Day-Ahead-Position (Default 0). VariableAgent überschreibt
            diese Methode und nutzt Forecast(t).
        """
        if self.is_multi_product:
            if product_id is None:
                raise ValueError("product_id required for multi-product agents")
            
            # Multi-Product mode
            pi = self.private_info
            da_pos = pi.da_positions.get(product_id, 0.0)
            market_pos = pi.positions.get(product_id, 0.0)
            pi.set_imbalance(product_id, da_pos - market_pos)
        else:
            # Single-Product mode (original)
            pi = self.private_info
            pi.imbalance = pi.da_position - pi.market_position

    def on_trade(
        self, 
        volume: float, 
        price: float, 
        side: Side,
        product_id: Optional[int] = None
    ) -> None:
        """
        Aktualisiert Marktposition und Erlöse nach einem Trade.

        **Single-Product Mode (product_id=None):**
        Orientierung an Shinde:
        - market_position p_mar erhöht sich bei Verkäufen, verringert sich bei Käufen
        - revenue r_{i,t} steigt bei Verkäufen und fällt bei Käufen
        
        **Multi-Product Mode (product_id specified):**
        - positions[product_id] updated
        - revenues[product_id] updated
        
        Args:
            volume: Traded volume
            price: Trade price
            side: BUY or SELL
            product_id: Product traded (Multi-Product only)
        """
        if self.is_multi_product:
            if product_id is None:
                raise ValueError("product_id required for multi-product agents")
            
            # Multi-Product mode
            pi = self.private_info
            if side == Side.SELL:
                pi.update_position(product_id, volume)
                pi.update_revenue(product_id, volume * price)
            else:  # BUY
                pi.update_position(product_id, -volume)
                pi.update_revenue(product_id, -volume * price)
        else:
            # Single-Product mode (original)
            if side == Side.SELL:
                self.private_info.market_position += volume
                self.private_info.revenue += volume * price
            else:  # BUY
                self.private_info.market_position -= volume
                self.private_info.revenue -= volume * price

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
        
        Args:
            public_info: Public market information
            side: BUY or SELL
            volume: Order volume
            
        Returns:
            Order price
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

    # ------------------------------------------------------------------
    # MULTI-PRODUCT INTERFACE (Neu)
    # ------------------------------------------------------------------

    def decide_orders(
        self, 
        t: int, 
        public_info: Dict[int, PublicInfo]
    ) -> Dict[int, Union[Order, List[Order]]]:
        """
        Trifft Handelsentscheidungen für mehrere Produkte (Multi-Product).
        
        Diese Methode wird von Multi-Product Simulation aufgerufen.
        Agents können für jedes Produkt 0, 1, oder mehrere Orders zurückgeben.
        
        Args:
            t: Current simulation time
            public_info: Dict mapping product_id to PublicInfo
            
        Returns:
            Dict mapping product_id to Order(s) or empty dict
        
        Example:
            def decide_orders(self, t, public_info):
                orders = {}
                for product_id, pub_info in public_info.items():
                    order = self._decide_for_product(t, product_id, pub_info)
                    if order:
                        orders[product_id] = order
                return orders
        
        Note:
            - Default implementation falls back to single-product decide_order()
            - Subclasses should override for true multi-product logic
        """
        if not self.is_multi_product:
            # Fallback für Single-Product Agents in Multi-Product Simulation
            # Nutze das erste (und einzige) Produkt
            if not public_info:
                return {}
            
            product_id = list(public_info.keys())[0]
            single_public = public_info[product_id]
            
            order = self.decide_order(t, single_public)
            if order:
                # Stelle sicher, dass product_id gesetzt ist
                order.product_id = product_id
                return {product_id: order}
            return {}
        
        # Multi-Product Agents müssen diese Methode überschreiben
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement decide_orders() "
            "for multi-product mode"
        )