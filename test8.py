"""
Test für Schritt 8: VariableAgent Multi-Product Support

Testet:
- Single-Product Mode funktioniert noch
- Multi-Product decide_orders()
- Produkt-spezifische Forecasts
- Produkt-spezifische Imbalances
- Update Forecast Mechanismus
"""

from intraday_abm.agents.variable import VariableAgent
from intraday_abm.core.types import AgentPrivateInfo, PublicInfo, TopOfBook, Side
from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo
from intraday_abm.core.product import create_hourly_products
from random import Random


def test_single_product_variable_agent():
    """Test dass Single-Product VariableAgent noch funktioniert."""
    print("\n=== Test 1: Single-Product VariableAgent ===")
    
    agent = VariableAgent.create(
        id=1,
        rng=Random(42),
        capacity=100.0,
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=2.0
    )
    
    assert agent.is_multi_product == False
    print(f"✅ Single-Product Agent erstellt")
    
    # Update imbalance
    agent.update_imbalance(t=100)
    
    # forecast = 50, market_position = 0 → imbalance = 50
    assert agent.private_info.imbalance == 50.0
    print(f"✅ Imbalance berechnet: {agent.private_info.imbalance}")
    
    # Decide order
    tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
    public_info = PublicInfo(tob=tob, da_price=50.0)
    
    order = agent.decide_order(t=100, public_info=public_info)
    
    assert order is not None
    assert order.side == Side.SELL  # Imbalance > 0 → SELL
    assert order.volume == 10.0  # base_volume
    print(f"✅ Order erstellt: {order.side.name} {order.volume} MW @ {order.price}")


def test_multi_product_variable_agent_creation():
    """Test Multi-Product VariableAgent Erstellung."""
    print("\n=== Test 2: Multi-Product VariableAgent erstellen ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_forecast=50.0
    )
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=2.0
    )
    
    assert agent.is_multi_product == True
    print(f"✅ Multi-Product Agent erstellt")
    
    # Alle Forecasts sollten 50.0 sein
    assert all(f == 50.0 for f in private_info.forecasts.values())
    print(f"✅ Initiale Forecasts: {private_info.forecasts}")


def test_multi_product_forecast():
    """Test produkt-spezifische Forecasts."""
    print("\n=== Test 3: Produkt-spezifische Forecasts ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_forecast=50.0
    )
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0
    )
    
    # Forecast für Produkt 0
    forecast_0 = agent._forecast(t=100, product_id=0)
    assert forecast_0 == 50.0
    print(f"✅ Forecast Produkt 0: {forecast_0}")
    
    # Update Forecast für Produkt 0
    agent.update_forecast(t=100, product_id=0, delta=5.0)
    
    forecast_0_new = agent._forecast(t=100, product_id=0)
    assert forecast_0_new == 55.0
    print(f"✅ Forecast Produkt 0 nach Update: {forecast_0_new}")
    
    # Andere Produkte unberührt
    assert agent._forecast(t=100, product_id=1) == 50.0
    assert agent._forecast(t=100, product_id=2) == 50.0
    print(f"✅ Andere Forecasts unberührt")


def test_multi_product_update_imbalance():
    """Test produkt-spezifische Imbalance Updates."""
    print("\n=== Test 4: Multi-Product update_imbalance() ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_forecast=50.0
    )
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0
    )
    
    # Set position für Produkt 0
    private_info.update_position(product_id=0, delta=30.0)  # position = 30
    
    # Update imbalance
    agent.update_imbalance(t=100, product_id=0)
    
    # imbalance[0] = forecast - position = 50 - 30 = 20
    assert private_info.imbalances[0] == 20.0
    print(f"✅ Imbalance Produkt 0: {private_info.imbalances[0]}")
    
    # Produkt 1 unberührt (position = 0)
    agent.update_imbalance(t=100, product_id=1)
    assert private_info.imbalances[1] == 50.0  # 50 - 0
    print(f"✅ Imbalance Produkt 1: {private_info.imbalances[1]}")


def test_multi_product_decide_orders():
    """Test decide_orders() für Multi-Product."""
    print("\n=== Test 5: Multi-Product decide_orders() ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_forecast=50.0
    )
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=5.0  # Höhere Toleranz
    )
    
    # Set unterschiedliche Positionen
    private_info.update_position(product_id=0, delta=30.0)  # imb = 50-30 = 20 → SELL
    private_info.update_position(product_id=1, delta=60.0)  # imb = 50-60 = -10 → BUY
    private_info.update_position(product_id=2, delta=48.0)  # imb = 50-48 = 2 → zu klein!
    
    # Public Info für 3 Produkte
    public_info = {}
    for pid in range(3):
        tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=50.0)
    
    orders = agent.decide_orders(t=100, public_info=public_info)
    
    # Sollte Orders für Produkt 0 und 1 geben (nicht 2, wegen Toleranz)
    assert len(orders) == 2
    assert 0 in orders
    assert 1 in orders
    assert 2 not in orders
    print(f"✅ {len(orders)} Orders erstellt (Produkt 0, 1)")
    
    # Check Sides
    assert orders[0].side == Side.SELL  # Imbalance > 0
    assert orders[1].side == Side.BUY   # Imbalance < 0
    print(f"✅ Produkt 0: {orders[0].side.name}")
    print(f"✅ Produkt 1: {orders[1].side.name}")
    
    # Check product_ids
    assert orders[0].product_id == 0
    assert orders[1].product_id == 1
    print(f"✅ product_ids korrekt gesetzt")


def test_forecast_evolution():
    """Test Forecast Evolution über Zeit."""
    print("\n=== Test 6: Forecast Evolution ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_forecast=50.0
    )
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0
    )
    
    # Simuliere Random Walk für Produkt 0
    for i in range(5):
        error = agent.rng.gauss(0, 2.0)
        agent.update_forecast(t=100+i, product_id=0, delta=error)
    
    forecast_0_final = agent._forecast(t=105, product_id=0)
    
    # Sollte nicht mehr 50.0 sein
    assert forecast_0_final != 50.0
    print(f"✅ Forecast Produkt 0 nach 5 Updates: {forecast_0_final}")
    
    # Produkt 1 sollte noch 50.0 sein
    assert agent._forecast(t=105, product_id=1) == 50.0
    print(f"✅ Produkt 1 unberührt: {agent._forecast(t=105, product_id=1)}")


def test_independent_product_trading():
    """Test dass Produkte unabhängig gehandelt werden."""
    print("\n=== Test 7: Unabhängiger Handel pro Produkt ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    # Set unterschiedliche Forecasts
    private_info.forecasts[0] = 60.0  # Hoch
    private_info.forecasts[1] = 40.0  # Niedrig
    private_info.forecasts[2] = 50.0  # Mittel
    
    agent = VariableAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        base_forecast=50.0,
        base_volume=10.0,
        imbalance_tolerance=5.0
    )
    
    # Update imbalances
    for pid in range(3):
        agent.update_imbalance(t=100, product_id=pid)
    
    # Imbalances sollten unterschiedlich sein
    assert private_info.imbalances[0] == 60.0  # 60 - 0
    assert private_info.imbalances[1] == 40.0  # 40 - 0
    assert private_info.imbalances[2] == 50.0  # 50 - 0
    print(f"✅ Unterschiedliche Imbalances: {private_info.imbalances}")
    
    # Trade in Produkt 0 sollte Produkt 1 nicht beeinflussen
    agent.on_trade(volume=10.0, price=50.0, side=Side.SELL, product_id=0)
    
    assert private_info.positions[0] == 10.0
    assert private_info.positions[1] == 0.0
    print(f"✅ Trade in Produkt 0 beeinflusst Produkt 1 nicht")


if __name__ == "__main__":
    print("=" * 60)
    print("VARIABLE AGENT MULTI-PRODUCT SUPPORT TESTS")
    print("=" * 60)
    
    test_single_product_variable_agent()
    test_multi_product_variable_agent_creation()
    test_multi_product_forecast()
    test_multi_product_update_imbalance()
    test_multi_product_decide_orders()
    test_forecast_evolution()
    test_independent_product_trading()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 7 TESTS BESTANDEN!")
    print("=" * 60)
