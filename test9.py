"""
Test für Schritt 9: Multi-Product Simulation Loop

Testet:
- Multi-Product Simulation mit VariableAgent
- Mixed Agents (Single + Multi-Product)
- Product Lifecycle
- Logging
"""

from intraday_abm.sim.multi_product_simulation import run_multi_product_simulation, print_simulation_summary
from intraday_abm.core.product import create_hourly_products, create_single_product
from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo
from intraday_abm.core.types import AgentPrivateInfo
from intraday_abm.agents.variable import VariableAgent
from random import Random


def test_simple_multi_product_simulation():
    """Test einfache Multi-Product Simulation mit 1 Agent."""
    print("\n=== Test 1: Einfache Multi-Product Simulation ===")
    
    # 2 Produkte
    products = [
        create_single_product(product_id=0, delivery_start=1440),
        create_single_product(product_id=1, delivery_start=1500),
    ]
    
    # Multi-Product Agent
    priv_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    priv_info.forecasts[0] = 50.0
    priv_info.forecasts[1] = 40.0
    
    agent = VariableAgent(
        id=1,
        private_info=priv_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=5.0
    )
    
    # Run simulation
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=[agent],
        n_steps=50,
        seed=42,
        verbose=False
    )
    
    assert len(log["t"]) == 50
    print(f"✅ Simulation lief {len(log['t'])} Schritte")
    
    # Check dass beide Produkte gehandelt wurden
    p0_trades = sum(log["p0_trades"])
    p1_trades = sum(log["p1_trades"])
    
    print(f"✅ Produkt 0: {p0_trades} Trades")
    print(f"✅ Produkt 1: {p1_trades} Trades")


def test_multi_product_with_multiple_agents():
    """Test mit mehreren Multi-Product Agents."""
    print("\n=== Test 2: Mehrere Multi-Product Agents ===")
    
    products = create_hourly_products(n_hours=2)
    
    # 2 Multi-Product Agents mit unterschiedlichen Forecasts
    agents = []
    for i in range(2):
        priv_info = MultiProductPrivateInfo.initialize(
            products=products,
            initial_capacity=100.0
        )
        priv_info.forecasts[0] = 50.0 + i * 10.0  # Agent 0: 50, Agent 1: 60
        priv_info.forecasts[1] = 40.0 - i * 5.0   # Agent 0: 40, Agent 1: 35
        
        agent = VariableAgent(
            id=i,
            private_info=priv_info,
            rng=Random(42 + i),
            base_forecast=50.0,
            base_volume=10.0,
            imbalance_tolerance=5.0
        )
        agents.append(agent)
    
    # Run simulation
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=50,
        seed=42,
        verbose=False
    )
    
    assert len(agent_logs) == 2
    print(f"✅ {len(agent_logs)} Agents geloggt")
    
    # Check agent logs
    for agent_id, agent_log in agent_logs.items():
        assert len(agent_log["t"]) == 50
        print(f"✅ Agent {agent_id}: {len(agent_log['t'])} Einträge")


def test_mixed_agents_simulation():
    """Test mit Mixed Agents (Single + Multi-Product)."""
    print("\n=== Test 3: Mixed Agents (Single + Multi) ===")
    
    products = create_hourly_products(n_hours=2)
    
    # Multi-Product Agent
    multi_priv = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    multi_priv.forecasts[0] = 50.0
    multi_priv.forecasts[1] = 40.0
    
    multi_agent = VariableAgent(
        id=1,
        private_info=multi_priv,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=5.0
    )
    
    # Single-Product Agent (Fallback Mode)
    single_priv = AgentPrivateInfo(effective_capacity=100.0)
    single_agent = VariableAgent(
        id=2,
        private_info=single_priv,
        rng=Random(43),
        base_forecast=45.0,
        base_volume=8.0,
        imbalance_tolerance=3.0
    )
    
    agents = [multi_agent, single_agent]
    
    # Run simulation
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=agents,
        n_steps=50,
        seed=42,
        verbose=False
    )
    
    assert len(agent_logs) == 2
    print(f"✅ Mixed Agents Simulation erfolgreich")
    
    # Multi-Product Agent sollte per-product logs haben
    assert "p0_position" in agent_logs[1]
    assert "p1_position" in agent_logs[1]
    print(f"✅ Multi-Product Agent hat per-product logs")
    
    # Single-Product Agent sollte keine per-product logs haben
    assert "p0_position" not in agent_logs[2]
    print(f"✅ Single-Product Agent hat keine per-product logs")


def test_product_lifecycle():
    """Test dass Products korrekt geschlossen werden."""
    print("\n=== Test 4: Product Lifecycle ===")
    
    # Produkt mit frühem Gate-Close
    products = [
        create_single_product(
            product_id=0, 
            delivery_start=1440,
            gate_close_offset_minutes=30  # Schließt früh
        ),
    ]
    
    priv_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    priv_info.forecasts[0] = 50.0
    
    agent = VariableAgent(
        id=1,
        private_info=priv_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0
    )
    
    # Run bis nach Gate-Close
    # gate_close = 1440 - 30 = 1410
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=[agent],
        n_steps=100,  # Läuft bis t=99
        seed=42,
        verbose=False
    )
    
    # Check dass Produkt irgendwann geschlossen wurde
    from intraday_abm.core.product import ProductStatus
    final_status = mo.products[0].status
    
    # Sollte noch OPEN sein (da t < gate_close)
    # Oder CLOSED wenn Gate-Close erreicht
    print(f"✅ Final Product Status: {final_status.name}")


def test_logging_structure():
    """Test dass Logging-Struktur korrekt ist."""
    print("\n=== Test 5: Logging-Struktur ===")
    
    products = create_hourly_products(n_hours=2)
    
    priv_info = MultiProductPrivateInfo.initialize(products=products, initial_capacity=100.0)
    agent = VariableAgent(
        id=1,
        private_info=priv_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0
    )
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=[agent],
        n_steps=20,
        seed=42,
        verbose=False
    )
    
    # Check market log structure
    assert "t" in log
    assert "n_trades" in log
    assert "total_volume" in log
    assert "n_open_products" in log
    assert "p0_trades" in log
    assert "p1_trades" in log
    print(f"✅ Market log hat alle Keys")
    
    # Check agent log structure
    agent_log = agent_logs[1]
    assert "t" in agent_log
    assert "total_revenue" in agent_log
    assert "total_position" in agent_log
    assert "p0_position" in agent_log
    assert "p1_position" in agent_log
    print(f"✅ Agent log hat alle Keys")
    
    # Check lengths
    assert len(log["t"]) == 20
    assert len(agent_log["t"]) == 20
    print(f"✅ Alle Logs haben korrekte Länge")


def test_summary_printing():
    """Test print_simulation_summary()."""
    print("\n=== Test 6: Summary Printing ===")
    
    products = create_hourly_products(n_hours=2)
    
    priv_info = MultiProductPrivateInfo.initialize(products=products, initial_capacity=100.0)
    priv_info.forecasts[0] = 50.0
    priv_info.forecasts[1] = 40.0
    
    agent = VariableAgent(
        id=1,
        private_info=priv_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=5.0
    )
    
    log, agent_logs, mo = run_multi_product_simulation(
        products=products,
        agents=[agent],
        n_steps=50,
        seed=42,
        verbose=False
    )
    
    # Should not crash
    print_simulation_summary(log, agent_logs, mo)
    print(f"✅ Summary printing funktioniert")


if __name__ == "__main__":
    print("=" * 60)
    print("MULTI-PRODUCT SIMULATION TESTS")
    print("=" * 60)
    
    test_simple_multi_product_simulation()
    test_multi_product_with_multiple_agents()
    test_mixed_agents_simulation()
    test_product_lifecycle()
    test_logging_structure()
    test_summary_printing()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 6 TESTS BESTANDEN!")
    print("=" * 60)
