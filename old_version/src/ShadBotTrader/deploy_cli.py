"""Deployment CLI (Phase 24).

python -m ShadBotTrader.deploy_cli health
python -m ShadBotTrader.deploy_cli manifest --environment production
python -m ShadBotTrader.deploy_cli backup --note "before migration"
python -m ShadBotTrader.deploy_cli backups
python -m ShadBotTrader.deploy_cli verify --file backups/shadbot-....db
python -m ShadBotTrader.deploy_cli restore --file backups/shadbot-....db
python -m ShadBotTrader.deploy_cli prune --keep 10
python -m ShadBotTrader.deploy_cli preflight --environment production
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from ShadBotTrader import __version__
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.deployment.health import HealthStatus
from ShadBotTrader.domain.deployment.release import (
    DeploymentManifest,
    Environment,
    ReleaseVersion,
)
from ShadBotTrader.infrastructure.deployment.backup import BackupService
from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor

DEFAULT_DB = "shadbot.db"
DEFAULT_STORAGE = "datasets"


def _git_commit() -> str:
    """Current commit, or empty when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=str(Path.cwd()),
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _schema_version(database: str) -> int:
    path = Path(database)
    if not path.exists():
        return 0
    from ShadBotTrader.infrastructure.persistence import Database

    db = Database(path)
    try:
        return db.schema_version
    finally:
        db.close()


def _service(args: argparse.Namespace) -> BackupService:
    return BackupService(args.db, getattr(args, "backup_root", None))


# ------------------------------------------------------------------ health --
def cmd_health(args: argparse.Namespace) -> int:
    """Report liveness, readiness and every dependency."""
    monitor = default_monitor(
        version=__version__,
        environment=args.environment,
        database_path=args.db if Path(args.db).exists() else None,
        storage_root=args.storage_root,
    )
    report = monitor.run()

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print("=== ShadBotTrader health ===")
        print(f"  version     : {report.version}")
        print(f"  environment : {report.environment}")
        print(f"  live        : {report.is_live}")
        print(f"  ready       : {report.is_ready}")
        print()
        for line in report.summary_lines():
            print(f"  {line}")
        if report.status is HealthStatus.DEGRADED:
            print("\n  Degraded: an optional dependency is unavailable.")
            print("  The platform still runs, with reduced capability.")

    # Exit code carries the verdict so a scheduler can act on it.
    return 0 if report.is_ready else 1


def cmd_manifest(args: argparse.Namespace) -> int:
    """Print (and optionally write) the deployment manifest."""
    try:
        environment = Environment.parse(args.environment)
        version = ReleaseVersion.parse(args.version or __version__)
    except ValidationError as error:
        print(f"  [X] {error}")
        return 1

    manifest = DeploymentManifest.create(
        version=version,
        environment=environment,
        schema_version=_schema_version(args.db),
        git_commit=_git_commit(),
        notes=args.note,
    )

    print(json.dumps(manifest.to_dict(), indent=2))
    for warning in manifest.warnings():
        print(f"\n  [!] {warning}", file=sys.stderr)

    if args.out:
        Path(args.out).write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}", file=sys.stderr)
    return 0


# ------------------------------------------------------------------ backup --
def cmd_backup(args: argparse.Namespace) -> int:
    """Take a verified backup."""
    try:
        record = _service(args).create(note=args.note, verify=not args.no_verify)
    except ValidationError as error:
        print(f"  [X] {error}")
        return 1

    print("=== Backup created ===")
    print(f"  file    : {record.path}")
    print(f"  size    : {record.size_kb:.1f} KB")
    print(f"  schema  : v{record.schema_version}")
    print(f"  rows    : {record.total_rows:,} across {len(record.table_counts)} tables")
    print(f"  verified: {record.verified}")
    if not record.verified:
        print("\n  [!] Unverified. A backup that has never been read back is")
        print("      not yet proven to be a backup.")
    return 0


def cmd_backups(args: argparse.Namespace) -> int:
    """List every backup, newest first."""
    records = _service(args).list_backups()
    if not records:
        print("No backups yet. Create one: python -m ShadBotTrader.deploy_cli backup")
        return 1

    print(f"{len(records)} backup(s) in {_service(args).backup_root}\n")
    print(f"  {'created':<28} {'size':>10} {'rows':>10}  verified  file")
    for record in records:
        print(
            f"  {record.created_at[:26]:<28} {record.size_kb:>8.1f}KB "
            f"{record.total_rows:>10,}  {str(record.verified):<8}  "
            f"{Path(record.path).name}"
        )
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Open a backup and prove it is intact."""
    try:
        record = _service(args).verify(args.file)
    except ValidationError as error:
        print(f"  [X] {error}")
        return 1

    print("=== Backup verified ===")
    print(f"  file   : {record.path}")
    print(f"  schema : v{record.schema_version}")
    print(f"  rows   : {record.total_rows:,}")
    for table, count in sorted(record.table_counts.items()):
        if count:
            print(f"    {table:<28} {count:>8,}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    """Restore a backup over the live database."""
    if not args.yes:
        print("  Restoring replaces the live database.")
        print("  Re-run with --yes to confirm.")
        return 1

    try:
        outcome = _service(args).restore(args.file, safety_copy=not args.no_safety_copy)
    except ValidationError as error:
        print(f"  [X] {error}")
        print("  The live database was NOT modified.")
        return 1

    print("=== Restored ===")
    print(f"  from     : {outcome['restored_from']}")
    print(f"  into     : {outcome['database']}")
    print(f"  schema   : v{outcome['schema_version']}")
    print(f"  rows     : {outcome['total_rows']:,}")
    if outcome["previous_saved_to"]:
        print(f"  previous : saved to {outcome['previous_saved_to']}")
    return 0


def cmd_prune(args: argparse.Namespace) -> int:
    """Delete old backups, keeping the newest N."""
    try:
        removed = _service(args).prune(keep=args.keep)
    except ValidationError as error:
        print(f"  [X] {error}")
        return 1

    print(f"Removed {len(removed)} backup(s), kept the newest {args.keep}.")
    for path in removed:
        print(f"  - {Path(path).name}")
    return 0


# --------------------------------------------------------------- preflight --
def cmd_preflight(args: argparse.Namespace) -> int:
    """Everything that must be true before deploying (Phase 24, §17).

    A release gate: it reports every problem rather than stopping at the
    first, so one run tells an operator the whole story.
    """
    try:
        environment = Environment.parse(args.environment)
    except ValidationError as error:
        print(f"  [X] {error}")
        return 1

    print("=== Pre-deployment checks ===")
    print(f"  target environment : {environment.value}")
    print(f"  version            : {__version__}\n")

    problems: List[str] = []
    warnings: List[str] = []

    report = default_monitor(
        version=__version__,
        environment=environment.value,
        database_path=args.db if Path(args.db).exists() else None,
        storage_root=args.storage_root,
    ).run()
    for line in report.summary_lines():
        print(f"  {line}")
    if not report.is_ready:
        problems.append("a critical dependency is unavailable")

    database = Path(args.db)
    if not database.exists():
        warnings.append(f"database {database} does not exist yet")
    else:
        latest = _service(args).latest()
        if latest is None:
            problems.append("no backup exists — deploying without one is irreversible")
        else:
            print(f"\n  [ok  ] latest backup         {Path(latest.path).name}")

    if environment.is_production:
        if not _git_commit():
            problems.append("production deploy has no git commit to trace back to")
        if ReleaseVersion.parse(__version__).major == 0:
            warnings.append(f"deploying pre-1.0 version {__version__} to production")

    print()
    for warning in warnings:
        print(f"  [!] {warning}")
    for problem in problems:
        print(f"  [X] {problem}")

    if problems:
        print(f"\n  NOT READY — {len(problems)} problem(s) must be fixed first.")
        return 1

    if environment.requires_confirmation:
        print(f"\n  READY. {environment.value} requires explicit confirmation to deploy.")
    else:
        print("\n  READY.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader deployment CLI (Phase 24)")
    parser.add_argument("--db", default=DEFAULT_DB, help="database file")
    parser.add_argument("--backup-root", default=None, help="where backups live")
    parser.add_argument("--storage-root", default=DEFAULT_STORAGE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    health = subparsers.add_parser("health", help="liveness, readiness, dependencies")
    health.add_argument("--environment", default="development")
    health.add_argument("--json", action="store_true")
    health.set_defaults(func=cmd_health)

    manifest = subparsers.add_parser("manifest", help="describe this deployment")
    manifest.add_argument("--environment", default="development")
    manifest.add_argument("--version", default=None)
    manifest.add_argument("--note", default="")
    manifest.add_argument("--out", default=None)
    manifest.set_defaults(func=cmd_manifest)

    backup = subparsers.add_parser("backup", help="take a verified backup")
    backup.add_argument("--note", default="")
    backup.add_argument("--no-verify", action="store_true")
    backup.set_defaults(func=cmd_backup)

    backups = subparsers.add_parser("backups", help="list backups")
    backups.set_defaults(func=cmd_backups)

    verify = subparsers.add_parser("verify", help="prove a backup is intact")
    verify.add_argument("--file", required=True)
    verify.set_defaults(func=cmd_verify)

    restore = subparsers.add_parser("restore", help="restore a backup")
    restore.add_argument("--file", required=True)
    restore.add_argument("--yes", action="store_true", help="confirm the replacement")
    restore.add_argument("--no-safety-copy", action="store_true")
    restore.set_defaults(func=cmd_restore)

    prune = subparsers.add_parser("prune", help="delete old backups")
    prune.add_argument("--keep", type=int, default=10)
    prune.set_defaults(func=cmd_prune)

    preflight = subparsers.add_parser("preflight", help="pre-deployment release gate")
    preflight.add_argument("--environment", default="development")
    preflight.set_defaults(func=cmd_preflight)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
