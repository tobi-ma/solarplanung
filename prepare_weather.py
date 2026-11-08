"""Reproduce the compact weather file from two downloaded PVGIS seriescalc JSONs.

Usage: python prepare_weather.py /tmp/pv-heating-roof.json /tmp/pv-heating-wall.json
Full API URLs and normalization are recorded in README.md.
"""
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOF_MONTHS = [151.31,258.29,454.85,604.75,645.94,672.56,670.68,612.52,499.56,338.54,176.37,126.41]
WALL_MONTHS = [73.71,110.57,173.36,209.55,207.88,204.85,205.45,202.08,185.79,134.64,78.81,63.62]


def prepare(roof_path, wall_path):
    roof = json.loads(Path(roof_path).read_text())["outputs"]["hourly"]
    wall = json.loads(Path(wall_path).read_text())["outputs"]["hourly"]
    assert len(roof) == len(wall) == 8760
    sums = [[0.] * 12 for _ in range(2)]
    for group, data in enumerate((roof, wall)):
        for row in data:
            sums[group][int(row["time"][4:6])-1] += row["P"]
    out = Path(__file__).with_name("weather_2023.csv")
    with out.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["time_utc", "roof_kwh", "wall_kwh", "temperature_c"])
        for r, w in zip(roof, wall):
            assert r["time"] == w["time"]
            dt = datetime.strptime(r["time"], "%Y%m%d:%H%M").replace(tzinfo=timezone.utc)
            month = dt.month-1
            values = [r["P"] / sums[0][month] * ROOF_MONTHS[month],
                      w["P"] / sums[1][month] * WALL_MONTHS[month]]
            writer.writerow([dt.isoformat(), *(round(v, 8) for v in values), r["T2m"]])
    print(f"Prepared {len(roof)} hourly records: {out.name}")


if __name__ == "__main__":
    prepare(*sys.argv[1:])
