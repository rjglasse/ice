# The 2026 confirmation study

## What 2025 showed (paper: *Nudging Better Version Control Behavior*, ITiCSE 2026, `paper/iticse26.tex`)

Four nudges were introduced in the 2025 run of the introductory Java course (DD1337, nine
weekly tasks; ICE data continued through DD1338, tasks 10-18):

1. **Expected workflow** taught in the first lecture and a "Make a Plan" section in every task README.
2. **Clickable issue links** in each exercise that pre-fill an issue.
3. **Individual feedback**: a weekly automated issue in each student's repo with the ICE
   nudges (planning, coding, completion, automation) and a workflow category.
4. **Cohort positioning**: the class distribution of categories with the student's own marked.

Findings, against historical controls 2020-2024 (same instructor, tasks, tooling):

- **RQ1** commits per student rose markedly in 2025 versus every prior cohort (Mann-Whitney U,
  Bonferroni-corrected), with more issue use and closing via commit messages.
- **RQ2** the effect held across all nine weeks: the *Workflow Master* share grew to about 70%
  of active students, with a dip in task 8 (open-ended game task) and a rebound in task 9.
  A low-engagement subgroup persisted throughout.
- **RQ3** survey (n=103, 52%): issue links and the expected workflow were the nudges students
  would keep; individual feedback was mixed (indifference among consistent high scorers, calls
  for more qualitative feedback); cohort positioning was the least valued (3 of 103 would keep it).

## What 2026 asks

The question is whether the 2025 effect was a **novelty effect pushed by an enthusiastic first
run**, or a stable property of the nudges. Design: the same course, same nudges, second run,
compared against 2025 (nudged) and, where the historical data is available, against 2020-2024
(un-nudged).

- **C1 (RQ1 repeated)** Does the 2026 cohort sit with 2025 rather than with 2020-2024 on commits
  and issues per student? The 2020-2024 controls (tasks 1-9) are in `data/<year>/`;
  `python3 scripts/history.py --tasks task-1 ... task-N` compares the tasks completed so far
  across all years (`reports/history-commits.md`, `--metric issues` for issues), and
  `compare.py task-N --baseline 2024` gives the task-level view against any control year.
- **C2 (RQ2 repeated)** Does the weekly category distribution follow the same trajectory
  (heterogeneous in task 1, Master dominant by mid-course, dip on the open-ended task)?
  `reports/compare-2026-vs-2025.md` gives the task-by-task view.
- **C3 (task level)** For each task, 2026 vs 2025 medians, Cliff's delta and Mann-Whitney p for
  commits, issues, closed issues, closing references, plus category shares
  (`data/2026/task-N/compare.md`).

This is a confirmation study, not a strict replication: tooling improvements that do not change
what students see are fine; changes to the treatment (message wording, scoring, the guide, the
cohort comparison) are recorded in `docs/improvements.md` with the date so effects can be
attributed.

## Threats and how the tooling handles them

| Threat | Handling |
|---|---|
| Tasks changed between years | `docs/task-mapping/task-N.md` per task; `compare.py --baseline-task` for moved content. |
| Closing keyword regex differed during 2025 tasks 1-8 (`fix #N` not counted) | `compare.py` recomputes 2025 from raw data with the current code; `--as-delivered` shows what students saw. |
| Different TAs / template authors | Teachers are discovered per cohort (org admins + template commit authors) and excluded from commits and issues. |
| Deadline drift | Cutoff = end of the exercise day, discovered from the README (majority vote over clones); manual override in `cohorts/2026.json`. |
| Plus-track split after task 2-3 (active students fall from ~190 to ~150) | Plus students do alternative tasks in other repositories and leave the dataset in both years (no activity in the `<user>-task-N` repos; `effort.csv` only lists students with a commit or issue). Report n per task; compare shares, not counts; track repos with no commits (`inactive.csv`) as the weekly drop-off signal. |
| Second-year instructor effect, word of mouth from 2025 students | Cannot be controlled; note in the write-up. |
| Metric gaming once the model is public | Scoring code removed from the guide for 2026 (IMP-11); category names and pillars unchanged. |

## Baseline numbers to keep in view (2025, as delivered)

Run `python3 scripts/compare.py --all --cohort 2025 --baseline 2025 --as-delivered -q` for the
per-task 2025 tables; the paper's headline figures are in `paper/figures/`.
