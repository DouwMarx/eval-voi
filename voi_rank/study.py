"""A study is one directory: scenarios.json, protocols/, templates/, voi.db
and report/. Every CLI entry point takes --study PATH and derives all paths
from it (default: studies/business).

Tagged outputs: every analysis CLI that writes report files (figures,
tables, extra, compare_models) takes --tag NAME (lowercase letters only). Its files
then land in report/generated/NAME/ instead of report/generated/, and every
LaTeX macro it writes is renamed from \\voiX to \\voiNAMEX, so a paper can
input the headline run's macros and a baseline run's side by side.
Study.tagged maps a tag to (output dir, macro prefix) and newcommands
writes the macros under that prefix; no tag leaves both unchanged.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from voi_rank import db

DEFAULT_STUDY = "studies/business"
MACRO_PREFIX = "voi"            # every macro an analysis writes is \\voi<Name>
TAG_RE = re.compile(r"[a-z]+")   # a LaTeX control word, lowercase: never an untagged name


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

    def tagged(self, tag: str | None = None) -> tuple[Path, str]:
        """(output dir, macro prefix) of an analysis CLI: (generated/, 'voi')
        without a tag, (generated/<tag>/, 'voi<tag>') with one."""
        if tag is None:
            return self.generated_dir, MACRO_PREFIX
        return self.generated_dir / check_tag(tag), MACRO_PREFIX + tag

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

    def connect(self) -> sqlite3.Connection:
        return db.connect(self.db)

    def connect_copy(self) -> sqlite3.Connection:
        """An in-memory copy of voi.db (empty when the file is absent); the
        file is never created or written. Used by --dry-run."""
        return db.connect_copy(self.db)


def add_study_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--study", default=DEFAULT_STUDY,
                    help=f"study directory (default: {DEFAULT_STUDY})")


def check_tag(text: str) -> str:
    """The --tag value: lowercase letters only. It becomes part of LaTeX
    macro names (a control word has no digits or punctuation), and a
    lowercase tag can never recreate an untagged macro, whose name continues
    with an uppercase letter after \\voi; an uppercase one can ('Gauss'
    turns the tables' \\voiRunId into compare_models' \\voiGaussRunId)."""
    if not TAG_RE.fullmatch(text or ""):
        raise argparse.ArgumentTypeError(f"--tag takes lowercase letters only (a-z), got {text!r}")
    return text


def add_tag_arg(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--tag", type=check_tag, default=None,
                    help="write to report/generated/TAG/ and rename every macro \\voiX to \\voiTAGX"
                         " (lowercase letters only; default: report/generated/ and \\voiX)")


def newcommands(macros: dict, prefix: str = MACRO_PREFIX) -> list[str]:
    """One \\newcommand line per macro; every key is 'voi<Name>' and is
    written as '<prefix><Name>' (Study.tagged gives the prefix)."""
    lines = []
    for key, value in macros.items():
        if not key.startswith(MACRO_PREFIX):
            raise ValueError(f"macro {key!r} does not start with {MACRO_PREFIX!r}")
        lines.append(f"\\newcommand{{\\{prefix}{key[len(MACRO_PREFIX):]}}}{{{value}}}")
    return lines
