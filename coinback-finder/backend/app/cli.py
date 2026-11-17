"""Operator CLI for CoinBack module maintenance."""

from __future__ import annotations

import argparse

from app.database.session import SessionLocal
from app.services.bootstrap import ensure_defaults


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=("bootstrap",))
    parser.parse_args(argv)

    with SessionLocal() as db:
        ensure_defaults(db)
    print("CoinBack defaults ensured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
