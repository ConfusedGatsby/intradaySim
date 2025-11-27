from intraday_abm.core.product import create_single_product, ProductStatus
from intraday_abm.core.product_aware_order_book import ProductAwareOrderBook
from intraday_abm.core.order import Order
from intraday_abm.core.types import Side, TimeInForce


def test_product_aware_order_book_basic():
    """Test grundlegende Funktionalität."""
    print("\n=== Test 1: Grundlegende Funktionalität ===")
    
    # Erstelle Produkt
    product = create_single_product(
        product_id=0,
        delivery_start=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60,
        da_price=50.0
    )
    
    # Öffne das Produkt
    product = product.update_status(ProductStatus.OPEN)
    
    # Erstelle OrderBook
    ob = ProductAwareOrderBook(product=product)
    
    print(f"✅ ProductAwareOrderBook erstellt: {ob}")
    assert ob.product.product_id == 0
    assert len(ob) == 0
    print(f"✅ Leeres Buch: {len(ob)} Orders")


def test_is_open_validation():
    """Test is_open() und validate_order_time()."""
    print("\n=== Test 2: is_open() Validierung ===")
    
    product = create_single_product(
        product_id=0,
        delivery_start=1440,
        gate_open_offset_hours=24,
        gate_close_offset_minutes=60
    )
    
    # gate_open = 1440 - 24*60 = 0
    # gate_close = 1440 - 60 = 1380
    
    # Status PENDING: nicht offen
    ob = ProductAwareOrderBook(product=product)
    assert ob.is_open(100) == False
    print(f"✅ PENDING Status: is_open(100) = False")
    
    # Status OPEN: innerhalb Fenster offen
    product_open = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product_open)
    assert ob.is_open(100) == True
    print(f"✅ OPEN Status: is_open(100) = True")
    
    # Außerhalb Gate-Close: nicht offen
    assert ob.is_open(1400) == False
    print(f"✅ Nach Gate-Close: is_open(1400) = False")
    
    # Status CLOSED: nicht offen
    product_closed = product_open.update_status(ProductStatus.CLOSED)
    ob = ProductAwareOrderBook(product=product_closed)
    assert ob.is_open(100) == False
    print(f"✅ CLOSED Status: is_open(100) = False")


def test_add_order():
    """Test add_order mit und ohne Validierung."""
    print("\n=== Test 3: add_order() ===")
    
    product = create_single_product(product_id=0)
    product = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product)
    
    # Order erstellen
    order = Order(
        id=1,
        agent_id=1,
        side=Side.BUY,
        price=49.0,
        volume=10.0,
        product_id=0,
        time_in_force=TimeInForce.GTC,
        timestamp=100
    )
    
    # Ohne Validierung hinzufügen
    ob.add_order(order, validate_time=False)
    assert len(ob) == 1
    print(f"✅ Order ohne Validierung hinzugefügt: {len(ob)} Orders")
    
    # Mit Validierung hinzufügen (sollte funktionieren, da OPEN)
    order2 = Order(
        id=2,
        agent_id=1,
        side=Side.SELL,
        price=51.0,
        volume=15.0,
        product_id=0,
        time_in_force=TimeInForce.GTC,
        timestamp=100
    )
    ob.add_order(order2, validate_time=True, t=100)
    assert len(ob) == 2
    print(f"✅ Order mit Validierung hinzugefügt: {len(ob)} Orders")
    
    # Falsches product_id sollte Fehler werfen
    wrong_order = Order(
        id=3,
        agent_id=2,
        side=Side.BUY,
        price=50.0,
        volume=5.0,
        product_id=999,  # Falsches Produkt!
        time_in_force=TimeInForce.GTC
    )
    
    try:
        ob.add_order(wrong_order)
        assert False, "Sollte ValueError werfen"
    except ValueError as e:
        print(f"✅ Falsches product_id erkannt: {e}")


def test_best_bid_ask():
    """Test best_bid() und best_ask()."""
    print("\n=== Test 4: best_bid() und best_ask() ===")
    
    product = create_single_product(product_id=0)
    product = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product)
    
    # Füge mehrere Orders hinzu
    orders = [
        Order(1, 1, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC, 100),
        Order(2, 1, Side.BUY, 48.0, 5.0, 0, TimeInForce.GTC, 101),
        Order(3, 2, Side.SELL, 51.0, 15.0, 0, TimeInForce.GTC, 102),
        Order(4, 2, Side.SELL, 52.0, 20.0, 0, TimeInForce.GTC, 103),
    ]
    
    for order in orders:
        ob.add_order(order)
    
    # Best bid sollte 49.0 sein (höchster Preis)
    best_bid = ob.best_bid()
    assert best_bid is not None
    assert best_bid.price == 49.0
    print(f"✅ best_bid: {best_bid.price}")
    
    # Best ask sollte 51.0 sein (niedrigster Preis)
    best_ask = ob.best_ask()
    assert best_ask is not None
    assert best_ask.price == 51.0
    print(f"✅ best_ask: {best_ask.price}")


def test_remove_orders_by_agent():
    """Test remove_orders_by_agent()."""
    print("\n=== Test 5: remove_orders_by_agent() ===")
    
    product = create_single_product(product_id=0)
    product = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product)
    
    # Agent 1: 3 Orders
    # Agent 2: 2 Orders
    orders = [
        Order(1, 1, Side.BUY, 49.0, 10.0, 0, TimeInForce.GTC, 100),
        Order(2, 1, Side.BUY, 48.0, 5.0, 0, TimeInForce.GTC, 101),
        Order(3, 1, Side.SELL, 51.0, 15.0, 0, TimeInForce.GTC, 102),
        Order(4, 2, Side.BUY, 47.0, 20.0, 0, TimeInForce.GTC, 103),
        Order(5, 2, Side.SELL, 52.0, 25.0, 0, TimeInForce.GTC, 104),
    ]
    
    for order in orders:
        ob.add_order(order)
    
    assert len(ob) == 5
    print(f"✅ 5 Orders hinzugefügt: {len(ob)} Orders")
    
    # Entferne alle Orders von Agent 1
    removed = ob.remove_orders_by_agent(agent_id=1)
    assert removed == 3
    assert len(ob) == 2
    print(f"✅ {removed} Orders von Agent 1 entfernt, {len(ob)} übrig")
    
    # Übrige Orders sollten nur von Agent 2 sein
    for price_level in list(ob.bids.values()) + list(ob.asks.values()):
        for order in price_level:
            assert order.agent_id == 2


def test_matching():
    """Test match_order() Logik."""
    print("\n=== Test 6: match_order() ===")
    
    product = create_single_product(product_id=0)
    product = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product)
    
    # Resting order: SELL 51.0, 10 MW
    resting = Order(1, 1, Side.SELL, 51.0, 10.0, 0, TimeInForce.GTC, 100)
    ob.add_order(resting)
    
    # Incoming order: BUY 52.0, 15 MW (crosses!)
    incoming = Order(2, 2, Side.BUY, 52.0, 15.0, 0, TimeInForce.GTC, 101)
    
    trades = ob.match_order(incoming, t=101)
    
    # Sollte einen Trade geben: 10 MW @ 51.0 (pay-as-bid)
    assert len(trades) == 1
    assert trades[0].volume == 10.0
    assert trades[0].price == 51.0  # Preis der liegenden Order
    print(f"✅ Trade ausgeführt: {trades[0].volume} MW @ {trades[0].price}")
    
    # Resting order sollte entfernt sein
    assert len(ob) == 0
    print(f"✅ Resting order entfernt, Buch leer")
    
    # Incoming order sollte 5 MW übrig haben
    assert incoming.volume == 5.0
    print(f"✅ Incoming order hat noch {incoming.volume} MW übrig")


def test_clear_all_orders():
    """Test clear_all_orders() (Gate-Close)."""
    print("\n=== Test 7: clear_all_orders() ===")
    
    product = create_single_product(product_id=0)
    product = product.update_status(ProductStatus.OPEN)
    ob = ProductAwareOrderBook(product=product)
    
    # Füge Orders hinzu
    orders = [
        Order(1, 1, Side.BUY, 49.0, 10.0, 0),
        Order(2, 1, Side.SELL, 51.0, 15.0, 0),
        Order(3, 2, Side.BUY, 48.0, 20.0, 0),
    ]
    for order in orders:
        ob.add_order(order)
    
    assert len(ob) == 3
    print(f"✅ 3 Orders im Buch")
    
    # Lösche alle
    cleared = ob.clear_all_orders()
    assert cleared == 3
    assert len(ob) == 0
    print(f"✅ {cleared} Orders gelöscht, Buch leer")


if __name__ == "__main__":
    print("=" * 60)
    print("PRODUKTAWARE ORDERBOOK TESTS")
    print("=" * 60)
    
    test_product_aware_order_book_basic()
    test_is_open_validation()
    test_add_order()
    test_best_bid_ask()
    test_remove_orders_by_agent()
    test_matching()
    test_clear_all_orders()
    
    print("\n" + "=" * 60)
    print("🎉 ALLE TESTS BESTANDEN!")
    print("=" * 60)