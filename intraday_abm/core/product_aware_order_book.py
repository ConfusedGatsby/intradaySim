"""
Product-aware OrderBook for multi-product CID market simulation.

This module provides ProductAwareOrderBook, which extends the basic OrderBook
with product lifecycle awareness and validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict

from intraday_abm.core.order import Order, Trade
from intraday_abm.core.types import Side
from intraday_abm.core.product import Product, ProductStatus


@dataclass
class ProductAwareOrderBook:
    """
    Order book for a specific product with lifecycle awareness.
    
    Unlike the basic OrderBook which only stores a product_id,
    this class holds a reference to the full Product object and
    enforces trading rules based on product lifecycle (gate-open/close).
    
    Attributes:
        product: Product instance with delivery and gate times
        bids: Dict mapping price levels to list of buy orders (descending priority)
        asks: Dict mapping price levels to list of sell orders (ascending priority)
    
    Example:
        from intraday_abm.core.product import create_single_product
        
        product = create_single_product(product_id=0, da_price=50.0)
        order_book = ProductAwareOrderBook(product=product)
        
        # Check if trading is allowed
        if order_book.is_open(t=100):
            order_book.add_order(order)
    """
    product: Product
    bids: Dict[float, List[Order]] = field(default_factory=lambda: defaultdict(list))
    asks: Dict[float, List[Order]] = field(default_factory=lambda: defaultdict(list))
    
    def __post_init__(self):
        """Convert regular dicts to defaultdicts if needed."""
        if not isinstance(self.bids, defaultdict):
            self.bids = defaultdict(list, self.bids)
        if not isinstance(self.asks, defaultdict):
            self.asks = defaultdict(list, self.asks)
    
    # ------------------------------------------------------------------
    # Product Lifecycle Checks
    # ------------------------------------------------------------------
    
    def is_open(self, t: int) -> bool:
        """
        Check if product is open for trading at time t.
        
        Args:
            t: Current simulation time
            
        Returns:
            True if product status is OPEN and within trading window
        """
        return (
            self.product.status == ProductStatus.OPEN and
            self.product.is_open(t)
        )
    
    def validate_order_time(self, t: int) -> None:
        """
        Validate that an order can be placed at time t.
        
        Args:
            t: Current simulation time
            
        Raises:
            ValueError: If product is not open for trading
        """
        if not self.is_open(t):
            raise ValueError(
                f"Cannot place order for product {self.product.product_id} at t={t}. "
                f"Product status: {self.product.status.name}, "
                f"Gate window: {self.product.gate_open}-{self.product.gate_close}"
            )
    
    # ------------------------------------------------------------------
    # Order Management
    # ------------------------------------------------------------------
    
    def add_order(self, order: Order, validate_time: bool = False, t: Optional[int] = None) -> None:
        """
        Add an order to the book.
        
        Args:
            order: Order to add
            validate_time: If True, check product is open before adding
            t: Current time (required if validate_time=True)
            
        Raises:
            ValueError: If order product_id doesn't match book's product
            ValueError: If validate_time=True and product is not open
        """
        # Verify order belongs to this product
        if order.product_id != self.product.product_id:
            raise ValueError(
                f"Order product_id {order.product_id} doesn't match "
                f"book product_id {self.product.product_id}"
            )
        
        # Optional time validation
        if validate_time:
            if t is None:
                raise ValueError("Time t must be provided when validate_time=True")
            self.validate_order_time(t)
        
        # Add to appropriate side
        if order.side == Side.BUY:
            self.bids[order.price].append(order)
        else:
            self.asks[order.price].append(order)
    
    def remove_order(self, order: Order) -> None:
        """
        Remove a specific order from the book.
        
        Args:
            order: Order to remove
        """
        if order.side == Side.BUY:
            level = self.bids.get(order.price, [])
            if order in level:
                level.remove(order)
            if not level and order.price in self.bids:
                del self.bids[order.price]
        else:
            level = self.asks.get(order.price, [])
            if order in level:
                level.remove(order)
            if not level and order.price in self.asks:
                del self.asks[order.price]
    
    def remove_orders_by_agent(self, agent_id: int) -> int:
        """
        Remove all orders from a specific agent.
        
        Args:
            agent_id: ID of agent whose orders should be removed
            
        Returns:
            Number of orders removed
        """
        removed_count = 0
        
        # Remove from bids
        for price in list(self.bids.keys()):
            original_len = len(self.bids[price])
            self.bids[price] = [o for o in self.bids[price] if o.agent_id != agent_id]
            removed_count += original_len - len(self.bids[price])
            
            # Clean up empty price levels
            if not self.bids[price]:
                del self.bids[price]
        
        # Remove from asks
        for price in list(self.asks.keys()):
            original_len = len(self.asks[price])
            self.asks[price] = [o for o in self.asks[price] if o.agent_id != agent_id]
            removed_count += original_len - len(self.asks[price])
            
            # Clean up empty price levels
            if not self.asks[price]:
                del self.asks[price]
        
        return removed_count
    
    def clear_all_orders(self) -> int:
        """
        Remove all orders from the book (e.g., at gate closure).
        
        Returns:
            Number of orders removed
        """
        count = len(self)
        self.bids.clear()
        self.asks.clear()
        return count
    
    # ------------------------------------------------------------------
    # Top-of-Book Queries
    # ------------------------------------------------------------------
    
    def best_bid(self) -> Optional[Order]:
        """
        Get the best (highest price) buy order.
        
        Returns:
            Best bid order, or None if no bids exist
        """
        if not self.bids:
            return None
        best_price = max(self.bids.keys())
        level = self.bids[best_price]
        return level[0] if level else None
    
    def best_ask(self) -> Optional[Order]:
        """
        Get the best (lowest price) sell order.
        
        Returns:
            Best ask order, or None if no asks exist
        """
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        level = self.asks[best_price]
        return level[0] if level else None
    
    def best_bid_price(self) -> Optional[float]:
        """Get best bid price, or None if no bids."""
        bid = self.best_bid()
        return bid.price if bid else None
    
    def best_ask_price(self) -> Optional[float]:
        """Get best ask price, or None if no asks."""
        ask = self.best_ask()
        return ask.price if ask else None
    
    # ------------------------------------------------------------------
    # Matching Logic (Pay-as-Bid)
    # ------------------------------------------------------------------
    
    def match_order(self, incoming: Order, t: int) -> List[Trade]:
        """
        Match an incoming order against the book (pay-as-bid).
        
        This method implements:
        - Price-time priority
        - Pay-as-bid pricing (trade price = resting order price)
        - FIFO within price level
        - Partial fills
        
        Args:
            incoming: Incoming order to match
            t: Current simulation time
            
        Returns:
            List of trades generated
            
        Note:
            This method modifies the incoming order's volume and
            removes filled resting orders from the book.
        """
        if incoming.side == Side.BUY:
            return self._match_buy(incoming, t)
        else:
            return self._match_sell(incoming, t)
    
    def _match_buy(self, incoming: Order, t: int) -> List[Trade]:
        """Match incoming buy order against asks."""
        trades: List[Trade] = []
        
        while incoming.volume > 0:
            best_ask = self.best_ask()
            if best_ask is None:
                break
            
            # Crossing condition: buy price >= ask price
            if incoming.price < best_ask.price:
                break
            
            # Execute trade
            traded_volume = min(incoming.volume, best_ask.volume)
            trade_price = best_ask.price  # Pay-as-bid
            
            trade = Trade(
                product_id=self.product.product_id,
                price=trade_price,
                volume=traded_volume,
                buy_order_id=incoming.id,
                sell_order_id=best_ask.id,
                buy_agent_id=incoming.agent_id,
                sell_agent_id=best_ask.agent_id,
                time=t,
            )
            trades.append(trade)
            
            # Update volumes
            incoming.volume -= traded_volume
            best_ask.volume -= traded_volume
            
            # Remove filled resting order
            if best_ask.volume <= 0:
                self.remove_order(best_ask)
        
        return trades
    
    def _match_sell(self, incoming: Order, t: int) -> List[Trade]:
        """Match incoming sell order against bids."""
        trades: List[Trade] = []
        
        while incoming.volume > 0:
            best_bid = self.best_bid()
            if best_bid is None:
                break
            
            # Crossing condition: sell price <= bid price
            if incoming.price > best_bid.price:
                break
            
            # Execute trade
            traded_volume = min(incoming.volume, best_bid.volume)
            trade_price = best_bid.price  # Pay-as-bid
            
            trade = Trade(
                product_id=self.product.product_id,
                price=trade_price,
                volume=traded_volume,
                buy_order_id=best_bid.id,
                sell_order_id=incoming.id,
                buy_agent_id=best_bid.agent_id,
                sell_agent_id=incoming.agent_id,
                time=t,
            )
            trades.append(trade)
            
            # Update volumes
            incoming.volume -= traded_volume
            best_bid.volume -= traded_volume
            
            # Remove filled resting order
            if best_bid.volume <= 0:
                self.remove_order(best_bid)
        
        return trades
    
    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------
    
    def __len__(self) -> int:
        """Total number of orders in the book."""
        bid_count = sum(len(orders) for orders in self.bids.values())
        ask_count = sum(len(orders) for orders in self.asks.values())
        return bid_count + ask_count
    
    def __repr__(self) -> str:
        return (
            f"ProductAwareOrderBook(product_id={self.product.product_id}, "
            f"status={self.product.status.name}, "
            f"orders={len(self)})"
        )