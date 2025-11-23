"""
export_agent_logs.py

Hilfsfunktionen zum Export der Agenten-Logs in CSV-Dateien.

Ziel:
- Pro Agent eine eigene CSV-Datei mit sauberem, tabellarischem Format.
- Zusätzlich eine zusammengefasste CSV über alle Agenten (optional),
  damit man alles mit einem Aufruf in pandas laden kann.
"""

from __future__ import annotations

import csv
import os
from typing import Dict, Any


def save_agent_logs(agent_logs: Dict[int, Dict[str, Any]], output_dir: str) -> None:
    """
    Speichert die Agenten-Logs als CSV-Dateien.

    Erwartete Struktur von `agent_logs` (kommt aus der Simulation):

        agent_logs[agent_id] = {
            "t": [0, 1, 2, ...],
            "agent_type": "RandomLiquidityAgent",
            "position": [...],
            "revenue": [...],
            "imbalance": [...],
            "da_position": [...],
            "capacity": [...],
        }

    Ausgabe:
    - Ordner: <output_dir>/agent_logs
    - Pro Agent: agent_<ID>_<TYPE>.csv
      Spalten: agent_id, agent_type, t, position, revenue,
               imbalance, da_position, capacity
    - Zusätzlich: agent_logs_all.csv mit allen Agenten (Long-Format)
    """
    logs_dir = os.path.join(output_dir, "agent_logs")
    os.makedirs(logs_dir, exist_ok=True)

    # Gemeinsame Sammelliste über alle Agenten (für eine Gesamt-CSV)
    all_rows = []

    for agent_id, data in agent_logs.items():
        # Sicheres Auslesen mit Defaults
        t_values = list(data.get("t", []))
        agent_type = data.get("agent_type", "Agent")

        positions = list(data.get("position", []))
        revenues = list(data.get("revenue", []))
        imbalances = list(data.get("imbalance", []))
        da_positions = list(data.get("da_position", []))
        capacities = list(data.get("capacity", []))

        # Robustheit: wir nehmen die Länge der Zeitachse als Referenz.
        # Falls Listen unterschiedlich lang sind, wird abgeschnitten.
        n = len(t_values)
        if n == 0:
            # nichts zu loggen
            continue

        fieldnames = [
            "agent_id",
            "agent_type",
            "t",
            "position",
            "revenue",
            "imbalance",
            "da_position",
            "capacity",
        ]

        # Dateiname inkl. Agententyp (gut lesbar)
        safe_type = str(agent_type).replace(" ", "_")
        filename = f"agent_{agent_id}_{safe_type}.csv"
        filepath = os.path.join(logs_dir, filename)

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i in range(n):
                row = {
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "t": t_values[i] if i < len(t_values) else i,
                    "position": positions[i] if i < len(positions) else None,
                    "revenue": revenues[i] if i < len(revenues) else None,
                    "imbalance": imbalances[i] if i < len(imbalances) else None,
                    "da_position": da_positions[i] if i < len(da_positions) else None,
                    "capacity": capacities[i] if i < len(capacities) else None,
                }
                writer.writerow(row)
                all_rows.append(row)

    # Gesamtdatei über alle Agenten (praktisch für pandas)
    if all_rows:
        all_path = os.path.join(logs_dir, "agent_logs_all.csv")
        fieldnames = [
            "agent_id",
            "agent_type",
            "t",
            "position",
            "revenue",
            "imbalance",
            "da_position",
            "capacity",
        ]
        with open(all_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"Agenten-Logs gespeichert unter: {logs_dir}")
        print(f"Gesamtdatei (alle Agenten): {all_path}")
    else:
        print("Warnung: Keine Agenten-Logs zum Speichern vorhanden.")
