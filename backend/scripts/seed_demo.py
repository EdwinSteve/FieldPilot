"""Rebuild the demo farm database (D074).

Run: make seed (stop `make dev` first: this replaces the database file while
the simulator keeps the old state in memory).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.demo_seed import seed_demo_farm
from app.settings import Settings


def main() -> None:
    args = parse_args()
    url = args.db or Settings().database_url
    if not url.startswith("sqlite:///"):
        print("make seed only rebuilds a local sqlite file.")
        raise SystemExit(1)
    path = Path(url.split("sqlite:///", 1)[1])
    if path.exists() and not args.force:
        print(f"{path} exists: pass --force to replace it (stop `make dev` first).")
        raise SystemExit(1)
    if path.exists():
        path.unlink()
    summary = seed_demo_farm(url)
    print(f"Demo farm ready at {path}: plot {summary.plot_id}, zone {summary.zone_id}.")
    print("Run `make dev`, then execute the daily cycle once: the mock day replays on it.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild the demo farm database.")
    parser.add_argument("--db", default=None, help="sqlite database URL (default: the app's)")
    parser.add_argument("--force", action="store_true", help="replace the database file")
    return parser.parse_args()


if __name__ == "__main__":
    main()
