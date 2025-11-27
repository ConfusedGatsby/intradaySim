from __future__ import annotations

from dataclasses import dataclass
from typing import List

from intraday_abm.core.order import Order, Trade
from intraday_abm.core.multi_product_order_book import MultiProductOrderBook
from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.types import Side


@dataclass
class MarketOperator:
    """Verwaltet das Orderbuch und fuehrt Matching aus (Pay-as-Bid, Price-Time-Priority)."""

    order_book: OrderBook
    next_order_id: int = 1

    def _assign_order_id(self, order: Order, time: int) -> Order:
        order.id = self.next_order_id
        self.next_order_id += 1
        order.timestamp = time
        return order

    def _get_book_for_product(self, product_id: int):
        if isinstance(self.order_book, MultiProductOrderBook):
            return self.order_book.get_book(product_id)
        return self.order_book

    # Oeffentliche API ---------------------------------------------------------

    def process_order(self, order: Order, time: int) -> List[Trade]:
        """
        Nimmt eine neue Order entgegen, weist eine ID zu und matched diese
        gegen das bestehende Orderbuch.
        """
        self._assign_order_id(order, time)

        book = self._get_book_for_product(order.product_id)

        if order.side == Side.BUY:
            trades = self._match_buy(order, time, book)
        else:
            trades = self._match_sell(order, time, book)

        # Falls noch Restvolumen vorhanden ist und GTC: ins Buch legen
        if order.volume > 0 and order.time_in_force is not None:
            from intraday_abm.core.types import TimeInForce  # vermeiden von Zyklusimport
            if order.time_in_force == TimeInForce.GTC:
                book.add_order(order)

        return trades

    def cancel_agent_orders(self, agent_id: int) -> None:
        """Loescht alle offenen Orders eines Agenten aus dem Orderbuch."""
        if isinstance(self.order_book, MultiProductOrderBook):
            for book in self.order_book.books.values():
                book.remove_orders_by_agent(agent_id)
        else:
            self.order_book.remove_orders_by_agent(agent_id)

    def get_tob(self, product_id: int = 0) -> dict:
        """
        Gibt das aktuelle Top-of-Book als Dict zurueck:
        {
            "best_bid_price": float | None,
            "best_ask_price": float | None
        }
        """
        book = self._get_book_for_product(product_id)

        best_bid = book.best_bid()
        best_ask = book.best_ask()

        return {
            "best_bid_price": best_bid.price if best_bid else None,
            "best_ask_price": best_ask.price if best_ask else None,
        }

    # Interne Matching-Logik --------------------------------------------------

    def _match_buy(self, incoming: Order, time: int, book: OrderBook) -> List[Trade]:
        """
        Matching fuer eingehende Kauforder (BUY).

        - matched gegen beste Asks
        - Preis = Preis der liegenden Order (Pay-as-Bid)
        - FIFO innerhalb eines Preislevels (durch OrderBook sichergestellt)
        """
        trades: List[Trade] = []

        while incoming.volume > 0:
            best_ask = book.best_ask()
            if best_ask is None:
                break

            # Crossing-Bedingung: Buy-Preis >= Ask-Preis
            if incoming.price < best_ask.price:
                break

            traded_volume = min(incoming.volume, best_ask.volume)
            trade_price = best_ask.price  # Pay-as-Bid -> Preis der liegenden Order

            # Trade-Objekt mit Order- und Agent-IDs
            tr = Trade(
                price=trade_price,
                volume=traded_volume,
                buy_order_id=incoming.id,
                sell_order_id=best_ask.id,
                buy_agent_id=incoming.agent_id,
                sell_agent_id=best_ask.agent_id,
                time=time,
            )
            trades.append(tr)

            # Volumen anpassen
            incoming.volume -= traded_volume
            best_ask.volume -= traded_volume

            # Liegende Order ggf. entfernen
            if best_ask.volume <= 0:
                book.remove_order(best_ask)

        return trades

    def _match_sell(self, incoming: Order, time: int, book: OrderBook) -> List[Trade]:
        """
        Matching fuer eingehende Verkauforder (SELL).

        - matched gegen beste Bids
        - Preis = Preis der liegenden Order (Pay-as-Bid)
        - FIFO innerhalb eines Preislevels (durch OrderBook sichergestellt)
        """
        trades: List[Trade] = []

        while incoming.volume > 0:
            best_bid = book.best_bid()
            if best_bid is None:
                break

            # Crossing-Bedingung: Sell-Preis <= Bid-Preis
            if incoming.price > best_bid.price:
                break

            traded_volume = min(incoming.volume, best_bid.volume)
            trade_price = best_bid.price  # Pay-as-Bid -> Preis der liegenden Order

            tr = Trade(
                price=trade_price,
                volume=traded_volume,
                buy_order_id=best_bid.id,
                sell_order_id=incoming.id,
                buy_agent_id=best_bid.agent_id,
                sell_agent_id=incoming.agent_id,
                time=time,
            )
            trades.append(tr)

            incoming.volume -= traded_volume
            best_bid.volume -= traded_volume

            if best_bid.volume <= 0:
                book.remove_order(best_bid)

        return trades