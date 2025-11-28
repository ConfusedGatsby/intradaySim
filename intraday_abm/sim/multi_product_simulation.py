"""
Multi-Product Simulation for Continuous Intraday Market.

This module provides run_multi_product_simulation() which orchestrates
trading across multiple delivery products with product lifecycle management.

FIXED VERSION:
- Counterparty agents (resting orders) now get on_trade() callbacks
- Both buyer AND seller are updated for every trade
- Fixes VariableAgent position/revenue tracking bug
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
    n_steps: int,
    seed: int = 42,
    verbose: bool = False
) -> tuple[Dict[str, List], Dict[int, Dict[str, List]], MultiProductMarketOperator]:
    """
    Run multi-product continuous intraday market simulation.
    
    Args:
        products: List of Product instances (delivery periods)
        agents: List of Agent instances (traders)
        n_steps: Number of simulation steps
        seed: Random seed
        verbose: Print progress output
        
    Returns:
        Tuple of (market_log, agent_logs, market_operator)
    """
    rng = Random(seed)
    
    # Initialize market operator with proper order books
    mo = MultiProductMarketOperator.from_products(products)
    # Update initial statuses (open products where gate_open has passed)
    mo.update_product_status(t=0)
    
    # ============================================================================
    # FIX: Create agent lookup map for counterparty updates
    # ============================================================================
    agent_by_id = {ag.id: ag for ag in agents}
    
    # Initialize logging dictionaries
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
    agent_logs = {}
    for agent in agents:
        agent_log = {
            "agent_id": agent.id,
            "agent_type": agent.__class__.__name__,
            "t": [],
            "total_revenue": [],
            "total_position": [],
            "total_imbalance": [],
            "n_orders_placed": [],
        }
        
        # Per-product state for multi-product agents
        if agent.is_multi_product:
            for product in products:
                pid = product.product_id
                agent_log[f"p{pid}_position"] = []
                agent_log[f"p{pid}_revenue"] = []
                agent_log[f"p{pid}_imbalance"] = []
        
        agent_logs[agent.id] = agent_log
    
    if verbose:
        print("\n" + "="*60)
        print("MULTI-PRODUCT SIMULATION")
        print("="*60)
        print(f"Products: {len(products)}")
        print(f"Agents: {len(agents)}")
        print(f"  - Multi-Product: {sum(1 for a in agents if a.is_multi_product)}")
        print(f"  - Single-Product: {sum(1 for a in agents if not a.is_multi_product)}")
        print(f"Steps: {n_steps}")
        print("="*60)
    
    sim_debug_print("\n" + "="*60)
    sim_debug_print("MULTI-PRODUCT SIMULATION START")
    sim_debug_print("="*60)
    sim_debug_print(f"Products: {len(products)}")
    sim_debug_print(f"Agents: {len(agents)}")
    sim_debug_print(f"Steps: {n_steps}")
    
    # Main simulation loop
    for t in range(n_steps):
        sim_debug_print(f"\n{'='*60}")
        sim_debug_print(f"STEP {t}")
        sim_debug_print(f"{'='*60}")
        
        # Update product lifecycle (open/close/settle)
        closed_products = mo.update_product_status(t)
        if verbose and closed_products and t % 50 == 0:
            print(f"  t={t}: Closed products {closed_products}")
        if closed_products:
            sim_debug_print(f"Closed products: {closed_products}")
        
        # Get currently open products
        open_product_ids = mo.get_open_products(t)
        sim_debug_print(f"\nOpen products: {open_product_ids}")
        
        # Track trades this step
        step_trades = []
        step_volume = 0.0
        
        # Build public info for all open products
        from intraday_abm.core.types import PublicInfo
        
        public_info = {}
        for product_id in open_product_ids:
            tob = mo.get_tob(product_id)
            product = mo.products[product_id]
            
            public_info[product_id] = PublicInfo(
                tob=tob,
                da_price=product.da_price,
                product=product
            )
        
        # Agent decision and order processing
        for agent in agents:
            sim_debug_print(f"\n--- Agent {agent.id} (is_multi_product={agent.is_multi_product}) ---")
            
            # Multi-Product or Single-Product?
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
                            
                            # ============================================================================
                            # FIX: Update BOTH buyer AND seller (not just current agent)
                            # ============================================================================
                            for trade in trades:
                                from intraday_abm.core.types import Side
                                
                                # Update BUYER (might be current agent OR resting order counterparty)
                                buyer = agent_by_id.get(trade.buy_agent_id)
                                if buyer:
                                    buyer.on_trade(
                                        volume=trade.volume,
                                        price=trade.price,
                                        side=Side.BUY,
                                        product_id=trade.product_id
                                    )
                                    sim_debug_print(f"      → Agent {trade.buy_agent_id} was BUYER in trade")
                                
                                # Update SELLER (might be current agent OR resting order counterparty)
                                seller = agent_by_id.get(trade.sell_agent_id)
                                if seller:
                                    seller.on_trade(
                                        volume=trade.volume,
                                        price=trade.price,
                                        side=Side.SELL,
                                        product_id=trade.product_id
                                    )
                                    sim_debug_print(f"      → Agent {trade.sell_agent_id} was SELLER in trade")
                                
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
                        
                        # ============================================================================
                        # FIX: Update BOTH buyer AND seller (not just current agent)
                        # ============================================================================
                        for trade in trades:
                            from intraday_abm.core.types import Side
                            
                            # Update BUYER
                            buyer = agent_by_id.get(trade.buy_agent_id)
                            if buyer:
                                buyer.on_trade(
                                    volume=trade.volume,
                                    price=trade.price,
                                    side=Side.BUY
                                )
                                sim_debug_print(f"    → Agent {trade.buy_agent_id} was BUYER in trade")
                            
                            # Update SELLER
                            seller = agent_by_id.get(trade.sell_agent_id)
                            if seller:
                                seller.on_trade(
                                    volume=trade.volume,
                                    price=trade.price,
                                    side=Side.SELL
                                )
                                sim_debug_print(f"    → Agent {trade.sell_agent_id} was SELLER in trade")
                            
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
        total_trades = sum(market_log["n_trades"])
        total_volume = sum(market_log["total_volume"])
        print("\n" + "="*60)
        print("SIMULATION COMPLETE")
        print("="*60)
        print(f"Total Trades: {total_trades}")
        print(f"Total Volume: {total_volume:.1f} MW")
        print("="*60)
    
    return market_log, agent_logs, mo


def print_simulation_summary(
    market_log: Dict[str, List],
    agent_logs: Dict[int, Dict[str, List]],
    mo: MultiProductMarketOperator
) -> None:
    """
    Print summary statistics from simulation results.
    
    Args:
        market_log: Market-level log dictionary
        agent_logs: Agent-level log dictionaries
        mo: Market operator instance
    """
    print("\n" + "="*60)
    print("SIMULATION SUMMARY")
    print("="*60)
    
    # Market statistics
    total_trades = sum(market_log["n_trades"])
    total_volume = sum(market_log["total_volume"])
    avg_trades_per_step = total_trades / len(market_log["t"]) if market_log["t"] else 0
    
    print(f"\nMarket Statistics:")
    print(f"  Total Trades: {total_trades}")
    print(f"  Total Volume: {total_volume:.1f} MW")
    print(f"  Avg Trades/Step: {avg_trades_per_step:.2f}")
    
    # Per-product statistics (show sample)
    print(f"\nPer-Product Statistics:")
    products = list(mo.products.values())
    
    # Show first 10 products or all if fewer
    sample_products = products[:min(10, len(products))]
    
    for product in sample_products:
        pid = product.product_id
        product_trades = market_log[f"p{pid}_trades"][-1] if f"p{pid}_trades" in market_log else 0
        product_volume = market_log[f"p{pid}_volume"][-1] if f"p{pid}_volume" in market_log else 0.0
        
        product_name = product.name if hasattr(product, 'name') and product.name else f"Product {pid}"
        print(f"  {product_name}: {product_trades} trades, {product_volume:.1f} MW")
    
    if len(products) > 10:
        print(f"  ... and {len(products) - 10} more products")
    
    # Agent statistics
    print(f"\nAgent Statistics:")
    for agent_id, agent_log in agent_logs.items():
        if not agent_log["t"]:
            continue
        
        final_revenue = agent_log["total_revenue"][-1]
        final_position = agent_log["total_position"][-1]
        agent_type = agent_log["agent_type"]
        
        print(f"  Agent {agent_id}: Revenue={final_revenue:.2f} €, Position={final_position:.2f} MW")
    
    print("="*60)
