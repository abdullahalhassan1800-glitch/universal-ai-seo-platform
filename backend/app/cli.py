"""Database init/seed CLI: python -m backend.app.cli init-db [--drop-first]."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from .core.db import Base, SessionLocal, engine
from .core.config import settings
from . import models  # noqa: F401  (register all tables on Base.metadata)


def init_db(drop_first: bool = False) -> None:
    if drop_first:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed()
    print("Database initialized (tables created + seed data).")


def seed() -> None:
    from .models import SearchEngine

    db = SessionLocal()
    try:
        engines = [
            ("google", "Google", True),
            ("bing", "Bing", True),
            ("yandex", "Yandex", True),
            ("brave", "Brave Search", True),
            ("duckduckgo", "DuckDuckGo", True),
            ("yahoo", "Yahoo", True),
        ]
        existing = {r[0] for r in db.query(SearchEngine.engine_id).all()}
        for engine_id, name, supported in engines:
            if engine_id not in existing:
                db.add(SearchEngine(engine_id=engine_id, display_name=name, supported=supported))
        db.commit()
        print("Seeded search engines:", ", ".join(e[0] for e in engines))
    finally:
        db.close()


def ping() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"Database OK: {settings.database_url}")
    except Exception as exc:
        print(f"Database connection FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Universal AI SEO Platform DB tooling")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init-db", help="Create tables + seed")
    init.add_argument("--drop-first", action="store_true", help="Drop all tables first")
    sub.add_parser("ping", help="Test database connection")
    sub.add_parser("seed", help="Seed reference data")
    args = parser.parse_args()

    if args.command == "init-db":
        init_db(drop_first=args.drop_first)
    elif args.command == "seed":
        seed()
    elif args.command == "ping":
        ping()


if __name__ == "__main__":
    main()
