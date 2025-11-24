import csv
import os


def save_agent_logs(agent_logs: dict, results_dir: str):
    """
    Speichert für jeden Agenten eine eigene CSV und zusätzlich eine aggregierte CSV.
    CSV-Format: Komma-getrennt (Lösung A).
    """

    os.makedirs(results_dir, exist_ok=True)

    # 1) Einzel-CSV pro Agent
    for agent_id, rows in agent_logs.items():
        if not rows:
            continue

        # Agententyp aus erster Zeile auslesen
        agent_type = rows[0].get("agent_type", "UnknownAgent")

        filename = f"agent_{agent_id}_{agent_type}.csv"
        filepath = os.path.join(results_dir, filename)

        # Header extrahieren
        headers = list(rows[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
            writer.writeheader()
            writer.writerows(rows)

    # 2) Gesamte CSV mit allen Agenten
    all_rows = []
    for rows in agent_logs.values():
        all_rows.extend(rows)

    if all_rows:
        all_csv_path = os.path.join(results_dir, "agent_logs_all.csv")
        headers = list(all_rows[0].keys())

        with open(all_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"Agenten-Log (alle) gespeichert unter: {all_csv_path}")
