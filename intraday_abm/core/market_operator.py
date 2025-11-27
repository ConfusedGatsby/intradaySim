from __future__ import annotations

from dataclasses import dataclass
from typing import List

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.order import Order, Trade
from intraday_abm.core.types import Side, TimeInForce, TopOfBook


@dataclass
class MarketOperator:
    """
    Verwaltet das Orderbuch und führt Matching aus
    (Pay-as-Bid, Price-Time-Priority).

    Aktuell ist der MarketOperator noch an ein einzelnes OrderBook
    gebunden. Über `product_id` im OrderBook und in Order/Trade ist
    er aber bereits Multi-Produkt-fähig (z.B. ein MO je Produkt oder
    später via MultiProductOrderBook).
    """
    order_book: OrderBook
    next_order_id: int = 1

    # ------------------------------------------------------------------
    # Interne Hilfsfunktion: Order-ID & Timestamp setzen
    # ------------------------------------------------------------------
    def _assign_order_id(self, order: Order, time: int) -> Order:
        order.id = self.next_order_id
        self.next_order_id += 1
        order.timestamp = time
        return order

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------
    def process_order(self, order: Order, time: int) -> List[Trade]:
        """
        Nimmt eine neue Order entgegen, weist eine ID zu und matched sie
        gegen das bestehende Orderbuch.

        Rückgabe: Liste der in diesem Schritt erzeugten Trades.
        """
        self._assign_order_id(order, time)

        if order.side == Side.BUY:
            trades = self._match_buy(order, time)
        else:
            trades = self._match_sell(order, time)

        # Restvolumen ggf. ins Buch legen (GTC)
        if order.volume > 0 and order.time_in_force is not None:
            if order.time_in_force == TimeInForce.GTC:
                self.order_book.add_order(order)

        return trades

    def cancel_agent_orders(self, agent_id: int) -> None:
        """
        Löscht alle offenen Orders eines Agenten aus dem Orderbuch.
        (A2: 'cancel-first' Mechanismus).
        """
        self.order_book.remove_orders_by_agent(agent_id)

    def get_tob(self) -> TopOfBook:
        """
        Gibt das aktuelle Top-of-Book als TopOfBook-Objekt zurück.
        
        Returns:
            TopOfBook mit best_bid/ask prices und volumes
        """
        best_bid = self.order_book.best_bid()
        best_ask = self.order_book.best_ask()

        return TopOfBook(
            best_bid_price=best_bid.price if best_bid else None,
            best_bid_volume=best_bid.volume if best_bid else None,
            best_ask_price=best_ask.price if best_ask else None,
            best_ask_volume=best_ask.volume if best_ask else None,
        )

    # ------------------------------------------------------------------
    # Interne Matching-Logik
    # ------------------------------------------------------------------
    def _match_buy(self, incoming: Order, time: int) -> List[Trade]:
        """
        Matching für eingehende Kauforder (BUY).

        - matched gegen beste Asks
        - Preis = Preis der liegenden Order (Pay-as-Bid)
        - FIFO innerhalb eines Preislevels (durch OrderBook sichergestellt)
        """
        trades: List[Trade] = []
        product_id = self.order_book.product_id

        while incoming.volume > 0:
            best_ask = self.order_book.best_ask()
            if best_ask is None:
                break

            # Crossing-Bedingung: Buy-Preis >= Ask-Preis
            if incoming.price < best_ask.price:
                break

            traded_volume = min(incoming.volume, best_ask.volume)
            trade_price = best_ask.price  # Pay-as-Bid -> Preis der liegenden Order

            tr = Trade(
                product_id=product_id,
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
                self.order_book.remove_order(best_ask)

        return trades

    def _match_sell(self, incoming: Order, time: int) -> List[Trade]:
        """
        Matching für eingehende Verkaufsorder (SELL).

        - matched gegen beste Bids
        - Preis = Preis der liegenden Order (Pay-as-Bid)
        - FIFO innerhalb eines Preislevels (durch OrderBook sichergestellt)
        """
        trades: List[Trade] = []
        product_id = self.order_book.product_id

        while incoming.volume > 0:
            best_bid = self.order_book.best_bid()
            if best_bid is None:
                break

            # Crossing-Bedingung: Sell-Preis <= Bid-Preis
            if incoming.price > best_bid.price:
                break

            traded_volume = min(incoming.volume, best_bid.volume)
            trade_price = best_bid.price  # Pay-as-Bid -> Preis der liegenden Order

            tr = Trade(
                product_id=product_id,
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
                self.order_book.remove_order(best_bid)

        return trades