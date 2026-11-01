"""Regenerate src/plugin/data/crashes.json, the plugin's synthetic dataset: `python src/datagen/make_crashes.py`.

The rows are made up, drawn from a fixed seed, so the file is the same on every computer. It is generated
once and committed; the plugin only ever reads the committed file.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

ROADS = ["I-45", "I-10", "US-59", "I-610", "BW-8"]
WEATHER = (["clear"] * 70) + (["rain"] * 22) + (["fog"] * 8)
SEVERITY = (["none"] * 45) + (["minor"] * 35) + (["serious"] * 15) + (["fatal"] * 5)
HOURS = [h for h in range(24) for _ in range(5 if h in (7, 8, 16, 17, 18) else 2 if 6 <= h <= 21 else 1)]
INJURIES = {"none": (0, 0), "minor": (1, 2), "serious": (1, 4), "fatal": (1, 6)}


def main() -> None:
    rng = random.Random(580)
    rows = []
    for number in range(1, 401):
        day = date(2025, 1, 1) + timedelta(days=rng.randrange(181))
        hour = rng.choice(HOURS)
        severity = rng.choice(SEVERITY)
        rows.append({
            "crash_id": f"HOU-{number:04d}",
            "date": day.isoformat(),
            "weekday": day.strftime("%A"),
            "hour": hour,
            "road": rng.choice(ROADS),
            "severity": severity,
            "vehicles": rng.choice([1, 1, 2, 2, 2, 3, 3, 4, 5]),
            "injuries": rng.randint(*INJURIES[severity]),
            "weather": rng.choice(WEATHER),
            "lighting": "day" if 6 <= hour < 18 else "night",
        })
    out = Path(__file__).resolve().parents[1] / "plugin" / "data" / "crashes.json"
    out.write_text(json.dumps(rows, indent=0) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
