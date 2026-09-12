#!/usr/bin/env python3
"""Cohort configuration loader.

A *cohort* is one run of the course (one GitHub organisation). Each cohort is described
by ``cohorts/<name>.json`` and shares ``cohorts/teachers.txt``. The name is normally the
year (``2026``); a separately managed group gets its own name (``2026-plus``) and states
its ``year`` in the JSON, which is what cross-year tables use. The cohort used by default
is named in ``cohorts/current``; every script accepts ``--cohort NAME`` to override it
(e.g. to re-run the 2025 baseline).

Layout conventions derived from the cohort name::

    repos/<name>/<student>/<student>-task-N   student clones (repobee, gitignored)
    data/<name>/task-N/*.csv                  extracted data and derived metrics

``default_plan`` (default true) says whether the task READMEs carry the pre-filled issue
links; with false, every issue is the student's own plan and the v2 planning line says so.
"""

import json
from datetime import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COHORTS_DIR = ROOT / 'cohorts'


class Cohort:
    def __init__(self, name, raw):
        self.name = str(name)
        if self.name.isdigit():
            self.year = int(raw.get('year', self.name))
        elif 'year' in raw:
            self.year = int(raw['year'])
        else:
            raise SystemExit(f"cohorts/{self.name}.json needs a \"year\" (the course year it belongs to)")
        self.raw = raw
        self.default_plan = bool(raw.get('default_plan', True))
        self.org = raw['org']
        self.host = raw.get('host', 'gits-15.sys.kth.se')
        self.course_start_date = raw['course_start']
        self.tasks = raw.get('tasks', {})
        self.notes = raw.get('notes', '')
        self.students_file = ROOT / raw['students_file'] if raw.get('students_file') else None
        self.repos_dir = ROOT / 'repos' / self.name
        self.data_dir = ROOT / 'data' / self.name
        # shared list (substring matching, historical) + cohort-specific discovered names (exact matching)
        self.teachers = load_teachers()
        self.cohort_teachers = list(raw.get('teachers', []))

    @property
    def is_year(self):
        """True for a plain year cohort (the ones cross-year tables compare)."""
        return self.name.isdigit()

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
        path = COHORTS_DIR / f'{self.name}.json'
        path.write_text(json.dumps(self.raw, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    def __repr__(self):
        return f"Cohort({self.name}, org={self.org}, tasks={len(self.tasks)})"


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


def current_name():
    """Name of the default cohort: cohorts/current, else the latest year with a config."""
    marker = COHORTS_DIR / 'current'
    if marker.exists():
        return marker.read_text().strip()
    years = available_years()
    return str(max(years)) if years else str(dt.now().year)


def current_year():
    name = current_name()
    if name.isdigit():
        return int(name)
    return load(name).year


def available_years():
    return sorted(int(p.stem) for p in COHORTS_DIR.glob('*.json') if p.stem.isdigit())


def available_cohorts():
    return sorted(p.stem for p in COHORTS_DIR.glob('*.json') if not p.stem.startswith('example'))


def load(name=None):
    name = str(name) if name else current_name()
    path = COHORTS_DIR / f'{name}.json'
    if not path.exists():
        raise SystemExit(f"No cohort config at {path}. Available: {available_cohorts()}")
    return Cohort(name, json.loads(path.read_text(encoding='utf-8')))


def add_cohort_arg(parser):
    """Attach the standard --cohort option to an argparse parser."""
    parser.add_argument('--cohort', type=str, default=None, metavar='NAME',
                        help=f'cohort year or name, e.g. 2026 or 2026-plus (default: {current_name()} from cohorts/current)')
    return parser


# Backwards-compatible module-level names for the current cohort.
_current = load()
teachers = _current.teachers
course_start_date = _current.course_start_date
tasks = _current.tasks
