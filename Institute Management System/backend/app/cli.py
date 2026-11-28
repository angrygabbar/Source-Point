"""Operational CLI.

Usage (inside the backend container):
  python -m app.cli migrate
  python -m app.cli create-institute --name "My Institute" --code MYINST --admin-email admin@example.com --admin-name "Admin"
  python -m app.cli create-superuser --email root@example.com --name "Platform Admin"
  python -m app.cli generate-sessions --days 28
"""

import argparse
import getpass
import sys
from datetime import date, timedelta

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.core.logging import configure_logging
from app.db.session import session_scope


def _alembic_cfg() -> Config:
    import os

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    cfg = Config(os.path.join(here, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(here, "migrations"))
    return cfg


def cmd_migrate(_args) -> None:
    command.upgrade(_alembic_cfg(), "head")
    from app.bootstrap import seed_system

    with session_scope() as db:
        result = seed_system(db)
    print(f"Migrations applied. Seeded {result['permissions']} permissions and {result['roles']} system roles.")


def cmd_create_institute(args) -> None:
    from app.bootstrap import provision_institute

    password = None
    if args.prompt_password:
        password = getpass.getpass("Admin password: ")
    with session_scope() as db:
        inst, admin, temp = provision_institute(db, args.name, args.code, args.admin_email, args.admin_name, password, args.branch_name)
        print(f"Institute created: {inst.name} ({inst.code}) id={inst.id}")
        print(f"Administrator: {admin.email}")
        if temp:
            print(f"Temporary password (change at first login): {temp}")


def cmd_create_superuser(args) -> None:
    from app.bootstrap import create_superuser

    password = getpass.getpass("Password: ") if args.prompt_password else None
    with session_scope() as db:
        user, temp = create_superuser(db, args.email, args.name, password)
        print(f"Platform administrator created: {user.email}")
        if temp:
            print(f"Temporary password (change at first login): {temp}")


def cmd_generate_sessions(args) -> None:
    from app.models import Institute
    from app.services.scheduling import generate_sessions

    with session_scope() as db:
        for inst in db.scalars(select(Institute).where(Institute.is_active.is_(True))):
            r = generate_sessions(db, inst.id, date.today(), date.today() + timedelta(days=args.days))
            print(f"{inst.code}: {r}")


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    parser = argparse.ArgumentParser(prog="classflow")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate").set_defaults(func=cmd_migrate)
    ci = sub.add_parser("create-institute")
    ci.add_argument("--name", required=True)
    ci.add_argument("--code", required=True)
    ci.add_argument("--admin-email", required=True)
    ci.add_argument("--admin-name", required=True)
    ci.add_argument("--branch-name", default="Main Branch")
    ci.add_argument("--prompt-password", action="store_true", help="Prompt for a password instead of generating one")
    ci.set_defaults(func=cmd_create_institute)
    su = sub.add_parser("create-superuser")
    su.add_argument("--email", required=True)
    su.add_argument("--name", required=True)
    su.add_argument("--prompt-password", action="store_true")
    su.set_defaults(func=cmd_create_superuser)
    gs = sub.add_parser("generate-sessions")
    gs.add_argument("--days", type=int, default=28)
    gs.set_defaults(func=cmd_generate_sessions)
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
