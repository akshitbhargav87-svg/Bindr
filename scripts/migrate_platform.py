"""Explicit additive migration or read-only deployment check. No destructive downgrade."""

import argparse
from backend.app.core.database import engine
from backend.migrations import upgrade, assert_current


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--upgrade", action="store_true")
    args = parser.parse_args()
    if args.upgrade:
        upgrade(engine)
    print("Schema revision:", assert_current(engine))


if __name__ == "__main__":
    main()
