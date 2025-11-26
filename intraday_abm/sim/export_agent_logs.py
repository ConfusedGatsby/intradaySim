import csv
import os
from typing import Any


def save_agent_logs(agent_logs: dict[int, list[dict[str, Any]]], results_dir: str):
    """
    Speichert für jeden Agenten eine eigene CSV und zusätzlich eine aggregierte CSV.
    Unterstützt mehrere Orders pro Zeitschritt (Variante A).
    """

    agent_logs_dir = os.path.join(results_dir, "agent_logs")
    os.makedirs(agent_logs_dir, exist_ok=True)

    all_rows = []

    for agent_id, rows in agent_logs.items():
        if not rows:
            continue

        # Wenn es eine Liste von Dicts ist: direkt weiterverarbeiten
        if isinstance(rows, list):
            rows_list = rows
        elif isinstance(rows, dict):
            # Spaltenorientiert → konvertieren
            cols = list(rows.keys())
            list_lengths = [len(rows[c]) for c in cols if isinstance(rows[c], (list, tuple))]
            n = max(list_lengths) if list_lengths else 1
            rows_list = []
            for i in range(n):
                row = {}
                for c in cols:
                    v = rows[c]
                    if isinstance(v, (list, tuple)):
                        row[c] = v[i] if i < len(v) else None
                    else:
                        row[c] = v
                rows_list.append(row)
        else:
            try:
                rows_list = list(rows)
            except Exception:
                continue

        if not rows_list:
            continue

        agent_type = rows_list[0].get("agent_type", "UnknownAgent")
        filename = f"agent_{agent_id}_{agent_type}.csv"
        filepath = os.path.join(agent_logs_dir, filename)

        headers = sorted(set().union(*(row.keys() for row in rows_list)))

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows_list)

        all_rows.extend(rows_list)

    if all_rows:
        all_csv_path = os.path.join(agent_logs_dir, "agent_logs_all.csv")
        headers = sorted(set().union(*(row.keys() for row in all_rows)))
        with open(all_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"Agenten-Log (alle) gespeichert unter: {all_csv_path}")
