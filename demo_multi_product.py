"""
Multi-Product Intraday Market Demo (MIT SHINDE PRICING!)

Demonstriert die Multi-Product Simulation mit:
- Mehreren Delivery-Produkten (stündlich)
- Multi-Product VariableAgents
- Multi-Product RandomLiquidityAgents mit Shinde-konformer Pricing Strategy
- Limit Prices (limit_buy, limit_sell) für realistische Preisbildung
- Visualisierung und Export
- Duales Debug-System (Agent + Simulation)

ÄNDERUNGEN ZUR ALTEN VERSION:
- ✅ MultiProductPrivateInfo.initialize() mit limit_buy/limit_sell
- ✅ NaivePricingStrategy jetzt Shinde-konform (Equations 20-27)
- ✅ Realistische Limit Prices für alle Agents
- ✅ Garantierte Trades durch überlappende BUY/SELL Ranges
"""

from random import Random

from intraday_abm.sim.multi_product_simulation import (
    run_multi_product_simulation,
    print_simulation_summary,
    set_sim_debug_file,
    close_sim_debug_file
)
from intraday_abm.core.product import create_hourly_products
from intraday_abm.core.types import MultiProductPrivateInfo, PublicInfo, TopOfBook, Side
from intraday_abm.agents.variable import VariableAgent
from intraday_abm.agents.random_liquidity import RandomLiquidityAgent, set_debug_file, close_debug_file
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy

import os


def demo_basic_multi_product():
    """
    Demo 1: Grundlegende Multi-Product Simulation mit Shinde Pricing
    
    - 3 stündliche Produkte (H00, H01, H02)
    - 2 Multi-Product VariableAgents (Wind)
    - 3 Multi-Product RandomLiquidityAgents (Shinde-konforme Liquidität!)
    - 200 Zeitschritte
    
    NEU: Realistische Limit Prices für garantierte Trades!
    """
    print("\n" + "="*70)
    print("DEMO 1: MULTI-PRODUCT MIT SHINDE PRICING")
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
    print(f"\n👥 Creating VariableAgents:")
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            initial_forecast=50.0 + i * 10.0,
            limit_buy=60.0,      # ← NEU! Bereit bis 60 €/MWh zu zahlen
            limit_sell=40.0      # ← NEU! Bereit ab 40 €/MWh zu verkaufen
        )
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=10.0,
            imbalance_tolerance=3.0
        )
        
        # Show forecasts and limits
        forecasts = [priv_info.forecasts[pid] for pid in range(3)]
        print(f"   Agent {agent.id}: Forecasts = {forecasts}, "
              f"Limits = [Buy: {priv_info.limit_buy:.1f}, Sell: {priv_info.limit_sell:.1f}]")
        
        agents.append(agent)
    
    # --- Multi-Product RandomLiquidity Agents (MIT SHINDE PRICING!) ---
    print(f"\n👥 Creating RandomLiquidityAgents (Shinde-konform):")
    for i in range(3):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=200.0,
            limit_buy=65.0,      # ← NEU! Höhere Limits für Liquidity Provider
            limit_sell=35.0      # ← NEU! Niedrigere Limits für Liquidity Provider
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=30.0,      # Absolute Bounds (weiter als Limits!)
            max_price=70.0,
            min_volume=2.0,
            max_volume=8.0,
            n_orders=5
        )
        
        # Assign SHINDE-KONFORME Pricing Strategy
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(300 + i),
            pi_range=5.0,        # ± 5 €/MWh um Referenzpreis (Shinde-typisch)
            n_segments=10,
            n_orders=5,
            min_price=30.0,
            max_price=70.0
        )
        
        # Test strategy mit realistischem ToB
        test_tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
        test_pub = PublicInfo(tob=test_tob, da_price=50.0)
        test_curve = agent.pricing_strategy.build_price_volume_curve(
            agent=agent,
            public_info=test_pub,
            side=Side.BUY,
            total_volume=25.0
        )
        
        if test_curve:
            prices = [p for p, v in test_curve]
            print(f"   Agent {agent.id}: Limits [Buy: {priv_info.limit_buy:.1f}, Sell: {priv_info.limit_sell:.1f}], "
                  f"Test Range: [{min(prices):.1f}, {max(prices):.1f}] €/MWh")
        
        agents.append(agent)
    
    print(f"\n📊 Total Agents: {len(agents)}")
    
    # Enable BOTH debug logs
    os.makedirs("debug_logs", exist_ok=True)
    set_debug_file("debug_logs/demo1_agent_debug.txt")
    set_sim_debug_file("debug_logs/demo1_sim_debug.txt")
    
    # Run simulation
    print(f"\n▶️  Running simulation (200 steps)...")
    print(f"   📝 Agent debug → debug_logs/demo1_agent_debug.txt")
    print(f"   📝 Sim debug → debug_logs/demo1_sim_debug.txt")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=200,
        seed=42,
        verbose=True
    )
    
    # Close BOTH debug files
    close_debug_file()
    close_sim_debug_file()
    
    # Print summary
    print_simulation_summary(log, agent_logs, mo)
    
    print(f"\n💾 Debug logs saved:")
    print(f"   - debug_logs/demo1_agent_debug.txt")
    print(f"   - debug_logs/demo1_sim_debug.txt")
    
    return log, agent_logs, mo


def demo_many_products():
    """
    Demo 2: Viele Produkte (24 Stunden) mit Shinde Pricing
    
    - 24 stündliche Produkte (voller Tag)
    - 5 Multi-Product VariableAgents
    - 5 Multi-Product RandomLiquidityAgents (Shinde-konform)
    - 500 Zeitschritte
    
    NEU: Diverse Limit Prices je nach Agent-Typ
    """
    print("\n" + "="*70)
    print("DEMO 2: VIELE PRODUKTE (24 STUNDEN) MIT SHINDE PRICING")
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
    
    # --- Multi-Product Variable Agents with diverse forecasts AND LIMITS ---
    print(f"\n👥 Creating VariableAgents:")
    for i in range(5):
        # Diverse Limit Prices je nach Agent
        limit_buy = 55.0 + i * 2.0    # 55, 57, 59, 61, 63
        limit_sell = 45.0 - i * 1.0   # 45, 44, 43, 42, 41
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            limit_buy=limit_buy,
            limit_sell=limit_sell
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
        
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}]")
        agents.append(agent)
    
    # --- Multi-Product RandomLiquidity Agents (SHINDE-KONFORM) ---
    print(f"\n👥 Creating RandomLiquidityAgents (Shinde-konform):")
    for i in range(5):
        # Breite Limits für Liquidity Provider
        limit_buy = 70.0 + i * 2.0    # 70, 72, 74, 76, 78
        limit_sell = 30.0 - i * 1.0   # 30, 29, 28, 27, 26
        
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=300.0,
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=20.0,
            max_price=80.0,
            min_volume=2.0,
            max_volume=10.0,
            n_orders=7
        )
        
        # SHINDE-KONFORME STRATEGY
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(300 + i),
            pi_range=8.0,        # Größerer Range für 24h Markt
            n_segments=15,
            n_orders=7,
            min_price=20.0,
            max_price=80.0
        )
        
        print(f"   Agent {agent.id}: Limits [Buy: {limit_buy:.1f}, Sell: {limit_sell:.1f}]")
        agents.append(agent)
    
    print(f"\n📊 Total Agents: {len(agents)}")
    
    # Run simulation (ohne Debug für Performance)
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
    print(f"\n📊 Per-Hour Trading Activity (Sample):")
    for hour in [0, 6, 12, 18, 23]:
        trades = sum(log[f"p{hour}_trades"])
        volume = sum(log[f"p{hour}_volume"])
        print(f"   H{hour:02d}: {trades:4d} trades, {volume:8.1f} MW")
    
    return log, agent_logs, mo


def demo_minimal_test():
    """
    Demo 3: Minimaler Test mit Shinde Pricing (1 Produkt)
    
    - 1 Produkt
    - 1 VariableAgent
    - 2 RandomLiquidityAgents (Shinde-konform)
    - 100 Zeitschritte
    
    NEU: Enge Limit Prices für garantierte Trades!
    """
    print("\n" + "="*70)
    print("DEMO 3: MINIMAL TEST (1 PRODUKT) MIT SHINDE PRICING")
    print("="*70)
    
    products = create_hourly_products(n_hours=1, start_time=1440)
    
    print(f"\n📦 {len(products)} Product created")
    
    agents = []
    
    # 1 Variable Agent (wird SELL, da forecast > position)
    priv_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_forecast=60.0,   # Hoher Forecast → will verkaufen
        limit_buy=55.0,          # ← NEU! Enge Limits
        limit_sell=45.0          # ← NEU!
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
    print(f"\n👥 VariableAgent: Limits [Buy: {priv_info.limit_buy:.1f}, Sell: {priv_info.limit_sell:.1f}]")
    
    # 2 RandomLiquidity Agents (SHINDE-KONFORM, ENGE LIMITS!)
    print(f"\n👥 Creating RandomLiquidityAgents (Shinde-konform, enge Limits):")
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0,
            limit_buy=52.0,      # ← NEU! Sehr enge Limits für garantierte Matches!
            limit_sell=48.0      # ← NEU!
        )
        
        agent = RandomLiquidityAgent(
            id=100 + i,
            private_info=priv_info,
            rng=Random(200 + i),
            min_price=45.0,      # Bounds weiter als Limits
            max_price=55.0,
            min_volume=2.0,
            max_volume=6.0,
            n_orders=4
        )
        
        # SHINDE-KONFORME STRATEGY mit KLEINEM pi_range!
        agent.pricing_strategy = NaivePricingStrategy(
            rng=Random(300 + i),
            pi_range=3.0,        # ← Kleiner Range für mehr Overlap!
            n_segments=8,
            n_orders=4,
            min_price=45.0,
            max_price=55.0
        )
        
        print(f"   Agent {agent.id}: Limits [Buy: {priv_info.limit_buy:.1f}, Sell: {priv_info.limit_sell:.1f}]")
        agents.append(agent)
    
    print(f"\n📊 Total Agents: {len(agents)}")
    
    # Enable debug for minimal test
    os.makedirs("debug_logs", exist_ok=True)
    set_debug_file("debug_logs/demo3_agent_debug.txt")
    set_sim_debug_file("debug_logs/demo3_sim_debug.txt")
    
    print(f"\n▶️  Running simulation (100 steps)...")
    print(f"   📝 Agent debug → debug_logs/demo3_agent_debug.txt")
    print(f"   📝 Sim debug → debug_logs/demo3_sim_debug.txt")
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=100,
        seed=42,
        verbose=True
    )
    
    close_debug_file()
    close_sim_debug_file()
    
    print_simulation_summary(log, agent_logs, mo)
    
    print(f"\n💾 Debug logs saved:")
    print(f"   - debug_logs/demo3_agent_debug.txt")
    print(f"   - debug_logs/demo3_sim_debug.txt")
    
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
    print("   (MIT SHINDE-KONFORMER PRICING STRATEGY!)")
    print("🚀"*35)
    
    # Demo 1: Basic with Shinde Pricing (with FULL debug)
    log1, agent_logs1, mo1 = demo_basic_multi_product()
    
    # Demo 2: Many Products with Shinde Pricing (no debug)
    log2, agent_logs2, mo2 = demo_many_products()
    
    # Demo 3: Minimal Test with Shinde Pricing (with FULL debug)
    log3, agent_logs3, mo3 = demo_minimal_test()
    
    # Export results
    os.makedirs("results", exist_ok=True)
    export_results_to_csv(log1, agent_logs1, "results/demo1_shinde_pricing.csv")
    export_results_to_csv(log2, agent_logs2, "results/demo2_many_products.csv")
    export_results_to_csv(log3, agent_logs3, "results/demo3_minimal.csv")
    
    print("\n" + "="*70)
    print("✨ ALL DEMOS COMPLETED!")
    print("="*70)
    print(f"\n📁 Results saved to:")
    print(f"   - results/demo1_shinde_pricing.csv")
    print(f"   - results/demo2_many_products.csv")
    print(f"   - results/demo3_minimal.csv")
    print(f"\n📝 Debug logs saved to:")
    print(f"   - debug_logs/demo1_agent_debug.txt (Agent decisions)")
    print(f"   - debug_logs/demo1_sim_debug.txt (Order processing)")
    print(f"   - debug_logs/demo3_agent_debug.txt (Agent decisions)")
    print(f"   - debug_logs/demo3_sim_debug.txt (Order processing)")
    print(f"\n🎉 Mit Shinde-konformer Pricing Strategy sollten jetzt TRADES passieren!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()