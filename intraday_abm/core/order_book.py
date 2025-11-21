from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from collections import defaultdict

from intraday_abm.core.order import Order
from intraday_abm.core.types import Side


@dataclass
class OrderBook:
    """
    Einfaches Orderbuch mit Price-Time-Priority (FIFO je Preislevel).

    Datenstruktur:
    - bids: Dict[price -> List[Order]] (höchster Preis zuerst)
    - asks: Dict[price -> List[Order]] (niedrigster Preis zuerst)
    """
    product_id: int
    bids: Dict[float, List[Order]] = field(default_factory=lambda: defaultdict(list))
    asks: Dict[float, List[Order]] = field(default_factory=lambda: defaultdict(list))

    # ---------------------------------------------------------
    # ORDER HINZUFÜGEN
    # ---------------------------------------------------------
    def add_order(self, order: Order) -> None:
        """Legt eine Order in das Orderbuch (entsprechendes Preislevel)."""
        if order.side == Side.BUY:
            self.bids[order.price].append(order)
        else:
            self.asks[order.price].append(order)

    # ---------------------------------------------------------
    # ORDER ENTFERNEN
    # ---------------------------------------------------------
    def remove_order(self, order: Order) -> None:
        """Entfernt eine konkrete Order aus dem jeweiligen Preislevel."""
        book = self.bids if order.side == Side.BUY else self.asks
        level = book.get(order.price, [])
        if order in level:
            level.remove(order)
        if not level:
            del book[order.price]

    # ---------------------------------------------------------
    # A2: ENTFERNEN ALLER ORDERS EINES AGENTEN
    # ---------------------------------------------------------
    def remove_orders_by_agent(self, agent_id: int) -> None:
        """
        Entfernt ALLE offenen Orders eines Agenten aus dem Orderbuch.
        Wird in A2 benötigt, weil in jedem Schritt 'cancel-first' erfolgt.
        """
        # BIDS
        for price in list(self.bids.keys()):
            new_list = [o for o in self.bids[price] if o.agent_id != agent_id]
            if new_list:
                self.bids[price] = new_list
            else:
                del self.bids[price]

        # ASKS
        for price in list(self.asks.keys()):
            new_list = [o for o in self.asks[price] if o.agent_id != agent_id]
            if new_list:
                self.asks[price] = new_list
            else:
                del self.asks[price]

    # ---------------------------------------------------------
    # TOP-OF-BOOK
    # ---------------------------------------------------------
    def best_bid(self) -> Optional[Order]:
        """Gibt die beste (höchste Preis) BUY-Order zurück."""
        if not self.bids:
            return None
        best_price = max(self.bids.keys())
        level = self.bids[best_price]
        return level[0] if level else None

    def best_ask(self) -> Optional[Order]:
        """Gibt die beste (niedrigste Preis) SELL-Order zurück."""
        if not self.asks:
            return None
        best_price = min(self.asks.keys())
        level = self.asks[best_price]
        return level[0] if level else None

    # ---------------------------------------------------------
    # LENGTH / SIZE
    # ---------------------------------------------------------
    def __len__(self) -> int:
        """Gesamtzahl offener Orders im Buch."""
        return sum(len(v) for v in self.bids.values()) + sum(len(v) for v in self.asks.values())
