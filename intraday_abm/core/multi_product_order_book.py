from __future__ import annotations

from .order_book import OrderBook


class MultiProductOrderBook:
    """Wrapper für mehrere OrderBooks (Vorbereitung für Multi-Produkt-Support)."""

    def __init__(self, product_ids: list[int]):
        self.books = {pid: OrderBook(product_id=pid) for pid in product_ids}

    def get_book(self, product_id: int) -> OrderBook:
        return self.books[product_id]

    def __len__(self):
        return sum(len(book) for book in self.books.values())