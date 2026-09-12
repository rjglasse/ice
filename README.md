# ICE

Issues, Commits, Effort (ICE) analyses student Git/GitHub behaviour in the KTH INDA courses
(DD1337 / DD1338) and posts weekly nudges as issues in each student's task repository. It
was introduced in 2025 and evaluated in *Nudging Better Version Control Behavior* (ITiCSE
2026, `paper/`). In 2026 it runs a second time as a confirmation study: does the effect hold
once the novelty is gone? See `docs/study-2026.md`.

## What ICE measures

Per student and task, from the repository and its issue tracker:

- **Planning**: issues created versus the number of exercises
- **Coding**: commits, and commits per issue
- **Completion**: open versus closed issues
- **Traceability**: commits that reference an issue (`#12`)
- **Automation**: commits that close an issue with a keyword (`Fixes #12`)

These feed a workflow score and category (Workflow Master ... Getting Started) and a nudge
message per student (`scripts/nudges.py`). The student-facing explanation is `ice-guide.md`.

## Weekly run

```bash
python3 scripts/ice.py task-N          # clone/update repos, extract, analyse, compare; feedback dry run
python3 scripts/ice.py task-N --post   # post the nudges
```

Full procedure and per-step scripts: `docs/runbook.md`.

## Trying it out

The public repository (`github.com/rjglasse/ice`) carries the tooling only. Student data
(`data/`, `students/`, `feedback/`, `reports/`) lives in the private working copy and is never
pushed; `scripts/publish.py` is what syncs the tooling out. To try ICE you therefore need
access to the course organisation:

1. `gh auth login --hostname gits-15.sys.kth.se` with an account that can see `inda-26`, and
   `repobee` configured for it (`docs/runbook.md`, "Setup on a new machine").
2. `python3 scripts/discover.py --students --write` to build `students/2026/students.txt`.
3. `python3 scripts/ice.py task-N` clones, extracts, analyses and ends with a feedback
   **dry run**. Read `data/2026/task-N/nudges.csv` (score, category, message per student).

To look at your own exercise group, put the usernames (or KTH emails) one per line in a
file and pass it: `inactive.py task-N -g group.txt` or `ice.py task-N --group group.txt`.

The comparison steps need the 2025 baseline and the 2020-2024 controls, which are not in
the public repository; `compare.py` and `history.py` report the missing data and skip.

Posting needs `--post` and is the course responsible's call: it writes an issue into every
student repository. Do not add it while trying things out.

ICE is configured for the regular-track organisation (`inda-26`) only. Plus-track students
do alternative tasks in other repositories and are not in the dataset (see
`docs/study-2026.md`); running ICE on another organisation would need its own cohort config,
and the loader currently keys cohorts by year.

## Layout

```
cohorts/        one JSON per cohort year 2020-2026 (org, course start, tasks: deadline + exercises),
                shared teachers.txt, and `current` (the year the scripts default to)
students/<y>/   student username lists
repos/<y>/      student clones, by-team layout (gitignored)
data/<y>/task-N/  commits.csv, issues.csv, effort.csv, plan.csv, nudges.csv, inactive.csv, compare.md
data/<y>/behaviour.csv  per student-task behavioural rows (behaviour.py)
reports/        markdown reports: weekly comparison, history, behaviour, plan styles
report/         the ACM-style working report (report.tex) with generated tables/ and figures/
docs/           runbook, study design, survey themes, improvements backlog, task mapping, analysis ideas
paper/          the ITiCSE 2026 paper source and figures
feedback/       the 2025 student survey (raw CSV)
scripts/        the tooling (see below)
```

`data/2020` to `data/2024` are the un-nudged control cohorts (tasks 1-9) and `data/2025/` the
nudged cohort from the paper; none of them is ever re-extracted by the tooling. `data/`,
`students/`, `feedback/`, `reports/`, `report/`, `paper/`, the per-task mapping files and
`docs/feedback-2025-themes.md` exist only in the private working copy (see "Trying it out").

## Scripts

| Script | Purpose |
|---|---|
| `ice.py` | the whole week in one command |
| `discover.py` | infer config from the data: teachers (org admins, template commit authors), students (repo owners), deadline and exercise count (README majority vote) |
| `commits.py`, `issues.py` | extract raw data from clones / `gh` |
| `effort.py` | per-student metrics |
| `plan.py` | how the student planned: default links, partial, own, mixed (from issue titles) |
| `nudges.py` | score, category, message; model v1 (2025) and v2 (2026) selected per cohort |
| `inactive.py` | students without commits, optional group check |
| `feedback.py` | post nudges as issues (dry run by default) |
| `compare.py` | this cohort vs a baseline year per task and across tasks |
| `history.py` | commits (or issues) per student by cohort, 2020 to now |
| `behaviour.py` | commit shape, message quality, issue fidelity and pacing per cohort |
| `report.py` | regenerate all report tables and figures and build `report/report.pdf` |
| `publish.py` | sync the tooling (allowlisted files, cohort configs without names) onto the `public` branch; `--push` sends it to origin |
| `task_diff.py` | exercise-level diff of a task README between years |
| `context.py`, `common.py` | cohort loader and shared helpers |

All scripts take the task name and `--cohort YEAR`; `-h` documents the rest.

## Configuration

`cohorts/2026.json` needs `org`, `course_start` and `students_file` (`host` defaults to
`gits-15.sys.kth.se`; `nudge_model` selects the v1 or v2 message model, default v1). Everything
else is discovered on the first weekly run and written back: task deadlines and exercise counts from
the task READMEs (majority vote across clones guards against edited READMEs), teachers from
the organisation's admins and the authors of template commits, students from the
organisation's `<user>-task-N` repositories. A value you type into the JSON wins over
discovery; a value marked `"provisional": true` does not.

Requirements: Python 3.9+ (standard library only), `git`, `gh` (logged in to the cohort host,
for issues and posting), `repobee` (for cloning), `latexmk` (optional, only for the PDF in
`report.py`).
