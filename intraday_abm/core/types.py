"""
Core type definitions for the CID market simulation.

Defines fundamental types used throughout the simulation:
- Side, TimeInForce enums
- TopOfBook (market state snapshot)
- PublicInfo (public market information)
- AgentPrivateInfo (agent-specific private state)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from intraday_abm.core.product import Product


class Side(Enum):
    """Order direction in the order book."""
    BUY = auto()
    SELL = auto()


class TimeInForce(Enum):
    """Order validity duration."""
    GTC = auto()  # Good till cancelled
    IOC = auto()  # Immediate or cancel


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
        This should never happen in a properly functioning market.
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


@dataclass
class AgentPrivateInfo:
    """
    Agent-specific private information (not observable by other agents).
    
    Corresponds to variables defined in Shinde et al. papers:
    - effective_capacity: C_{i,t}, currently available capacity
    - da_position: p_i^{DA}, day-ahead market position
    - market_position: p^{mar}_{i,t}, cumulative intraday market position
    - revenue: r_{i,t}, cumulative revenue from intraday trades
    - imbalance: δ_{i,t}, imbalance (e.g., target - position)
    - imbalance_cost: cumulative imbalance costs
    - est_imb_price_up / est_imb_price_down: estimated imbalance prices
    
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
    """
    effective_capacity: float
    da_position: float = 0.0
    market_position: float = 0.0
    revenue: float = 0.0
    imbalance: float = 0.0
    imbalance_cost: float = 0.0
    est_imb_price_up: float = 0.0
    est_imb_price_down: float = 0.0