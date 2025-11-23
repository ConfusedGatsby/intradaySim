from __future__ import annotations

import csv
import os
from typing import Dict, Any


def save_agent_logs(agent_logs: Dict[int, Dict[str, Any]], results_dir: str) -> None:
    """
    Schreibt für jeden Agenten eine eigene CSV in:
    results/agent_logs/agent_{id}_{type}.csv

    Format pro Datei:
        t;agent_type;position;revenue;imbalance;da_position;capacity
    """

    out_dir = os.path.join(results_dir, "agent_logs")
    os.makedirs(out_dir, exist_ok=True)

    for agent_id, data in agent_logs.items():
        agent_type = data["agent_type"]

        filename = f"agent_{agent_id}_{agent_type}.csv"
        path = os.path.join(out_dir, filename)

        fieldnames = [
            "t",
            "agent_type",
            "position",
            "revenue",
            "imbalance",
            "da_position",
            "capacity",
        ]

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()

            n = len(data["t"])
            for i in range(n):
                row = {
                    "t": data["t"][i],
                    "agent_type": data["agent_type"],
                    "position": data["position"][i],
                    "revenue": data["revenue"][i],
                    "imbalance": data["imbalance"][i],
                    "da_position": data["da_position"][i],
                    "capacity": data["capacity"][i],
                }
                writer.writerow(row)

        print(f"Agent-Log gespeichert: {path}")
