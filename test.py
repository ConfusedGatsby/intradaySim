"""
Test für Schritt 5: MultiProductMarketOperator

Testet:
- Erstellung von MultiProductMarketOperator
- Produkt-Lifecycle-Management
- Order-Routing zu korrekten Produkten
- Multi-Product Order-Cancellation
- Public Info Abfrage für mehrere Produkte
"""

from intraday_abm.core.product import create_hourly_products, create_single_product, ProductStatus
from intraday_abm.core.multi_product_market_operator import MultiProductMarketOperator
from intraday_abm.core.order import Order
from intraday_abm.core.types import Side, TimeInForce


def test_create_multi_product_mo():
    """Test Erstellung von MultiProductMarketOperator."""
    print("\n=== Test 1: MultiProductMarketOperator erstellen ===")
    
    # Erstelle 3 Produkte
    products = create_hourly_products(
        n_hours=3,
        start_time=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    mo = MultiProductMarketOperator.from_products(products)
    
    assert len(mo.products) == 3
    assert len(mo.order_books) == 3
    print(f"✅ MultiProductMarketOperator mit {len(mo.products)} Produkten erstellt")
    
    # Überprüfe, dass alle Produkte im Status PENDING sind
    for product_id, product in mo.products.items():
        assert product.status == ProductStatus.PENDING
    print(f"✅ Alle Produkte im Status PENDING")


def test_open_products():
    """Test open_products() Methode."""
    print("\n=== Test 2: open_products() ===")
    
    # Erstelle Produkte mit GLEICHER delivery_start aber unterschiedlichen IDs
    products = []
    for i in range(3):
        product = create_single_product(
            product_id=i,
            delivery_start=1440,  # GLEICHE Lieferzeit für alle!
            delivery_duration=60,
            gate_open_offset_hours=24,  # Alle öffnen gleichzeitig
            gate_close_offset_minutes=60,
            da_price=50.0
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    
    # Alle sollten gate_open bei (1440 - 24*60) = 0 haben
    for pid, product in mo.products.items():
        assert product.gate_open == 0, f"Product {pid} has gate_open={product.gate_open}, expected 0"
    
    # Öffne Produkte bei t=0
    opened = mo.open_products(t=0)
    
    assert len(opened) == 3
    print(f"✅ {len(opened)} Produkte geöffnet")
    
    # Alle Produkte sollten jetzt OPEN sein
    for product_id in opened:
        product = mo.products[product_id]
        assert product.status == ProductStatus.OPEN
    print(f"✅ Alle Produkte haben Status OPEN")


def test_open_products_staggered():
    """Test open_products() mit gestaffelten Öffnungszeiten."""
    print("\n=== Test 2b: open_products() gestaffelt ===")
    
    products = create_hourly_products(
        n_hours=3,
        start_time=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    mo = MultiProductMarketOperator.from_products(products)
    
    # Bei t=0 sollte nur Produkt 0 öffnen (gate_open=0)
    opened = mo.open_products(t=0)
    assert len(opened) == 1
    assert 0 in opened
    print(f"✅ Bei t=0: Produkt 0 geöffnet")
    
    # Bei t=60 sollte Produkt 1 öffnen (gate_open=60)
    opened = mo.open_products(t=60)
    assert len(opened) == 1
    assert 1 in opened
    print(f"✅ Bei t=60: Produkt 1 geöffnet")
    
    # Bei t=120 sollte Produkt 2 öffnen (gate_open=120)
    opened = mo.open_products(t=120)
    assert len(opened) == 1
    assert 2 in opened
    print(f"✅ Bei t=120: Produkt 2 geöffnet")


def test_get_open_products():
    """Test get_open_products()."""
    print("\n=== Test 3: get_open_products() ===")
    
    products = []
    for i in range(3):
        product = create_single_product(
            product_id=i,
            delivery_start=1440,  # GLEICHE Lieferzeit
            gate_open_offset_hours=24,
            gate_close_offset_minutes=60
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    mo.open_products(t=0)
    
    # Alle sollten offen sein bei t=100
    open_pids = mo.get_open_products(t=100)
    assert len(open_pids) == 3
    print(f"✅ {len(open_pids)} Produkte offen bei t=100")
    
    # gate_close für alle: (1440 - 60) = 1380
    # Bei t=1400 sollten alle geschlossen sein
    open_pids = mo.get_open_products(t=1400)
    assert len(open_pids) == 0
    print(f"✅ Alle Produkte geschlossen bei t=1400")


def test_update_product_status():
    """Test update_product_status() - automatisches Schließen."""
    print("\n=== Test 4: update_product_status() ===")
    
    products = []
    for i in range(2):
        product = create_single_product(
            product_id=i,
            delivery_start=1440 + i * 60,  # Unterschiedliche Lieferzeiten
            gate_open_offset_hours=24,
            gate_close_offset_minutes=60
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    
    # Öffne beide Produkte
    mo.open_products(t=0)  # Produkt 0 öffnet
    mo.open_products(t=60)  # Produkt 1 öffnet
    
    # Produkt 0: gate_close = 1380
    # Produkt 1: gate_close = 1440
    
    # Bei t=1380 sollte Produkt 0 geschlossen werden
    closed = mo.update_product_status(t=1380)
    
    assert 0 in closed
    assert mo.products[0].status == ProductStatus.CLOSED
    print(f"✅ Produkt 0 automatisch geschlossen bei t=1380")
    
    # Produkt 1 sollte noch offen sein
    assert mo.products[1].status == ProductStatus.OPEN
    print(f"✅ Produkt 1 noch offen")


def test_process_order_routing():
    """Test process_order() - Order-Routing."""
    print("\n=== Test 5: process_order() - Routing ===")
    
    products = []
    for i in range(3):
        product = create_single_product(
            product_id=i,
            delivery_start=1440,  # GLEICHE Lieferzeit
            gate_open_offset_hours=24
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    mo.open_products(t=0)
    
    # Order für Produkt 0
    order_p0 = Order(
        id=0,  # Wird zugewiesen
        agent_id=1,
        side=Side.BUY,
        price=49.0,
        volume=10.0,
        product_id=0,
        time_in_force=TimeInForce.GTC
    )
    
    trades = mo.process_order(order_p0, t=100)
    
    # Keine Trades (keine Gegenseite)
    assert len(trades) == 0
    print(f"✅ Order für Produkt 0 verarbeitet, keine Trades")
    
    # Order sollte im Buch von Produkt 0 sein
    ob_0 = mo.order_books[0]
    assert len(ob_0) == 1
    print(f"✅ Order in OrderBook von Produkt 0: {len(ob_0)} Orders")
    
    # Order für Produkt 1
    order_p1 = Order(
        id=0,
        agent_id=2,
        side=Side.SELL,
        price=51.0,
        volume=15.0,
        product_id=1,
        time_in_force=TimeInForce.GTC
    )
    
    trades = mo.process_order(order_p1, t=100)
    
    # Sollte in Produkt 1 sein
    ob_1 = mo.order_books[1]
    assert len(ob_1) == 1
    print(f"✅ Order in OrderBook von Produkt 1: {len(ob_1)} Orders")
    
    # Produkt 2 sollte leer sein
    ob_2 = mo.order_books[2]
    assert len(ob_2) == 0
    print(f"✅ OrderBook von Produkt 2 leer: {len(ob_2)} Orders")


def test_matching_across_products():
    """Test Matching innerhalb eines Produkts."""
    print("\n=== Test 6: Matching innerhalb Produkt ===")
    
    products = []
    for i in range(2):
        product = create_single_product(
            product_id=i,
            delivery_start=1440  # GLEICHE Lieferzeit
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    mo.open_products(t=0)
    
    # Resting order in Produkt 0: SELL 51.0
    resting = Order(
        id=0,
        agent_id=1,
        side=Side.SELL,
        price=51.0,
        volume=10.0,
        product_id=0,
        time_in_force=TimeInForce.GTC
    )
    mo.process_order(resting, t=100)
    
    # Incoming order in Produkt 0: BUY 52.0 (crosses)
    incoming = Order(
        id=0,
        agent_id=2,
        side=Side.BUY,
        price=52.0,
        volume=10.0,
        product_id=0,
        time_in_force=TimeInForce.GTC
    )
    trades = mo.process_order(incoming, t=101)
    
    # Sollte matchen
    assert len(trades) == 1
    assert trades[0].volume == 10.0
    assert trades[0].price == 51.0
    assert trades[0].product_id == 0
    print(f"✅ Trade in Produkt 0: {trades[0].volume} MW @ {trades[0].price}")
    
    # Buch sollte leer sein
    assert len(mo.order_books[0]) == 0
    print(f"✅ OrderBook 0 nach Match leer")


def test_cancel_agent_orders():
    """Test cancel_agent_orders() über mehrere Produkte."""
    print("\n=== Test 7: cancel_agent_orders() ===")
    
    products = []
    for i in range(3):
        product = create_single_product(
            product_id=i,
            delivery_start=1440  # GLEICHE Lieferzeit
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    mo.open_products(t=0)
    
    # Agent 1: Orders in Produkt 0, 1, 2
    orders = [
        Order(0, 1, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC),
        Order(0, 1, Side.BUY, 48.0, 5.0, 1, TimeInForce.GTC),
        Order(0, 1, Side.SELL, 51.0, 15.0, 2, TimeInForce.GTC),
    ]
    
    for order in orders:
        mo.process_order(order, t=100)
    
    assert mo.total_orders() == 3
    print(f"✅ {mo.total_orders()} Orders von Agent 1 platziert")
    
    # Lösche alle Orders von Agent 1
    cancelled = mo.cancel_agent_orders(agent_id=1)
    
    assert cancelled == 3
    assert mo.total_orders() == 0
    print(f"✅ {cancelled} Orders von Agent 1 gelöscht")
    
    # Teste produkt-spezifische Löschung
    orders2 = [
        Order(0, 2, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC),
        Order(0, 2, Side.BUY, 48.0, 5.0, 1, TimeInForce.GTC),
    ]
    for order in orders2:
        mo.process_order(order, t=100)
    
    # Lösche nur in Produkt 0
    cancelled = mo.cancel_agent_orders(agent_id=2, product_id=0)
    assert cancelled == 1
    assert len(mo.order_books[0]) == 0
    assert len(mo.order_books[1]) == 1
    print(f"✅ Produkt-spezifische Löschung funktioniert")


def test_get_public_info():
    """Test get_public_info() für mehrere Produkte."""
    print("\n=== Test 8: get_public_info() ===")
    
    products = []
    for i in range(3):
        product = create_single_product(
            product_id=i,
            delivery_start=1440  # GLEICHE Lieferzeit
        )
        products.append(product)
    
    mo = MultiProductMarketOperator.from_products(products)
    mo.open_products(t=0)
    
    # Füge Orders hinzu
    orders = [
        Order(0, 1, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC),
        Order(0, 1, Side.SELL, 51.0, 15.0, 0, TimeInForce.GTC),
        Order(0, 2, Side.BUY, 48.0, 5.0, 1, TimeInForce.GTC),
    ]
    for order in orders:
        mo.process_order(order, t=100)
    
    # Hole Public Info für alle offenen Produkte
    public_info = mo.get_public_info(t=100)
    
    assert len(public_info) == 3
    print(f"✅ Public Info für {len(public_info)} Produkte")
    
    # Überprüfe Produkt 0
    info_0 = public_info[0]
    assert info_0.tob.best_bid_price == 49.0
    assert info_0.tob.best_ask_price == 51.0
    assert info_0.product.product_id == 0
    print(f"✅ Produkt 0: bid={info_0.tob.best_bid_price}, ask={info_0.tob.best_ask_price}")
    
    # Hole Public Info nur für bestimmte Produkte
    public_info_subset = mo.get_public_info(t=100, product_ids=[0, 1])
    assert len(public_info_subset) == 2
    assert 2 not in public_info_subset
    print(f"✅ Subset-Abfrage funktioniert")


def test_gate_close_clears_orders():
    """Test dass update_product_status Orders löscht bei Gate-Close."""
    print("\n=== Test 9: Gate-Close löscht Orders ===")
    
    product = create_single_product(
        product_id=0,
        delivery_start=1440,
        gate_close_offset_minutes=60
    )
    
    mo = MultiProductMarketOperator.from_products([product])
    mo.open_products(t=0)
    
    # Füge Orders hinzu
    orders = [
        Order(0, 1, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC),
        Order(0, 1, Side.SELL, 51.0, 15.0, 0, TimeInForce.GTC),
    ]
    for order in orders:
        mo.process_order(order, t=100)
    
    assert len(mo.order_books[0]) == 2
    print(f"✅ 2 Orders im Buch vor Gate-Close")
    
    # gate_close = 1440 - 60 = 1380
    closed = mo.update_product_status(t=1380)
    
    assert 0 in closed
    assert len(mo.order_books[0]) == 0
    print(f"✅ Alle Orders gelöscht bei Gate-Close")


if __name__ == "__main__":
    print("=" * 60)
    print("MULTI-PRODUCT MARKET OPERATOR TESTS")
    print("=" * 60)
    
    test_create_multi_product_mo()
    test_open_products()
    test_open_products_staggered()
    test_get_open_products()
    test_update_product_status()
    test_process_order_routing()
    test_matching_across_products()
    test_cancel_agent_orders()
    test_get_public_info()
    test_gate_close_clears_orders()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE 10 TESTS BESTANDEN!")
    print("=" * 60)