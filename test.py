"""Einfacher Test für erweiterte types.py"""

from intraday_abm.core.types import TopOfBook, PublicInfo
from intraday_abm.core.product import create_single_product

def test_topofbook():
    # Test 1: TopOfBook mit Midprice und Spread
    tob = TopOfBook(
        best_bid_price=49.0,
        best_bid_volume=10.0,
        best_ask_price=51.0,
        best_ask_volume=15.0
    )
    
    # Midprice testen
    assert tob.midprice() == 50.0, f"Midprice sollte 50.0 sein, ist {tob.midprice()}"
    print(f"✅ Midprice: {tob.midprice()}")
    
    # Spread testen
    assert tob.spread() == 2.0, f"Spread sollte 2.0 sein, ist {tob.spread()}"
    print(f"✅ Spread: {tob.spread()}")
    
    # has_bid/has_ask testen
    assert tob.has_bid() == True
    assert tob.has_ask() == True
    print(f"✅ has_bid() und has_ask() funktionieren")
    
    # Test 2: Leeres TOB
    empty_tob = TopOfBook(None, None, None, None)
    assert empty_tob.midprice() is None
    assert empty_tob.spread() is None
    assert empty_tob.has_bid() == False
    print(f"✅ Leeres TOB behandelt")
    
    # Test 3: PublicInfo mit Product
    product = create_single_product(product_id=0)
    public_info = PublicInfo(
        tob=tob,
        da_price=50.0,
        product=product
    )
    
    assert public_info.da_price == 50.0
    assert public_info.time_to_gate_close(100) is not None
    print(f"✅ PublicInfo mit Product funktioniert")
    print(f"   Zeit bis Gate-Close bei t=100: {public_info.time_to_gate_close(100)}")
    
    print("\n🎉 ALLE TESTS BESTANDEN!")

if __name__ == "__main__":
    test_topofbook()