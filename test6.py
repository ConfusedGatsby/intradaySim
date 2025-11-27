"""
Test für Schritt 6: MultiProductPrivateInfo

Testet:
- Initialisierung mit mehreren Produkten
- Aggregationsmethoden (total_revenue, net_profit, etc.)
- Produkt-spezifische Updates
- State Queries
"""

from intraday_abm.core.product import create_hourly_products, create_single_product
from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo


def test_initialize():
    """Test Initialisierung von MultiProductPrivateInfo."""
    print("\n=== Test 1: Initialisierung ===")
    
    products = create_hourly_products(n_hours=3)
    
    info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_da_position=80.0,
        initial_forecast=50.0
    )
    
    assert len(info.positions) == 3
    assert len(info.revenues) == 3
    assert len(info.imbalances) == 3
    print(f"✅ Initialisiert für {len(info.positions)} Produkte")
    
    # Alle Positionen sollten 0 sein
    assert all(pos == 0.0 for pos in info.positions.values())
    print(f"✅ Alle Positionen bei 0.0")
    
    # Alle DA-Positionen sollten 80 sein
    assert all(da == 80.0 for da in info.da_positions.values())
    print(f"✅ Alle DA-Positionen bei 80.0")
    
    # Alle Forecasts sollten 50 sein
    assert all(f == 50.0 for f in info.forecasts.values())
    print(f"✅ Alle Forecasts bei 50.0")


def test_update_position():
    """Test update_position()."""
    print("\n=== Test 2: update_position() ===")
    
    products = create_hourly_products(n_hours=3)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Update Position für Produkt 0
    info.update_position(product_id=0, delta=10.0)
    assert info.positions[0] == 10.0
    print(f"✅ Position Produkt 0: {info.positions[0]}")
    
    # Weitere Updates
    info.update_position(product_id=0, delta=5.0)
    assert info.positions[0] == 15.0
    print(f"✅ Position Produkt 0 nach weiterem Update: {info.positions[0]}")
    
    # Andere Produkte unberührt
    assert info.positions[1] == 0.0
    assert info.positions[2] == 0.0
    print(f"✅ Andere Produkte unberührt")


def test_update_revenue():
    """Test update_revenue()."""
    print("\n=== Test 3: update_revenue() ===")
    
    products = create_hourly_products(n_hours=3)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Update Revenue für verschiedene Produkte
    info.update_revenue(product_id=0, delta=100.0)
    info.update_revenue(product_id=1, delta=200.0)
    info.update_revenue(product_id=2, delta=150.0)
    
    assert info.revenues[0] == 100.0
    assert info.revenues[1] == 200.0
    assert info.revenues[2] == 150.0
    print(f"✅ Revenues pro Produkt: {info.revenues}")


def test_total_revenue():
    """Test total_revenue() Aggregation."""
    print("\n=== Test 4: total_revenue() ===")
    
    products = create_hourly_products(n_hours=3)
    info = MultiProductPrivateInfo.initialize(products)
    
    info.update_revenue(product_id=0, delta=100.0)
    info.update_revenue(product_id=1, delta=200.0)
    info.update_revenue(product_id=2, delta=150.0)
    
    total = info.total_revenue()
    assert total == 450.0
    print(f"✅ Total Revenue: {total}")


def test_imbalance_management():
    """Test Imbalance Setting und Kosten."""
    print("\n=== Test 5: Imbalance Management ===")
    
    products = create_hourly_products(n_hours=3)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Set Imbalances
    info.set_imbalance(product_id=0, imbalance=5.0)
    info.set_imbalance(product_id=1, imbalance=-3.0)
    info.set_imbalance(product_id=2, imbalance=0.0)
    
    assert info.imbalances[0] == 5.0
    assert info.imbalances[1] == -3.0
    assert info.imbalances[2] == 0.0
    print(f"✅ Imbalances gesetzt: {info.imbalances}")
    
    # Set Imbalance Costs
    info.set_imbalance_cost(product_id=0, cost=50.0)
    info.set_imbalance_cost(product_id=1, cost=30.0)
    
    total_cost = info.total_imbalance_cost()
    assert total_cost == 80.0
    print(f"✅ Total Imbalance Cost: {total_cost}")


def test_net_profit():
    """Test net_profit() Berechnung."""
    print("\n=== Test 6: net_profit() ===")
    
    products = create_hourly_products(n_hours=2)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Revenue
    info.update_revenue(product_id=0, delta=500.0)
    info.update_revenue(product_id=1, delta=300.0)
    
    # Imbalance Costs
    info.set_imbalance_cost(product_id=0, cost=50.0)
    info.set_imbalance_cost(product_id=1, cost=30.0)
    
    net = info.net_profit()
    assert net == 720.0  # 800 - 80
    print(f"✅ Net Profit: {net} (Revenue: {info.total_revenue()}, Costs: {info.total_imbalance_cost()})")


def test_get_product_state():
    """Test get_product_state()."""
    print("\n=== Test 7: get_product_state() ===")
    
    products = create_hourly_products(n_hours=2)
    info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0,
        initial_da_position=80.0
    )
    
    # Update für Produkt 0
    info.update_position(product_id=0, delta=10.0)
    info.update_revenue(product_id=0, delta=500.0)
    info.set_imbalance(product_id=0, imbalance=2.0)
    
    state = info.get_product_state(product_id=0)
    
    assert state['position'] == 10.0
    assert state['revenue'] == 500.0
    assert state['imbalance'] == 2.0
    assert state['da_position'] == 80.0
    assert state['capacity'] == 100.0
    print(f"✅ Product 0 State: {state}")


def test_get_products_with_imbalance():
    """Test get_products_with_imbalance()."""
    print("\n=== Test 8: get_products_with_imbalance() ===")
    
    products = create_hourly_products(n_hours=4)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Set Imbalances
    info.set_imbalance(product_id=0, imbalance=5.0)
    info.set_imbalance(product_id=1, imbalance=0.0)
    info.set_imbalance(product_id=2, imbalance=-3.5)
    info.set_imbalance(product_id=3, imbalance=0.005)  # Sehr klein
    
    products_with_imb = info.get_products_with_imbalance(min_imbalance=0.1)
    
    assert 0 in products_with_imb
    assert 1 not in products_with_imb
    assert 2 in products_with_imb
    assert 3 not in products_with_imb
    print(f"✅ Produkte mit Imbalance: {products_with_imb}")


def test_reset_product():
    """Test reset_product()."""
    print("\n=== Test 9: reset_product() ===")
    
    products = create_hourly_products(n_hours=2)
    info = MultiProductPrivateInfo.initialize(products)
    
    # Set some values
    info.update_position(product_id=0, delta=10.0)
    info.update_revenue(product_id=0, delta=500.0)
    info.set_imbalance(product_id=0, imbalance=5.0)
    
    assert info.positions[0] == 10.0
    print(f"✅ Vor Reset: Position={info.positions[0]}, Revenue={info.revenues[0]}")
    
    # Reset
    info.reset_product(product_id=0)
    
    assert info.positions[0] == 0.0
    assert info.revenues[0] == 0.0
    assert info.imbalances[0] == 0.0
    print(f"✅ Nach Reset: Alle Werte bei 0.0")


def test_soc_for_bess():
    """Test SoC (State of Charge) für BESS Agenten."""
    print("\n=== Test 10: SoC für BESS ===")
    
    products = create_hourly_products(n_hours=3)
    info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_soc=50.0  # 50 MWh geladen
    )
    
    assert info.soc == 50.0
    print(f"✅ Initiales SoC: {info.soc} MWh")
    
    # SoC Update (manuell)
    info.soc = 60.0
    assert info.soc == 60.0
    print(f"✅ SoC Update: {info.soc} MWh")
    
    # SoC ist global (nicht per Produkt)
    assert 'soc' not in info.positions
    print(f"✅ SoC ist global, nicht per Produkt")


if __name__ == "__main__":
    print("=" * 60)
    print("MULTI-PRODUCT PRIVATE INFO TESTS")
    print("=" * 60)
    
    test_initialize()
    test_update_position()
    test_update_revenue()
    test_total_revenue()
    test_imbalance_management()
    test_net_profit()
    test_get_product_state()
    test_get_products_with_imbalance()
    test_reset_product()
    test_soc_for_bess()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 10 TESTS BESTANDEN!")
    print("=" * 60)
