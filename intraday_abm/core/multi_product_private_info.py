"""
Multi-Product Private Information for agents.

This module provides MultiProductPrivateInfo, which stores agent state
(positions, revenues, imbalances) indexed by product_id for multi-product trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from intraday_abm.core.product import Product


@dataclass
class MultiProductPrivateInfo:
    """
    Agent-specific private information indexed by product.
    
    For multi-product agents, all state variables are stored per product_id:
    - positions[product_id]: p_{i,t,d} - market position for product d
    - revenues[product_id]: r_{i,t,d} - cumulative revenue from trading product d
    - imbalances[product_id]: δ_{i,t,d} - imbalance for product d
    - da_positions[product_id]: p_i^{DA,d} - day-ahead position for product d
    - forecasts[product_id]: forecast for product d (variable agents)
    
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
    
    Example:
        # Initialize for 3 products
        products = create_hourly_products(n_hours=3)
        private_info = MultiProductPrivateInfo.initialize(products)
        
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
    
    @classmethod
    def initialize(
        cls,
        products: List[Product],
        initial_capacity: float = 0.0,
        initial_da_position: float = 0.0,
        initial_forecast: Optional[float] = None,
        initial_soc: Optional[float] = None
    ) -> MultiProductPrivateInfo:
        """
        Initialize MultiProductPrivateInfo with default values for all products.
        
        Args:
            products: List of Product instances
            initial_capacity: Initial capacity for all products (default 0.0)
            initial_da_position: Initial DA position for all products (default 0.0)
            initial_forecast: Initial forecast for all products (default None)
            initial_soc: Initial state of charge for BESS (default None)
            
        Returns:
            Initialized MultiProductPrivateInfo instance
        
        Example:
            products = create_hourly_products(n_hours=24)
            info = MultiProductPrivateInfo.initialize(
                products=products,
                initial_capacity=100.0,
                initial_da_position=80.0
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
            soc=initial_soc
        )
    
    # ------------------------------------------------------------------
    # Aggregation Methods
    # ------------------------------------------------------------------
    
    def total_revenue(self) -> float:
        """
        Calculate total revenue across all products.
        
        Returns:
            Sum of revenues from all products
        """
        return sum(self.revenues.values())
    
    def total_imbalance_cost(self) -> float:
        """
        Calculate total imbalance cost across all products.
        
        Returns:
            Sum of imbalance costs from all products
        """
        return sum(self.imbalance_costs.values())
    
    def net_profit(self) -> float:
        """
        Calculate net profit (revenue - imbalance costs).
        
        Returns:
            Total revenue minus total imbalance costs
        """
        return self.total_revenue() - self.total_imbalance_cost()
    
    def total_position(self) -> float:
        """
        Calculate total position across all products.
        
        Note: This may not be meaningful for all agent types,
        as positions in different delivery periods are independent.
        
        Returns:
            Sum of positions across all products
        """
        return sum(self.positions.values())
    
    def total_imbalance(self) -> float:
        """
        Calculate total imbalance across all products.
        
        Returns:
            Sum of imbalances across all products
        """
        return sum(self.imbalances.values())
    
    # ------------------------------------------------------------------
    # Product-Specific Queries
    # ------------------------------------------------------------------
    
    def get_product_state(self, product_id: int) -> Dict[str, float]:
        """
        Get complete state for a specific product.
        
        Args:
            product_id: Product to query
            
        Returns:
            Dict with all state variables for this product
        
        Example:
            state = info.get_product_state(product_id=5)
            print(f"Position: {state['position']}")
            print(f"Revenue: {state['revenue']}")
        """
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
        """
        Get list of products with non-zero imbalance.
        
        Args:
            min_imbalance: Minimum absolute imbalance to consider (default 0.01)
            
        Returns:
            List of product_ids with |imbalance| >= min_imbalance
        """
        return [
            pid
            for pid, imb in self.imbalances.items()
            if abs(imb) >= min_imbalance
        ]
    
    # ------------------------------------------------------------------
    # Update Methods
    # ------------------------------------------------------------------
    
    def update_position(self, product_id: int, delta: float) -> None:
        """
        Update position for a specific product.
        
        Args:
            product_id: Product to update
            delta: Change in position (positive for buy, negative for sell)
        """
        if product_id not in self.positions:
            self.positions[product_id] = 0.0
        self.positions[product_id] += delta
    
    def update_revenue(self, product_id: int, delta: float) -> None:
        """
        Update revenue for a specific product.
        
        Args:
            product_id: Product to update
            delta: Change in revenue
        """
        if product_id not in self.revenues:
            self.revenues[product_id] = 0.0
        self.revenues[product_id] += delta
    
    def set_imbalance(self, product_id: int, imbalance: float) -> None:
        """
        Set imbalance for a specific product.
        
        Args:
            product_id: Product to update
            imbalance: New imbalance value
        """
        self.imbalances[product_id] = imbalance
    
    def set_imbalance_cost(self, product_id: int, cost: float) -> None:
        """
        Set imbalance cost for a specific product.
        
        Args:
            product_id: Product to update
            cost: Imbalance cost
        """
        self.imbalance_costs[product_id] = cost
    
    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------
    
    def reset_product(self, product_id: int) -> None:
        """
        Reset all state for a specific product to zero.
        
        Useful for testing or when a product settles.
        
        Args:
            product_id: Product to reset
        """
        self.positions[product_id] = 0.0
        self.revenues[product_id] = 0.0
        self.imbalances[product_id] = 0.0
        self.imbalance_costs[product_id] = 0.0
    
    def __repr__(self) -> str:
        n_products = len(self.positions)
        total_rev = self.total_revenue()
        total_pos = self.total_position()
        return (
            f"MultiProductPrivateInfo("
            f"products={n_products}, "
            f"total_position={total_pos:.2f}, "
            f"total_revenue={total_rev:.2f}, "
            f"soc={self.soc})"
        )