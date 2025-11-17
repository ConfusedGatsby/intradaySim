from dataclasses import dataclass, field
from typing import List, Dict
from .order_book import OrderBook
from .order import Order, Trade
from .types import Side, OrderStatus, TimeInForce


@dataclass
class MarketOperator:
    """
    Market Operator für das Mini-Shinde-Modell.

    Aufgaben:
    - verwaltet das OrderBook
    - führt Matching nach Price–Time Priority durch
    - setzt Pay-as-Bid-Preise (Preis = Preis der liegenden Order)
    - unterstützt Teilfüllungen und Restvolumen (GTC / IOC)
    """
    order_book: OrderBook
    trades: List[Trade] = field(default_factory=list)
    _next_trade_id: int = 0

    # -------------------------------------------------------------------------
    # Top-of-Book / Marktinfo
    # -------------------------------------------------------------------------
    def get_tob(self) -> Dict[str, float]:
        """
        Liefert ein einfaches Top-of-Book-Objekt:
        - best_bid_price, best_bid_volume
        - best_ask_price, best_ask_volume
        """
        bb = self.order_book.best_bid()
        ba = self.order_book.best_ask()
        return {
            "best_bid_price": bb.price if bb else None,
            "best_bid_volume": bb.volume if bb else 0.0,
            "best_ask_price": ba.price if ba else None,
            "best_ask_volume": ba.volume if ba else 0.0,
        }

    # -------------------------------------------------------------------------
    # Cancel-Handling (Shinde: Agent cancelt eigene Orders vor neuer Order)
    # -------------------------------------------------------------------------
    def cancel_agent_orders(self, agent_id: int) -> None:
        """
        Entfernt alle Orders eines Agents aus dem Orderbuch.

        Entspricht dem Verhalten im Shinde-Modell:
        Ein Agent, der in einem Zeitschritt aktiv ist, cancelt zunächst alle
        eigenen offenen Orders und submitet dann ggf. eine neue.
        """
        self.order_book.bids = [
            o for o in self.order_book.bids if o.agent_id != agent_id
        ]
        self.order_book.asks = [
            o for o in self.order_book.asks if o.agent_id != agent_id
        ]

    # -------------------------------------------------------------------------
    # Kern: Orderverarbeitung und Matching
    # -------------------------------------------------------------------------
    def process_order(self, incoming: Order, time: int) -> List[Trade]:
        """
        Verarbeitet eine eingehende Order:
        - Matching gegen die Gegenseite im LOB
        - Price–Time Priority
        - Pay-as-Bid (Preis = Preis der liegenden Order)
        - Teilfills
        - Restvolumen:
            * GTC: wird in das Buch gelegt
            * IOC: wird verworfen (status = CANCELLED)
        """
        trades_this_order: List[Trade] = []

        def match_against_book(aggr_order: Order) -> None:
            """
            Shinde-nahe Matching-Logik:
            - Aggressive Order (incoming) trifft auf best-ask bzw. best-bid.
            - Solange Preis-Crossing gilt und Volumen > 0, wird gematcht.
            """
            nonlocal trades_this_order
            book = self.order_book

            while aggr_order.volume > 1e-9:
                # Gegenseite bestimmen
                best_opp = (
                    book.best_ask() if aggr_order.side is Side.BUY
                    else book.best_bid()
                )
                if best_opp is None:
                    break  # keine Gegenseite im Buch

                # Preis-Crossing-Bedingung
                if aggr_order.side is Side.BUY:
                    if aggr_order.price < best_opp.price:
                        break
                else:  # SELL
                    if aggr_order.price > best_opp.price:
                        break

                # Handelsvolumen (Teilfills möglich)
                traded_volume = min(aggr_order.volume, best_opp.volume)

                # Pay-as-Bid: Preis = Preis der liegenden (älteren) Order
                trade_price = best_opp.price

                trade = Trade(
                    id=self._next_trade_id,
                    buy_order_id=(
                        aggr_order.id if aggr_order.side is Side.BUY else best_opp.id
                    ),
                    sell_order_id=(
                        best_opp.id if aggr_order.side is Side.BUY else aggr_order.id
                    ),
                    product_id=aggr_order.product_id,
                    price=trade_price,
                    volume=traded_volume,
                    time=time,
                )
                self._next_trade_id += 1
                self.trades.append(trade)
                trades_this_order.append(trade)

                # Volumen updaten
                aggr_order.volume -= traded_volume
                best_opp.volume -= traded_volume

                # Status der liegenden Order
                if best_opp.volume <= 1e-9:
                    best_opp.status = OrderStatus.FILLED
                    book.remove_order(best_opp)
                else:
                    best_opp.status = OrderStatus.PARTIALLY_FILLED

                # Status der aggressiven Order
                if aggr_order.volume <= 1e-9:
                    aggr_order.status = OrderStatus.FILLED
                    break
                else:
                    aggr_order.status = OrderStatus.PARTIALLY_FILLED

        # Matching durchführen
        match_against_book(incoming)

        # Restvolumen behandeln
        if incoming.volume > 1e-9:
            if incoming.tif is TimeInForce.GTC:
                # GTC: verbleibendes Volumen ins Buch einfügen
                self.order_book.add_order(incoming)
                incoming.status = OrderStatus.ACTIVE
            else:
                # IOC: verbleibendes Volumen wird nicht ins Buch gestellt
                incoming.status = OrderStatus.CANCELLED

        return trades_this_order

    # -------------------------------------------------------------------------
    # Debug / Utility
    # -------------------------------------------------------------------------
    def __repr__(self) -> str:
        return (f"MarketOperator(book={self.order_book}, "
                f"n_trades={len(self.trades)})")
