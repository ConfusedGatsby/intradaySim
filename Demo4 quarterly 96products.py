"""
Demo 4: Full Day with 96 Quarterly Products (15-min granularity) + THERMAL AGENTS

Wissenschaftlich fundierte Simulation mit:
- 96 Produkten (24h × 4 Quarterstunden)
- Realistische DA-Preise (Kremer et al. 2021)
- 10 VariableAgents mit diversen Forecasts
- 10 RandomLiquidityAgents (Shinde-konforme Pricing)
- 5 ThermalAgents (Dispatchable mit Ramping Constraints) ⬅️ NEW!
- 1500 Simulation Steps
- Erwartung: ~70,000-150,000 Trades (erhöht durch Thermal Agents)

UPDATED: Implementiert Shinde 2023 konforme Thermal Agents!
"""

from random import Random
from typing import Dict, List
import os

from intraday_abm.sim.multi_product_simulation import (
    run_multi_product_simulation,
    print_simulation_summary,
)
from intraday_abm.core.product import (
    create_quarterly_products,
    print_quarterly_products_summary
)
from intraday_abm.core.types import MultiProductPrivateInfo
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.dispatchable import DispatchableAgent  # ⬅️ NEW IMPORT!
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy


def create_thermal_agents_for_demo4(products, n_agents=5, seed=500):
    """
    Create Shinde 2023 compliant thermal agents for Demo 4.
    
    Creates diverse thermal power plants with:
    - Different marginal costs (40-60 €/MWh)
    - Different capacities (200-400 MW)
    - Different ramping rates (30-70 MW/hour)
    - Different switch parameters (0.4-0.8)
    
    Args:
        products: List of Product instances (96 quarterly products)
        n_agents: Number of thermal agents to create (default: 5)
        seed: Random seed for reproducibility
        
    Returns:
        List of DispatchableAgent instances
    """
    thermal_agents = []
    
    print(f"\n🏭 Creating {n_agents} ThermalAgents (Dispatchable with Ramping):")
    
    for i in range(n_agents):
        # Diversify parameters across agents
        marginal_cost = 40.0 + i * 5.0      # 40, 45, 50, 55, 60 €/MWh
        capacity = 200.0 + i * 50.0         # 200, 250, 300, 350, 400 MW
        ramping_rate = 30.0 + i * 10.0      # 30, 40, 50, 60, 70 MW/hour
        switch_param = 0.4 + i * 0.1        # 0.4, 0.5, 0.6, 0.7, 0.8
        
        # Create Multi-Product PrivateInfo
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=capacity,
            initial_da_position=capacity * 0.6,  # Start at 60% capacity
        )
        
        # Initialize limit prices (Shinde-style)
        # These are REQUIRED for the DispatchableAgent to work properly
        priv_info.limit_buy_initial = marginal_cost + 20.0   # e.g., 60-80 €/MWh
        priv_info.limit_sell_initial = marginal_cost - 15.0  # e.g., 25-45 €/MWh
        priv_info.limit_buy = priv_info.limit_buy_initial
        priv_info.limit_sell = priv_info.limit_sell_initial
        
        # Create DispatchableAgent with all Shinde 2023 parameters
        agent = DispatchableAgent(
            id=200 + i,
            private_info=priv_info,
            rng=Random(seed + i),
            
            # Basic parameters
            marginal_cost=marginal_cost,
            base_volume=15.0,
            epsilon_price=2.0,
            
            # Shinde 2021 parameters (Equations 8-12)
            min_stable_load=capacity * 0.25,  # 25% of capacity
            alpha=0.3,                         # Limit price update factor
            pi_imb_plus=marginal_cost + 15.0,  # Positive imbalance price
            pi_imb_minus=marginal_cost - 10.0, # Negative imbalance price
            e_imb=5.0,                         # Imbalance price error variance
            
            # Shinde 2023 ramping parameters (Equations 18-21)
            ramping_up_rate=ramping_rate,
            ramping_down_rate=ramping_rate,
            switch_parameter=switch_param,
            nu_R=1.0,
        )
        
        # Assign Naive Pricing Strategy (Shinde-compliant)
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(seed + 100 + i),
            pi_range=10.0,
            n_segments=20,
            n_orders=7,
            min_price=15.0,
            max_price=120.0
        )
        
        # Show agent configuration
        print(f"   Agent {agent.id}: MC={marginal_cost:.0f} €/MWh, "
              f"Cap={capacity:.0f} MW, Ramp={ramping_rate:.0f} MW/h, "
              f"Switch={switch_param:.0%}, MinLoad={capacity*0.25:.0f} MW")
        
        thermal_agents.append(agent)
    
    return thermal_agents


def print_scientific_simulation_summary(
    log: Dict,
    agent_logs: Dict[int, Dict],
    mo,
    agents: List,
    products: List
) -> None:
    """
    Print scientifically structured simulation summary.
    
    Structure:
    1. Market Overview (total trades, volume, efficiency)
    2. Product Analysis (temporal patterns, utilization)
    3. Agent Performance (by type, sorted by revenue)
    4. Trading Behavior Analysis
    
    Args:
        log: Market log dictionary
        agent_logs: Agent-level logs
        mo: Market operator
        agents: List of agents
        products: List of products
    """
    print("\n" + "="*70)
    print("SIMULATION RESULTS - SCIENTIFIC SUMMARY")
    print("="*70)
    
    # ========== 1. MARKET OVERVIEW ==========
    print(f"\n{'─'*70}")
    print("1. MARKET OVERVIEW")
    print(f"{'─'*70}")
    
    total_trades = sum(log["n_trades"])
    total_volume = sum(log["total_volume"])
    avg_trade_size = total_volume / total_trades if total_trades > 0 else 0
    n_steps = len(log["t"])
    
    print(f"\nAggregate Statistics:")
    print(f"  Total Trades:        {total_trades:>10,}")
    print(f"  Total Volume:        {total_volume:>10,.1f} MW")
    print(f"  Average Trade Size:  {avg_trade_size:>10.2f} MW")
    print(f"  Trades per Step:     {total_trades/n_steps:>10.2f}")
    print(f"  Simulation Steps:    {n_steps:>10,}")
    
    # Trading intensity
    steps_with_trades = sum(1 for n in log["n_trades"] if n > 0)
    market_activity = steps_with_trades / n_steps * 100 if n_steps > 0 else 0
    
    print(f"\nMarket Efficiency:")
    print(f"  Steps with Trades:   {steps_with_trades:>10,} ({market_activity:.1f}%)")
    print(f"  Max Open Products:   {max(log['n_open_products']):>10}")
    print(f"  Avg Open Products:   {sum(log['n_open_products'])/n_steps:>10.1f}")
    
    # ========== 2. PRODUCT ANALYSIS ==========
    print(f"\n{'─'*70}")
    print("2. TEMPORAL PRODUCT ANALYSIS")
    print(f"{'─'*70}")
    
    # Calculate per-product totals
    product_stats = []
    for pid in range(len(products)):
        if f"p{pid}_trades" in log:
            trades = sum(log[f"p{pid}_trades"])
            volume = sum(log[f"p{pid}_volume"])
            product_stats.append({
                'pid': pid,
                'name': products[pid].name,
                'hour': pid // 4,
                'quarter': pid % 4,
                'trades': trades,
                'volume': volume,
                'da_price': products[pid].da_price
            })
    
    # Hourly aggregation
    hourly_stats = {}
    for h in range(24):
        hour_products = [p for p in product_stats if p['hour'] == h]
        hourly_stats[h] = {
            'trades': sum(p['trades'] for p in hour_products),
            'volume': sum(p['volume'] for p in hour_products),
            'avg_da': sum(p['da_price'] for p in hour_products) / len(hour_products) if hour_products else 0
        }
    
    print(f"\nHourly Trading Activity:")
    print(f"  {'Hour':<6} {'Trades':>8} {'Volume (MW)':>12} {'Avg DA (€/MWh)':>16}")
    print(f"  {'-'*50}")
    
    # Show selected hours
    for h in [0, 6, 12, 18, 23]:
        stats = hourly_stats[h]
        print(f"  H{h:02d}    {stats['trades']:>8,} {stats['volume']:>12,.0f} {stats['avg_da']:>16.2f}")
    
    # Peak vs Off-Peak
    peak_hours = list(range(8, 20))
    peak_trades = sum(hourly_stats[h]['trades'] for h in peak_hours)
    off_peak_trades = total_trades - peak_trades
    
    print(f"\nPeak/Off-Peak Distribution:")
    print(f"  Peak (08:00-20:00):      {peak_trades:>8,} ({peak_trades/total_trades*100:>5.1f}%)")
    print(f"  Off-Peak (00:00-08:00,   {off_peak_trades:>8,} ({off_peak_trades/total_trades*100:>5.1f}%)")
    print(f"            20:00-24:00)")
    
    # ========== 3. AGENT PERFORMANCE ==========
    print(f"\n{'─'*70}")
    print("3. AGENT PERFORMANCE ANALYSIS")
    print(f"{'─'*70}")
    
    # Categorize agents
    agent_categories = {
        'Variable': [],
        'RandomLiquidity': [],
        'Dispatchable': []
    }
    
    for agent in agents:
        agent_log = agent_logs.get(agent.id, {})
        if not agent_log or not agent_log.get('t'):
            continue
            
        agent_type = type(agent).__name__
        category = 'Variable' if 'Variable' in agent_type else \
                   'Dispatchable' if 'Dispatchable' in agent_type else \
                   'RandomLiquidity' if 'Random' in agent_type else 'Other'
        
        revenue = agent_log['total_revenue'][-1]
        position = agent_log['total_position'][-1]
        
        agent_info = {
            'id': agent.id,
            'revenue': revenue,
            'position': position,
            'agent': agent
        }
        
        agent_categories[category].append(agent_info)
    
    # Print by category
    for category in ['Variable', 'RandomLiquidity', 'Dispatchable']:
        category_agents = agent_categories[category]
        if not category_agents:
            continue
        
        # Sort by revenue (descending)
        category_agents.sort(key=lambda x: x['revenue'], reverse=True)
        
        print(f"\n{category} Agents (n={len(category_agents)}):")
        print(f"  {'Agent ID':<10} {'Revenue (€)':>15} {'Position (MW)':>15} {'Details':<30}")
        print(f"  {'-'*75}")
        
        for agent_info in category_agents:
            agent = agent_info['agent']
            
            # Build details string
            if category == 'Dispatchable':
                # Thermal agent details
                mc = agent.marginal_cost
                cap = agent.private_info.capacities.get(0, 0) if hasattr(agent.private_info, 'capacities') else 0
                switch = agent.switch_parameter
                switch_activated = "✓" if agent._switch_activated else "○"
                details = f"MC={mc:.0f} €/MWh, Cap={cap:.0f} MW [{switch_activated}]"
            elif category == 'Variable':
                # Variable agent details
                limit_buy = agent.private_info.limit_buy if hasattr(agent.private_info, 'limit_buy') else 0
                limit_sell = agent.private_info.limit_sell if hasattr(agent.private_info, 'limit_sell') else 0
                details = f"Limits: Buy={limit_buy:.1f}, Sell={limit_sell:.1f}"
            else:
                # Liquidity agent details
                limit_buy = agent.private_info.limit_buy if hasattr(agent.private_info, 'limit_buy') else 0
                limit_sell = agent.private_info.limit_sell if hasattr(agent.private_info, 'limit_sell') else 0
                details = f"Liquidity Provider"
            
            print(f"  {agent_info['id']:<10} {agent_info['revenue']:>15,.0f} "
                  f"{agent_info['position']:>15,.0f} {details:<30}")
        
        # Category summary
        total_revenue = sum(a['revenue'] for a in category_agents)
        total_position = sum(a['position'] for a in category_agents)
        print(f"  {'-'*75}")
        print(f"  {'TOTAL':<10} {total_revenue:>15,.0f} {total_position:>15,.0f}")
    
    # ========== 4. MARKET BALANCE ==========
    print(f"\n{'─'*70}")
    print("4. MARKET BALANCE CHECK")
    print(f"{'─'*70}")
    
    total_agent_position = sum(
        agent_logs[aid]['total_position'][-1] 
        for aid in agent_logs 
        if agent_logs[aid].get('t')
    )
    total_agent_revenue = sum(
        agent_logs[aid]['total_revenue'][-1] 
        for aid in agent_logs 
        if agent_logs[aid].get('t')
    )
    
    print(f"\nMarket Equilibrium:")
    print(f"  Sum of Positions:    {total_agent_position:>15,.2f} MW")
    print(f"  Sum of Revenues:     {total_agent_revenue:>15,.2f} €")
    print(f"  Position Balance:    {'✓ BALANCED' if abs(total_agent_position) < 1.0 else '✗ IMBALANCED'}")
    print(f"  Revenue Balance:     {'✓ BALANCED' if abs(total_agent_revenue) < 1.0 else '✗ IMBALANCED'}")
    
    # Dispatchable agent behavior analysis
    if agent_categories['Dispatchable']:
        print(f"\nDispatchable Agent Behavior:")
        print(f"  {'Agent':<8} {'Mode':<15} {'MC (€/MWh)':>12} {'Switch @':>10} {'Ramping':>10}")
        print(f"  {'-'*60}")
        
        for agent_info in agent_categories['Dispatchable']:
            agent = agent_info['agent']
            mc = agent.marginal_cost
            switch_step = int(agent.switch_parameter * n_steps)
            mode = "RAMPING" if agent._switch_activated else "PROFIT"
            ramping = f"{agent.ramping_up_rate:.0f} MW/h"
            
            print(f"  {agent.id:<8} {mode:<15} {mc:>12.0f} {switch_step:>10} {ramping:>10}")
    
    print("="*70)


def demo_full_day_quarterly():
    """
    Demo 4: Full Day mit 96 Quarterly Products (15-min).
    
    Setup:
    - 96 Produkte (H00Q1 - H23Q4)
    - Realistische DA-Preise (Winter-Szenario)
    - 10 VariableAgents (Wind/Solar mit diversen Forecasts)
    - 10 RandomLiquidityAgents (Shinde-Pricing, breite Limits)
    - 5 ThermalAgents (Dispatchable mit Ramping Constraints) ⬅️ NEW!
    - 1500 Steps (ausreichend für alle 96 Produkte)
    
    Erwartete Resultate:
    - ~70,000-150,000 Trades (erhöht durch Thermal Agents)
    - ~300,000-600,000 MW Volumen
    - Peak bei ~8-12 offenen Produkten
    - Realistische Preisverteilung
    - Thermal Agents: Profit Mode → Ramping Mode Transition
    """
    print("\n" + "="*70)
    print("DEMO 4: FULL DAY QUARTERLY (96 × 15-MIN PRODUCTS) + THERMAL AGENTS")
    print("="*70)
    
    # Create 96 quarterly products with realistic DA prices
    # NOW USING INTEGRATED FUNCTION FROM product.py!
    products = create_quarterly_products(
        n_hours=24,
        start_time=1440,  # Day 2
        gate_open_offset_hours=24,
        gate_close_offset_minutes=5,
        season='winter',  # Winter scenario (higher peak prices)
        base_da_price=45.0,
        price_volatility=5.0,
        add_stochastic_volatility=True,
        seed=42
    )
    
    print_quarterly_products_summary(products)
    
    agents = []
    
    # --- 10 Multi-Product Variable Agents (Wind/Solar) ---
    print(f"\n👥 Creating 10 VariableAgents (Diverse Forecasts):")
    for i in range(10):
        # Diverse Limit Prices
        limit_buy = 55.0 + i * 3.0    # 55, 58, 61, ..., 82 €/MWh
        limit_sell = 45.0 - i * 1.5   # 45, 43.5, 42, ..., 31.5 €/MWh
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=150.0,  # Larger capacity for 96 products
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
        
        # Create diverse forecast patterns
        # Simulate realistic wind/solar patterns
        base_forecast = 40.0 + i * 10.0  # 40, 50, ..., 130 MW
        
        for pid in range(96):
            hour = pid // 4
            quarter = pid % 4
            
            # Solar pattern (higher during day, zero at night)
            if 6 <= hour < 20:
                # Day time
                solar_factor = 1.0 + 0.5 * ((hour - 13) / 7.0) ** 2  # Peak at noon
                solar_component = base_forecast * 0.3 * solar_factor
            else:
                solar_component = 0.0
            
            # Wind pattern (more stable, slight day/night variation)
            wind_component = base_forecast * 0.7 * (1.0 + 0.2 * (hour / 24.0))
            
            # Quarterly variation (small)
            quarterly_var = 5.0 * (quarter / 4.0 - 0.5)
            
            forecast = solar_component + wind_component + quarterly_var
            priv_info.forecasts[pid] = max(10.0, forecast)
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=base_forecast,
            base_volume=15.0,
            imbalance_tolerance=5.0
        )
        
        # Show sample forecasts
        sample_forecasts = [priv_info.forecasts[pid] for pid in [0, 24, 48, 72]]  # H00, H06, H12, H18
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}], "
              f"Forecasts [H00: {sample_forecasts[0]:.0f}, H06: {sample_forecasts[1]:.0f}, "
              f"H12: {sample_forecasts[2]:.0f}, H18: {sample_forecasts[3]:.0f}] MW")
        
        agents.append(agent)
    
    # --- 10 Multi-Product RandomLiquidity Agents ---
    print(f"\n👥 Creating 10 RandomLiquidityAgents (Shinde-Pricing):")
    for i in range(10):
        # Wide Limits for Liquidity Providers
        limit_buy = 75.0 + i * 3.0    # 75, 78, 81, ..., 102 €/MWh
        limit_sell = 25.0 - i * 1.0   # 25, 24, 23, ..., 16 €/MWh
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=400.0,  # Large capacity for liquidity
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=15.0,   # Wide absolute bounds
            max_price=120.0,
            min_volume=3.0,
            max_volume=12.0,
            n_orders=7  # More orders for more products
        )
        
        # SHINDE-KONFORME STRATEGY
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(300 + i),
            pi_range=8.0,     # Larger range for 96 products
            n_segments=15,
            n_orders=7,
            min_price=15.0,
            max_price=120.0
        )
        
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}]")
        agents.append(agent)
    
    # ===== NEW: Add 5 Thermal Agents =====
    thermal_agents = create_thermal_agents_for_demo4(products, n_agents=5, seed=500)
    agents.extend(thermal_agents)
    
    print(f"\n📊 Total Agents: {len(agents)}")
    print(f"   VariableAgents:       10")
    print(f"   RandomLiquidityAgents: 10")
    print(f"   ThermalAgents:         5  ⬅️ NEW!")
    
    # Run simulation (NO debug for performance with 96 products)
    print(f"\n▶️  Running simulation (1500 steps)...")
    print(f"   ⚠️  Debug disabled for performance (96 products = high volume)")
    print(f"   💡 Expected: ~70,000-150,000 Trades (WITH thermal agents)")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=1500,
        seed=42,
        verbose=True  # Keep progress output
    )
    
    # Print scientific summary
    print_scientific_simulation_summary(log, agent_logs, mo, agents, products)
    
    # Additional quarterly granularity analysis
    print(f"\n" + "="*70)
    print("QUARTERLY GRANULARITY DETAIL")
    print("="*70)
    
    # Quarterly pattern (show all 4 quarters for selected hour)
    print(f"\nIntra-Hour Trading Pattern (Example: H12):")
    print(f"  {'Product':<8} {'Trades':>8} {'Volume (MW)':>12} {'DA Price (€/MWh)':>18}")
    print(f"  {'-'*55}")
    for q in range(4):
        pid = 12 * 4 + q
        # FIX: Sum over ALL timesteps!
        trades = sum(log[f"p{pid}_trades"]) if f"p{pid}_trades" in log else 0
        volume = sum(log[f"p{pid}_volume"]) if f"p{pid}_volume" in log else 0.0
        print(f"  {products[pid].name:<8} {trades:>8,} {volume:>12,.0f} {products[pid].da_price:>18.2f}")
    
    print(f"\nNote: Demonstrates uniform trading across 15-minute intervals")
    print("="*70)
    
    return log, agent_logs, mo, products


def export_quarterly_results_to_csv(log, products, filename="demo4_quarterly_96products.csv"):
    """
    Export 96-product simulation results to CSV.
    
    Args:
        log: Market log from simulation
        products: List of Product instances
        filename: Output filename
    """
    import csv
    
    print(f"\n💾 Exporting 96-product results to {filename}...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["t", "n_trades", "total_volume", "n_open_products", "total_orders"]
        
        # Add product columns (96 products!)
        for pid in range(96):
            header.extend([f"p{pid}_trades", f"p{pid}_volume", f"p{pid}_orders"])
        
        writer.writerow(header)
        
        # Data
        for i in range(len(log["t"])):
            row = [
                log["t"][i],
                log["n_trades"][i],
                log["total_volume"][i],
                log["n_open_products"][i],
                log["total_orders"][i]
            ]
            
            for pid in range(96):
                row.extend([
                    log[f"p{pid}_trades"][i],
                    log[f"p{pid}_volume"][i],
                    log[f"p{pid}_orders"][i]
                ])
            
            writer.writerow(row)
    
    print(f"✅ Exported {len(log['t'])} rows × {len(header)} columns to {filename}")
    print(f"   File size: ~{len(log['t']) * 96 * 3 * 8 / 1024 / 1024:.1f} MB (estimated)")


def main():
    """Run Demo 4 with 96 quarterly products + thermal agents."""
    
    print("\n" + "🚀"*35)
    print("   96-PRODUCT QUARTERLY SIMULATION DEMO")
    print("   (15-MIN GRANULARITY + THERMAL AGENTS)")
    print("🚀"*35)
    
    # Run Demo 4
    log, agent_logs, mo, products = demo_full_day_quarterly()
    
    # Export results
    os.makedirs("results", exist_ok=True)
    export_quarterly_results_to_csv(log, products, "results/demo4_quarterly_96products_thermal.csv")
    
    print("\n" + "="*70)
    print("✨ DEMO 4 COMPLETED WITH THERMAL AGENTS!")
    print("="*70)
    print(f"\n📁 Results saved to:")
    print(f"   - results/demo4_quarterly_96products_thermal.csv")
    print(f"\n🎉 96-Product Simulation mit 5 Thermal Agents erfolgreich!")
    print(f"\n🏭 Thermal Agents Features:")
    print(f"   - Shinde 2021 Equations 8-12 (Imbalance, Margins, Limit Prices)")
    print(f"   - Shinde 2023 Equations 18-21 (Ramping Constraints)")
    print(f"   - Switch Parameter: Profit Mode → Ramping Mode")
    print(f"   - Multi-Product Support mit 96 Quarterstunden")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()