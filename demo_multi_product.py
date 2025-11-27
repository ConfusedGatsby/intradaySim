"""
Multi-Product Intraday Market Demo

Demonstriert die Multi-Product Simulation mit:
- Mehreren Delivery-Produkten (stündlich)
- Multi-Product VariableAgents
- Multi-Product RandomLiquidityAgents (liefern Liquidität!)
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
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy

import os


def demo_basic_multi_product():
    """
    Demo 1: Grundlegende Multi-Product Simulation mit Liquidität
    
    - 3 stündliche Produkte (H00, H01, H02)
    - 2 Multi-Product VariableAgents (Wind)
    - 3 Multi-Product RandomLiquidityAgents (liefern Liquidität auf beiden Seiten!)
    - 200 Zeitschritte
    """
    print("\n" + "="*70)
    print("DEMO 1: MULTI-PRODUCT MIT LIQUIDITÄT")
    print("="*70)
    
    # Create 3 hourly products
    products = create_hourly_products(
        n_hours=3,
        start_time=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    print(f"\n📦 Products created:")
    for p in products:
        print(f"   Product {p.product_id}: Delivery {p.delivery_start}-{p.delivery_end}, "
              f"Gate {p.gate_open}-{p.gate_close}")
    
    agents = []
    
    # --- Multi-Product Variable Agents (Wind farms) ---
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            initial_forecast=50.0 + i * 10.0
        )
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=10.0,
            imbalance_tolerance=3.0
        )
        agents.append(agent)
    
    # --- Multi-Product RandomLiquidity Agents ---
    for i in range(3):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=200.0
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=30.0,
            max_price=70.0,
            min_volume=2.0,
            max_volume=8.0,
            n_orders=5
        )
        
        # Assign pricing strategy
        agent.pricing_strategy = NaivePricingStrategy(
            pi_range=10.0,
            n_segments=20,
            min_price=30.0,
            max_price=70.0,
            rng=Random(300 + i),
            n_orders=5
        )
        
        agents.append(agent)
    
    print(f"\n👥 Agents created:")
    print(f"   - {sum(1 for a in agents if isinstance(a, VariableAgent))} Multi-Product VariableAgents")
    print(f"   - {sum(1 for a in agents if isinstance(a, RandomLiquidityAgent))} Multi-Product RandomLiquidityAgents")
    
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
    Demo 2: Viele Produkte (24 Stunden) mit Liquidität
    
    - 24 stündliche Produkte (voller Tag)
    - 5 Multi-Product VariableAgents
    - 5 Multi-Product RandomLiquidityAgents
    - 500 Zeitschritte
    """
    print("\n" + "="*70)
    print("DEMO 2: VIELE PRODUKTE (24 STUNDEN) MIT LIQUIDITÄT")
    print("="*70)
    
    # Create 24 hourly products (full day)
    products = create_hourly_products(
        n_hours=24,
        start_time=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    print(f"\n📦 {len(products)} Products created (H00-H23)")
    
    agents = []
    
    # --- Multi-Product Variable Agents with diverse forecasts ---
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
            daily_pattern = 15.0 * (0.5 + 0.5 * ((hour - 12) / 12.0))
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
    
    # --- Multi-Product RandomLiquidity Agents ---
    for i in range(5):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=300.0
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=25.0,
            max_price=75.0,
            min_volume=2.0,
            max_volume=10.0,
            n_orders=7
        )
        
        agent.pricing_strategy = NaivePricingStrategy(
            pi_range=12.0,
            n_segments=25,
            min_price=25.0,
            max_price=75.0,
            rng=Random(300 + i),
            n_orders=7
        )
        
        agents.append(agent)
    
    print(f"\n👥 {len(agents)} Agents created:")
    print(f"   - 5 Multi-Product VariableAgents")
    print(f"   - 5 Multi-Product RandomLiquidityAgents")
    
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


def demo_minimal_test():
    """
    Demo 3: Minimaler Test (1 Produkt, wenig Agents)
    
    - 1 Produkt
    - 1 VariableAgent
    - 2 RandomLiquidityAgents
    - 100 Zeitschritte
    
    Zum Debuggen falls andere Demos keine Trades zeigen.
    """
    print("\n" + "="*70)
    print("DEMO 3: MINIMAL TEST (1 PRODUKT)")
    print("="*70)
    
    products = create_hourly_products(n_hours=1, start_time=1440)
    
    print(f"\n📦 {len(products)} Product created")
    
    agents = []
    
    # 1 Variable Agent
    priv_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_forecast=60.0  # High forecast → will SELL
    )
    
    variable_agent = VariableAgent(
        id=1,
        private_info=priv_info,
        rng=Random(42),
        base_forecast=60.0,
        base_volume=10.0,
        imbalance_tolerance=2.0
    )
    agents.append(variable_agent)
    
    # 2 RandomLiquidity Agents
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=35.0,
            max_price=65.0,
            min_volume=2.0,
            max_volume=6.0,
            n_orders=4
        )
        
        agent.pricing_strategy = NaivePricingStrategy(
            pi_range=10.0,
            n_segments=15,
            min_price=35.0,
            max_price=65.0,
            rng=Random(300 + i),
            n_orders=4
        )
        
        agents.append(agent)
    
    print(f"\n👥 {len(agents)} Agents created:")
    print(f"   - 1 VariableAgent (forecast=60, will SELL)")
    print(f"   - 2 RandomLiquidityAgents")
    
    # Run simulation
    print(f"\n▶️  Running simulation (100 steps)...")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=100,
        seed=42,
        verbose=True
    )
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
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
    
    # Demo 1: Basic with Liquidity
    log1, agent_logs1, mo1 = demo_basic_multi_product()
    
    # Demo 2: Many Products
    log2, agent_logs2, mo2 = demo_many_products()
    
    # Demo 3: Minimal Test
    log3, agent_logs3, mo3 = demo_minimal_test()
    
    # Export results
    os.makedirs("results", exist_ok=True)
    export_results_to_csv(log1, agent_logs1, "results/demo1_basic_liquidity.csv")
    export_results_to_csv(log2, agent_logs2, "results/demo2_many_products.csv")
    export_results_to_csv(log3, agent_logs3, "results/demo3_minimal.csv")
    
    print("\n" + "="*70)
    print("✨ ALL DEMOS COMPLETED!")
    print("="*70)
    print(f"\n📁 Results saved to:")
    print(f"   - results/demo1_basic_liquidity.csv")
    print(f"   - results/demo2_many_products.csv")
    print(f"   - results/demo3_minimal.csv")
    print(f"\n💡 Next: Run 'python plot_multi_product_results.py' to visualize!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()