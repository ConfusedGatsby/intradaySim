"""
Pricing Strategies für Trading Agents

Enthält:
- PricingStrategy (Abstract Base Class)
- NaivePricingStrategy (JETZT Shinde-konform, Equations 20-27)
- MTAAPricingStrategy (Placeholder)
"""

from __future__ import annotations
from typing import List, Tuple, Optional
from random import Random

from intraday_abm.core.types import Side, PublicInfo


# ============================================================================
# BASE CLASS
# ============================================================================

class PricingStrategy:
    """
    Abstrakte Basisklasse für Preisstrategien.
    
    Jede konkrete Strategie muss implementieren:
    - build_price_volume_curve(): Für RandomLiquidityAgent (mehrere Orders)
    - compute_price(): Für DispatchableAgent/VariableAgent (einzelne Order)
    """
    
    def __init__(self, rng: Random):
        self.rng = rng
    
    def build_price_volume_curve(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> List[Tuple[float, float]]:
        """
        Erzeugt eine Price-Volume-Kurve für den Agenten.
        
        Args:
            agent: Agent der die Orders platziert
            public_info: Öffentliche Marktinformation (ToB, DA-Preis)
            side: BUY oder SELL
            total_volume: Gesamtvolumen zu handeln
            
        Returns:
            Liste von (price, volume) Tupeln
        """
        raise NotImplementedError
    
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
        Berechnet einen einzelnen Preis für eine Order.
        
        Args:
            agent: Agent der die Order platziert (optional)
            public_info: Öffentliche Marktinformation
            side: BUY oder SELL
            volume: Ordervolumen
            
        Returns:
            Preis für die Order
        """
        raise NotImplementedError


# ============================================================================
# NAIVE STRATEGY (JETZT SHINDE-KONFORM!)
# ============================================================================

class NaivePricingStrategy(PricingStrategy):
    """
    Shinde-konforme Naive Pricing Strategy.
    
    Implementiert Equations 20-27 aus:
    Shinde et al., "Analyzing Trade in Continuous Intraday Electricity Market"
    
    SELL Orders (Equations 20-21):
        π_min^sell = max(bbp_t - π_range, l_t^sell)
        π_max^sell = max(bap_t + π_range, l_t^sell + π_range)
    
    BUY Orders (Equations 22-23):
        π_min^buy = min(bbp_t - π_range, l_t^buy - π_range)
        π_max^buy = min(bap_t + π_range, l_t^buy)
    
    Attributes:
        rng: Random number generator
        pi_range: Preisintervall-Parameter (π_range)
        n_segments: Anzahl Preissegmente (für build_price_volume_curve)
        n_orders: Anzahl Orders zu erstellen
        min_price: Absolute Preisuntergrenze
        max_price: Absolute Preisobergrenze
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
        """
        Initialisiere Naive Pricing Strategy.
        
        Args:
            rng: Random number generator
            pi_range: Preisintervall-Parameter (typisch 5-10 €/MWh)
            n_segments: Anzahl Preissegmente (wird für Kompatibilität behalten)
            n_orders: Anzahl Orders zu erstellen
            min_price: Absolute Preisuntergrenze
            max_price: Absolute Preisobergrenze
        """
        super().__init__(rng)
        self.pi_range = pi_range
        self.n_segments = max(1, n_segments)  # Für Legacy-Kompatibilität
        self.n_orders = max(1, n_orders)
        self.min_price = min_price
        self.max_price = max_price
    
    # -------------------------------------------------------------------------
    # Hilfsfunktionen
    # -------------------------------------------------------------------------
    
    def _get_limit_prices(self, agent: "Agent") -> Tuple[float, float]:
        """
        Holt Limit Prices aus Agent's Private Info.
        
        Args:
            agent: Agent Instanz
            
        Returns:
            (limit_buy, limit_sell) Tupel
        """
        pi = agent.private_info
        
        # Check if agent has limit prices
        if hasattr(pi, 'limit_buy') and hasattr(pi, 'limit_sell'):
            return pi.limit_buy, pi.limit_sell
        
        # Fallback: Verwende vernünftige Defaults
        # limit_buy = max_price (bereit viel zu zahlen)
        # limit_sell = min_price (bereit billig zu verkaufen)
        return self.max_price, self.min_price
    
    def _clip_price(self, p: float) -> float:
        """Clippe Preis auf absolute Grenzen."""
        return max(self.min_price, min(self.max_price, p))
    
    # -------------------------------------------------------------------------
    # Für RandomLiquidityAgent (Price-Volume-Kurve)
    # -------------------------------------------------------------------------
    
    def build_price_volume_curve(
        self,
        *,
        agent: "Agent",
        public_info: PublicInfo,
        side: Side,
        total_volume: float,
    ) -> List[Tuple[float, float]]:
        """
        Erstelle Price-Volume-Kurve nach Shinde Naive Strategy (Eqs 20-27).
        
        Args:
            agent: Agent der die Orders platziert
            public_info: Aktuelle Marktinformation (ToB, DA-Preis)
            side: BUY oder SELL
            total_volume: Gesamtvolumen zu verteilen
            
        Returns:
            Liste von (price, volume) Tupeln
        """
        if total_volume <= 0.0:
            return []
        
        # Hole Top of Book
        tob = public_info.tob
        bbp = tob.best_bid_price if tob.best_bid_price is not None else public_info.da_price
        bap = tob.best_ask_price if tob.best_ask_price is not None else public_info.da_price
        
        # Hole Limit Prices vom Agent
        limit_buy, limit_sell = self._get_limit_prices(agent)
        
        # Berechne Preisintervall basierend auf Side (SHINDE EQUATIONS 20-23)
        if side == Side.SELL:
            # Equation 20-21
            pi_min = max(bbp - self.pi_range, limit_sell)
            pi_max = max(bap + self.pi_range, limit_sell + self.pi_range)
        else:  # BUY
            # Equation 22-23
            pi_min = min(bbp - self.pi_range, limit_buy - self.pi_range)
            pi_max = min(bap + self.pi_range, limit_buy)
        
        # Clippe auf absolute Grenzen
        pi_min = self._clip_price(pi_min)
        pi_max = self._clip_price(pi_max)
        
        # Handle degeneriertes Intervall
        if pi_max <= pi_min:
            # Alle Orders am gleichen Preis
            return [(pi_min, total_volume)]
        
        # Verteile Volume gleichmäßig (Equation 27)
        vol_per_order = total_volume / float(self.n_orders)
        
        # Sample n Preise uniform aus [pi_min, pi_max] (SHINDE METHOD)
        curve: List[Tuple[float, float]] = []
        
        for _ in range(self.n_orders):
            # Uniform Random Sampling aus Preisintervall
            price = self.rng.uniform(pi_min, pi_max)
            curve.append((price, vol_per_order))
        
        return curve
    
    # -------------------------------------------------------------------------
    # Für DispatchableAgent / VariableAgent (einzelner Preis)
    # -------------------------------------------------------------------------
    
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
        Berechne einzelnen Preis nach Shinde Naive Strategy.
        
        Args:
            agent: Agent der die Order platziert
            public_info: Aktuelle Marktinformation
            side: BUY oder SELL
            volume: Ordervolumen (nicht genutzt in Naive Strategy)
            
        Returns:
            Gesampelter Preis
        """
        if agent is None:
            # Fallback zu DA-Preis
            return public_info.da_price
        
        # Hole Top of Book
        tob = public_info.tob
        bbp = tob.best_bid_price if tob.best_bid_price is not None else public_info.da_price
        bap = tob.best_ask_price if tob.best_ask_price is not None else public_info.da_price
        
        # Hole Limit Prices
        limit_buy, limit_sell = self._get_limit_prices(agent)
        
        # Berechne Preisintervall (SHINDE EQUATIONS)
        if side == Side.SELL:
            pi_min = max(bbp - self.pi_range, limit_sell)
            pi_max = max(bap + self.pi_range, limit_sell + self.pi_range)
        else:  # BUY
            pi_min = min(bbp - self.pi_range, limit_buy - self.pi_range)
            pi_max = min(bap + self.pi_range, limit_buy)
        
        # Clippe
        pi_min = self._clip_price(pi_min)
        pi_max = self._clip_price(pi_max)
        
        # Sample
        if pi_max <= pi_min:
            return pi_min
        
        return self.rng.uniform(pi_min, pi_max)


# ============================================================================
# MTAA STRATEGY (Placeholder)
# ============================================================================

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
    
    def compute_price(
        self,
        *,
        agent: Optional["Agent"] = None,
        public_info: PublicInfo,
        side: Side,
        volume: float,
        **kwargs,
    ) -> float:
        raise NotImplementedError("MTAA-Strategie ist noch nicht implementiert.")