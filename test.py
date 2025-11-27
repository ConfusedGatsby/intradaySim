"""Test für Schritt 3: TopOfBook Integration"""

from intraday_abm.core.types import TopOfBook
from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.market_operator import MarketOperator

def test_market_operator_tob():
    # Test: MarketOperator gibt TopOfBook zurück
    ob = OrderBook(product_id=0)
    mo = MarketOperator(order_book=ob)
    
    tob = mo.get_tob()
    
    # Sollte TopOfBook-Objekt sein
    assert isinstance(tob, TopOfBook), f"Expected TopOfBook, got {type(tob)}"
    print(f"✅ MarketOperator.get_tob() gibt TopOfBook zurück: {tob}")
    
    # Sollte None-Werte haben (leeres Buch)
    assert tob.best_bid_price is None
    assert tob.best_ask_price is None
    print(f"✅ Leeres Orderbuch korrekt: bid={tob.best_bid_price}, ask={tob.best_ask_price}")
    
    # Teste Methoden
    assert tob.midprice() is None
    assert tob.spread() is None
    assert tob.has_bid() == False
    assert tob.has_ask() == False
    print(f"✅ TopOfBook-Methoden funktionieren auf leerem Buch")
    
    print("\n🎉 ALLE TESTS BESTANDEN!")

if __name__ == "__main__":
    test_market_operator_tob()