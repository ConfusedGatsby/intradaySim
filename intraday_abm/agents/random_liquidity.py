from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Union

from intraday_abm.agents.base import Agent
from intraday_abm.core.types import Side, PublicInfo, AgentPrivateInfo
from intraday_abm.core.order import Order


@dataclass
class RandomLiquidityAgent(Agent):
    """
    Shinde-nahe naive Trader mit diskretem Preisband und mehreren Orders.
    
    Unterstützt BEIDE Modi:
    - Single-Product: Platziert Orders für ein Produkt
    - Multi-Product: Platziert Orders für mehrere Produkte
    
    Refaktorisierte Version (Phase 1 + 2 + Multi-Product):

    - Die eigentliche Preisband- und Preisfindungslogik liegt in einer
      externen PricingStrategy (z.B. NaivePricingStrategy).
    - Der Agent selbst entscheidet nur noch:
        * wie viele Orders er typischerweise platzieren möchte (n_orders)
        * welches Gesamtvolumen er in einem Tick bereitstellen möchte
        * die Orderrichtung (BUY/SELL) pro Order
        * lokale Volumengrenzen pro Order

    Die Strategy wird von außen (in der Simulation) zugewiesen:
    agent.pricing_strategy = <PricingStrategy-Instanz>
    
    **Multi-Product Verhalten:**
    - Platziert Orders in ALLEN offenen Produkten
    - Unabhängige zufällige Sides pro Produkt
    - Gleiche Volumen-Parameter für alle Produkte
    - Keine Imbalance (liefert nur Liquidität)
    
    Attributes:
        min_price: Minimum price for orders
        max_price: Maximum price for orders
        min_volume: Minimum volume per order
        max_volume: Maximum volume per order
        price_band_pi: Price band width (used by PricingStrategy)
        n_segments: Number of price segments (used by PricingStrategy)
        n_orders: Number of orders to place per step
    """

    min_price: float
    max_price: float
    min_volume: float
    max_volume: float

    # Shinde-nahe Konfig:
    # price_band_pi und n_segments werden von der Strategy genutzt und sind
    # hier nur noch zur Dokumentation / Konsistenz abgelegt. n_orders wird
    # lokal genutzt, um das Ziel-Gesamtvolumen pro Tick zu bestimmen.
    price_band_pi: float = 10.0
    n_segments: int = 20
    n_orders: int = 5

    # ------------------------------------------------------------------
    # Single-Product Interface
    # ------------------------------------------------------------------

    def decide_order(self, t: int, public_info: PublicInfo) -> Optional[Order | List[Order]]:
        """
        Platziert mehrere Orders (Single-Product), deren Preise durch eine PricingStrategy
        (z.B. NaivePricingStrategy) bestimmt werden.

        Schritte:
        1. Gesamtvolumen abschätzen, das der Agent in diesem Tick bereitstellen
           möchte (auf Basis von min/max_volume und n_orders).
        2. Über die PricingStrategy eine diskrete Price-Volume-Curve erzeugen.
        3. Für jedes Preis-Volumen-Paar eine Order mit zufälliger Side erzeugen.
        
        Args:
            t: Current simulation time
            public_info: Public market information
            
        Returns:
            List of Orders or None
        """

        # Fallback: wenn keine Strategy gesetzt ist, keine Aktivität
        if self.pricing_strategy is None:
            return None

        if self.n_orders <= 0:
            return None

        # Einfacher Ansatz: Gesamtvolumen = erwarteter Mittelwert aller Orders
        avg_volume = 0.5 * (self.min_volume + self.max_volume)
        total_volume = avg_volume * self.n_orders

        if total_volume <= 0.0:
            return None

        # Die Preisstrategie erzeugt eine diskrete Price-Volume-Kurve.
        # Hinweis: Für die Referenzpreis-Bestimmung ist bei vorhandenem Bid & Ask
        # die Side hier irrelevant (Midprice). Wir geben BUY mit.
        curve = self.pricing_strategy.build_price_volume_curve(
            agent=self,
            public_info=public_info,
            side=Side.BUY,
            total_volume=total_volume,
        )

        if not curve:
            return None

        orders: List[Order] = []

        for price, vol in curve:
            # Volumen innerhalb der Agenten-Grenzen halten
            volume = max(self.min_volume, min(self.max_volume, vol))
            if volume <= 0.0:
                continue

            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL

            order = Order(
                id=-1,
                agent_id=self.id,
                side=side,
                price=price,
                volume=volume,
                product_id=0,
            )
            orders.append(order)

        if not orders:
            return None

        return orders

    # ------------------------------------------------------------------
    # Multi-Product Interface
    # ------------------------------------------------------------------

    def decide_orders(
        self, 
        t: int, 
        public_info: Dict[int, PublicInfo]
    ) -> Dict[int, Union[Order, List[Order]]]:
        """
        Multi-Product: Platziert Orders für mehrere Produkte.
        
        Strategie:
        - Für jedes offene Produkt: Nutze gleiche Logik wie decide_order()
        - Unabhängige zufällige Sides pro Produkt
        - Liefert Liquidität auf beiden Seiten
        
        Args:
            t: Current simulation time
            public_info: Dict mapping product_id to PublicInfo
            
        Returns:
            Dict mapping product_id to List[Order]
        """
        if not self.is_multi_product:
            # Fallback to single-product
            return super().decide_orders(t, public_info)
        
        all_orders = {}
        
        for product_id, pub_info in public_info.items():
            orders = self._decide_for_product(t, product_id, pub_info)
            if orders:
                all_orders[product_id] = orders
        
        return all_orders

    def _decide_for_product(
        self, 
        t: int, 
        product_id: int, 
        public_info: PublicInfo
    ) -> Optional[List[Order]]:
        """
        Hilfsmethode: Entscheide Orders für ein spezifisches Produkt.
        
        Nutzt die gleiche Logik wie decide_order(), aber mit product_id.
        
        Args:
            t: Current simulation time
            product_id: Product to trade
            public_info: Public info for this product
            
        Returns:
            List of Orders or None
        """
        # Fallback: wenn keine Strategy gesetzt ist, keine Aktivität
        if self.pricing_strategy is None:
            return None

        if self.n_orders <= 0:
            return None

        # Einfacher Ansatz: Gesamtvolumen = erwarteter Mittelwert aller Orders
        avg_volume = 0.5 * (self.min_volume + self.max_volume)
        total_volume = avg_volume * self.n_orders

        if total_volume <= 0.0:
            return None

        # Die Preisstrategie erzeugt eine diskrete Price-Volume-Kurve.
        curve = self.pricing_strategy.build_price_volume_curve(
            agent=self,
            public_info=public_info,
            side=Side.BUY,
            total_volume=total_volume,
        )

        if not curve:
            return None

        orders: List[Order] = []

        for price, vol in curve:
            # Volumen innerhalb der Agenten-Grenzen halten
            volume = max(self.min_volume, min(self.max_volume, vol))
            if volume <= 0.0:
                continue

            # Zufällige Side für dieses Produkt
            side = Side.BUY if self.rng.random() < 0.5 else Side.SELL

            order = Order(
                id=-1,
                agent_id=self.id,
                side=side,
                price=price,
                volume=volume,
                product_id=product_id,
            )
            orders.append(order)

        if not orders:
            return None

        return orders

    # ------------------------------------------------------------------
    # Override BaseAgent methods
    # ------------------------------------------------------------------
    
    def update_imbalance(self, t: int, product_id: Optional[int] = None) -> None:
        """
        RandomLiquidityAgent hat keine physische Imbalance.
        
        Diese Methode überschreibt die BaseAgent-Implementierung,
        da RandomLiquidity kein "physisches Ziel" hat - er liefert
        nur Liquidität auf beiden Seiten.
        
        Args:
            t: Current simulation time
            product_id: Product to update (Multi-Product only)
        """
        # RandomLiquidity hat keine Imbalance
        # Setze auf 0 für Logging/Tracking
        if self.is_multi_product:
            if product_id is not None:
                self.private_info.set_imbalance(product_id, 0.0)
        else:
            self.private_info.imbalance = 0.0

    # ------------------------------------------------------------------
    # Factory Method
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        *,
        id: int,
        rng,
        capacity: float,
        min_price: float,
        max_price: float,
        min_volume: float,
        max_volume: float,
        price_band_pi: float = 10.0,
        n_segments: int = 20,
        n_orders: int = 5,
    ) -> "RandomLiquidityAgent":
        """
        Factory-Methode zum Erzeugen eines RandomLiquidityAgent (Single-Product).

        WICHTIG (Phase 2):
        - Die eigentliche PricingStrategy (Naive / MTAA / ...) wird NICHT mehr
          hier erzeugt, sondern in der Simulation und anschließend dem Agenten
          zugewiesen:
              agent.pricing_strategy = strategy

        - Die hier übergebenen Parameter (insbesondere n_orders) steuern nur
          das agentenspezifische Verhalten (z.B. Ziel-Gesamtvolumen pro Tick).
          
        Args:
            id: Agent ID
            rng: Random number generator
            capacity: Agent capacity
            min_price: Minimum price for orders
            max_price: Maximum price for orders
            min_volume: Minimum volume per order
            max_volume: Maximum volume per order
            price_band_pi: Price band width
            n_segments: Number of price segments
            n_orders: Number of orders per step
            
        Returns:
            RandomLiquidityAgent instance
        """
        priv = AgentPrivateInfo(effective_capacity=capacity)

        agent = cls(
            id=id,
            private_info=priv,
            rng=rng,
            min_price=min_price,
            max_price=max_price,
            min_volume=min_volume,
            max_volume=max_volume,
            price_band_pi=price_band_pi,
            n_segments=n_segments,
            n_orders=n_orders,
        )

        return agent