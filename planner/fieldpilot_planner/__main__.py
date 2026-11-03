"""Command line: `python -m fieldpilot_planner <stage>... [--force <stage>...]`."""

import argparse
import logging
import sys
from datetime import datetime

from fieldpilot_planner.paths import Paths
from fieldpilot_planner.pipeline import DEFAULT_ALL, STAGES, Pipeline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fieldpilot_planner", description=__doc__)
    parser.add_argument("stages", nargs="+", choices=(*STAGES, "all"))
    parser.add_argument(
        "--force", nargs="*", default=[], choices=STAGES, help="re-run these stages"
    )
    parser.add_argument("--run", default="main", help="run name under data/planner/runs/")
    args = parser.parse_args(argv)

    paths = Paths()
    logs = paths.data / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs / f"{stamp}.log", encoding="utf-8"),
        ],
    )
    stages = DEFAULT_ALL if "all" in args.stages else tuple(args.stages)
    Pipeline(paths, args.run, frozenset(args.force)).run(stages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
