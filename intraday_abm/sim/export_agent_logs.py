import csv
import os


def save_agent_logs(agent_logs: dict, results_dir: str):
    """
    Speichert für jeden Agenten eine eigene CSV und zusätzlich eine aggregierte CSV.
    CSV-Format: Komma-getrennt (Lösung A).
    """

    # Schreibe Agenten-Logs in ein Unterverzeichnis `agent_logs`
    agent_logs_dir = os.path.join(results_dir, "agent_logs")
    os.makedirs(agent_logs_dir, exist_ok=True)

    # 1) Einzel-CSV pro Agent
    all_rows = []
    for agent_id, rows in agent_logs.items():
        # Unterstützung für zwei Formate:
        # - rows: List[Dict]  -> bereits zeilenorientiert
        # - rows: Dict[str, List] -> spaltenorientiert (keys -> Listen)
        if not rows:
            continue

        # Normalisiere auf Liste von Zeilen (Dicts)
        if isinstance(rows, dict):
            # columns -> lists
            cols = list(rows.keys())
            # Bestimme Länge nur anhand von list-/tuple-Spalten (skalare Werte wie agent_type
            # dürfen nicht als Iterable interpretiert werden)
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
                        # Skalare Werte (z. B. agent_type) als konstante Spalte verwenden
                        row[c] = v
                rows_list.append(row)
        elif isinstance(rows, list):
            rows_list = rows
        else:
            # Fallback: versuche, iterierbare Zeilen zu bauen
            try:
                rows_list = list(rows)
            except Exception:
                continue

        if not rows_list:
            continue

        # Agententyp aus erster Zeile auslesen
        agent_type = rows_list[0].get("agent_type", "UnknownAgent")

        filename = f"agent_{agent_id}_{agent_type}.csv"
        filepath = os.path.join(agent_logs_dir, filename)

        # Header extrahieren
        headers = list(rows_list[0].keys())

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
            writer.writeheader()
            writer.writerows(rows_list)

        all_rows.extend(rows_list)

    # 2) Gesamte CSV mit allen Agenten (in `agent_logs`-Ordner)
    if all_rows:
        all_csv_path = os.path.join(agent_logs_dir, "agent_logs_all.csv")
        headers = list(all_rows[0].keys())

        with open(all_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=headers, delimiter=",")
            writer.writeheader()
            writer.writerows(all_rows)

        print(f"Agenten-Log (alle) gespeichert unter: {all_csv_path}")
