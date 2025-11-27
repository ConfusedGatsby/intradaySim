"""
Multi-Product Intraday Market Demo

Demonstriert die Multi-Product Simulation mit:
- Mehreren Delivery-Produkten (stündlich)
- Multi-Product VariableAgents
- Mixed Agents (Single + Multi)
- Visualisierung und Export
"""

from random import Random

from intraday_abm.sim.multi_product_simulation import (
    run_multi_product_simulation,
    print_simulation_summary
)
from intraday_abm.core.product import create_hourly_products
from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo
from intraday_abm.core.types import AgentPrivateInfo
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent

import os


def demo_basic_multi_product():
    """
    Demo 1: Grundlegende Multi-Product Simulation
    
    - 3 stündliche Produkte (H00, H01, H02)
    - 2 Multi-Product VariableAgents (Wind)
    - 200 Zeitschritte
    """
    print("\n" + "="*70)
    print("DEMO 1: GRUNDLEGENDE MULTI-PRODUCT SIMULATION")
    print("="*70)
    
    # Create 3 hourly products
    products = create_hourly_products(
        n_hours=3,
        start_time=1440,  # Delivery starts at minute 1440 (Day 2, 00:00)
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    print(f"\n📦 Products created:")
    for p in products:
        print(f"   Product {p.product_id}: Delivery {p.delivery_start}-{p.delivery_end}, "
              f"Gate {p.gate_open}-{p.gate_close}")
    
    # Create Multi-Product Variable Agents (Wind farms)
    agents = []
    
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            initial_forecast=50.0
        )
        
        # Set different forecasts per product (simulate wind variation)
        priv_info.forecasts[0] = 50.0 + i * 5.0   # Agent 0: 50, Agent 1: 55
        priv_info.forecasts[1] = 45.0 + i * 3.0   # Agent 0: 45, Agent 1: 48
        priv_info.forecasts[2] = 40.0 + i * 2.0   # Agent 0: 40, Agent 1: 42
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=10.0,
            imbalance_tolerance=3.0
        )
        agents.append(agent)
    
    print(f"\n👥 Agents created: {len(agents)} Multi-Product VariableAgents")
    for i, agent in enumerate(agents):
        forecasts = [agent.private_info.forecasts[pid] for pid in range(3)]
        print(f"   Agent {i}: Forecasts = {forecasts}")
    
    # Run simulation
    print(f"\n▶️  Running simulation (200 steps)...")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=200,
        seed=42,
        verbose=True
    )
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
    return log, agent_logs, mo


def demo_mixed_agents():
    """
    Demo 2: Mixed Agents Simulation
    
    - 3 stündliche Produkte
    - 2 Multi-Product VariableAgents
    - 3 Single-Product RandomLiquidityAgents (Fallback Mode)
    """
    print("\n" + "="*70)
    print("DEMO 2: MIXED AGENTS (MULTI-PRODUCT + SINGLE-PRODUCT)")
    print("="*70)
    
    # Create products
    products = create_hourly_products(n_hours=3, start_time=1440)
    
    print(f"\n📦 {len(products)} Products created")
    
    agents = []
    
    # Multi-Product Variable Agents
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            initial_forecast=50.0 + i * 5.0
        )
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=8.0,
            imbalance_tolerance=2.0
        )
        agents.append(agent)
    
    # Single-Product Random Liquidity Agents (Fallback Mode)
    for i in range(3):
        agent = RandomLiquidityAgent.create(
            id=100 + i,
            rng=Random(100 + i),
            capacity=50.0,
            min_price=30.0,
            max_price=70.0,
            min_volume=1.0,
            max_volume=5.0,
            n_orders=3
        )
        agents.append(agent)
    
    print(f"\n👥 Agents created:")
    print(f"   - {sum(1 for a in agents if a.is_multi_product)} Multi-Product (VariableAgents)")
    print(f"   - {sum(1 for a in agents if not a.is_multi_product)} Single-Product (RandomLiquidity, Fallback)")
    
    # Run simulation
    print(f"\n▶️  Running simulation (200 steps)...")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=200,
        seed=42,
        verbose=True
    )
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
    return log, agent_logs, mo


def demo_many_products():
    """
    Demo 3: Viele Produkte (24 Stunden)
    
    - 24 stündliche Produkte (voller Tag)
    - 5 Multi-Product VariableAgents
    - 500 Zeitschritte
    """
    print("\n" + "="*70)
    print("DEMO 3: VIELE PRODUKTE (24 STUNDEN)")
    print("="*70)
    
    # Create 24 hourly products (full day)
    products = create_hourly_products(
        n_hours=24,
        start_time=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    print(f"\n📦 {len(products)} Products created (H00-H23)")
    
    # Create 5 Multi-Product Variable Agents with diverse forecasts
    agents = []
    
    for i in range(5):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0
        )
        
        # Create diverse forecast patterns
        base = 40.0 + i * 8.0
        for pid in range(24):
            # Simulate daily pattern (higher during day, lower at night)
            hour = pid
            daily_pattern = 20.0 * (0.5 + 0.5 * ((hour - 12) / 24.0))  # Peak at noon
            priv_info.forecasts[pid] = base + daily_pattern
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=10.0,
            imbalance_tolerance=3.0
        )
        agents.append(agent)
    
    print(f"\n👥 {len(agents)} Multi-Product VariableAgents created")
    print(f"   Forecast ranges:")
    for i, agent in enumerate(agents):
        forecasts = [agent.private_info.forecasts[pid] for pid in range(24)]
        print(f"   Agent {i}: {min(forecasts):.1f} - {max(forecasts):.1f} MW")
    
    # Run simulation
    print(f"\n▶️  Running simulation (500 steps)...")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=500,
        seed=42,
        verbose=True
    )
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
    # Additional stats for many products
    print(f"\n📊 Per-Hour Trading Activity:")
    for hour in [0, 6, 12, 18, 23]:
        trades = sum(log[f"p{hour}_trades"])
        volume = sum(log[f"p{hour}_volume"])
        print(f"   H{hour:02d}: {trades:4d} trades, {volume:8.1f} MW")
    
    return log, agent_logs, mo


def export_results_to_csv(log, agent_logs, filename="multi_product_results.csv"):
    """
    Export simulation results to CSV.
    
    Args:
        log: Market log from simulation
        agent_logs: Agent logs from simulation
        filename: Output filename
    """
    import csv
    
    print(f"\n💾 Exporting results to {filename}...")
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ["t", "n_trades", "total_volume", "n_open_products", "total_orders"]
        
        # Add product columns
        n_products = sum(1 for key in log.keys() if key.startswith("p") and key.endswith("_trades"))
        for pid in range(n_products):
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
            
            for pid in range(n_products):
                row.extend([
                    log[f"p{pid}_trades"][i],
                    log[f"p{pid}_volume"][i],
                    log[f"p{pid}_orders"][i]
                ])
            
            writer.writerow(row)
    
    print(f"✅ Exported {len(log['t'])} rows to {filename}")


def main():
    """Run all demos."""
    
    print("\n" + "🚀"*35)
    print("   MULTI-PRODUCT INTRADAY MARKET SIMULATION DEMOS")
    print("🚀"*35)
    
    # Demo 1: Basic
    log1, agent_logs1, mo1 = demo_basic_multi_product()
    
    # Demo 2: Mixed Agents
    log2, agent_logs2, mo2 = demo_mixed_agents()
    
    # Demo 3: Many Products
    log3, agent_logs3, mo3 = demo_many_products()
    
    # Export results
    os.makedirs("results", exist_ok=True)
    export_results_to_csv(log1, agent_logs1, "results/demo1_basic.csv")
    export_results_to_csv(log2, agent_logs2, "results/demo2_mixed.csv")
    export_results_to_csv(log3, agent_logs3, "results/demo3_many_products.csv")
    
    print("\n" + "="*70)
    print("✨ ALL DEMOS COMPLETED!")
    print("="*70)
    print(f"\n📁 Results saved to:")
    print(f"   - results/demo1_basic.csv")
    print(f"   - results/demo2_mixed.csv")
    print(f"   - results/demo3_many_products.csv")
    print(f"\n💡 Next: Run 'python plot_multi_product_results.py' to visualize!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()