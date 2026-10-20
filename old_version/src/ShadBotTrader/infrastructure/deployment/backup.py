"""Database backup, verification and restore (Phase 24, §27, 79-82).

Section 80 states the rule this module is built around: **a backup that
has never been restored is not a backup.** So every backup taken here is
immediately opened, integrity-checked and row-counted before it is
declared good. A file that merely exists proves nothing.

Backups use SQLite's online backup API rather than copying the file.
Copying a database while a writer is mid-transaction produces a file
that looks fine and restores corrupt — the worst possible failure mode,
because it is only discovered when it is needed.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ShadBotTrader.domain.common.errors import ValidationError

#: Timestamp format used in backup file names — sorts chronologically.
_STAMP = "%Y%m%d-%H%M%S"


@dataclass(frozen=True)
class BackupRecord:
    """One verified backup."""

    path: str
    created_at: str
    size_bytes: int
    schema_version: int
    table_counts: Dict[str, int] = field(default_factory=dict)
    verified: bool = False
    note: str = ""

    @property
    def total_rows(self) -> int:
        return sum(self.table_counts.values())

    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "created_at": self.created_at,
            "size_bytes": self.size_bytes,
            "size_kb": round(self.size_kb, 1),
            "schema_version": self.schema_version,
            "table_counts": dict(self.table_counts),
            "total_rows": self.total_rows,
            "verified": self.verified,
            "note": self.note,
        }


def _inspect(path: Path) -> tuple[int, Dict[str, int]]:
    """Read schema version and row counts from a database file.

    Any SQLite-level failure is translated into a ``ValidationError``:
    callers of a backup service should not have to catch driver
    exceptions to find out that a file is not a database.
    """
    try:
        connection = sqlite3.connect(str(path))
    except sqlite3.Error as error:
        raise ValidationError(f"Cannot open {path} as a database: {error}") from error

    try:
        try:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError as error:
            raise ValidationError(f"{path} is not a readable SQLite database: {error}") from error

        if not integrity or integrity[0] != "ok":
            raise ValidationError(
                f"Integrity check failed for {path}: {integrity[0] if integrity else 'no result'}"
            )

        try:
            row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
            schema_version = int(row[0]) if row and row[0] is not None else 0
        except sqlite3.Error:
            # A database without the migrations table is still a valid
            # file — it simply has no schema version to report.
            schema_version = 0

        tables = [
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' " "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        counts: Dict[str, int] = {}
        for table in tables:
            # Table names come from sqlite_master, not user input.
            counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        return schema_version, counts
    finally:
        connection.close()


class BackupService:
    """Takes, verifies, lists, prunes and restores database backups."""

    def __init__(self, database_path: str | Path, backup_root: str | Path | None = None) -> None:
        self._database = Path(database_path)
        self._root = Path(backup_root) if backup_root else self._database.parent / "backups"

    @property
    def backup_root(self) -> Path:
        return self._root

    # ------------------------------------------------------------ create --
    def create(self, note: str = "", verify: bool = True) -> BackupRecord:
        """Take a backup and (by default) prove it can be read back.

        Uses the online backup API, which is safe against concurrent
        writers; a plain file copy is not.
        """
        if not self._database.exists():
            raise ValidationError(
                f"Cannot back up a database that does not exist: {self._database}"
            )

        self._root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime(_STAMP)
        target = self._root / f"{self._database.stem}-{stamp}.db"

        counter = 1
        while target.exists():  # two backups in the same second
            target = self._root / f"{self._database.stem}-{stamp}-{counter}.db"
            counter += 1

        source = sqlite3.connect(str(self._database))
        destination = sqlite3.connect(str(target))
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()

        schema_version: int = 0
        counts: Dict[str, int] = {}
        verified = False
        if verify:
            # Section 80: an unverified backup is not a backup.
            schema_version, counts = _inspect(target)
            verified = True

        record = BackupRecord(
            path=str(target),
            created_at=datetime.now(timezone.utc).isoformat(),
            size_bytes=target.stat().st_size,
            schema_version=schema_version,
            table_counts=counts,
            verified=verified,
            note=note,
        )
        self._write_sidecar(target, record)
        return record

    # ------------------------------------------------------------ verify --
    def verify(self, backup_path: str | Path) -> BackupRecord:
        """Open a backup and confirm it is readable and intact."""
        path = Path(backup_path)
        if not path.exists():
            raise ValidationError(f"Backup not found: {path}")

        schema_version, counts = _inspect(path)
        return BackupRecord(
            path=str(path),
            created_at=datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat(),
            size_bytes=path.stat().st_size,
            schema_version=schema_version,
            table_counts=counts,
            verified=True,
            note="verified on demand",
        )

    # -------------------------------------------------------------- list --
    def list_backups(self) -> List[BackupRecord]:
        """Every backup, newest first.

        Ordered by recorded creation time rather than by filename. Two
        backups taken in the same second differ only by a numeric suffix,
        and ``live-...-1.db`` sorts *before* ``live-...db`` lexically —
        which would report the older file as the newest and hand a
        restore the wrong data.
        """
        if not self._root.exists():
            return []

        records: List[BackupRecord] = []
        for path in sorted(self._root.glob("*.db")):
            sidecar = path.with_suffix(".json")
            if sidecar.exists():
                try:
                    payload = json.loads(sidecar.read_text(encoding="utf-8"))
                    records.append(
                        BackupRecord(
                            path=str(path),
                            created_at=payload.get("created_at", ""),
                            size_bytes=int(payload.get("size_bytes", 0)),
                            schema_version=int(payload.get("schema_version", 0)),
                            table_counts=dict(payload.get("table_counts", {})),
                            verified=bool(payload.get("verified", False)),
                            note=str(payload.get("note", "")),
                        )
                    )
                    continue
                except (json.JSONDecodeError, ValueError):
                    pass  # fall through to a filesystem-only record

            records.append(
                BackupRecord(
                    path=str(path),
                    created_at=datetime.fromtimestamp(
                        path.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                    size_bytes=path.stat().st_size,
                    schema_version=0,
                    verified=False,
                    note="no metadata sidecar",
                )
            )

        # Creation time is authoritative; file modification time is the
        # tie-breaker for records written within the same timestamp.
        records.sort(
            key=lambda record: (record.created_at, Path(record.path).stat().st_mtime),
            reverse=True,
        )
        return records

    def latest(self) -> Optional[BackupRecord]:
        backups = self.list_backups()
        return backups[0] if backups else None

    # ----------------------------------------------------------- restore --
    def restore(self, backup_path: str | Path, safety_copy: bool = True) -> Dict[str, Any]:
        """Restore a backup over the live database.

        The current database is copied aside first unless explicitly
        disabled: restoring the wrong backup must not be the end of the
        story. The backup is verified *before* anything is overwritten.
        """
        path = Path(backup_path)
        record = self.verify(path)  # refuses to proceed on a corrupt file

        replaced: Optional[str] = None
        if safety_copy and self._database.exists():
            stamp = datetime.now(timezone.utc).strftime(_STAMP)
            aside = self._database.with_name(f"{self._database.stem}-replaced-{stamp}.db")
            shutil.copy2(self._database, aside)
            replaced = str(aside)

        self._database.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, self._database)

        after = _inspect(self._database)
        return {
            "restored_from": str(path),
            "database": str(self._database),
            "schema_version": after[0],
            "table_counts": after[1],
            "total_rows": sum(after[1].values()),
            "previous_saved_to": replaced,
            "backup_rows": record.total_rows,
        }

    # ------------------------------------------------------------- prune --
    def prune(self, keep: int = 10) -> List[str]:
        """Delete all but the ``keep`` newest backups."""
        if keep < 1:
            raise ValidationError("keep must be >= 1 — pruning everything is not a policy")

        removed: List[str] = []
        for record in self.list_backups()[keep:]:
            path = Path(record.path)
            sidecar = path.with_suffix(".json")
            path.unlink(missing_ok=True)
            sidecar.unlink(missing_ok=True)
            removed.append(str(path))
        return removed

    # -------------------------------------------------------- internals --
    def _write_sidecar(self, target: Path, record: BackupRecord) -> None:
        target.with_suffix(".json").write_text(
            json.dumps(record.to_dict(), indent=2), encoding="utf-8"
        )
