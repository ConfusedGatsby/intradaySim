"""
Multi-Product Simulation for Continuous Intraday Market.

This module provides run_multi_product_simulation() which orchestrates
trading across multiple delivery products with product lifecycle management.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from random import Random

from intraday_abm.agents.base import Agent
from intraday_abm.core.product import Product
from intraday_abm.core.multi_product_market_operator import MultiProductMarketOperator
from intraday_abm.core.order import Order


# Global debug file handle
_sim_debug_file = None


def set_sim_debug_file(filepath: str):
    """Set the simulation debug output file."""
    global _sim_debug_file
    _sim_debug_file = open(filepath, 'w', encoding='utf-8')


def close_sim_debug_file():
    """Close the simulation debug output file."""
    global _sim_debug_file
    if _sim_debug_file:
        _sim_debug_file.close()
        _sim_debug_file = None


def sim_debug_print(msg: str):
    """Print to simulation debug file if set, otherwise do nothing."""
    global _sim_debug_file
    if _sim_debug_file:
        _sim_debug_file.write(msg + '\n')
        _sim_debug_file.flush()


def run_multi_product_simulation(
    products: List[Product],
    agents: List[Agent],
    n_steps: int = 200,
    seed: Optional[int] = None,
    verbose: bool = True,
) -> tuple[Dict[str, List], Dict[int, Dict[str, List]], MultiProductMarketOperator]:
    """
    Run multi-product continuous intraday market simulation.
    
    This function orchestrates trading across multiple delivery products,
    managing product lifecycles (PENDING → OPEN → CLOSED → SETTLED) and
    routing agent orders to the correct products.
    
    Features:
    - Supports both multi-product and single-product agents (intelligent fallback)
    - Product lifecycle management (gate opening/closing)
    - Per-product logging
    - Agent state tracking per product
    
    Args:
        products: List of Product instances to simulate
        agents: List of Agent instances (can mix single and multi-product)
        n_steps: Number of simulation steps
        seed: Random seed for reproducibility
        verbose: If True, print progress
        
    Returns:
        Tuple of (market_log, agent_logs, market_operator)
        - market_log: Dict with keys ["t", "n_trades", "total_volume", "product_states", ...]
        - agent_logs: Dict[agent_id, Dict[str, List]] with per-agent tracking
        - market_operator: Final MultiProductMarketOperator state
    """
    
    if seed is not None:
        rng = Random(seed)
    else:
        rng = Random()
    
    # Initialize market operator
    mo = MultiProductMarketOperator.from_products(products)
    
    # Open all products at t=0 (for simplicity)
    mo.open_products(t=0)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"MULTI-PRODUCT SIMULATION")
        print(f"{'='*60}")
        print(f"Products: {len(products)}")
        print(f"Agents: {len(agents)}")
        print(f"  - Multi-Product: {sum(1 for a in agents if a.is_multi_product)}")
        print(f"  - Single-Product: {sum(1 for a in agents if not a.is_multi_product)}")
        print(f"Steps: {n_steps}")
        print(f"{'='*60}\n")
    
    sim_debug_print("\n" + "="*60)
    sim_debug_print("SIMULATION DEBUG LOG")
    sim_debug_print("="*60)
    sim_debug_print(f"Products: {len(products)}")
    sim_debug_print(f"Agents: {len(agents)}")
    sim_debug_print(f"Steps: {n_steps}")
    sim_debug_print("="*60 + "\n")
    
    # Initialize logging
    market_log = {
        "t": [],
        "n_trades": [],
        "total_volume": [],
        "n_open_products": [],
        "total_orders": [],
    }
    
    # Per-product logging
    for product in products:
        pid = product.product_id
        market_log[f"p{pid}_trades"] = []
        market_log[f"p{pid}_volume"] = []
        market_log[f"p{pid}_orders"] = []
        market_log[f"p{pid}_status"] = []
    
    # Agent logging
    agent_logs: Dict[int, Dict[str, List]] = {}
    for agent in agents:
        agent_logs[agent.id] = {
            "t": [],
            "total_revenue": [],
            "total_position": [],
            "total_imbalance": [],
            "n_orders_placed": [],
        }
        
        # If multi-product, add per-product tracking
        if agent.is_multi_product:
            for product in products:
                pid = product.product_id
                agent_logs[agent.id][f"p{pid}_position"] = []
                agent_logs[agent.id][f"p{pid}_revenue"] = []
                agent_logs[agent.id][f"p{pid}_imbalance"] = []
    
    # Main simulation loop
    for t in range(n_steps):
        
        sim_debug_print(f"\n{'='*60}")
        sim_debug_print(f"TIMESTEP t={t}")
        sim_debug_print(f"{'='*60}")
        
        # Update product statuses (handle gate closures)
        closed_products = mo.update_product_status(t)
        if closed_products and verbose and t % 50 == 0:
            print(f"  t={t}: Closed products {closed_products}")
        
        if closed_products:
            sim_debug_print(f"Closed products: {closed_products}")
        
        # Get currently open products
        open_product_ids = mo.get_open_products(t)
        
        sim_debug_print(f"Open products: {open_product_ids}")
        
        if not open_product_ids:
            if verbose and t % 50 == 0:
                print(f"  t={t}: No open products")
            sim_debug_print("No open products - skipping")
            continue
        
        # Get public info for open products
        public_info = mo.get_public_info(t, product_ids=open_product_ids)
        
        sim_debug_print(f"\nPublic Info:")
        for pid, info in public_info.items():
            sim_debug_print(f"  Product {pid}: tob={info.tob}, da_price={info.da_price}")
        
        # Shuffle agent order for fairness
        agent_order = list(agents)
        rng.shuffle(agent_order)
        
        sim_debug_print(f"\nAgent order: {[a.id for a in agent_order]}")
        
        # Track trades this step
        step_trades = []
        step_volume = 0.0
        
        # Each agent decides and places orders
        for agent in agent_order:
            
            sim_debug_print(f"\n--- Agent {agent.id} (is_multi_product={agent.is_multi_product}) ---")
            
            if agent.is_multi_product:
                # Multi-Product Agent: decide_orders()
                sim_debug_print(f"Calling decide_orders() for Agent {agent.id}...")
                
                orders_dict = agent.decide_orders(t, public_info)
                
                sim_debug_print(f"Agent {agent.id} returned orders for {len(orders_dict)} products")
                
                # Process orders for each product
                for product_id, order_or_list in orders_dict.items():
                    if product_id not in open_product_ids:
                        sim_debug_print(f"  Product {product_id} not in open_product_ids - SKIPPING")
                        continue  # Skip closed products
                    
                    # Handle single order or list of orders
                    orders = order_or_list if isinstance(order_or_list, list) else [order_or_list]
                    
                    sim_debug_print(f"  Product {product_id}: Processing {len(orders)} orders")
                    
                    for idx, order in enumerate(orders):
                        if order is None:
                            sim_debug_print(f"    Order {idx}: None - SKIPPING")
                            continue
                        
                        sim_debug_print(f"    Order {idx}: Agent {order.agent_id}, {order.side.name}, "
                                      f"{order.volume:.2f} MW @ {order.price:.2f} €, Product {order.product_id}")
                        
                        # Process order
                        try:
                            trades = mo.process_order(order, t, validate_time=True)
                            
                            sim_debug_print(f"      → Processed successfully, {len(trades)} trades generated")
                            
                            # Update agent state
                            for trade in trades:
                                from intraday_abm.core.types import Side
                                
                                # Determine which side the agent was on
                                if trade.buy_agent_id == agent.id:
                                    agent.on_trade(
                                        volume=trade.volume,
                                        price=trade.price,
                                        side=Side.BUY,
                                        product_id=trade.product_id
                                    )
                                    sim_debug_print(f"      → Agent {agent.id} was BUYER in trade")
                                elif trade.sell_agent_id == agent.id:
                                    agent.on_trade(
                                        volume=trade.volume,
                                        price=trade.price,
                                        side=Side.SELL,
                                        product_id=trade.product_id
                                    )
                                    sim_debug_print(f"      → Agent {agent.id} was SELLER in trade")
                                
                                step_trades.append(trade)
                                step_volume += trade.volume
                        
                        except ValueError as e:
                            # Product not open anymore
                            sim_debug_print(f"      → ValueError: {e}")
                            if verbose and "not open" in str(e).lower():
                                pass  # Silently ignore
                            else:
                                if verbose:
                                    print(f"  Warning: {e}")
                        except Exception as e:
                            sim_debug_print(f"      → Exception: {type(e).__name__}: {e}")
                            if verbose:
                                print(f"  Warning: {type(e).__name__}: {e}")
            
            else:
                # Single-Product Agent: fallback to decide_order()
                # Use first open product
                if not open_product_ids:
                    sim_debug_print(f"Agent {agent.id}: No open products for single-product agent")
                    continue
                
                fallback_product_id = open_product_ids[0]
                fallback_public_info = public_info[fallback_product_id]
                
                sim_debug_print(f"Calling decide_order() for Agent {agent.id} (fallback to Product {fallback_product_id})...")
                
                order_or_list = agent.decide_order(t, fallback_public_info)
                
                if order_or_list is None:
                    sim_debug_print(f"Agent {agent.id} returned None")
                    continue
                
                # Handle single order or list of orders
                orders = order_or_list if isinstance(order_or_list, list) else [order_or_list]
                
                sim_debug_print(f"Agent {agent.id} returned {len(orders)} orders")
                
                for idx, order in enumerate(orders):
                    if order is None:
                        sim_debug_print(f"  Order {idx}: None - SKIPPING")
                        continue
                    
                    # Set product_id if not set
                    if order.product_id is None or order.product_id == 0:
                        order.product_id = fallback_product_id
                    
                    sim_debug_print(f"  Order {idx}: Agent {order.agent_id}, {order.side.name}, "
                                  f"{order.volume:.2f} MW @ {order.price:.2f} €, Product {order.product_id}")
                    
                    # Process order
                    try:
                        trades = mo.process_order(order, t, validate_time=True)
                        
                        sim_debug_print(f"    → Processed successfully, {len(trades)} trades generated")
                        
                        # Update agent state (single-product style)
                        for trade in trades:
                            from intraday_abm.core.types import Side
                            
                            if trade.buy_agent_id == agent.id:
                                agent.on_trade(
                                    volume=trade.volume,
                                    price=trade.price,
                                    side=Side.BUY
                                )
                                sim_debug_print(f"    → Agent {agent.id} was BUYER in trade")
                            elif trade.sell_agent_id == agent.id:
                                agent.on_trade(
                                    volume=trade.volume,
                                    price=trade.price,
                                    side=Side.SELL
                                )
                                sim_debug_print(f"    → Agent {agent.id} was SELLER in trade")
                            
                            step_trades.append(trade)
                            step_volume += trade.volume
                    
                    except ValueError as e:
                        sim_debug_print(f"    → ValueError: {e}")
                        if verbose and "not open" not in str(e).lower():
                            print(f"  Warning: {e}")
                    except Exception as e:
                        sim_debug_print(f"    → Exception: {type(e).__name__}: {e}")
                        if verbose:
                            print(f"  Warning: {type(e).__name__}: {e}")
        
        sim_debug_print(f"\nStep {t} summary: {len(step_trades)} trades, {step_volume:.2f} MW")
        
        # Update imbalances for all agents and products
        for agent in agents:
            if agent.is_multi_product:
                for product_id in open_product_ids:
                    try:
                        agent.update_imbalance(t, product_id)
                    except Exception:
                        pass  # Skip if product not relevant for agent
            else:
                agent.update_imbalance(t)
        
        # Log market state
        market_log["t"].append(t)
        market_log["n_trades"].append(len(step_trades))
        market_log["total_volume"].append(step_volume)
        market_log["n_open_products"].append(len(open_product_ids))
        market_log["total_orders"].append(mo.total_orders())
        
        # Log per-product state
        for product in products:
            pid = product.product_id
            
            # Count trades for this product
            product_trades = [tr for tr in step_trades if tr.product_id == pid]
            product_volume = sum(tr.volume for tr in product_trades)
            
            market_log[f"p{pid}_trades"].append(len(product_trades))
            market_log[f"p{pid}_volume"].append(product_volume)
            market_log[f"p{pid}_orders"].append(len(mo.order_books[pid]) if pid in mo.order_books else 0)
            market_log[f"p{pid}_status"].append(mo.products[pid].status.name if pid in mo.products else "UNKNOWN")
        
        # Log agent state
        for agent in agents:
            agent_log = agent_logs[agent.id]
            agent_log["t"].append(t)
            
            if agent.is_multi_product:
                pi = agent.private_info
                agent_log["total_revenue"].append(pi.total_revenue())
                agent_log["total_position"].append(pi.total_position())
                agent_log["total_imbalance"].append(pi.total_imbalance())
                agent_log["n_orders_placed"].append(0)  # TODO: track
                
                # Per-product state
                for product in products:
                    pid = product.product_id
                    agent_log[f"p{pid}_position"].append(pi.positions.get(pid, 0.0))
                    agent_log[f"p{pid}_revenue"].append(pi.revenues.get(pid, 0.0))
                    agent_log[f"p{pid}_imbalance"].append(pi.imbalances.get(pid, 0.0))
            else:
                pi = agent.private_info
                agent_log["total_revenue"].append(pi.revenue)
                agent_log["total_position"].append(pi.market_position)
                agent_log["total_imbalance"].append(pi.imbalance)
                agent_log["n_orders_placed"].append(0)  # TODO: track
        
        # Progress output
        if verbose and t % 50 == 0:
            print(f"  t={t:3d} | Open: {len(open_product_ids)} | "
                  f"Trades: {len(step_trades):3d} | Volume: {step_volume:6.1f} MW | "
                  f"Orders: {mo.total_orders():3d}")
    
    sim_debug_print("\n" + "="*60)
    sim_debug_print("SIMULATION COMPLETE")
    sim_debug_print("="*60)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"SIMULATION COMPLETE")
        print(f"{'='*60}")
        total_trades = sum(market_log["n_trades"])
        total_vol = sum(market_log["total_volume"])
        print(f"Total Trades: {total_trades}")
        print(f"Total Volume: {total_vol:.1f} MW")
        print(f"{'='*60}\n")
    
    return market_log, agent_logs, mo


def print_simulation_summary(
    market_log: Dict[str, List],
    agent_logs: Dict[int, Dict[str, List]],
    mo: MultiProductMarketOperator
):
    """
    Print summary statistics from multi-product simulation.
    
    Args:
        market_log: Market log from run_multi_product_simulation
        agent_logs: Agent logs from run_multi_product_simulation
        mo: Market operator from run_multi_product_simulation
    """
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    
    # Market stats
    total_trades = sum(market_log["n_trades"])
    total_volume = sum(market_log["total_volume"])
    avg_trades_per_step = total_trades / len(market_log["t"]) if market_log["t"] else 0
    
    print(f"\nMarket Statistics:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Total Volume: {total_volume:.1f} MW")
    print(f"  Avg Trades/Step: {avg_trades_per_step:.2f}")
    
    # Per-product stats
    print(f"\nPer-Product Statistics:")
    for pid in range(len(mo.products)):
        if f"p{pid}_trades" in market_log:
            p_trades = sum(market_log[f"p{pid}_trades"])
            p_volume = sum(market_log[f"p{pid}_volume"])
            print(f"  Product {pid}: {p_trades} trades, {p_volume:.1f} MW")
    
    # Agent stats
    print(f"\nAgent Statistics:")
    for agent_id, log in agent_logs.items():
        if log["total_revenue"]:
            final_revenue = log["total_revenue"][-1]
            final_position = log["total_position"][-1]
            print(f"  Agent {agent_id}: Revenue={final_revenue:.2f} €, Position={final_position:.2f} MW")
    
    print("="*60)