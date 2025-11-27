from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from intraday_abm.core.order_book import OrderBook
from intraday_abm.core.order import Order
from intraday_abm.core.types import Side


@dataclass
class MultiProductOrderBook:
    """
    Container für mehrere produkt-spezifische Orderbücher.

    Idee:
    - Jedes Produkt d hat sein eigenes OrderBook(product_id=d).
    - Dieses Objekt hält eine Map product_id -> OrderBook.
    - Hilfsfunktionen vereinfachen das Routing von Orders.

    Damit kannst du:
    - in der Simulation über alle Produkte iterieren,
    - oder gezielt das Buch für ein Produkt holen.
    """
    books: Dict[int, OrderBook] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Fabrikmethoden
    # ------------------------------------------------------------------
    @classmethod
    def from_product_ids(cls, product_ids: Iterable[int]) -> MultiProductOrderBook:
        """
        Erzeugt ein MultiProductOrderBook mit einem leeren OrderBook
        für jedes übergebene Produkt.
        """
        obj = cls()
        for pid in product_ids:
            obj.books[pid] = OrderBook(product_id=pid)
        return obj

    # ------------------------------------------------------------------
    # Zugriff auf einzelne Orderbücher
    # ------------------------------------------------------------------
    def get_book(self, product_id: int) -> OrderBook:
        """
        Liefert das OrderBook für ein bestimmtes Produkt.
        Falls noch nicht vorhanden, wird es angelegt.
        """
        if product_id not in self.books:
            self.books[product_id] = OrderBook(product_id=product_id)
        return self.books[product_id]

    # ------------------------------------------------------------------
    # Convenience-Methoden fürs Routing von Orders
    # ------------------------------------------------------------------
    def add_order(self, order: Order) -> None:
        """
        Legt eine Order in das passende produkt-spezifische Orderbuch.
        """
        book = self.get_book(order.product_id)
        book.add_order(order)

    def remove_order(self, order: Order) -> None:
        """
        Entfernt eine Order aus dem passenden produkt-spezifischen Buch.
        """
        book = self.get_book(order.product_id)
        book.remove_order(order)

    def remove_orders_by_agent(self, agent_id: int, product_id: Optional[int] = None) -> None:
        """
        Entfernt alle offenen Orders eines Agenten.

        - Wenn product_id angegeben: nur in diesem Produkt.
        - Wenn None: in allen Produkten.
        """
        if product_id is not None:
            book = self.get_book(product_id)
            book.remove_orders_by_agent(agent_id)
        else:
            for book in self.books.values():
                book.remove_orders_by_agent(agent_id)

    # ------------------------------------------------------------------
    # Top-of-Book-Information
    # ------------------------------------------------------------------
    def best_bid(self, product_id: int) -> Optional[Order]:
        """
        Beste Bid-Order eines Produkts.
        """
        return self.get_book(product_id).best_bid()

    def best_ask(self, product_id: int) -> Optional[Order]:
        """
        Beste Ask-Order eines Produkts.
        """
        return self.get_book(product_id).best_ask()

    # ------------------------------------------------------------------
    # Buchgröße
    # ------------------------------------------------------------------
    def __len__(self) -> int:
        """
        Gesamtzahl offener Orders über alle Produkte.
        """
        return sum(len(book) for book in self.books.values())
