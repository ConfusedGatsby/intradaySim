from __future__ import annotations

import csv
import os
from typing import Any, Dict, List


def save_log_to_csv(log: Dict[str, List[Any]], filepath: str) -> None:
    """
    Speichert das Log-Dictionary als CSV mit:
    - Semikolon als Trennzeichen (Excel-kompatibel)
    - Dezimaltrennzeichen ',' statt '.'
    """

    # Zielordner anlegen, falls nicht vorhanden
    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Spaltennamen
    fieldnames = list(log.keys())

    # Anzahl Zeilen anhand der ersten Spalte
    n_rows = len(next(iter(log.values())))

    # CSV schreiben
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()

        for i in range(n_rows):
            row = {key: log[key][i] for key in fieldnames}

            # Dezimalpunkt -> Komma konvertieren
            converted_row = {}
            for key, value in row.items():
                if isinstance(value, float):
                    # Float in String + "." -> ","
                    converted_row[key] = str(value).replace(".", ",")
                elif value is None:
                    # None -> leere Zelle
                    converted_row[key] = ""
                else:
                    converted_row[key] = value

            writer.writerow(converted_row)
