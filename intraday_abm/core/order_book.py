from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .order import Order
from .types import Side


@dataclass
class OrderBook:
    """
    Einfaches Limit Order Book für ein Produkt.

    Bids und Asks werden als Listen von Orders gehalten und nach
    Preis-Time-Priority sortiert:
    - beste Bid = höchster Preis, bei Gleichstand ältere Order zuerst
    - beste Ask = niedrigster Preis, bei Gleichstand ältere Order zuerst
    """
    product_id: int
    bids: List[Order] = field(default_factory=list)
    asks: List[Order] = field(default_factory=list)

    def __len__(self) -> int:
        """Anzahl noch offener Orders im Buch."""
        return len(self.bids) + len(self.asks)

    def add_order(self, order: Order) -> None:
        """
        Fügt eine neue Order ins Buch ein und sortiert nach Price-Time-Priority.
        """
        book_side = self.bids if order.side == Side.BUY else self.asks
        book_side.append(order)

        if order.side == Side.BUY:
            # zuerst nach Preis absteigend, dann Zeit aufsteigend
            book_side.sort(key=lambda o: (-o.price, o.time))
        else:
            # zuerst nach Preis aufsteigend, dann Zeit aufsteigend
            book_side.sort(key=lambda o: (o.price, o.time))

    def best_bid(self) -> Optional[Order]:
        """Gibt die beste Bid-Order zurück oder None, falls keine vorhanden ist."""
        return self.bids[0] if self.bids else None

    def best_ask(self) -> Optional[Order]:
        """Gibt die beste Ask-Order zurück oder None, falls keine vorhanden ist."""
        return self.asks[0] if self.asks else None

    def remove_order(self, order: Order) -> None:
        """Entfernt eine Order aus dem Buch, falls vorhanden."""
        book_side = self.bids if order.side == Side.BUY else self.asks
        try:
            book_side.remove(order)
        except ValueError:
            # Wenn die Order nicht gefunden wird, ignorieren wir das still.
            pass
