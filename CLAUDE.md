# ICE: notes for Claude Code

Purpose: weekly analysis of student Git workflow (INDA courses at KTH) that posts nudges as
issues, and a 2026 confirmation study of the 2025 paper (`paper/iticse26.tex`). Read
`README.md`, then `docs/runbook.md` and `docs/study-2026.md`.

Invariants:
- `data/2025/` is the study baseline. Never re-extract or edit it. `ice.py` refuses to run
  extraction for a non-current cohort; keep that guard.
- Metric definitions (`effort.py`), the scoring models and message templates (`nudges.py`, `plan.py`)
  and `ice-guide.md` are the *treatment*. The v1 (2025) model must stay byte-for-byte as it is:
  `compare.py` uses it for all cross-year tables. Any change to them must be logged in
  `docs/improvements.md` with the date, because it can move the 2026 numbers.
- A manual value in `cohorts/<year>.json` wins over `discover.py`; discovery only fills
  missing or `provisional` entries.
- A cohort is keyed by its config file name. Year cohorts (`2026`) are the study; a named cohort
  (`2026-plus`, copied from `cohorts/example-plus.json`) is a separately managed group with its
  own `data/`, `repos/` and `students/` folders, skipped by the cross-year tables. `default_plan`
  must stay true for the year cohorts: false switches the v2 planning wording to own-plan style.
- `feedback.py` is the only script that writes to student repositories. Dry run is the default;
  never add `--post` on the user's behalf.
- The `repos/` directory is gitignored and large. `data/`, `students/` and `feedback/` are
  committed in the private working copy only. The public remote (origin) is updated solely
  through `scripts/publish.py`, which copies an allowlist of tooling files onto the `public`
  branch; never push `main` to origin.

Conventions: plain Python 3.9 standard library only (no pip dependencies); scripts are also
importable modules with a `run(...)` function; one output folder per task under
`data/<year>/task-N/`.
