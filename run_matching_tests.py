"""
Einfache Einzelfall-Tests für die Matching-Logik des Orderbuchs.

Getestet werden:
- Price-Time-Priority
- Pay-as-Bid (Preis der liegenden Order)
- korrekte Volumenreduktion
- Teilfüllungen
- FIFO innerhalb eines Preislevels
"""

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.market_operator import MarketOperator
from intraday_abm.core.order import Order
from intraday_abm.core.types import Side


def _assert_equal(name: str, actual, expected) -> bool:
    if actual != expected:
        print(f"[FAIL] {name}: expected={expected}, got={actual}")
        return False
    print(f"[OK]   {name}")
    return True


def test_pay_as_bid_and_partial_fill() -> bool:
    """
    Szenario:
    - Zwei Bids im Buch:
        Bid1: 10 @ 50 (ältere Order, besserer Preis)
        Bid2:  5 @ 49
    - Eingehende Ask: 8 @ 48 (aggressive Sell-Order)

    Erwartung:
    - Es entsteht genau 1 Trade
    - Trade-Preis = 50 (Preis der liegenden Bid1)  -> Pay-as-Bid
    - Trade-Volumen = 8
    - Restvolumen Bid1 = 2
    - Bid2 bleibt unverändert (5 @ 49)
    """

    ob = OrderBook(product_id=0)
    mo = MarketOperator(order_book=ob)

    # Zwei Bids ins Buch legen (nur Bids -> kein sofortiger Trade)
    bid1 = Order(
        id=1,
        agent_id=1,
        side=Side.BUY,
        price=50.0,
        volume=10.0,
        product_id=0,
    )
    bid2 = Order(
        id=2,
        agent_id=2,
        side=Side.BUY,
        price=49.0,
        volume=5.0,
        product_id=0,
    )

    mo.process_order(bid1, time=0)
    mo.process_order(bid2, time=1)

    # Aggressive Ask, der beide Bids preislich crossing könnte
    ask = Order(
        id=3,
        agent_id=3,
        side=Side.SELL,
        price=48.0,  # unter best bid -> crossing
        volume=8.0,
        product_id=0,
    )

    trades = mo.process_order(ask, time=2)

    ok = True
    ok &= _assert_equal("Anzahl Trades", len(trades), 1)

    if trades:
        trade = trades[0]
        ok &= _assert_equal("Trade-Preis (Pay-as-Bid)", trade.price, 50.0)
        ok &= _assert_equal("Trade-Volumen", trade.volume, 8.0)
        ok &= _assert_equal("Trade-Buyer-Order-ID", trade.buy_order_id, bid1.id)
        ok &= _assert_equal("Trade-Seller-Order-ID", trade.sell_order_id, ask.id)

    # Prüfen: Restvolumen Bid1 = 2, Bid2 unverändert = 5
    # Wir greifen direkt auf das Orderbuch zu
    bids = ob.bids  # Annahme: Liste von Orders, wie wir sie definiert haben

    # sortiert sollte an Index 0 die beste Bid liegen (Preis-Time-Priority)
    best_bid = bids[0]
    second_bid = bids[1]

    ok &= _assert_equal("Restvolumen Bid1", best_bid.volume, 2.0)
    ok &= _assert_equal("Bid1-Preis bleibt 50", best_bid.price, 50.0)
    ok &= _assert_equal("Bid2-Volumen unverändert", second_bid.volume, 5.0)
    ok &= _assert_equal("Bid2-Preis bleibt 49", second_bid.price, 49.0)

    return ok


def test_fifo_within_price_level() -> bool:
    """
    Szenario:
    - Zwei Bids mit gleichem Preis:
        BidA: 5 @ 50 (älter, kommt zuerst)
        BidB: 7 @ 50 (jünger)
    - Eingehende Ask: 10 @ 49 (crossing beide)

    Erwartung:
    - Zwei Trades:
        Trade1 füllt BidA vollständig (5 @ 50)
        Trade2 füllt BidB teilweise (5 von 7 @ 50)
    - Rest im Buch:
        ein Bid (BidB) mit Restvolumen 2 @ 50
    - Reihenfolge der Fills entspricht FIFO innerhalb des Preislevels.
    """

    ob = OrderBook(product_id=0)
    mo = MarketOperator(order_book=ob)

    bid_a = Order(
        id=10,
        agent_id=1,
        side=Side.BUY,
        price=50.0,
        volume=5.0,
        product_id=0,
    )
    bid_b = Order(
        id=11,
        agent_id=2,
        side=Side.BUY,
        price=50.0,
        volume=7.0,
        product_id=0,
    )

    mo.process_order(bid_a, time=0)
    mo.process_order(bid_b, time=1)

    ask = Order(
        id=12,
        agent_id=3,
        side=Side.SELL,
        price=49.0,
        volume=10.0,
        product_id=0,
    )

    trades = mo.process_order(ask, time=2)

    ok = True
    ok &= _assert_equal("Anzahl Trades (FIFO)", len(trades), 2)

    if len(trades) == 2:
        t1, t2 = trades

        # Erster Trade sollte BidA füllen
        ok &= _assert_equal("Trade1 Volumen (BidA)", t1.volume, 5.0)
        ok &= _assert_equal("Trade1 Buy-Order-ID (BidA)", t1.buy_order_id, bid_a.id)
        ok &= _assert_equal("Trade1 Preis", t1.price, 50.0)

        # Zweiter Trade sollte BidB teilweise füllen (5 von 7)
        ok &= _assert_equal("Trade2 Volumen (BidB-Teilfill)", t2.volume, 5.0)
        ok &= _assert_equal("Trade2 Buy-Order-ID (BidB)", t2.buy_order_id, bid_b.id)
        ok &= _assert_equal("Trade2 Preis", t2.price, 50.0)

    # Restvolumen im Orderbuch prüfen
    bids = ob.bids
    ok &= _assert_equal("Restliche Bids im Buch", len(bids), 1)
    if bids:
        remaining = bids[0]
        ok &= _assert_equal("Rest-Bid ist BidB", remaining.id, bid_b.id)
        ok &= _assert_equal("Restvolumen BidB", remaining.volume, 2.0)
        ok &= _assert_equal("Restpreis BidB", remaining.price, 50.0)

    return ok


def run_all_tests() -> None:
    print("== Matching-Tests starten ==\n")

    results = []
    results.append(("Pay-as-Bid & Partial Fill", test_pay_as_bid_and_partial_fill()))
    results.append(("FIFO innerhalb Preislevel", test_fifo_within_price_level()))

    print("\n== Zusammenfassung ==")
    all_ok = True
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"{name}: {status}")
        all_ok &= ok

    if all_ok:
        print("\nALLE TESTS BESTANDEN ✅")
    else:
        print("\nEINIGE TESTS SIND FEHLGESCHLAGEN ❌")


if __name__ == "__main__":
    run_all_tests()
