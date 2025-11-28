"""
Test für Schritt 7: BaseAgent Multi-Product Support

Testet:
- is_multi_product Detection
- Single-Product Interface funktioniert noch
- Multi-Product Interface (update_imbalance, on_trade)
- Fallback-Verhalten
"""

from intraday_abm.core.types import AgentPrivateInfo, PublicInfo, TopOfBook, Side
from intraday_abm.core.types import MultiProductPrivateInfo
from intraday_abm.core.product import create_hourly_products
from intraday_abm.core.order import Order
from intraday_abm.agents.base import Agent
from random import Random


class DummySingleProductAgent(Agent):
    """Dummy Agent für Single-Product Tests."""
    
    def decide_order(self, t, public_info):
        # Simple logic: always buy
        return Order(
            id=0,
            agent_id=self.id,
            side=Side.BUY,
            price=public_info.da_price,
            volume=10.0,
            product_id=0
        )


class DummyMultiProductAgent(Agent):
    """Dummy Agent für Multi-Product Tests."""
    
    def decide_order(self, t, public_info):
        # Not used in multi-product mode
        return None
    
    def decide_orders(self, t, public_info):
        # Simple logic: buy in each product
        orders = {}
        for product_id, pub_info in public_info.items():
            orders[product_id] = Order(
                id=0,
                agent_id=self.id,
                side=Side.BUY,
                price=pub_info.da_price,
                volume=10.0,
                product_id=product_id
            )
        return orders


def test_single_product_detection():
    """Test dass Single-Product Mode erkannt wird."""
    print("\n=== Test 1: Single-Product Detection ===")
    
    private_info = AgentPrivateInfo(effective_capacity=100.0)
    agent = DummySingleProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    assert agent.is_multi_product == False
    print(f"✅ Single-Product Agent erkannt: is_multi_product={agent.is_multi_product}")


def test_multi_product_detection():
    """Test dass Multi-Product Mode erkannt wird."""
    print("\n=== Test 2: Multi-Product Detection ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(products)
    agent = DummyMultiProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    assert agent.is_multi_product == True
    print(f"✅ Multi-Product Agent erkannt: is_multi_product={agent.is_multi_product}")


def test_single_product_update_imbalance():
    """Test update_imbalance() in Single-Product Mode."""
    print("\n=== Test 3: Single-Product update_imbalance() ===")
    
    private_info = AgentPrivateInfo(
        effective_capacity=100.0,
        da_position=80.0,
        market_position=70.0
    )
    agent = DummySingleProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    agent.update_imbalance(t=100)
    
    # imbalance = da_position - market_position = 80 - 70 = 10
    assert agent.private_info.imbalance == 10.0
    print(f"✅ Imbalance berechnet: {agent.private_info.imbalance}")


def test_multi_product_update_imbalance():
    """Test update_imbalance() in Multi-Product Mode."""
    print("\n=== Test 4: Multi-Product update_imbalance() ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(
        products=products,
        initial_da_position=80.0
    )
    
    # Set market position für Produkt 0
    private_info.update_position(product_id=0, delta=-70.0)  # position = -70
    
    agent = DummyMultiProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    agent.update_imbalance(t=100, product_id=0)
    
    # imbalance[0] = 80 - (-70) = 150
    assert private_info.imbalances[0] == 150.0
    print(f"✅ Imbalance für Produkt 0: {private_info.imbalances[0]}")


def test_single_product_on_trade():
    """Test on_trade() in Single-Product Mode."""
    print("\n=== Test 5: Single-Product on_trade() ===")
    
    private_info = AgentPrivateInfo(
        effective_capacity=100.0,
        market_position=0.0,
        revenue=0.0
    )
    agent = DummySingleProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    # SELL Trade
    agent.on_trade(volume=10.0, price=50.0, side=Side.SELL)
    
    assert agent.private_info.market_position == 10.0
    assert agent.private_info.revenue == 500.0
    print(f"✅ SELL Trade: position={agent.private_info.market_position}, revenue={agent.private_info.revenue}")
    
    # BUY Trade
    agent.on_trade(volume=5.0, price=49.0, side=Side.BUY)
    
    assert agent.private_info.market_position == 5.0  # 10 - 5
    assert agent.private_info.revenue == 255.0  # 500 - 245
    print(f"✅ BUY Trade: position={agent.private_info.market_position}, revenue={agent.private_info.revenue}")


def test_multi_product_on_trade():
    """Test on_trade() in Multi-Product Mode."""
    print("\n=== Test 6: Multi-Product on_trade() ===")
    
    products = create_hourly_products(n_hours=2)
    private_info = MultiProductPrivateInfo.initialize(products)
    
    agent = DummyMultiProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    # SELL Trade in Produkt 0
    agent.on_trade(volume=10.0, price=50.0, side=Side.SELL, product_id=0)
    
    assert private_info.positions[0] == 10.0
    assert private_info.revenues[0] == 500.0
    print(f"✅ Produkt 0 SELL: position={private_info.positions[0]}, revenue={private_info.revenues[0]}")
    
    # BUY Trade in Produkt 1
    agent.on_trade(volume=5.0, price=48.0, side=Side.BUY, product_id=1)
    
    assert private_info.positions[1] == -5.0
    assert private_info.revenues[1] == -240.0
    print(f"✅ Produkt 1 BUY: position={private_info.positions[1]}, revenue={private_info.revenues[1]}")
    
    # Produkt 0 unberührt
    assert private_info.positions[0] == 10.0
    print(f"✅ Produkt 0 unberührt: position={private_info.positions[0]}")


def test_single_product_decide_order():
    """Test decide_order() funktioniert noch."""
    print("\n=== Test 7: Single-Product decide_order() ===")
    
    private_info = AgentPrivateInfo(effective_capacity=100.0)
    agent = DummySingleProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
    public_info = PublicInfo(tob=tob, da_price=50.0)
    
    order = agent.decide_order(t=100, public_info=public_info)
    
    assert order is not None
    assert order.side == Side.BUY
    assert order.price == 50.0
    assert order.volume == 10.0
    print(f"✅ decide_order() gibt Order zurück: {order.side.name} {order.volume} @ {order.price}")


def test_multi_product_decide_orders():
    """Test decide_orders() für Multi-Product."""
    print("\n=== Test 8: Multi-Product decide_orders() ===")
    
    products = create_hourly_products(n_hours=3)
    private_info = MultiProductPrivateInfo.initialize(products)
    
    agent = DummyMultiProductAgent(
        id=1,
        private_info=private_info,
        rng=Random(42)
    )
    
    # Public Info für 3 Produkte
    public_info = {}
    for pid in range(3):
        tob = TopOfBook(49.0, 10.0, 51.0, 15.0)
        public_info[pid] = PublicInfo(tob=tob, da_price=50.0 + pid)
    
    orders = agent.decide_orders(t=100, public_info=public_info)
    
    assert len(orders) == 3
    assert 0 in orders
    assert 1 in orders
    assert 2 in orders
    print(f"✅ decide_orders() gibt {len(orders)} Orders zurück")
    
    # Überprüfe Produkt-IDs
    assert orders[0].product_id == 0
    assert orders[1].product_id == 1
    assert orders[2].product_id == 2
    print(f"✅ product_ids korrekt gesetzt")


if __name__ == "__main__":
    print("=" * 60)
    print("BASE AGENT MULTI-PRODUCT SUPPORT TESTS")
    print("=" * 60)
    
    test_single_product_detection()
    test_multi_product_detection()
    test_single_product_update_imbalance()
    test_multi_product_update_imbalance()
    test_single_product_on_trade()
    test_multi_product_on_trade()
    test_single_product_decide_order()
    test_multi_product_decide_orders()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 8 TESTS BESTANDEN!")
    print("=" * 60)
