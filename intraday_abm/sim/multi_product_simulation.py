"""
Multi-Product Simulation for Continuous Intraday Market.

This module provides run_multi_product_simulation() which orchestrates
trading across multiple delivery products with product lifecycle management.

FIXED VERSION:
- Counterparty agents (resting orders) now get on_trade() callbacks
- Both buyer AND seller are updated for every trade
- Fixes VariableAgent position/revenue tracking bug
- SETTLEMENT: Added imbalance cost settlement for closed products
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from random import Random

from intraday_abm.agents.base import Agent
from intraday_abm.core.product import Product
from intraday_abm.core.multi_product_market_operator import MultiProductMarketOperator
from intraday_abm.core.order import Order

# SETTLEMENT: Import settlement functions
from intraday_abm.sim.settlement import (
    settle_products,
    log_settlement_results
)


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
    verbose: bool = False,
    # SETTLEMENT: New parameters
    enable_settlement: bool = True,
    settlement_offset: float = 10.0,
    settlement_volatility: float = 2.0,
    use_stochastic_settlement: bool = False
) -> tuple[Dict[str, List], Dict[int, Dict[str, List]], MultiProductMarketOperator]:
    """
    Run multi-product continuous intraday market simulation.
    
    Args:
        products: List of Product instances (delivery periods)
        agents: List of Agent instances (traders)
        n_steps: Number of simulation steps
        seed: Random seed
        verbose: Print progress output
        enable_settlement: Enable imbalance cost settlement (default: True)
        settlement_offset: Base offset for imbalance prices (default: 10.0 EUR/MWh)
        settlement_volatility: Stochastic volatility (default: 2.0 EUR/MWh)
        use_stochastic_settlement: Add randomness to imbalance prices (default: False)
        
    Returns:
        Tuple of (market_log, agent_logs, market_operator)
    """
    rng = Random(seed)
    
    # Initialize market operator with proper order books
    mo = MultiProductMarketOperator.from_products(products)
    # Update initial statuses (open products where gate_open has passed)
    mo.update_product_status(t=0)
    
    # ============================================================================
    # Create agent lookup map for counterparty updates
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
        agent_logs[agent.id] = {
            "t": [],
            "total_revenue": [],
            "agent_type": agent.__class__.__name__,
            # SETTLEMENT: Add settlement tracking
            "settlement_products": [],
            "settlement_imbalances": [],
            "settlement_costs": [],
            "settlement_lambda_up": [],      # ⬅️ NEU! Diese Zeile hinzufügen
            "settlement_lambda_down": [],    # ⬅️ NEU! Diese Zeile hinzufügen
            "total_settlement_cost": [],
        }
    
    # SETTLEMENT: Track total settlement statistics
    total_settlement_cost = 0.0
    total_settled_products = 0
    
    # Banner
    if verbose:
        print()
        print("="*60)
        print("MULTI-PRODUCT SIMULATION")
        print("="*60)
        print(f"Products: {len(products)}")
        print(f"Agents: {len(agents)}")
        print(f"  - Multi-Product: {sum(1 for a in agents if a.is_multi_product)}")
        print(f"  - Single-Product: {sum(1 for a in agents if not a.is_multi_product)}")
        print(f"Steps: {n_steps}")
        print(f"Settlement: {'Enabled' if enable_settlement else 'Disabled'}")
        print("="*60)
    
    # Main simulation loop
    for t in range(n_steps):
        sim_debug_print(f"\n{'='*60}")
        sim_debug_print(f"STEP {t}")
        sim_debug_print(f"{'='*60}")
        
        # Update product lifecycle (open/close/settle)
        closed_products = mo.update_product_status(t)
        
        # ========================================================================
        # SETTLEMENT: Settle closed products
        # ========================================================================
        if closed_products and enable_settlement:
            # Get Product objects for closed products
            products_to_settle = [mo.products[pid] for pid in closed_products]
            
            # Perform settlement
            settlement_results = settle_products(
                products_to_settle=products_to_settle,
                agents=agents,
                base_offset=settlement_offset,
                volatility=settlement_volatility,
                use_stochastic=use_stochastic_settlement,
                rng=rng,
                apply_to_revenue=True,  # Actually deduct costs from revenue!
                verbose=False  # Don't spam console per product
            )
            
            # Log settlement results to agent_logs
            log_settlement_results(settlement_results, agent_logs)
            
            # Track statistics
            step_settlement_cost = 0.0
            for results in settlement_results.values():
                total_settled_products += 1
                for r in results:
                    step_settlement_cost += r.imbalance_cost
            
            total_settlement_cost += step_settlement_cost
            
            if verbose and t % 50 == 0:
                print(f"  t={t:4d} | Settled {len(closed_products)} products, "
                      f"Cost: {step_settlement_cost:>10,.0f} EUR")
        
        # ========================================================================
        # END SETTLEMENT CODE
        # ========================================================================
        
        elif verbose and closed_products and t % 50 == 0:
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
                                    side=Side.BUY,
                                    product_id=trade.product_id
                                )
                                sim_debug_print(f"    → Agent {trade.buy_agent_id} was BUYER in trade")
                            
                            # Update SELLER
                            seller = agent_by_id.get(trade.sell_agent_id)
                            if seller:
                                seller.on_trade(
                                    volume=trade.volume,
                                    price=trade.price,
                                    side=Side.SELL,
                                    product_id=trade.product_id
                                )
                                sim_debug_print(f"    → Agent {trade.sell_agent_id} was SELLER in trade")
                            
                            step_trades.append(trade)
                            step_volume += trade.volume
                    
                    except ValueError as e:
                        sim_debug_print(f"    → ValueError: {e}")
                        if verbose and "not open" in str(e).lower():
                            pass  # Silently ignore
                        else:
                            if verbose:
                                print(f"  Warning: {e}")
                    except Exception as e:
                        sim_debug_print(f"    → Exception: {type(e).__name__}: {e}")
                        if verbose:
                            print(f"  Warning: {type(e).__name__}: {e}")
        
        # Log market state for this step
        market_log["t"].append(t)
        market_log["n_trades"].append(len(step_trades))
        market_log["total_volume"].append(step_volume)
        market_log["n_open_products"].append(len(open_product_ids))
        
        # Count total orders across all products
        market_log["total_orders"].append(mo.total_orders())
        
        # Per-product logs
        for product in products:
            pid = product.product_id
            product_trades = [tr for tr in step_trades if tr.product_id == pid]
            product_volume = sum(tr.volume for tr in product_trades)
            
            # Count orders for this product
            ob = mo.order_books[pid]
            product_orders = sum(len(orders) for orders in ob.bids.values()) + sum(len(orders) for orders in ob.asks.values())
            
            market_log[f"p{pid}_trades"].append(len(product_trades))
            market_log[f"p{pid}_volume"].append(product_volume)
            market_log[f"p{pid}_orders"].append(product_orders)
            market_log[f"p{pid}_status"].append(mo.products[pid].status.value)
        
        # Agent logging
        for agent in agents:
            if agent.is_multi_product:
                # Sum revenues across all products
                total_revenue = sum(agent.private_info.revenues.values())
            else:
                total_revenue = agent.private_info.revenue
            
            agent_logs[agent.id]["t"].append(t)
            agent_logs[agent.id]["total_revenue"].append(total_revenue)
            
            # SETTLEMENT: Log cumulative settlement cost
            if enable_settlement:
                cumulative_settlement = sum(agent_logs[agent.id].get("settlement_costs", []))
                agent_logs[agent.id]["total_settlement_cost"].append(cumulative_settlement)
        
        # Progress output
        if verbose and t % 50 == 0:
            print(f"  t={t:4d} | Open: {len(open_product_ids):2d} | "
                  f"Trades: {len(step_trades):3d} | "
                  f"Volume: {step_volume:>8.1f} MW | "
                  f"Orders: {mo.total_orders():3d}")
    
    # Final summary
    if verbose:
        print()
        print("="*60)
        print("SIMULATION COMPLETE")
        print("="*60)
        total_trades = sum(market_log["n_trades"])
        total_volume = sum(market_log["total_volume"])
        print(f"Total Trades: {total_trades}")
        print(f"Total Volume: {total_volume:.1f} MW")
        
        # SETTLEMENT: Print settlement summary
        if enable_settlement:
            print()
            print("="*60)
            print("SETTLEMENT SUMMARY")
            print("="*60)
            print(f"Products Settled:      {total_settled_products}")
            print(f"Total Settlement Cost: {total_settlement_cost:,.0f} EUR")
            if total_settled_products > 0:
                print(f"Avg Cost per Product:  {total_settlement_cost/total_settled_products:,.0f} EUR")
            
            # Per-agent settlement costs
            agent_settlement_totals = {}
            for agent_id, logs in agent_logs.items():
                total = sum(logs.get("settlement_costs", []))
                if total > 0:
                    agent_settlement_totals[agent_id] = total
            
            if agent_settlement_totals:
                print()
                print("Top 10 Agents by Settlement Cost:")
                sorted_agents = sorted(agent_settlement_totals.items(), 
                                     key=lambda x: x[1], reverse=True)[:10]
                for agent_id, cost in sorted_agents:
                    agent_type = agent_logs[agent_id].get("agent_type", "Unknown")
                    print(f"  Agent {agent_id:3d} ({agent_type:20s}): {cost:>12,.0f} EUR")
        
        print("="*60)
    
    return market_log, agent_logs, mo