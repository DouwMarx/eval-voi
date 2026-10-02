"""A study is one directory: scenarios.json, protocols/, templates/, voi.db
and report/. Every CLI entry point takes --study PATH and derives all paths
from it (default: DEFAULT_STUDY)."""

from __future__ import annotations

import argparse
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from voi_rank import db

DEFAULT_STUDY = "studies/safety-evals"


@dataclass(frozen=True)
class Study:
    root: Path

    @classmethod
    def resolve(cls, path: str | Path = DEFAULT_STUDY) -> Study:
        """A path relative to the current directory, else to the repo root."""
        p = Path(path)
        if not p.is_absolute() and not p.exists() and (db.ROOT / p).exists():
            p = db.ROOT / p
        if not p.is_dir():
            raise FileNotFoundError(f"study directory not found: {path}")
        return cls(p.resolve())

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def db(self) -> Path:
        return self.root / "voi.db"

    @property
    def scenarios_json(self) -> Path:
        return self.root / "scenarios.json"

    @property
    def protocols_dir(self) -> Path:
        return self.root / "protocols"

    @property
    def templates_dir(self) -> Path:
        return self.root / "templates"

    @property
    def report_dir(self) -> Path:
        return self.root / "report"

    @property
    def generated_dir(self) -> Path:
        return self.root / "report" / "generated"

    def protocol_path(self, name_or_path: str | Path) -> Path:
        """'p001' -> protocols/p001.yaml; an explicit path is used as given
        (relative to the study root first, then to the current directory)."""
        s = str(name_or_path)
        if not s.endswith((".yaml", ".yml")):
            return self.protocols_dir / f"{s}.yaml"
        p = Path(s)
        if not p.is_absolute() and (self.root / p).exists():
            return self.root / p
        return p

    @property
    def archived(self) -> bool:
        """Whether the study lies under an archive/ directory (a read-only
        record): read through connect_copy only. The
        test is on the path's shape (any `archive` component), not on this
        checkout's root, so the archive of another checkout or worktree is
        refused too."""
        return "archive" in self.root.resolve().parts

    def check_writable(self) -> None:
        """DESIGN section 9: never write to a database under archive/. Called
        by connect() (whose migration would otherwise alter the tracked file
        in place) and by elicit's paid path before the confirmation."""
        if self.archived:
            raise SystemExit(f"archived study {self.root}: read-only (a frozen record);"
                             " read it with connect_copy (a dry run needs a two-stage protocol file),"
                             " or copy it outside archive/")

    def connect(self) -> sqlite3.Connection:
        """The study's voi.db, created and migrated as needed; refused for a
        study under archive/."""
        self.check_writable()
        return db.connect(self.db)

    def connect_copy(self) -> sqlite3.Connection:
        """An in-memory copy of voi.db (empty when the file is absent); the
        file is never created or written. Used by --dry-run."""
        return db.connect_copy(self.db)


def add_study_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--study", default=DEFAULT_STUDY,
                    help=f"study directory (default: {DEFAULT_STUDY})")
