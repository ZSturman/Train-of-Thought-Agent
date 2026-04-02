from __future__ import annotations

import argparse
from pathlib import Path

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.session import SessionController


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tree-of-Thought Location Agent — an interactive learning agent "
        "that associates grayscale observations and sensor-path inputs with "
        "nested, inspectable location context.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Minimal output suitable for scripting and automated testing.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear all learned location memory and exit.",
    )
    args = parser.parse_args()

    runtime_dir = Path.cwd() / "runtime"
    store = MemoryStore(runtime_dir / "location_memory.json")

    if args.reset:
        count = store.reset_memory()
        print(f"Memory reset — {count} location model(s) removed.")
        return

    event_logger = EventLogger(runtime_dir / "agent_events.jsonl")
    SessionController(store=store, event_logger=event_logger, quiet=args.quiet).run()


if __name__ == "__main__":
    main()
