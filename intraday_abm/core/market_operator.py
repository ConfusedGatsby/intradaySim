from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Optional

from .order_book import OrderBook
from .order import Order
from .types import Side, TimeInForce


@dataclass
class Trade:
    """
    Ausgeführter Handel zwischen einer Bid- und einer Ask-Order.
    """
    price: float
    volume: float
    buy_order_id: int
    sell_order_id: int
    time: int


@dataclass
class MarketOperator:
    """
    Zentraler Market Operator (MO).

    Verantwortlichkeiten:
    - Verwaltung des Orderbuchs
    - Vergabe von Order-IDs
    - Matching eingehender Orders gegen das Buch
    - Einhalten von Price-Time-Priority und Pay-as-Bid
    """
    order_book: OrderBook
    _next_order_id: int = 1

    def _assign_order_id(self, order: Order) -> None:
        """Vergibt eine eindeutige Order-ID, falls noch keine gesetzt ist."""
        if order.id < 0:
            order.id = self._next_order_id
            self._next_order_id += 1

    def process_order(self, order: Order, time: int) -> List[Trade]:
        """
        Verarbeitet eine eingehende Order:
        - vergibt ID und Zeit
        - matched gegen Gegenseite (Price-Time-Priority, Pay-as-Bid)
        - fügt Restvolumen ggf. ins Buch ein (bei GTC)
        """
        self._assign_order_id(order)
        order.time = time

        trades: List[Trade] = []

        # Bestimme Gegenseite
        book = self.order_book
        if order.side == Side.BUY:
            opposite = book.asks
            same_side = book.bids
        else:
            opposite = book.bids
            same_side = book.asks

        # Matching-Schleife, solange Crossing möglich ist
        while opposite and order.volume > 0:
            best = opposite[0]

            # Preis-Crossing-Bedingung
            if order.side == Side.BUY and order.price < best.price:
                break
            if order.side == Side.SELL and order.price > best.price:
                break

            # Pay-as-Bid: Preis der liegenden Order
            trade_price = best.price
            traded_volume = min(order.volume, best.volume)

            trades.append(
                Trade(
                    price=trade_price,
                    volume=traded_volume,
                    buy_order_id=order.id if order.side == Side.BUY else best.id,
                    sell_order_id=order.id if order.side == Side.SELL else best.id,
                    time=time,
                )
            )

            # Volumen anpassen
            order.volume -= traded_volume
            best.volume -= traded_volume

            # Voll gefüllte Gegenseite aus dem Buch entfernen
            if best.volume <= 0:
                opposite.pop(0)

        # Restvolumen bei GTC ins Buch einstellen
        if order.volume > 0 and order.tif == TimeInForce.GTC:
            book.add_order(order)

        return trades

    def cancel_agent_orders(self, agent_id: int) -> None:
        """
        Löscht alle Orders eines Agenten aus dem Orderbuch.
        Shinde-nah: Agent cancelt vor dem Platzieren neuer Orders.
        """
        bids = self.order_book.bids
        asks = self.order_book.asks

        self.order_book.bids = [o for o in bids if o.agent_id != agent_id]
        self.order_book.asks = [o for o in asks if o.agent_id != agent_id]

    def get_tob(self) -> Dict[str, Optional[float]]:
        """
        Gibt ein einfaches Top-of-Book-Objekt zurück:
        - beste Bid/Ask-Preise
        (optional erweiterbar um Volumen/VWAP, falls benötigt)
        """
        best_bid = self.order_book.best_bid()
        best_ask = self.order_book.best_ask()
        return {
            "best_bid_price": best_bid.price if best_bid else None,
            "best_ask_price": best_ask.price if best_ask else None,
        }

    def __len__(self) -> int:
        """Anzahl offener Orders im Orderbuch."""
        return len(self.order_book)
