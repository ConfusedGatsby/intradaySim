"""
Core type definitions for the CID market simulation.

Defines fundamental types used throughout the simulation:
- Side, TimeInForce enums
- TopOfBook (market state snapshot)
- PublicInfo (public market information)
- AgentPrivateInfo (single-product agent state)
- MultiProductPrivateInfo (multi-product agent state)

Both PrivateInfo classes include Shinde limit prices (limit_buy, limit_sell).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Dict, List, TYPE_CHECKING

if TYPE_CHECKING:
    from intraday_abm.core.product import Product


# ============================================================================
# ENUMS
# ============================================================================

class Side(Enum):
    """Order direction in the order book."""
    BUY = auto()
    SELL = auto()


class TimeInForce(Enum):
    """Order validity duration."""
    GTC = auto()  # Good till cancelled
    IOC = auto()  # Immediate or cancel


# ============================================================================
# MARKET STATE TYPES
# ============================================================================

@dataclass
class TopOfBook:
    """
    Top-of-Book (TOB) snapshot for a specific product.
    
    Represents the best available bid and ask prices and volumes
    at a specific point in time.
    
    Attributes:
        best_bid_price: Highest bid price (buy), or None if no bids
        best_bid_volume: Volume at best bid level, or None
        best_ask_price: Lowest ask price (sell), or None if no asks
        best_ask_volume: Volume at best ask level, or None
    
    Example:
        tob = TopOfBook(
            best_bid_price=49.5,
            best_bid_volume=10.0,
            best_ask_price=50.5,
            best_ask_volume=15.0
        )
        
        midprice = tob.midprice()  # 50.0
        spread = tob.spread()      # 1.0
    """
    best_bid_price: Optional[float]
    best_bid_volume: Optional[float]
    best_ask_price: Optional[float]
    best_ask_volume: Optional[float]
    
    def midprice(self) -> Optional[float]:
        """
        Calculate midprice (average of best bid and ask).
        
        Returns:
            (best_bid_price + best_ask_price) / 2, or None if either is missing
        """
        if self.best_bid_price is not None and self.best_ask_price is not None:
            return 0.5 * (self.best_bid_price + self.best_ask_price)
        return None
    
    def spread(self) -> Optional[float]:
        """
        Calculate bid-ask spread.
        
        Returns:
            best_ask_price - best_bid_price, or None if either is missing
        """
        if self.best_bid_price is not None and self.best_ask_price is not None:
            return self.best_ask_price - self.best_bid_price
        return None
    
    def has_bid(self) -> bool:
        """Check if there is at least one bid in the book."""
        return self.best_bid_price is not None
    
    def has_ask(self) -> bool:
        """Check if there is at least one ask in the book."""
        return self.best_ask_price is not None
    
    def is_crossed(self) -> bool:
        """
        Check if book is crossed (bid >= ask).
        
        This should never happen in a properly functioning market,
        but can be useful for debugging.
        """
        if self.best_bid_price is not None and self.best_ask_price is not None:
            return self.best_bid_price >= self.best_ask_price
        return False


@dataclass
class PublicInfo:
    """
    Public market information available to all agents for a specific product.
    
    Represents the observable market state s_public = (TOB, DA-price, product).
    
    Attributes:
        tob: Top-of-book snapshot (best bid/ask prices and volumes)
        da_price: Day-ahead clearing price for this product (€/MWh)
        product: Optional Product metadata (delivery times, gate times, etc.)
    
    Example:
        from intraday_abm.core.product import create_single_product
        
        product = create_single_product(product_id=0, da_price=50.0)
        tob = TopOfBook(best_bid_price=49.0, best_ask_price=51.0, ...)
        
        public_info = PublicInfo(
            tob=tob,
            da_price=50.0,
            product=product
        )
    """
    tob: TopOfBook
    da_price: float
    product: Optional[Product] = None
    
    def time_to_gate_close(self, t: int) -> Optional[int]:
        """
        Convenience method to get time until gate closure.
        
        Args:
            t: Current simulation time
            
        Returns:
            Time steps until gate_close, or None if product not available
        """
        if self.product is not None:
            return self.product.time_to_gate_close(t)
        return None


# ============================================================================
# AGENT PRIVATE INFO (SINGLE-PRODUCT)
# ============================================================================

@dataclass
class AgentPrivateInfo:
    """
    Agent-specific private information (not observable by other agents).
    
    For single-product agents (trading only one delivery product).
    
    Corresponds to variables defined in Shinde et al. papers:
    - effective_capacity: C_{i,t}, currently available capacity
    - da_position: p_i^{DA}, day-ahead market position
    - market_position: p^{mar}_{i,t}, cumulative intraday market position
    - revenue: r_{i,t}, cumulative revenue from intraday trades
    - imbalance: δ_{i,t}, imbalance (e.g., target - position)
    - imbalance_cost: cumulative imbalance costs
    - est_imb_price_up / est_imb_price_down: estimated imbalance prices
    - limit_buy / limit_sell: price limits for pricing strategies (Shinde)
    
    Note: For multi-product agents, use MultiProductPrivateInfo instead,
    which stores these values per product_id.
    
    Attributes:
        effective_capacity: Agent's available capacity (MW)
        da_position: Position committed in day-ahead market
        market_position: Current intraday market position
        revenue: Cumulative trading revenue (€)
        imbalance: Current imbalance (MW)
        imbalance_cost: Cumulative imbalance costs (€)
        est_imb_price_up: Estimated upward regulation price (€/MWh)
        est_imb_price_down: Estimated downward regulation price (€/MWh)
        limit_buy: Maximum price willing to pay (l^buy in Shinde) (€/MWh)
        limit_sell: Minimum price willing to accept (l^sell in Shinde) (€/MWh)
    
    Example:
        # Single-product agent state
        private_info = AgentPrivateInfo(
            effective_capacity=100.0,
            da_position=80.0,
            market_position=85.0,
            revenue=250.0,
            imbalance=5.0,
            est_imb_price_up=60.0,
            est_imb_price_down=40.0,
            limit_buy=65.0,
            limit_sell=35.0
        )
    """
    effective_capacity: float
    da_position: float = 0.0
    market_position: float = 0.0
    revenue: float = 0.0
    imbalance: float = 0.0
    imbalance_cost: float = 0.0
    est_imb_price_up: float = 0.0
    est_imb_price_down: float = 0.0
    
    # Shinde limit prices for pricing strategies
    limit_buy: float = 100.0    # Maximum price to pay (l^buy)
    limit_sell: float = 0.0     # Minimum price to sell (l^sell)


# ============================================================================
# MULTI-PRODUCT PRIVATE INFO
# ============================================================================

@dataclass
class MultiProductPrivateInfo:
    """
    Agent-specific private information indexed by product.
    
    For multi-product agents trading multiple delivery products simultaneously.
    All state variables are stored per product_id in dictionaries.
    
    Corresponds to Shinde multi-product extensions:
    - positions[product_id]: p_{i,t,d} - market position for product d
    - revenues[product_id]: r_{i,t,d} - cumulative revenue from trading product d
    - imbalances[product_id]: δ_{i,t,d} - imbalance for product d
    - da_positions[product_id]: p_i^{DA,d} - day-ahead position for product d
    - forecasts[product_id]: forecast for product d (variable agents)
    - limit_buy / limit_sell: price limits (GLOBAL across all products)
    
    Attributes:
        positions: Dict[product_id, float] - market positions per product
        revenues: Dict[product_id, float] - trading revenues per product
        imbalances: Dict[product_id, float] - imbalances per product
        imbalance_costs: Dict[product_id, float] - imbalance costs per product
        da_positions: Dict[product_id, float] - day-ahead positions per product
        forecasts: Dict[product_id, float] - forecasts per product (optional)
        capacities: Dict[product_id, float] - capacities per product (optional)
        est_imb_price_up: Dict[product_id, float] - estimated upward imbalance prices
        est_imb_price_down: Dict[product_id, float] - estimated downward imbalance prices
        soc: Optional[float] - State of Charge (for BESS, global across products)
        limit_buy: Maximum price willing to pay (l^buy in Shinde) (€/MWh)
        limit_sell: Minimum price willing to accept (l^sell in Shinde) (€/MWh)
    
    Example:
        # Initialize for 3 products
        products = create_hourly_products(n_hours=3)
        private_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            limit_buy=65.0,
            limit_sell=35.0
        )
        
        # Update position for product 0
        private_info.positions[0] += 10.0
        private_info.revenues[0] += 500.0
        
        # Get total revenue across all products
        total = private_info.total_revenue()
    """
    positions: Dict[int, float] = field(default_factory=dict)
    revenues: Dict[int, float] = field(default_factory=dict)
    imbalances: Dict[int, float] = field(default_factory=dict)
    imbalance_costs: Dict[int, float] = field(default_factory=dict)
    da_positions: Dict[int, float] = field(default_factory=dict)
    forecasts: Dict[int, float] = field(default_factory=dict)
    capacities: Dict[int, float] = field(default_factory=dict)
    est_imb_price_up: Dict[int, float] = field(default_factory=dict)
    est_imb_price_down: Dict[int, float] = field(default_factory=dict)
    
    # Global state (not per-product)
    soc: Optional[float] = None  # For BESS agents
    
    # Shinde limit prices (GLOBAL across all products)
    limit_buy: float = 100.0    # Maximum price to pay (l^buy)
    limit_sell: float = 0.0     # Minimum price to sell (l^sell)
    
    @classmethod
    def initialize(
        cls,
        products: List[Product],
        initial_capacity: float = 0.0,
        initial_da_position: float = 0.0,
        initial_forecast: Optional[float] = None,
        initial_soc: Optional[float] = None,
        limit_buy: float = 100.0,
        limit_sell: float = 0.0,
    ) -> MultiProductPrivateInfo:
        """
        Initialize MultiProductPrivateInfo with default values for all products.
        
        Args:
            products: List of Product instances
            initial_capacity: Initial capacity for all products (default 0.0)
            initial_da_position: Initial DA position for all products (default 0.0)
            initial_forecast: Initial forecast for all products (default None)
            initial_soc: Initial state of charge for BESS (default None)
            limit_buy: Maximum price willing to pay (default 100.0)
            limit_sell: Minimum price willing to accept (default 0.0)
            
        Returns:
            Initialized MultiProductPrivateInfo instance
        
        Example:
            products = create_hourly_products(n_hours=24)
            info = MultiProductPrivateInfo.initialize(
                products=products,
                initial_capacity=100.0,
                initial_da_position=80.0,
                limit_buy=65.0,
                limit_sell=35.0
            )
        """
        product_ids = [p.product_id for p in products]
        
        return cls(
            positions={pid: 0.0 for pid in product_ids},
            revenues={pid: 0.0 for pid in product_ids},
            imbalances={pid: 0.0 for pid in product_ids},
            imbalance_costs={pid: 0.0 for pid in product_ids},
            da_positions={pid: initial_da_position for pid in product_ids},
            forecasts={pid: initial_forecast if initial_forecast is not None else 0.0 for pid in product_ids},
            capacities={pid: initial_capacity for pid in product_ids},
            est_imb_price_up={pid: 0.0 for pid in product_ids},
            est_imb_price_down={pid: 0.0 for pid in product_ids},
            soc=initial_soc,
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
    
    # ------------------------------------------------------------------
    # Aggregation Methods
    # ------------------------------------------------------------------
    
    def total_revenue(self) -> float:
        """Calculate total revenue across all products."""
        return sum(self.revenues.values())
    
    def total_imbalance_cost(self) -> float:
        """Calculate total imbalance cost across all products."""
        return sum(self.imbalance_costs.values())
    
    def net_profit(self) -> float:
        """Calculate net profit (revenue - imbalance costs)."""
        return self.total_revenue() - self.total_imbalance_cost()
    
    def total_position(self) -> float:
        """Calculate total position across all products."""
        return sum(self.positions.values())
    
    def total_imbalance(self) -> float:
        """Calculate total imbalance across all products."""
        return sum(self.imbalances.values())
    
    # ------------------------------------------------------------------
    # Product-Specific Queries
    # ------------------------------------------------------------------
    
    def get_product_state(self, product_id: int) -> Dict[str, float]:
        """Get complete state for a specific product."""
        return {
            'position': self.positions.get(product_id, 0.0),
            'revenue': self.revenues.get(product_id, 0.0),
            'imbalance': self.imbalances.get(product_id, 0.0),
            'imbalance_cost': self.imbalance_costs.get(product_id, 0.0),
            'da_position': self.da_positions.get(product_id, 0.0),
            'forecast': self.forecasts.get(product_id, 0.0),
            'capacity': self.capacities.get(product_id, 0.0),
            'est_imb_price_up': self.est_imb_price_up.get(product_id, 0.0),
            'est_imb_price_down': self.est_imb_price_down.get(product_id, 0.0),
        }
    
    def get_products_with_imbalance(self, min_imbalance: float = 0.01) -> List[int]:
        """Get list of products with non-zero imbalance."""
        return [
            pid for pid, imb in self.imbalances.items()
            if abs(imb) >= min_imbalance
        ]
    
    def get_products_with_position(self, min_position: float = 0.01) -> List[int]:
        """Get list of products with non-zero position."""
        return [
            pid for pid, pos in self.positions.items()
            if abs(pos) >= min_position
        ]
    
    # ------------------------------------------------------------------
    # Update Methods
    # ------------------------------------------------------------------
    
    def update_position(self, product_id: int, delta: float) -> None:
        """Update market position for a specific product."""
        if product_id not in self.positions:
            self.positions[product_id] = 0.0
        self.positions[product_id] += delta
    
    def update_revenue(self, product_id: int, delta: float) -> None:
        """Update revenue for a specific product."""
        if product_id not in self.revenues:
            self.revenues[product_id] = 0.0
        self.revenues[product_id] += delta
    
    def update_imbalance(self, product_id: int, imbalance: float) -> None:
        """Set imbalance for a specific product."""
        self.imbalances[product_id] = imbalance
    
    def set_imbalance(self, product_id: int, imbalance: float) -> None:
        """Alias for update_imbalance() for backward compatibility."""
        self.update_imbalance(product_id, imbalance)
    
    def update_forecast(self, product_id: int, forecast: float) -> None:
        """Update forecast for a specific product."""
        self.forecasts[product_id] = forecast