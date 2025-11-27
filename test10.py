"""
Test für Schritt 10: RandomLiquidityAgent Multi-Product Support

Testet:
- Single-Product Mode funktioniert noch
- Multi-Product decide_orders()
- Liquidität auf beiden Seiten (BUY + SELL)
- Orders für alle offenen Produkte
"""

from intraday_abm.agents.random_liquidity import RandomLiquidityAgent
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy
from intraday_abm.core.types import AgentPrivateInfo, PublicInfo, TopOfBook, Side
from intraday_abm.core.multi_product_private_info import MultiProductPrivateInfo
from intraday_abm.core.product import create_hourly_products
from random import Random


def test_single_product_random_liquidity():
    """Test dass Single-Product RandomLiquidityAgent noch funktioniert."""
    print("\n=== Test 1: Single-Product RandomLiquidityAgent ===")
    
    rng = Random(42)
    
    agent = RandomLiquidityAgent.create(
        id=1,
        rng=rng,
        capacity=100.0,
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=3
    )
    
    # Assign pricing strategy with correct parameters
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=3
    )
    
    assert agent.is_multi_product == False
    print(f"✅ Single-Product Agent erstellt")
    
    # Decide orders
    tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
    public_info = PublicInfo(tob=tob, da_price=50.0)
    
    orders = agent.decide_order(t=100, public_info=public_info)
    
    assert orders is not None
    assert isinstance(orders, list)
    assert len(orders) > 0
    print(f"✅ {len(orders)} Orders erstellt")
    
    # Check that we have both BUY and SELL (probabilistically)
    sides = [order.side for order in orders]
    print(f"✅ Sides: {[s.name for s in sides]}")


def test_multi_product_random_liquidity_creation():
    """Test Multi-Product RandomLiquidityAgent Erstellung."""
    print("\n=== Test 2: Multi-Product RandomLiquidityAgent erstellen ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    agent = RandomLiquidityAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=3
    )
    
    # Assign pricing strategy
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=3
    )
    
    assert agent.is_multi_product == True
    print(f"✅ Multi-Product Agent erstellt")


def test_multi_product_decide_orders():
    """Test decide_orders() für Multi-Product."""
    print("\n=== Test 3: Multi-Product decide_orders() ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    agent = RandomLiquidityAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=3
    )
    
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=3
    )
    
    # Public Info für 3 Produkte
    public_info = {}
    for pid in range(3):
        tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=50.0 + pid)
    
    orders_dict = agent.decide_orders(t=100, public_info=public_info)
    
    # Sollte Orders für alle 3 Produkte geben
    assert len(orders_dict) == 3
    assert 0 in orders_dict
    assert 1 in orders_dict
    assert 2 in orders_dict
    print(f"✅ Orders für {len(orders_dict)} Produkte erstellt")
    
    # Check dass jedes Produkt mehrere Orders hat
    for pid, orders in orders_dict.items():
        assert isinstance(orders, list)
        assert len(orders) > 0
        print(f"✅ Produkt {pid}: {len(orders)} Orders")


def test_liquidity_on_both_sides():
    """Test dass RandomLiquidity auf beiden Seiten liefert."""
    print("\n=== Test 4: Liquidität auf beiden Seiten ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    agent = RandomLiquidityAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=10  # Mehr Orders für bessere Statistik
    )
    
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=10
    )
    
    # Public Info
    public_info = {}
    for pid in range(2):
        tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=50.0)
    
    orders_dict = agent.decide_orders(t=100, public_info=public_info)
    
    # Sammle alle Orders
    all_orders = []
    for orders in orders_dict.values():
        all_orders.extend(orders)
    
    # Check Sides
    buy_orders = [o for o in all_orders if o.side == Side.BUY]
    sell_orders = [o for o in all_orders if o.side == Side.SELL]
    
    assert len(buy_orders) > 0
    assert len(sell_orders) > 0
    print(f"✅ BUY Orders: {len(buy_orders)}, SELL Orders: {len(sell_orders)}")
    print(f"✅ Liquidität auf beiden Seiten!")


def test_independent_products():
    """Test dass Produkte unabhängig gehandelt werden."""
    print("\n=== Test 5: Unabhängige Produkte ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    agent = RandomLiquidityAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=5
    )
    
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=5
    )
    
    # Public Info mit unterschiedlichen DA-Preisen
    public_info = {}
    for pid in range(3):
        tob = TopOfBook(40.0 + pid*5, 10.0, 42.0 + pid*5, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=41.0 + pid*5)
    
    orders_dict = agent.decide_orders(t=100, public_info=public_info)
    
    # Jedes Produkt sollte eigene Orders haben
    for pid in range(3):
        orders = orders_dict[pid]
        # Alle Orders sollten korrekte product_id haben
        for order in orders:
            assert order.product_id == pid
        print(f"✅ Produkt {pid}: Alle Orders haben product_id={pid}")


def test_product_ids_correctly_set():
    """Test dass product_ids korrekt gesetzt sind."""
    print("\n=== Test 6: product_ids korrekt gesetzt ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_capacity=100.0
    )
    
    agent = RandomLiquidityAgent(
        id=1,
        private_info=private_info,
        rng=Random(42),
        min_price=30.0,
        max_price=70.0,
        min_volume=1.0,
        max_volume=5.0,
        n_orders=3
    )
    
    agent.pricing_strategy = NaivePricingStrategy(
        pi_range=10.0,
        n_segments=20,
        min_price=30.0,
        max_price=70.0,
        rng=Random(43),
        n_orders=3
    )
    
    public_info = {}
    for pid in range(2):
        tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=50.0)
    
    orders_dict = agent.decide_orders(t=100, public_info=public_info)
    
    # Check product_ids
    for pid, orders in orders_dict.items():
        for order in orders:
            assert order.product_id == pid
            assert order.agent_id == agent.id
    
    print(f"✅ Alle product_ids korrekt gesetzt")


if __name__ == "__main__":
    print("=" * 60)
    print("RANDOM LIQUIDITY AGENT MULTI-PRODUCT SUPPORT TESTS")
    print("=" * 60)
    
    test_single_product_random_liquidity()
    test_multi_product_random_liquidity_creation()
    test_multi_product_decide_orders()
    test_liquidity_on_both_sides()
    test_independent_products()
    test_product_ids_correctly_set()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 6 TESTS BESTANDEN!")
    print("=" * 60)