"""
Einfaches Plot-Skript für die Simulationsergebnisse.

- liest eine CSV aus ./results/
- plottet Midprice, Spread und Trades je Zeitschritt
"""

import csv
import os

import matplotlib.pyplot as plt


def _parse_float_maybe(value: str):
    """
    Hilfsfunktion:
    - leere Strings -> None
    - Dezimal-Komma -> Dezimal-Punkt
    """
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() == "none":
        return None
    # deutsches Dezimaltrennzeichen wieder in Punkt umwandeln
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def load_log_from_csv(path: str):
    """Lädt das Log aus einer CSV-Datei in einfache Listen."""
    t = []
    midprice = []
    spread = []
    trades = []

    with open(path, newline="", encoding="utf-8") as f:
        # WICHTIG: Semikolon als Separator
        reader = csv.DictReader(f, delimiter=";")

        # Optional: zum Debuggen könntest du dir das ansehen:
        # print("Felder:", reader.fieldnames)

        for row in reader:
            # Zeitschritt
            t_str = row.get("t", "").strip()
            if t_str == "":
                continue
            t.append(int(t_str))

            # Midprice & Spread können leer sein
            mp = _parse_float_maybe(row.get("midprice", ""))
            sp = _parse_float_maybe(row.get("spread", ""))

            midprice.append(mp)
            spread.append(sp)

            # Trades sind Ganzzahlen
            tr_str = row.get("trades", "0").strip()
            trades.append(int(tr_str) if tr_str else 0)

    return t, midprice, spread, trades


def plot_results(csv_path: str):
    t, midprice, spread, trades = load_log_from_csv(csv_path)

    # Midprice (nur Punkte mit Wert)
    t_mp = [ti for ti, mp in zip(t, midprice) if mp is not None]
    mp_vals = [mp for mp in midprice if mp is not None]

    # Spread (nur Punkte mit Wert)
    t_sp = [ti for ti, sp in zip(t, spread) if sp is not None]
    sp_vals = [sp for sp in spread if sp is not None]

    # --- Plot 1: Midprice ---
    plt.figure()
    plt.plot(t_mp, mp_vals)
    plt.xlabel("t")
    plt.ylabel("Midprice")
    plt.title("Midprice über die Zeit")
    plt.grid(True)

    # --- Plot 2: Spread ---
    plt.figure()
    plt.plot(t_sp, sp_vals)
    plt.xlabel("t")
    plt.ylabel("Spread (Ask - Bid)")
    plt.title("Spread über die Zeit")
    plt.grid(True)

    # --- Plot 3: Trades pro Zeitschritt ---
    plt.figure()
    plt.bar(t, trades)
    plt.xlabel("t")
    plt.ylabel("Anzahl Trades")
    plt.title("Trades pro Zeitschritt")
    plt.grid(True)

    plt.show()


if __name__ == "__main__":
    # Pfad zur gewünschten CSV (z.B. letztes Ergebnis)
    # Achtung: relativ zum Projekt-Root, von dem du das Script startest
    csv_path = os.path.join("results", "sim_log_seed_42.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(
            f"CSV nicht gefunden: {csv_path}. "
            "Bitte zuerst run_simulation.py ausführen."
        )

    plot_results(csv_path)
