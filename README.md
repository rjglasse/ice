# ICE

Issues, Commits, Effort (ICE) analyses student Git/Github behaviour and generates nudges as actionable feedback. Student-facing guidance lives in [ice-guide.md](/Users/ric/dev/ice/ice-guide.md).

## What ICE measures

ICE evaluates workflow across five dimensions:
- Planning through issue creation
- Coding activity through commits
- Completion through issue state
- Traceability through issue references in commit messages
- Automation through closing keywords such as `Fixes #12`

## Prerequisites

- Python 3
- `git`
- GitHub CLI (`gh`) for `scripts/issues.py` and `scripts/feedback.py`
- A local `repos/` directory containing student repositories

The scripts assume repositories are arranged under `repos/` in a student-first layout such as `repos/alice/alice-task-1`.

## Configuration

Edit [scripts/context.py](/Users/ric/dev/ice/scripts/context.py) to set:
- `course_start_date`
- `teachers` used for filtering
- `tasks` with deadlines and expected exercise counts

## Quick Start

1. Extract raw data for a task:

```bash
python3 scripts/commits.py task-1
python3 scripts/issues.py task-1
```

2. Derive metrics and generate nudges:

```bash
python3 scripts/effort.py task-1
python3 scripts/nudges.py task-1
```

3. Preview or publish feedback issues:

```bash
python3 scripts/feedback.py task-1 --dry-run
python3 scripts/feedback.py task-1
python3 scripts/feedback.py task-1 --student username
```

## Outputs

Generated files are written to `data/<task>/`:
- `commits.csv`: filtered commit data
- `issues.csv`: issue metadata collected through `gh`
- `effort.csv`: per-student workflow metrics
- `nudges.csv`: per-student feedback ready for issue creation
