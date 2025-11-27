"""
Product types for multi-product CID market simulation.

This module defines the Product abstraction representing delivery periods,
their lifecycle (gate-open, gate-close, delivery), and factory functions
for creating product sets.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, replace
from typing import Optional, List


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
    delivery (e.g., H00 = 00:00-01:00, H01 = 01:00-02:00).
    
    Attributes:
        product_id: Unique identifier (e.g., 0, 1, 2, ...)
        delivery_start: Start time of physical delivery (simulation time units)
        delivery_end: End time of physical delivery
        gate_open: Time when trading begins for this product
        gate_close: Time when trading ends for this product
        duration: Length of delivery period in minutes (15, 30, or 60)
        da_price: Day-ahead market clearing price for this product (€/MWh)
        status: Current lifecycle status
    """
    product_id: int
    delivery_start: int
    delivery_end: int
    gate_open: int
    gate_close: int
    duration: int
    da_price: float
    status: ProductStatus = ProductStatus.PENDING
    
    def is_open(self, t: int) -> bool:
        """Check if product is open for trading at time t."""
        return self.gate_open <= t < self.gate_close
    
    def time_to_gate_close(self, t: int) -> Optional[int]:
        """Return time steps until gate closure, or None if already closed."""
        if t >= self.gate_close:
            return None
        return self.gate_close - t
    
    def time_to_delivery(self, t: int) -> Optional[int]:
        """Return time steps until delivery starts, or None if already started."""
        if t >= self.delivery_start:
            return None
        return self.delivery_start - t
    
    def update_status(self, new_status: ProductStatus) -> Product:
        """Return new Product instance with updated status (immutable)."""
        return replace(self, status=new_status)
    
    def __repr__(self) -> str:
        return (
            f"Product(id={self.product_id}, "
            f"delivery={self.delivery_start}-{self.delivery_end}, "
            f"gate={self.gate_open}-{self.gate_close}, "
            f"status={self.status.name})"
        )


@dataclass
class ProductConfig:
    """Configuration for creating a Product instance."""
    product_id: int
    delivery_start: int
    delivery_duration: int = 60
    gate_open_offset_hours: int = 24
    gate_close_offset_minutes: int = 60
    da_price: float = 50.0
    
    def to_product(self) -> Product:
        """Convert configuration to Product instance."""
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
            status=ProductStatus.PENDING
        )


def create_single_product(
    product_id: int = 0,
    delivery_start: int = 1440,
    delivery_duration: int = 60,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 60,
    da_price: float = 50.0
) -> Product:
    """Create a single product (useful for backward compatibility)."""
    config = ProductConfig(
        product_id=product_id,
        delivery_start=delivery_start,
        delivery_duration=delivery_duration,
        gate_open_offset_hours=gate_open_offset_hours,
        gate_close_offset_minutes=gate_close_offset_minutes,
        da_price=da_price
    )
    return config.to_product()


def create_hourly_products(
    n_hours: int = 24,
    start_time: int = 1440,
    gate_open_offset_hours: int = 24,
    gate_close_offset_minutes: int = 60,
    da_prices: Optional[List[float]] = None
) -> List[Product]:
    """Create a sequence of hourly products."""
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
            da_price=da_prices[i]
        )
        products.append(config.to_product())
    
    return products