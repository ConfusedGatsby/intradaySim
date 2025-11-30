"""
Settlement Module for Multi-Product Intraday Market Simulation.

This module handles the settlement of closed products, including:
- Imbalance calculation
- Imbalance cost calculation
- Revenue adjustments
- Settlement logging

Based on standard European Intraday Market settlement procedures.
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from intraday_abm.agents.base import Agent
from intraday_abm.core.product import Product


@dataclass
class SettlementResult:
    """
    Settlement result for a single agent and product.
    
    Attributes:
        agent_id: Agent identifier
        product_id: Product identifier
        da_position: Day-ahead position in MW
        market_position: Final market position in MW
        imbalance: Imbalance (da_position - market_position) in MW
        imbalance_cost: Cost of imbalance in EUR
        lambda_up: Positive imbalance price used (EUR/MWh)
        lambda_down: Negative imbalance price used (EUR/MWh)
        revenue_before: Revenue before settlement in EUR
        revenue_after: Revenue after settlement in EUR
    """
    agent_id: int
    product_id: int
    da_position: float
    market_position: float
    imbalance: float
    imbalance_cost: float
    lambda_up: float
    lambda_down: float
    revenue_before: float
    revenue_after: float
    
    def __repr__(self) -> str:
        return (
            f"Settlement(agent={self.agent_id}, product={self.product_id}, "
            f"imb={self.imbalance:.2f} MW, cost={self.imbalance_cost:.2f} EUR)"
        )


def get_imbalance_prices(
    product: Product,
    base_offset: float = 10.0,
    volatility: float = 2.0,
    use_stochastic: bool = False,
    rng: Optional[Any] = None
) -> tuple[float, float]:
    """
    Calculate imbalance prices for settlement.
    
    European intraday markets typically use:
    - lambda_up (positive imbalance): higher than DA price
    - lambda_down (negative imbalance): lower than DA price
    
    Args:
        product: Product being settled
        base_offset: Base offset from DA price (EUR/MWh)
        volatility: Stochastic volatility (EUR/MWh)
        use_stochastic: Add random component
        rng: Random number generator
        
    Returns:
        Tuple of (lambda_up, lambda_down) in EUR/MWh
        
    Example:
        DA Price = 45 EUR/MWh, offset = 10
        -> lambda_up = 55 EUR/MWh
        -> lambda_down = 35 EUR/MWh
    """
    da_price = product.da_price
    
    if use_stochastic and rng is not None:
        # Add stochastic component
        offset_up = base_offset + rng.uniform(-volatility, volatility)
        offset_down = base_offset + rng.uniform(-volatility, volatility)
    else:
        offset_up = base_offset
        offset_down = base_offset
    
    lambda_up = da_price + offset_up
    lambda_down = max(0.0, da_price - offset_down)
    
    return lambda_up, lambda_down


def calculate_imbalance_cost(
    imbalance: float,
    lambda_up: float,
    lambda_down: float
) -> float:
    """
    Calculate imbalance cost based on European market convention.
    
    Convention:
    - Positive imbalance (over-production): pay lambda_up
    - Negative imbalance (under-production): pay lambda_down
    
    Args:
        imbalance: Imbalance in MW (da_position - market_position)
        lambda_up: Positive imbalance price (EUR/MWh)
        lambda_down: Negative imbalance price (EUR/MWh)
        
    Returns:
        Imbalance cost in EUR (always positive)
        
    Example:
        imbalance = +10 MW (over-production)
        lambda_up = 55 EUR/MWh
        -> cost = 10 * 55 = 550 EUR
        
        imbalance = -10 MW (under-production)
        lambda_down = 35 EUR/MWh
        -> cost = 10 * 35 = 350 EUR
    """
    if imbalance > 0.0:
        # Over-production: pay lambda_up
        cost = imbalance * lambda_up
    elif imbalance < 0.0:
        # Under-production: pay lambda_down
        cost = abs(imbalance) * lambda_down
    else:
        cost = 0.0
    
    return cost


def settle_agent_product(
    agent: Agent,
    product: Product,
    lambda_up: float,
    lambda_down: float,
    apply_to_revenue: bool = True
) -> SettlementResult:
    """
    Settle a single agent for a single product.
    
    This function:
    1. Retrieves agent's positions (DA and market)
    2. Calculates imbalance
    3. Calculates imbalance cost
    4. Optionally applies cost to agent's revenue
    5. Returns detailed settlement result
    
    Args:
        agent: Agent to settle
        product: Product being settled
        lambda_up: Positive imbalance price
        lambda_down: Negative imbalance price
        apply_to_revenue: If True, deduct cost from agent revenue
        
    Returns:
        SettlementResult with all settlement details
    """
    product_id = product.product_id
    pi = agent.private_info
    
    # Get positions
    if agent.is_multi_product:
        da_position = pi.da_positions.get(product_id, 0.0)
        market_position = pi.positions.get(product_id, 0.0)
        revenue_before = pi.revenues.get(product_id, 0.0)
    else:
        # Single-product mode (fallback)
        da_position = pi.da_position
        market_position = pi.market_position
        revenue_before = pi.revenue
    
    # Calculate imbalance
    imbalance = da_position - market_position
    
    # Calculate cost
    imbalance_cost = calculate_imbalance_cost(imbalance, lambda_up, lambda_down)
    
    # Apply to revenue if requested
    if apply_to_revenue and imbalance_cost > 0:
        if agent.is_multi_product:
            pi.update_revenue(product_id, -imbalance_cost)
            revenue_after = pi.revenues.get(product_id, 0.0)
        else:
            pi.revenue -= imbalance_cost
            revenue_after = pi.revenue
    else:
        revenue_after = revenue_before
    
    # Create settlement result
    result = SettlementResult(
        agent_id=agent.id,
        product_id=product_id,
        da_position=da_position,
        market_position=market_position,
        imbalance=imbalance,
        imbalance_cost=imbalance_cost,
        lambda_up=lambda_up,
        lambda_down=lambda_down,
        revenue_before=revenue_before,
        revenue_after=revenue_after
    )
    
    return result


def settle_products(
    products_to_settle: List[Product],
    agents: List[Agent],
    base_offset: float = 10.0,
    volatility: float = 2.0,
    use_stochastic: bool = False,
    rng: Optional[Any] = None,
    apply_to_revenue: bool = True,
    verbose: bool = False
) -> Dict[int, List[SettlementResult]]:
    """
    Settle multiple products for all agents.
    
    This is the main settlement function called when products close.
    
    Args:
        products_to_settle: List of products to settle
        agents: List of all agents
        base_offset: Base offset for imbalance prices
        volatility: Stochastic volatility
        use_stochastic: Use stochastic imbalance prices
        rng: Random number generator
        apply_to_revenue: Apply costs to agent revenues
        verbose: Print settlement summary
        
    Returns:
        Dictionary mapping product_id to list of SettlementResults
        
    Example:
        # At each simulation step
        closed_products = mo.update_product_status(t)
        if closed_products:
            products = [mo.products[pid] for pid in closed_products]
            results = settle_products(products, agents, verbose=True)
    """
    all_results = {}
    
    for product in products_to_settle:
        product_id = product.product_id
        
        # Get imbalance prices for this product
        lambda_up, lambda_down = get_imbalance_prices(
            product=product,
            base_offset=base_offset,
            volatility=volatility,
            use_stochastic=use_stochastic,
            rng=rng
        )
        
        # Settle each agent
        product_results = []
        total_imbalance = 0.0
        total_cost = 0.0
        
        for agent in agents:
            if not agent.is_multi_product:
                continue  # Skip single-product agents
            
            result = settle_agent_product(
                agent=agent,
                product=product,
                lambda_up=lambda_up,
                lambda_down=lambda_down,
                apply_to_revenue=apply_to_revenue
            )
            
            product_results.append(result)
            total_imbalance += result.imbalance
            total_cost += result.imbalance_cost
        
        all_results[product_id] = product_results
        
        # Verbose output
        if verbose:
            print(f"  Settlement P{product_id}: "
                  f"{len(product_results)} agents, "
                  f"Total Imb: {total_imbalance:+.1f} MW, "
                  f"Total Cost: {total_cost:,.0f} EUR, "
                  f"λ+={lambda_up:.2f}, λ-={lambda_down:.2f}")
    
    return all_results


def log_settlement_results(
    settlement_results: Dict[int, List[SettlementResult]],
    agent_logs: Dict[int, Dict[str, List]]
) -> None:
    """
    Log settlement results to agent logs.
    
    This function updates agent_logs with settlement information for analysis.
    
    Args:
        settlement_results: Settlement results from settle_products()
        agent_logs: Agent logging dictionary to update
        
    Example:
        results = settle_products(closed_products, agents)
        log_settlement_results(results, agent_logs)
    """
    for product_id, results in settlement_results.items():
        for result in results:
            agent_id = result.agent_id
            
            if agent_id not in agent_logs:
                continue
            
            # Initialize settlement logging lists if needed
            if 'settlement_products' not in agent_logs[agent_id]:
                agent_logs[agent_id]['settlement_products'] = []
                agent_logs[agent_id]['settlement_imbalances'] = []
                agent_logs[agent_id]['settlement_costs'] = []
                agent_logs[agent_id]['settlement_lambda_up'] = []
                agent_logs[agent_id]['settlement_lambda_down'] = []
            
            # Append settlement data
            agent_logs[agent_id]['settlement_products'].append(product_id)
            agent_logs[agent_id]['settlement_imbalances'].append(result.imbalance)
            agent_logs[agent_id]['settlement_costs'].append(result.imbalance_cost)
            agent_logs[agent_id]['settlement_lambda_up'].append(result.lambda_up)
            agent_logs[agent_id]['settlement_lambda_down'].append(result.lambda_down)


def get_total_settlement_cost(
    agent_logs: Dict[int, Dict[str, List]],
    agent_id: int
) -> float:
    """
    Get total settlement cost for an agent across all products.
    
    Args:
        agent_logs: Agent logging dictionary
        agent_id: Agent identifier
        
    Returns:
        Total settlement cost in EUR
    """
    if agent_id not in agent_logs:
        return 0.0
    
    if 'settlement_costs' not in agent_logs[agent_id]:
        return 0.0
    
    return sum(agent_logs[agent_id]['settlement_costs'])


def print_settlement_summary(
    settlement_results: Dict[int, List[SettlementResult]],
    agents: List[Agent]
) -> None:
    """
    Print comprehensive settlement summary.
    
    Args:
        settlement_results: Settlement results from settle_products()
        agents: List of agents
    """
    print("\n" + "="*80)
    print("SETTLEMENT SUMMARY")
    print("="*80)
    
    # Calculate totals
    total_products = len(settlement_results)
    total_settlements = sum(len(results) for results in settlement_results.values())
    total_cost = sum(
        result.imbalance_cost 
        for results in settlement_results.values() 
        for result in results
    )
    total_imbalance = sum(
        abs(result.imbalance)
        for results in settlement_results.values()
        for result in results
    )
    
    print(f"\nProducts Settled:      {total_products}")
    print(f"Total Settlements:     {total_settlements}")
    print(f"Total Imbalance:       {total_imbalance:,.1f} MW")
    print(f"Total Imb. Costs:      {total_cost:,.0f} EUR")
    
    # Per-agent summary
    print(f"\n{'─'*80}")
    print("PER-AGENT SETTLEMENT COSTS")
    print(f"{'─'*80}")
    
    agent_costs = {}
    for results in settlement_results.values():
        for result in results:
            if result.agent_id not in agent_costs:
                agent_costs[result.agent_id] = 0.0
            agent_costs[result.agent_id] += result.imbalance_cost
    
    # Sort by cost (descending)
    sorted_agents = sorted(agent_costs.items(), key=lambda x: x[1], reverse=True)
    
    for agent_id, cost in sorted_agents[:10]:  # Top 10
        agent_type = "Unknown"
        for ag in agents:
            if ag.id == agent_id:
                agent_type = ag.__class__.__name__
                break
        print(f"  Agent {agent_id:3d} ({agent_type:20s}): {cost:>12,.0f} EUR")
    
    print("="*80)