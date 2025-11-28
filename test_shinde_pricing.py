"""
Test Suite für Shinde-konforme NaivePricingStrategy

Testet die angepasste Implementation gegen die Shinde Formeln.
"""

import sys
sys.path.append('/home/claude')

from random import Random
from intraday_abm.core.types import PublicInfo, TopOfBook, Side, AgentPrivateInfo
from intraday_abm.agents.pricing_strategies import NaivePricingStrategy


# ============================================================================
# MOCK AGENT MIT LIMIT PRICES
# ============================================================================

class MockAgent:
    """Mock Agent für Tests."""
    
    def __init__(self, limit_buy=100.0, limit_sell=0.0):
        self.private_info = AgentPrivateInfo(
            effective_capacity=100.0,
            limit_buy=limit_buy,
            limit_sell=limit_sell
        )


# ============================================================================
# TESTS
# ============================================================================

def test_1_sell_price_range():
    """Test Equation 20-21: SELL price range computation."""
    print("\n" + "="*70)
    print("TEST 1: SELL Price Range (Equations 20-21)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=5,
        min_price=0.0,
        max_price=200.0
    )
    
    # Setup: bbp=48, bap=52, limit_sell=40
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    # Build SELL curve
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        total_volume=25.0
    )
    
    # According to Eq 20-21:
    # pi_min = max(bbp - pi_range, limit_sell) = max(48-5, 40) = max(43, 40) = 43
    # pi_max = max(bap + pi_range, limit_sell + pi_range) = max(52+5, 40+5) = max(57, 45) = 57
    
    prices = [p for p, v in curve]
    
    print(f"\nSetup:")
    print(f"  bbp = 48.0, bap = 52.0, pi_range = 5.0")
    print(f"  limit_sell = 40.0")
    
    print(f"\nShinde Formeln (Eq 20-21):")
    print(f"  π_min^sell = max(bbp - π_range, l_sell)")
    print(f"           = max(48 - 5, 40) = max(43, 40) = 43.0")
    print(f"  π_max^sell = max(bap + π_range, l_sell + π_range)")
    print(f"           = max(52 + 5, 40 + 5) = max(57, 45) = 57.0")
    
    print(f"\nErgebnis:")
    print(f"  Expected Range: [43.0, 57.0]")
    print(f"  Actual Range:   [{min(prices):.2f}, {max(prices):.2f}]")
    print(f"  Sample Prices:  {[f'{p:.2f}' for p in prices[:3]]}")
    
    assert all(43.0 <= p <= 57.0 for p in prices), f"❌ Prices out of range: {prices}"
    print(f"\n✅ SELL price range KORREKT!")


def test_2_buy_price_range():
    """Test Equation 22-23: BUY price range computation."""
    print("\n" + "="*70)
    print("TEST 2: BUY Price Range (Equations 22-23)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=5,
        min_price=0.0,
        max_price=200.0
    )
    
    # Setup: bbp=48, bap=52, limit_buy=60
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    # Build BUY curve
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.BUY,
        total_volume=25.0
    )
    
    # According to Eq 22-23:
    # pi_min = min(bbp - pi_range, limit_buy - pi_range) = min(48-5, 60-5) = min(43, 55) = 43
    # pi_max = min(bap + pi_range, limit_buy) = min(52+5, 60) = min(57, 60) = 57
    
    prices = [p for p, v in curve]
    
    print(f"\nSetup:")
    print(f"  bbp = 48.0, bap = 52.0, pi_range = 5.0")
    print(f"  limit_buy = 60.0")
    
    print(f"\nShinde Formeln (Eq 22-23):")
    print(f"  π_min^buy = min(bbp - π_range, l_buy - π_range)")
    print(f"          = min(48 - 5, 60 - 5) = min(43, 55) = 43.0")
    print(f"  π_max^buy = min(bap + π_range, l_buy)")
    print(f"          = min(52 + 5, 60) = min(57, 60) = 57.0")
    
    print(f"\nErgebnis:")
    print(f"  Expected Range: [43.0, 57.0]")
    print(f"  Actual Range:   [{min(prices):.2f}, {max(prices):.2f}]")
    print(f"  Sample Prices:  {[f'{p:.2f}' for p in prices[:3]]}")
    
    assert all(43.0 <= p <= 57.0 for p in prices), f"❌ Prices out of range: {prices}"
    print(f"\n✅ BUY price range KORREKT!")


def test_3_limit_sell_enforcement():
    """Test dass SELL orders limit_sell respektieren."""
    print("\n" + "="*70)
    print("TEST 3: Limit Price Enforcement (SELL)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=10,
        min_price=0.0,
        max_price=200.0
    )
    
    # Setup: Hoher limit_sell (55) sollte Mindestpreis setzen
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=70.0, limit_sell=55.0)  # HIGH limit_sell!
    
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        total_volume=25.0
    )
    
    # pi_min = max(48-5, 55) = max(43, 55) = 55
    # All SELL prices should be >= 55
    
    prices = [p for p, v in curve]
    
    print(f"\nSetup:")
    print(f"  bbp = 48.0, bap = 52.0, pi_range = 5.0")
    print(f"  limit_sell = 55.0 (HOCH!)")
    
    print(f"\nShinde Formel (Eq 20):")
    print(f"  π_min^sell = max(bbp - π_range, l_sell)")
    print(f"           = max(48 - 5, 55) = max(43, 55) = 55.0")
    
    print(f"\nErgebnis:")
    print(f"  Alle Preise >= 55.0? {all(p >= 55.0 for p in prices)}")
    print(f"  Min Price: {min(prices):.2f}")
    print(f"  Max Price: {max(prices):.2f}")
    
    assert all(p >= 55.0 for p in prices), f"❌ SELL prices below limit_sell!"
    print(f"\n✅ Limit price für SELL wird KORREKT enforced!")


def test_4_limit_buy_enforcement():
    """Test dass BUY orders limit_buy respektieren."""
    print("\n" + "="*70)
    print("TEST 4: Limit Price Enforcement (BUY)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=10,
        min_price=0.0,
        max_price=200.0
    )
    
    # Setup: Niedriger limit_buy (50) sollte Maximalpreis setzen
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=50.0, limit_sell=40.0)  # LOW limit_buy!
    
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.BUY,
        total_volume=25.0
    )
    
    # pi_max = min(52+5, 50) = min(57, 50) = 50
    # All BUY prices should be <= 50
    
    prices = [p for p, v in curve]
    
    print(f"\nSetup:")
    print(f"  bbp = 48.0, bap = 52.0, pi_range = 5.0")
    print(f"  limit_buy = 50.0 (NIEDRIG!)")
    
    print(f"\nShinde Formel (Eq 23):")
    print(f"  π_max^buy = min(bap + π_range, l_buy)")
    print(f"          = min(52 + 5, 50) = min(57, 50) = 50.0")
    
    print(f"\nErgebnis:")
    print(f"  Alle Preise <= 50.0? {all(p <= 50.0 for p in prices)}")
    print(f"  Min Price: {min(prices):.2f}")
    print(f"  Max Price: {max(prices):.2f}")
    
    assert all(p <= 50.0 for p in prices), f"❌ BUY prices above limit_buy!"
    print(f"\n✅ Limit price für BUY wird KORREKT enforced!")


def test_5_volume_distribution():
    """Test dass Volume gleichmäßig verteilt wird."""
    print("\n" + "="*70)
    print("TEST 5: Volume Distribution (Equation 27)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=5,
        min_price=0.0,
        max_price=200.0
    )
    
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    total_volume = 25.0
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        total_volume=total_volume
    )
    
    volumes = [v for p, v in curve]
    expected_vol = total_volume / 5  # 5 orders
    
    print(f"\nSetup:")
    print(f"  Total Volume: {total_volume} MW")
    print(f"  n_orders: 5")
    
    print(f"\nShinde Formel (Eq 27):")
    print(f"  v_j = v / n = {total_volume} / 5 = {expected_vol}")
    
    print(f"\nErgebnis:")
    print(f"  Expected vol/order: {expected_vol}")
    print(f"  Actual volumes:     {[f'{v:.2f}' for v in volumes]}")
    print(f"  Sum of volumes:     {sum(volumes):.2f}")
    
    assert len(volumes) == 5, f"❌ Wrong number of orders: {len(volumes)}"
    assert all(abs(v - expected_vol) < 0.01 for v in volumes), f"❌ Unequal distribution!"
    assert abs(sum(volumes) - total_volume) < 0.01, f"❌ Total volume mismatch!"
    
    print(f"\n✅ Volume wird GLEICHMÄSSIG verteilt!")


def test_6_buy_sell_overlapping_ranges():
    """Test dass BUY und SELL Ranges sich überlappen (wichtig für Trades!)."""
    print("\n" + "="*70)
    print("TEST 6: BUY-SELL Range Overlap (WICHTIG FÜR TRADES!)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=20,  # Mehr Orders für bessere Statistik
        min_price=0.0,
        max_price=200.0
    )
    
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    # SELL curve
    sell_curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        total_volume=50.0
    )
    
    # BUY curve
    buy_curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.BUY,
        total_volume=50.0
    )
    
    sell_prices = [p for p, v in sell_curve]
    buy_prices = [p for p, v in buy_curve]
    
    sell_min, sell_max = min(sell_prices), max(sell_prices)
    buy_min, buy_max = min(buy_prices), max(buy_prices)
    
    print(f"\nSetup:")
    print(f"  bbp = 48.0, bap = 52.0, pi_range = 5.0")
    print(f"  limit_buy = 60.0, limit_sell = 40.0")
    
    print(f"\nBEIDE Ranges sollten [43, 57] sein:")
    print(f"  SELL Range: [{sell_min:.2f}, {sell_max:.2f}]")
    print(f"  BUY Range:  [{buy_min:.2f}, {buy_max:.2f}]")
    
    # Check for overlap
    overlap_min = max(buy_min, sell_min)
    overlap_max = min(buy_max, sell_max)
    has_overlap = overlap_max > overlap_min
    
    print(f"\nOverlap:")
    print(f"  Overlap exists: {has_overlap}")
    if has_overlap:
        print(f"  Overlap range: [{overlap_min:.2f}, {overlap_max:.2f}]")
        print(f"  Overlap size:  {overlap_max - overlap_min:.2f} €")
    
    assert has_overlap, "❌ BUY and SELL ranges don't overlap! Keine Trades möglich!"
    assert overlap_max - overlap_min > 10.0, "❌ Overlap zu klein für zuverlässige Trades!"
    
    print(f"\n✅ BUY und SELL Ranges überlappen KORREKT! Trades sind möglich!")


def test_7_no_tob_fallback():
    """Test Fallback wenn kein ToB vorhanden."""
    print("\n" + "="*70)
    print("TEST 7: Fallback ohne ToB (leeres Order Book)")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=5,
        min_price=0.0,
        max_price=200.0
    )
    
    # Empty order book -> None values
    tob = TopOfBook(None, None, None, None)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    curve = strategy.build_price_volume_curve(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        total_volume=25.0
    )
    
    prices = [p for p, v in curve]
    
    print(f"\nSetup:")
    print(f"  bbp = None, bap = None (leeres Buch)")
    print(f"  DA Price = 50.0 (Fallback)")
    
    print(f"\nErgebnis:")
    print(f"  Orders erstellt: {len(prices)}")
    print(f"  Price range: [{min(prices):.2f}, {max(prices):.2f}]")
    
    assert len(prices) == 5, "❌ Should create orders even without ToB"
    print(f"\n✅ Fallback zu DA-Preis funktioniert!")


def test_8_compute_price_single():
    """Test compute_price() für einzelne Orders (VariableAgent)."""
    print("\n" + "="*70)
    print("TEST 8: compute_price() für einzelne Orders")
    print("="*70)
    
    strategy = NaivePricingStrategy(
        rng=Random(42),
        pi_range=5.0,
        n_segments=10,
        n_orders=5,
        min_price=0.0,
        max_price=200.0
    )
    
    tob = TopOfBook(48.0, 10.0, 52.0, 10.0)
    pub_info = PublicInfo(tob=tob, da_price=50.0)
    agent = MockAgent(limit_buy=60.0, limit_sell=40.0)
    
    # Sample multiple prices
    sell_prices = [strategy.compute_price(
        agent=agent,
        public_info=pub_info,
        side=Side.SELL,
        volume=10.0
    ) for _ in range(20)]
    
    buy_prices = [strategy.compute_price(
        agent=agent,
        public_info=pub_info,
        side=Side.BUY,
        volume=10.0
    ) for _ in range(20)]
    
    print(f"\nSELL Prices (20 samples):")
    print(f"  Range: [{min(sell_prices):.2f}, {max(sell_prices):.2f}]")
    print(f"  Expected: [43.0, 57.0]")
    
    print(f"\nBUY Prices (20 samples):")
    print(f"  Range: [{min(buy_prices):.2f}, {max(buy_prices):.2f}]")
    print(f"  Expected: [43.0, 57.0]")
    
    assert all(43.0 <= p <= 57.0 for p in sell_prices), "❌ SELL prices out of range"
    assert all(43.0 <= p <= 57.0 for p in buy_prices), "❌ BUY prices out of range"
    
    print(f"\n✅ compute_price() funktioniert KORREKT!")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "🔬"*35)
    print("   SHINDE NAIVE PRICING STRATEGY TEST SUITE")
    print("🔬"*35)
    
    try:
        test_1_sell_price_range()
        test_2_buy_price_range()
        test_3_limit_sell_enforcement()
        test_4_limit_buy_enforcement()
        test_5_volume_distribution()
        test_6_buy_sell_overlapping_ranges()
        test_7_no_tob_fallback()
        test_8_compute_price_single()
        
        print("\n" + "="*70)
        print("✅ ✅ ✅  ALL TESTS PASSED!  ✅ ✅ ✅")
        print("="*70)
        print("\n🎉 Die Shinde-konforme NaivePricingStrategy funktioniert perfekt!")
        print("🎯 Nächster Schritt: MultiProductPrivateInfo erweitern")
        print("="*70 + "\n")
        
        return True
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)