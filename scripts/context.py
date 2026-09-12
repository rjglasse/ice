#!/usr/bin/env python3
"""Cohort configuration loader.

A *cohort* is one run of the course (one year, one GitHub organisation). Each cohort
is described by ``cohorts/<year>.json`` and shares ``cohorts/teachers.txt``. The
cohort used by default is named in ``cohorts/current``; every script accepts
``--cohort YEAR`` to override it (e.g. to re-run the 2025 baseline).

Layout conventions derived from the cohort year::

    repos/<year>/<student>/<student>-task-N   student clones (repobee, gitignored)
    data/<year>/task-N/*.csv                  extracted data and derived metrics
"""

import json
from datetime import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COHORTS_DIR = ROOT / 'cohorts'


class Cohort:
    def __init__(self, year, raw):
        self.year = int(year)
        self.raw = raw
        self.org = raw['org']
        self.host = raw.get('host', 'gits-15.sys.kth.se')
        self.course_start_date = raw['course_start']
        self.tasks = raw.get('tasks', {})
        self.notes = raw.get('notes', '')
        self.students_file = ROOT / raw['students_file'] if raw.get('students_file') else None
        self.repos_dir = ROOT / 'repos' / str(self.year)
        self.data_dir = ROOT / 'data' / str(self.year)
        # shared list (substring matching, historical) + cohort-specific discovered names (exact matching)
        self.teachers = load_teachers()
        self.cohort_teachers = list(raw.get('teachers', []))

    # --- task helpers -------------------------------------------------------
    def task(self, name):
        return self.tasks.get(name)

    def deadline(self, name):
        t = self.task(name)
        return dt.fromisoformat(t['deadline']) if t and t.get('deadline') else None

    def expected_exercises(self, name, default=5):
        t = self.task(name)
        return t.get('exercises', default) if t else default

    def is_provisional(self, name):
        t = self.task(name)
        return bool(t and t.get('provisional'))

    def task_data_dir(self, name):
        return self.data_dir / name

    def is_teacher(self, identity):
        """True for teachers/TAs. Shared list (cohorts/teachers.txt): case-insensitive
        substring match, as in 2025. Cohort list (discovered org admins and template
        authors in cohorts/<year>.json): exact case-insensitive match."""
        ident = (identity or '').strip().lower()
        if not ident:
            return False
        if any(ident == t.lower() for t in self.cohort_teachers):
            return True
        return any(t.lower() in ident for t in self.teachers)

    def save(self):
        """Write the (possibly updated) cohort config back to cohorts/<year>.json."""
        self.raw['tasks'] = self.tasks
        path = COHORTS_DIR / f'{self.year}.json'
        path.write_text(json.dumps(self.raw, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def __repr__(self):
        return f"Cohort({self.year}, org={self.org}, tasks={len(self.tasks)})"


def load_teachers():
    path = COHORTS_DIR / 'teachers.txt'
    if not path.exists():
        return []
    names = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            names.append(line)
    return names


def current_year():
    marker = COHORTS_DIR / 'current'
    if marker.exists():
        return int(marker.read_text().strip())
    years = available_years()
    return max(years) if years else dt.now().year


def available_years():
    return sorted(int(p.stem) for p in COHORTS_DIR.glob('*.json') if p.stem.isdigit())


def load(year=None):
    year = int(year) if year else current_year()
    path = COHORTS_DIR / f'{year}.json'
    if not path.exists():
        raise SystemExit(f"No cohort config at {path}. Available: {available_years()}")
    return Cohort(year, json.loads(path.read_text(encoding='utf-8')))


def add_cohort_arg(parser):
    """Attach the standard --cohort option to an argparse parser."""
    parser.add_argument('--cohort', type=int, default=None, metavar='YEAR',
                        help=f'cohort year (default: {current_year()} from cohorts/current)')
    return parser


# Backwards-compatible module-level names for the current cohort.
_current = load()
teachers = _current.teachers
course_start_date = _current.course_start_date
tasks = _current.tasks
