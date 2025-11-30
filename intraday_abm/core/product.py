"""
Product types for multi-product CID market simulation.

This module defines the Product abstraction representing delivery periods,
their lifecycle (gate-open, gate-close, delivery), and factory functions
for creating product sets.

Extensions:
- Quarterly products (15-min) with realistic DA prices
- Scientific price model based on Kremer et al. (2021)
- Sawtooth hourly seasonality pattern
- Peak/Off-Peak differences
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, replace
from typing import Optional, List, Literal
import numpy as np


class ProductStatus(Enum):
    """
    Lifecycle states of a delivery product in the CID market.
    
    PENDING: Product created but trading not yet started (before gate-open)
    OPEN: Product actively tradable (between gate-open and gate-close)
    CLOSED: Trading ended, awaiting physical delivery
    SETTLED: Physical delivery completed, imbalances settled
    """
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    SETTLED = "settled"


@dataclass(frozen=True)
class Product:
    """
    Represents a delivery product in the CID market.
    
    A product corresponds to a specific time window for physical electricity
    delivery (e.g., H00 = 00:00-01:00, H00Q1 = 00:00-00:15).
    
    Attributes:
        product_id: Unique identifier (e.g., 0, 1, 2, ...)
        delivery_start: Start time of physical delivery (simulation time units)
        delivery_end: End time of physical delivery
        gate_open: Time when trading begins for this product
        gate_close: Time when trading ends for this product
        duration: Length of delivery period in minutes (15, 30, or 60)
        da_price: Day-ahead market clearing price for this product (EUR/MWh)
        status: Current lifecycle status
        name: Optional human-readable name (e.g., "H00", "H12Q3")
    
    Example:
        # Hourly product H00 with 24h advance trading, 60min gate-closure
        Product(
            product_id=0,
            name="H00",
            delivery_start=1440,  # Day 2, 00:00 (in minutes)
            delivery_end=1500,
            gate_open=0,          # Day 1, 00:00
            gate_close=1380,      # Day 1, 23:00
            duration=60,
            da_price=50.0,
            status=ProductStatus.PENDING
        )
    """
    product_id: int
    delivery_start: int
    delivery_end: int
    gate_open: int
    gate_close: int
    duration: int
    da_price: float
    status: ProductStatus = ProductStatus.PENDING
    name: Optional[str] = None
    
    def is_open(self, t: int) -> bool:
        """
        Check if product is open for trading at time t.
        
        Args:
            t: Current simulation time
            
        Returns:
            True if gate_open <= t < gate_close, False otherwise
        """
        return self.gate_open <= t < self.gate_close
    
    def time_to_gate_close(self, t: int) -> Optional[int]:
        """
        Return time steps until gate closure.
        
        Args:
            t: Current simulation time
            
        Returns:
            Number of time steps until gate_close, or None if already closed
        """
        if t >= self.gate_close:
            return None
        return self.gate_close - t
    
    def time_to_delivery(self, t: int) -> Optional[int]:
        """
        Return time steps until delivery starts.
        
        Args:
            t: Current simulation time
            
        Returns:
            Number of time steps until delivery_start, or None if already started
        """
        if t >= self.delivery_start:
            return None
        return self.delivery_start - t
    
    def update_status(self, new_status: ProductStatus) -> Product:
        """
        Return new Product instance with updated status.
        
        Products are immutable, so this returns a copy with changed status.
        
        Args:
            new_status: New ProductStatus
            
        Returns:
            New Product instance with updated status
        """
        return replace(self, status=new_status)
    
    def __repr__(self) -> str:
        name_str = f", name={self.name}" if self.name else ""
        return (
            f"Product(id={self.product_id}{name_str}, "
            f"delivery={self.delivery_start}-{self.delivery_end}, "
            f"gate={self.gate_open}-{self.gate_close}, "
            f"status={self.status.name})"
        )


@dataclass
class ProductConfig:
    """
    Configuration for creating a Product instance.
    
    Provides more intuitive parameters (offsets in hours/minutes)
    that are converted to absolute times when creating the Product.
    
    Attributes:
        product_id: Unique identifier
        delivery_start: Absolute start time of delivery
        delivery_duration: Length of delivery period in minutes
        gate_open_offset_hours: Hours before delivery when trading opens
        gate_close_offset_minutes: Minutes before delivery when trading closes
        da_price: Day-ahead price for this product
        name: Optional human-readable name
    """
    product_id: int
    delivery_start: int
    delivery_duration: int = 60
    gate_open_offset_hours: int = 24
    gate_close_offset_minutes: int = 60
    da_price: float = 50.0
    name: Optional[str] = None
    
    def to_product(self) -> Product:
        """
        Convert configuration to Product instance.
        
        Computes absolute gate_open and gate_close times from offsets.
        
        Returns:
            Product instance
        """
        gate_open = self.delivery_start - (self.gate_open_offset_hours * 60)
        gate_close = self.delivery_start - self.gate_close_offset_minutes
        delivery_end = self.delivery_start + self.delivery_duration
        
        return Product(
            product_id=self.product_id,
            delivery_start=self.delivery_start,
            delivery_end=delivery_end,
            gate_open=gate_open,
            gate_close=gate_close,
            duration=self.delivery_duration,
            da_price=self.da_price,
            status=ProductStatus.PENDING,
            name=self.name
        )


# ============================================================================
# REALISTIC DA PRICE MODEL (Based on Kremer et al. 2021)
# ============================================================================

def generate_realistic_da_price(
    hour: int,
    quarter: int,
    season: Literal['summer', 'winter'] = 'winter',
    base_price: float = 45.0,
    volatility: float = 5.0,
    rng: Optional[np.random.Generator] = None
) -> float:
    """
    Generate realistic Day-Ahead prices based on Kremer et al. (2021).
    
    Implements empirical price patterns from EPEX SPOT data:
    - Sawtooth hourly seasonality
    - Peak hours (8-20h) with higher prices
    - Night valley (0-6h) with lower prices
    - Intra-hourly pattern (Q1 vs Q4)
    - Seasonal differences (summer vs winter)
    
    Source: Kremer, M., Kiesel, R., Paraschiv, F. (2021). "An econometric model
    for intraday electricity trading". Phil. Trans. R. Soc. A 379: 20190624.
    
    Args:
        hour: Hour (0-23)
        quarter: Quarter (0-3 for Q1-Q4)
        season: 'summer' or 'winter'
        base_price: Base price in EUR/MWh (default 45.0)
        volatility: Stochastic volatility in EUR/MWh (default 5.0)
        rng: NumPy random generator (optional)
        
    Returns:
        DA price in EUR/MWh
        
    Example:
        >>> price = generate_realistic_da_price(hour=12, quarter=0, season='winter')
        >>> print(f"H12Q1 Winter: {price:.2f} EUR/MWh")
        H12Q1 Winter: 52.34 EUR/MWh
    """
    if rng is None:
        rng = np.random.default_rng()
    
    # Base price adjustment by time of day
    if 0 <= hour < 6:
        # Night valley (H0-H5): Lowest prices
        time_adjustment = -8.0
    elif 6 <= hour < 8:
        # Early morning (H6-H7): Transition
        time_adjustment = -3.0
    elif 8 <= hour < 20:
        # Peak hours (H8-H19): Higher prices
        time_adjustment = +8.0
    else:
        # Evening (H20-H23): Medium prices
        time_adjustment = 0.0
    
    # Additional evening peak (H18-H20)
    if 18 <= hour < 20:
        time_adjustment += 5.0  # Extra premium
    
    # Seasonal adjustment
    seasonal_adjustment = 0.0
    if season == 'winter':
        # Winter generally higher prices during peak
        if 8 <= hour < 20:
            seasonal_adjustment = +3.0
        else:
            seasonal_adjustment = -1.0
    else:  # summer
        # Summer lower prices during peak
        if 8 <= hour < 20:
            seasonal_adjustment = -3.0
        else:
            seasonal_adjustment = +1.0
    
    # Intra-hourly pattern (Sawtooth based on Kremer et al.)
    # Morning hours (H8-H13): Q1 highest, Q4 lowest
    # Afternoon hours (H14-H19): Q1 lowest, Q4 highest
    quarter_adjustment = 0.0
    
    if 8 <= hour < 14:
        # Morning: Declining from Q1 to Q4
        quarter_adjustment = 3.0 - (quarter * 2.0)  # Q1: +3, Q2: +1, Q3: -1, Q4: -3
    elif 14 <= hour < 20:
        # Afternoon: Rising from Q1 to Q4
        quarter_adjustment = -3.0 + (quarter * 2.0)  # Q1: -3, Q2: -1, Q3: +1, Q4: +3
    else:
        # Off-peak: Mild U-shape
        if quarter in [0, 3]:  # Q1, Q4
            quarter_adjustment = +1.0
        else:  # Q2, Q3
            quarter_adjustment = -1.0
    
    # Stochastic component (market volatility)
    if volatility > 0:
        stochastic = rng.normal(0, volatility)
    else:
        stochastic = 0.0
    
    # Combine all components
    da_price = (
        base_price + 
        time_adjustment + 
        seasonal_adjustment + 
        quarter_adjustment + 
        stochastic
    )
    
    # Ensure price is positive and realistic
    da_price = max(10.0, min(150.0, da_price))
    
    return da_price


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_hourly_products(
    n_hours: int = 24,
    start_time: int = 1440,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 60,
    da_prices: Optional[List[float]] = None
) -> List[Product]:
    """
    Create a sequence of hourly products (60-minute delivery periods).
    
    Args:
        n_hours: Number of hourly products to create
        start_time: Absolute time of first product's delivery start
        gate_open_offset_hours: Hours before delivery when trading opens
        gate_close_offset_minutes: Minutes before delivery when trading closes
        da_prices: Optional list of DA prices per product. If None, uses 50.0 for all
    
    Returns:
        List of Product instances
    
    Example:
        # Create 24 hourly products starting at minute 1440 (Day 2, 00:00)
        # Trading opens at minute 0 (Day 1, 00:00)
        # Trading closes 60 min before delivery
        products = create_hourly_products(
            n_hours=24,
            start_time=1440,
            gate_open_offset_hours=24,
            gate_close_offset_minutes=60
        )
    """
    if da_prices is None:
        da_prices = [50.0] * n_hours
    elif len(da_prices) != n_hours:
        raise ValueError(f"da_prices length ({len(da_prices)}) must match n_hours ({n_hours})")
    
    products = []
    for i in range(n_hours):
        config = ProductConfig(
            product_id=i,
            delivery_start=start_time + (i * 60),
            delivery_duration=60,
            gate_open_offset_hours=gate_open_offset_hours,
            gate_close_offset_minutes=gate_close_offset_minutes,
            da_price=da_prices[i],
            name=f"H{i:02d}"
        )
        products.append(config.to_product())
    
    return products


def create_quarter_hourly_products(
    n_quarters: int = 96,
    start_time: int = 1440,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 5,
    da_prices: Optional[List[float]] = None
) -> List[Product]:
    """
    Create a sequence of quarter-hourly products (15-minute delivery periods).
    
    Args:
        n_quarters: Number of 15-minute products to create
        start_time: Absolute time of first product's delivery start
        gate_open_offset_hours: Hours before delivery when trading opens
        gate_close_offset_minutes: Minutes before delivery when trading closes
        da_prices: Optional list of DA prices per product. If None, uses 50.0 for all
    
    Returns:
        List of Product instances
    
    Example:
        # Create 96 quarter-hourly products (24 hours)
        # More realistic German intrazonal gate-closure: 5 minutes
        products = create_quarter_hourly_products(
            n_quarters=96,
            start_time=1440,
            gate_close_offset_minutes=5
        )
    """
    if da_prices is None:
        da_prices = [50.0] * n_quarters
    elif len(da_prices) != n_quarters:
        raise ValueError(f"da_prices length ({len(da_prices)}) must match n_quarters ({n_quarters})")
    
    products = []
    for i in range(n_quarters):
        hour = i // 4
        quarter = i % 4
        
        config = ProductConfig(
            product_id=i,
            delivery_start=start_time + (i * 15),
            delivery_duration=15,
            gate_open_offset_hours=gate_open_offset_hours,
            gate_close_offset_minutes=gate_close_offset_minutes,
            da_price=da_prices[i],
            name=f"H{hour:02d}Q{quarter + 1}"
        )
        products.append(config.to_product())
    
    return products


def create_quarterly_products(
    n_hours: int = 24,
    start_time: int = 1440,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 5,
    season: Literal['summer', 'winter'] = 'winter',
    base_da_price: float = 45.0,
    price_volatility: float = 5.0,
    add_stochastic_volatility: bool = True,
    seed: Optional[int] = None
) -> List[Product]:
    """
    Create 96 quarterly products (15-min) with realistic DA prices.
    
    Based on empirical data from:
    - Kremer et al. (2021) - EPEX SPOT 2015 data
    - Hourly seasonality patterns
    - Peak/Off-Peak differences
    
    This is the SCIENTIFIC VERSION with realistic price modeling!
    
    Args:
        n_hours: Number of hours (default 24 for full day)
        start_time: Simulation start in minutes (default 1440 = Day 2)
        gate_open_offset_hours: Gate opens X hours before delivery (default 24)
        gate_close_offset_minutes: Gate closes X min before delivery (default 5)
        season: 'summer' or 'winter' for seasonal price patterns
        base_da_price: Base Day-Ahead price in EUR/MWh (default 45.0)
        price_volatility: Stochastic volatility in EUR/MWh (default 5.0)
        add_stochastic_volatility: Whether to add random variation
        seed: Random seed for reproducibility
        
    Returns:
        List of 96 Product instances (H00Q1-H23Q4)
        
    Example:
        # Create 96 products for Winter with realistic prices
        products = create_quarterly_products(
            n_hours=24,
            season='winter',
            base_da_price=45.0,
            seed=42
        )
        
        # Check product details
        for p in products[:4]:
            print(f"{p.name}: DA={p.da_price:.2f} EUR/MWh")
    """
    rng = np.random.default_rng(seed) if seed is not None else np.random.default_rng()
    
    products = []
    product_id = 0
    
    for hour in range(n_hours):
        for quarter in range(4):  # 4 quarters per hour
            
            # Delivery period (15 minutes)
            delivery_start = start_time + (hour * 60) + (quarter * 15)
            
            # Product name (e.g., "H00Q1", "H12Q3", "H23Q4")
            name = f"H{hour:02d}Q{quarter + 1}"
            
            # Generate realistic DA price
            da_price = generate_realistic_da_price(
                hour=hour,
                quarter=quarter,
                season=season,
                base_price=base_da_price,
                volatility=price_volatility if add_stochastic_volatility else 0.0,
                rng=rng
            )
            
            # Create Product using ProductConfig
            config = ProductConfig(
                product_id=product_id,
                delivery_start=delivery_start,
                delivery_duration=15,
                gate_open_offset_hours=gate_open_offset_hours,
                gate_close_offset_minutes=gate_close_offset_minutes,
                da_price=da_price,
                name=name
            )
            
            products.append(config.to_product())
            product_id += 1
    
    return products


def create_single_product(
    product_id: int = 0,
    delivery_start: int = 1440,
    delivery_duration: int = 60,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 60,
    da_price: float = 50.0,
    name: Optional[str] = None
) -> Product:
    """
    Create a single product (useful for backward compatibility).
    
    Args:
        product_id: Product identifier
        delivery_start: Absolute delivery start time
        delivery_duration: Length of delivery in minutes
        gate_open_offset_hours: Hours before delivery when trading opens
        gate_close_offset_minutes: Minutes before delivery when trading closes
        da_price: Day-ahead price
        name: Optional product name
    
    Returns:
        Single Product instance
    
    Example:
        # Create single hourly product for testing
        product = create_single_product(
            product_id=0,
            delivery_start=1440,
            delivery_duration=60,
            da_price=50.0,
            name="H00"
        )
    """
    config = ProductConfig(
        product_id=product_id,
        delivery_start=delivery_start,
        delivery_duration=delivery_duration,
        gate_open_offset_hours=gate_open_offset_hours,
        gate_close_offset_minutes=gate_close_offset_minutes,
        da_price=da_price,
        name=name
    )
    return config.to_product()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def print_quarterly_products_summary(products: List[Product]) -> None:
    """
    Print summary of quarterly products with DA price statistics.
    
    Useful for debugging and validation of realistic price generation.
    
    Args:
        products: List of Product instances
        
    Example:
        products = create_quarterly_products(season='winter')
        print_quarterly_products_summary(products)
    """
    print("\n" + "="*70)
    print("QUARTERLY PRODUCTS SUMMARY")
    print("="*70)
    
    print(f"\nTotal Products: {len(products)}")
    
    # DA Price statistics
    da_prices = [p.da_price for p in products]
    print(f"\nDA PRICE STATISTICS:")
    print(f"   Min:     {min(da_prices):.2f} EUR/MWh")
    print(f"   Max:     {max(da_prices):.2f} EUR/MWh")
    print(f"   Mean:    {np.mean(da_prices):.2f} EUR/MWh")
    print(f"   Std Dev: {np.std(da_prices):.2f} EUR/MWh")
    
    # Sample products
    print(f"\nSAMPLE PRODUCTS:")
    if len(products) >= 96:
        sample_indices = [0, 12, 48, 72, 95]  # H00Q1, H03Q1, H12Q1, H18Q1, H23Q4
    else:
        sample_indices = list(range(min(5, len(products))))
    
    for idx in sample_indices:
        if idx < len(products):
            p = products[idx]
            name_str = p.name if p.name else f"P{p.product_id}"
            print(f"   {name_str}: Delivery {p.delivery_start}-{p.delivery_end} min, "
                  f"DA={p.da_price:.2f} EUR/MWh, Gate {p.gate_open}-{p.gate_close}")
    
    # Hourly averages (if we have 96 products)
    if len(products) == 96:
        print(f"\nHOURLY AVERAGE DA PRICES:")
        for hour in [0, 6, 12, 18, 23]:
            hour_products = [p for p in products if hour * 4 <= p.product_id < (hour + 1) * 4]
            if hour_products:
                avg_price = np.mean([p.da_price for p in hour_products])
                print(f"   H{hour:02d}: {avg_price:.2f} EUR/MWh (Q1-Q4 average)")
        
        # Peak vs Off-Peak
        peak_products = [p for p in products if 8 * 4 <= p.product_id < 20 * 4]
        off_peak_products = [p for p in products if p.product_id < 8 * 4 or p.product_id >= 20 * 4]
        
        if peak_products and off_peak_products:
            print(f"\nPEAK vs OFF-PEAK:")
            print(f"   Peak (H08-H19):    {np.mean([p.da_price for p in peak_products]):.2f} EUR/MWh")
            print(f"   Off-Peak (H00-H07, H20-H23): {np.mean([p.da_price for p in off_peak_products]):.2f} EUR/MWh")
    
    print("\n" + "="*70)
