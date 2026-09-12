# Weekly runbook (2026)

One command does the week. Run it on the Saturday after the exercise, when the task
deadline (end of the exercise day) has passed.

```bash
python3 scripts/ice.py task-N            # clone/update, extract, analyse, compare, feedback DRY RUN
```

Then:

1. **Check the config line** printed under "1b. discover". If the deadline or exercise
   count came from the README and looks wrong, edit `cohorts/2026.json` (a manual entry
   wins over discovery). The `provisional` flag was pre-filled from 2025 dates and is
   cleared when discovery fills a task in.
2. **Read** `data/2026/task-N/compare.md` (this task vs 2025), `reports/compare-2026-vs-2025.md`
   (all tasks so far) and `reports/history-commits.md` (2026 so far vs every year since 2020).
3. **Edit** `docs/task-mapping/task-N.md`: mark which exercises are comparable with 2025.
   The file is generated once from the two READMEs; your edits are kept.
4. **Skim** a few rows of `data/2026/task-N/nudges.csv` (message column) before posting.
5. **Post** the nudges:
   ```bash
   python3 scripts/ice.py task-N --no-clone --skip-issues --post
   # or, one student first:
   python3 scripts/feedback.py task-N --student USERNAME --post
   ```
   Posting is idempotent: rows already marked `issue_created` are skipped, so a crash
   halfway can simply be re-run.
6. **Rebuild the report** when you want the PDF current: `python3 scripts/report.py`
   (tables and figures regenerate; prose is yours in `report/report.tex`).
7. **Commit** the week in the private working copy:
   ```bash
   git add data/2026 reports docs cohorts && git commit -m "Weekly run 2026 task-N"
   ```
   The data never leaves this copy. When the tooling or docs changed and should reach the
   public repository, `python3 scripts/publish.py` rebuilds the `public` branch (tooling
   only, checked for usernames and CSVs) and `--push` sends it to origin.

## Individual steps

Every step is a script that takes the task name and `--cohort YEAR` (default: the year in
`cohorts/current`). Outputs go to `data/<year>/<task>/`.

| Step | Script | Output |
|---|---|---|
| clone/update | `repobee repos clone -a task-N --students-file students/2026/students.txt --update-local --dl by-team` (run in `repos/2026/`) | `repos/2026/<user>/<user>-task-N` |
| config | `discover.py task-N [--teachers] [--students] [--write]` | `cohorts/2026.json`, `students/2026/students.txt` |
| commits | `commits.py task-N` | `commits.csv` |
| issues | `issues.py task-N` (gh) | `issues.csv` |
| metrics | `effort.py task-N` | `effort.csv` |
| plan | `plan.py task-N` (also run by nudges.py under model v2) | `plan.csv` |
| nudges | `nudges.py task-N` | `nudges.csv` (both models' scores) |
| inactive | `inactive.py task-N [-g group.txt]` | `inactive.csv` |
| mapping | `task_diff.py task-N` | `docs/task-mapping/task-N.md` |
| compare | `compare.py task-N [--baseline YEAR]` / `compare.py --all` | `compare.md`, `reports/` |
| history | `history.py --tasks task-1 ... task-N` | `reports/history-commits.md` |
| post | `feedback.py task-N [--post] [--student U] [--limit N]` | issues in student repos |

## Setup on a new machine

1. Clone this repository. Python 3.9+ is the only runtime; the scripts use the standard
   library only.
2. `gh auth login --hostname gits-15.sys.kth.se` with an account that can see the `inda-26`
   organisation (the scripts use `gh` for issues, the API and posting). `ice.py` checks this
   before it starts and tells you what is missing.
3. `repobee` configured for the host with `org_name = inda-26` (`repobee config show`); only
   needed for the clone step (`--no-clone` skips it). Clones land in `repos/2026/`
   (gitignored, created on first run).
4. `cohorts/2026.json` and `cohorts/current` are in git. The student list and the extracted
   data are only in the private working copy: on a fresh checkout run
   `python3 scripts/discover.py --students --write` to build `students/2026/students.txt`
   (and again when late registrations appear; the script reports additions/removals).
   Missing task config is discovered on the first weekly run.

## Your own exercise group (TAs)

- Put the usernames or KTH emails of your group one per line in a file (not committed) and
  pass it: `python3 scripts/inactive.py task-N -g group.txt` lists who in the group has no
  commits or no repository; `ice.py task-N --group group.txt` does the same inside the weekly
  run. Both read the clones under `repos/2026/`, so run the clone step (or `--no-clone` on a
  machine that already has them) first.
- `data/2026/task-N/nudges.csv` has every student's score, category and message; filter it
  by username. `python3 scripts/feedback.py task-N --student USERNAME` prints one student's
  message as a dry run.
- Leave `--post` to the course responsible. Posting is the only step that touches student
  repositories, and each posted row is marked in `nudges.csv` so a second run would skip it,
  but a stray post is still a real issue in a student's repo.

## The student guide

`ice-guide.md` is the master copy. The nudge footer links to the copy in
`inda-26/course-instructions`; the same file also lives in the `inda-master` template org and is
copied forward each year. After editing it here, push the same content to both.

## Re-running the 2025 baseline

`data/2025/` is the study baseline: `ice.py` refuses to re-extract for a cohort that is
not the current one. `compare.py` recomputes 2025 metrics from the stored raw CSVs
(`commits.csv`, `issues.csv`) so both years use identical code; the stored 2025
`effort.csv`/`nudges.csv` are what students received and stay untouched
(`--as-delivered` compares against those instead).

## Troubleshooting

- `gh` says no remote: the clone lacks `origin`; `issues.py` adds it from the cohort host/org.
- Rate limits: `issues.py` makes one API call per repo (~180); fine on GitHub Enterprise.
- A student renamed their repo/folder: `find_task_repos` only matches `*-task-N`
  folders under `repos/<year>/<user>/`; check `inactive.py`'s "no repo" list.
- Windows students with odd git author names: identity is the repo owner, not the git author.
