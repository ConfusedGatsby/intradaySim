from dataclasses import dataclass, field
from typing import List, Optional
from .order import Order
from .types import Side


@dataclass
class OrderBook:
    """
    Einfaches, Shinde-nahes Limit Order Book für EIN Produkt.

    Eigenschaften:
    - getrennte Listen für BID- und ASK-Orders
    - Price–Time Priority:
        * Bids:  sortiert nach Preis absteigend, dann Zeit aufsteigend
        * Asks:  sortiert nach Preis aufsteigend, dann Zeit aufsteigend
    - best_bid() / best_ask() liefern jeweils das Top-of-Book auf der Seite.
    """
    product_id: int = 0
    bids: List[Order] = field(default_factory=list)
    asks: List[Order] = field(default_factory=list)

    # --- Top-of-Book-Zugriffe -------------------------------------------------

    def best_bid(self) -> Optional[Order]:
        """Gibt die beste Kauforder (höchster Preis) zurück oder None."""
        return self.bids[0] if self.bids else None

    def best_ask(self) -> Optional[Order]:
        """Gibt die beste Verkauforder (niedrigster Preis) zurück oder None."""
        return self.asks[0] if self.asks else None

    # --- Mutationen -----------------------------------------------------------

    def add_order(self, order: Order) -> None:
        """
        Fügt eine Order in das Orderbuch ein und hält Price–Time Priority ein.
        Wird nur aufgerufen, wenn die Order NICHT vollständig gematcht wurde.
        """
        if order.side is Side.BUY:
            self.bids.append(order)
            # Preis absteigend, dann Zeit → FIFO innerhalb eines Preislevels
            self.bids.sort(key=lambda o: (-o.price, o.time, o.id))
        else:
            self.asks.append(order)
            # Preis aufsteigend, dann Zeit → FIFO innerhalb eines Preislevels
            self.asks.sort(key=lambda o: (o.price, o.time, o.id))

    def remove_order(self, order: Order) -> None:
        """Entfernt eine Order aus der jeweiligen Seite des Orderbuchs."""
        container = self.bids if order.side is Side.BUY else self.asks
        try:
            container.remove(order)
        except ValueError:
            # Falls die Order schon raus ist (z.B. durch doppelte Behandlung),
            # ignorieren wir das still.
            pass

    # --- Utility / Debugging --------------------------------------------------

    def __len__(self) -> int:
        """Gesamtanzahl der im Orderbuch liegenden Orders."""
        return len(self.bids) + len(self.asks)

    def snapshot(self) -> dict:
        """
        Kleiner Snapshot des Buches für Debugging/Logging.
        Gibt nur Aggregates, kein komplettes Buch.
        """
        bb = self.best_bid()
        ba = self.best_ask()
        return {
            "product_id": self.product_id,
            "n_bids": len(self.bids),
            "n_asks": len(self.asks),
            "best_bid_price": bb.price if bb else None,
            "best_bid_volume": bb.volume if bb else 0.0,
            "best_ask_price": ba.price if ba else None,
            "best_ask_volume": ba.volume if ba else 0.0,
        }

    def __repr__(self) -> str:
        return (f"OrderBook(product_id={self.product_id}, "
                f"n_bids={len(self.bids)}, n_asks={len(self.asks)})")
