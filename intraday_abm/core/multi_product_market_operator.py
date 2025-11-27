"""
Multi-Product Market Operator for CID market simulation.

This module provides MultiProductMarketOperator, which manages multiple
product-specific order books and routes orders to the correct product.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from intraday_abm.core.product import Product, ProductStatus
from intraday_abm.core.product_aware_order_book import ProductAwareOrderBook
from intraday_abm.core.order import Order, Trade
from intraday_abm.core.types import TopOfBook, PublicInfo


@dataclass
class MultiProductMarketOperator:
    """
    Market operator managing multiple product-specific order books.
    
    This class orchestrates trading across multiple delivery products,
    handling order routing, product lifecycle management, and providing
    market information to agents.
    
    Attributes:
        products: Dict mapping product_id to Product instances
        order_books: Dict mapping product_id to ProductAwareOrderBook
        next_order_id: Counter for assigning unique order IDs
    
    Example:
        from intraday_abm.core.product import create_hourly_products
        
        products = create_hourly_products(n_hours=24)
        mo = MultiProductMarketOperator.from_products(products)
        
        # Open all products for trading
        mo.open_products(t=0)
        
        # Get open products
        open_pids = mo.get_open_products(t=100)
        
        # Process order for specific product
        order = Order(..., product_id=5)
        trades = mo.process_order(order, t=100)
    """
    products: Dict[int, Product] = field(default_factory=dict)
    order_books: Dict[int, ProductAwareOrderBook] = field(default_factory=dict)
    next_order_id: int = 1
    
    # ------------------------------------------------------------------
    # Factory Methods
    # ------------------------------------------------------------------
    
    @classmethod
    def from_products(cls, products: List[Product]) -> MultiProductMarketOperator:
        """
        Create MultiProductMarketOperator from list of products.
        
        Args:
            products: List of Product instances
            
        Returns:
            Initialized MultiProductMarketOperator
        
        Example:
            products = create_hourly_products(n_hours=24)
            mo = MultiProductMarketOperator.from_products(products)
        """
        products_dict = {p.product_id: p for p in products}
        order_books_dict = {
            p.product_id: ProductAwareOrderBook(product=p)
            for p in products
        }
        
        return cls(
            products=products_dict,
            order_books=order_books_dict
        )
    
    # ------------------------------------------------------------------
    # Product Lifecycle Management
    # ------------------------------------------------------------------
    
    def update_product_status(self, t: int) -> List[int]:
        """
        Update product statuses based on current time and close expired products.
        
        This method:
        1. Opens products that have reached gate_open
        2. Closes products that have reached gate_close (cancels all orders)
        3. Settles products that have finished delivery
        
        Args:
            t: Current simulation time
            
        Returns:
            List of product_ids that were closed in this step
        
        Example:
            # At each time step in simulation
            closed_products = mo.update_product_status(t)
            if closed_products:
                print(f"Products {closed_products} closed at t={t}")
        """
        closed_products = []
        
        for product_id, product in self.products.items():
            new_status = None
            
            # PENDING → OPEN: reached gate_open
            if product.status == ProductStatus.PENDING and t >= product.gate_open:
                new_status = ProductStatus.OPEN
            
            # OPEN → CLOSED: reached gate_close
            elif product.status == ProductStatus.OPEN and t >= product.gate_close:
                new_status = ProductStatus.CLOSED
                closed_products.append(product_id)
                
                # Cancel all remaining orders
                ob = self.order_books[product_id]
                cancelled_count = ob.clear_all_orders()
                if cancelled_count > 0:
                    print(f"  Product {product_id}: Cancelled {cancelled_count} orders at gate-close")
            
            # CLOSED → SETTLED: finished delivery
            elif product.status == ProductStatus.CLOSED and t >= product.delivery_end:
                new_status = ProductStatus.SETTLED
            
            # Update product status if changed
            if new_status is not None:
                updated_product = product.update_status(new_status)
                self.products[product_id] = updated_product
                
                # Update order book's product reference
                self.order_books[product_id].product = updated_product
        
        return closed_products
    
    def open_products(self, t: int) -> List[int]:
        """
        Explicitly open products for trading (set status to OPEN).
        
        Useful for initializing simulation where all products should
        be immediately tradable.
        
        Args:
            t: Current simulation time
            
        Returns:
            List of product_ids that were opened
        """
        opened = []
        
        for product_id, product in self.products.items():
            # Open any PENDING product where gate_open time has been reached
            if product.status == ProductStatus.PENDING:
                if t >= product.gate_open:
                    updated = product.update_status(ProductStatus.OPEN)
                    self.products[product_id] = updated
                    self.order_books[product_id].product = updated
                    opened.append(product_id)
        
        return opened
    
    def get_open_products(self, t: int) -> List[int]:
        """
        Get list of product_ids currently open for trading.
        
        Args:
            t: Current simulation time
            
        Returns:
            List of product_ids where status is OPEN and within trading window
        """
        return [
            product_id
            for product_id, ob in self.order_books.items()
            if ob.is_open(t)
        ]
    
    def get_product(self, product_id: int) -> Optional[Product]:
        """Get Product instance by ID."""
        return self.products.get(product_id)
    
    # ------------------------------------------------------------------
    # Order Processing
    # ------------------------------------------------------------------
    
    def process_order(self, order: Order, t: int, validate_time: bool = True) -> List[Trade]:
        """
        Process an order: assign ID, match against book, add remainder if GTC.
        
        Args:
            order: Order to process
            t: Current simulation time
            validate_time: If True, check product is open before processing
            
        Returns:
            List of trades generated
            
        Raises:
            ValueError: If product_id not found or not open (when validate_time=True)
        
        Example:
            order = Order(
                id=0,  # Will be assigned
                agent_id=1,
                side=Side.BUY,
                price=50.0,
                volume=10.0,
                product_id=5,
                time_in_force=TimeInForce.GTC
            )
            trades = mo.process_order(order, t=100)
        """
        product_id = order.product_id
        
        # Verify product exists
        if product_id not in self.order_books:
            raise ValueError(f"Product {product_id} not found in market operator")
        
        ob = self.order_books[product_id]
        
        # Optional: validate trading window
        if validate_time:
            ob.validate_order_time(t)
        
        # Assign order ID and timestamp
        order.id = self.next_order_id
        self.next_order_id += 1
        order.timestamp = t
        
        # Match order
        trades = ob.match_order(order, t)
        
        # Add remainder to book if GTC and volume left
        if order.volume > 0 and order.time_in_force is not None:
            from intraday_abm.core.types import TimeInForce
            if order.time_in_force == TimeInForce.GTC:
                ob.add_order(order, validate_time=False)  # Already validated
        
        return trades
    
    def cancel_agent_orders(self, agent_id: int, product_id: Optional[int] = None) -> int:
        """
        Cancel all orders from a specific agent.
        
        Args:
            agent_id: ID of agent whose orders should be cancelled
            product_id: If provided, only cancel orders for this product.
                       If None, cancel across all products.
            
        Returns:
            Total number of orders cancelled
        
        Example:
            # Cancel all orders from agent 1 across all products
            cancelled = mo.cancel_agent_orders(agent_id=1)
            
            # Cancel orders from agent 1 only for product 5
            cancelled = mo.cancel_agent_orders(agent_id=1, product_id=5)
        """
        total_cancelled = 0
        
        if product_id is not None:
            # Cancel for specific product
            if product_id in self.order_books:
                ob = self.order_books[product_id]
                total_cancelled = ob.remove_orders_by_agent(agent_id)
        else:
            # Cancel across all products
            for ob in self.order_books.values():
                total_cancelled += ob.remove_orders_by_agent(agent_id)
        
        return total_cancelled
    
    # ------------------------------------------------------------------
    # Market Information
    # ------------------------------------------------------------------
    
    def get_tob(self, product_id: int) -> TopOfBook:
        """
        Get top-of-book for a specific product.
        
        Args:
            product_id: Product to query
            
        Returns:
            TopOfBook snapshot
            
        Raises:
            ValueError: If product_id not found
        """
        if product_id not in self.order_books:
            raise ValueError(f"Product {product_id} not found")
        
        ob = self.order_books[product_id]
        best_bid = ob.best_bid()
        best_ask = ob.best_ask()
        
        return TopOfBook(
            best_bid_price=best_bid.price if best_bid else None,
            best_bid_volume=best_bid.volume if best_bid else None,
            best_ask_price=best_ask.price if best_ask else None,
            best_ask_volume=best_ask.volume if best_ask else None,
        )
    
    def get_public_info(self, t: int, product_ids: Optional[List[int]] = None) -> Dict[int, PublicInfo]:
        """
        Get public market information for multiple products.
        
        Args:
            t: Current simulation time
            product_ids: List of products to query. If None, returns all open products.
            
        Returns:
            Dict mapping product_id to PublicInfo
        
        Example:
            # Get info for all open products
            public_info = mo.get_public_info(t=100)
            
            # Get info for specific products
            public_info = mo.get_public_info(t=100, product_ids=[0, 1, 2])
        """
        if product_ids is None:
            product_ids = self.get_open_products(t)
        
        result = {}
        for product_id in product_ids:
            if product_id not in self.products:
                continue
            
            product = self.products[product_id]
            tob = self.get_tob(product_id)
            
            result[product_id] = PublicInfo(
                tob=tob,
                da_price=product.da_price,
                product=product
            )
        
        return result
    
    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------
    
    def get_book_sizes(self) -> Dict[int, int]:
        """
        Get number of orders in each product's book.
        
        Returns:
            Dict mapping product_id to number of orders
        """
        return {
            product_id: len(ob)
            for product_id, ob in self.order_books.items()
        }
    
    def total_orders(self) -> int:
        """Get total number of orders across all products."""
        return sum(len(ob) for ob in self.order_books.values())
    
    def __repr__(self) -> str:
        open_count = len(self.get_open_products(t=0))  # Approximation
        return (
            f"MultiProductMarketOperator("
            f"products={len(self.products)}, "
            f"open={open_count}, "
            f"total_orders={self.total_orders()})"
        )