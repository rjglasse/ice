#!/usr/bin/env python3
"""Run the whole ICE week for one task: clone/update repos, extract, analyse, compare.

    python3 scripts/ice.py task-1              # clone/update + analysis, feedback dry run
    python3 scripts/ice.py task-1 --post       # ...and post the nudge issues to students
    python3 scripts/ice.py task-1 --no-clone   # reuse the local clones

Steps (each is also a standalone script):
  1. repobee repos clone --update-local   (repos/<year>/)      [--no-clone skips]
  1b. discover.py: teachers from org admins/template commits, deadline + exercises
      from the task READMEs (majority vote); fills missing/provisional config
  2. commits.py    -> data/<year>/<task>/commits.csv
  3. issues.py     -> issues.csv                                 [--skip-issues skips]
  4. effort.py     -> effort.csv
  5. nudges.py     -> nudges.csv
  6. inactive.py   -> inactive.csv (+ optional group check with --group)
  7. task_diff.py  -> docs/task-mapping/<task>.md (only if missing)
  8. compare.py    -> compare.md (+ reports/ overview across tasks)
     history.py    -> reports/history-commits.md (2020.. vs this year, tasks so far)
  9. feedback.py   dry run, or real posting with --post

Posting is the only step that writes to student repositories. Extraction for a
cohort that is not the current one is refused unless --allow-baseline-rewrite is given,
because data/2025 is the study's baseline.
"""

import argparse
import shutil
import subprocess
import sys
import time

import context


def banner(msg):
    print(f"\n{'=' * 70}\n{msg}\n{'=' * 70}")


def check_tools(cohort, need_clone, need_issues):
    problems = []
    if need_clone and not shutil.which('repobee'):
        problems.append('repobee not on PATH (needed for cloning; use --no-clone)')
    if need_issues:
        if not shutil.which('gh'):
            problems.append('gh not on PATH (needed for issues)')
        else:
            r = subprocess.run(['gh', 'auth', 'status', '--hostname', cohort.host], capture_output=True, text=True)
            if r.returncode != 0:
                problems.append(f'gh is not logged in to {cohort.host} (run: gh auth login --hostname {cohort.host})')
    if need_clone and (cohort.students_file is None or not cohort.students_file.exists()):
        problems.append(f'students file missing: {cohort.students_file}')
    return problems


def clone(cohort, task):
    cohort.repos_dir.mkdir(parents=True, exist_ok=True)
    cmd = ['repobee', 'repos', 'clone', '-a', task, '--students-file', str(cohort.students_file), '--update-local', '--dl', 'by-team']
    print('$', ' '.join(cmd), f'   (cwd {cohort.repos_dir})')
    r = subprocess.run(cmd, cwd=cohort.repos_dir)
    if r.returncode != 0:
        print(f"[ice] WARNING: repobee exited with {r.returncode}; continuing with whatever was cloned")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('--no-clone', action='store_true', help='skip repobee clone/update')
    p.add_argument('--skip-issues', action='store_true', help='skip the gh issue extraction')
    p.add_argument('--post', action='store_true', help='post nudge issues to student repos (default: dry run)')
    p.add_argument('--group', help='usernames/emails file for the inactive-students group check')
    p.add_argument('--baseline', type=int, default=2025)
    p.add_argument('--baseline-task', help='baseline task to compare against if tasks moved')
    p.add_argument('--allow-baseline-rewrite', action='store_true')
    p.add_argument('-q', '--quiet', action='store_true', help='less per-student output')
    context.add_cohort_arg(p)
    a = p.parse_args()

    cohort = context.load(a.cohort)
    baseline = context.load(a.baseline)
    task = a.task
    t0 = time.time()

    banner(f"ICE {cohort.year}/{task}  (org {cohort.org}, baseline {baseline.year})")
    if cohort.year != context.current_year() and not a.allow_baseline_rewrite:
        sys.exit(f"[ice] {cohort.year} is not the current cohort ({context.current_year()}). "
                 f"Re-extracting would overwrite baseline data; pass --allow-baseline-rewrite if you really mean it.")
    if cohort.task(task) is None:
        print(f"[ice] WARNING: {task} is not defined in cohorts/{cohort.year}.json (no deadline filter, 5 exercises assumed)")
    elif cohort.is_provisional(task):
        print(f"[ice] WARNING: {task} deadline/exercise count are PROVISIONAL in cohorts/{cohort.year}.json: "
              f"{cohort.task(task)}. Check the task README and remove the 'provisional' flag.")
    problems = check_tools(cohort, not a.no_clone, not a.skip_issues)
    for pr in problems:
        print(f"[ice] PROBLEM: {pr}")
    if problems:
        sys.exit(1)

    if not a.no_clone:
        banner('1. clone / update repositories')
        clone(cohort, task)

    import commits, issues, effort, nudges, inactive, compare, task_diff, feedback, discover, history

    banner('1b. discover config from the data')
    teachers = discover.discover_teachers(cohort, verbose=False)
    new_teachers = discover.apply_teachers(cohort, teachers)
    if new_teachers:
        print(f"[ice] new teachers found (org admins/template authors): {' '.join(new_teachers)}")
    found = discover.discover_task(cohort, task)
    change = discover.apply_task(cohort, task, found) if found else None
    if change:
        print(f"[ice] {change}")
    if new_teachers or (change and not change.startswith('KEPT')):
        cohort.save()
        cohort = context.load(cohort.year)
        print(f"[ice] saved cohorts/{cohort.year}.json")

    banner('2. commits')
    commits.run(task, cohort, quiet=a.quiet)
    if not a.skip_issues:
        banner('3. issues')
        issues.run(task, cohort, quiet=a.quiet)
    banner('4. effort')
    effort.run(task, cohort)
    banner('5. nudges')
    nudges.run(task, cohort, quiet=True)
    banner('6. inactive students')
    inactive.run(task, cohort, a.group)

    banner('7. task mapping')
    mapping = context.ROOT / 'docs' / 'task-mapping' / f'{task}.md'
    if mapping.exists():
        print(f"[ice] {mapping} exists (edit the 'comparable' column if not done)")
    else:
        try:
            task_diff.run(task, cohort, baseline, mapping.parent, 'inda-master')
        except SystemExit as e:
            print(f"[ice] task_diff skipped: {e}")

    banner(f'8. compare with {baseline.year}')
    compare.run(task, cohort, baseline, a.baseline_task, quiet=True)
    compare.run(None, cohort, baseline, all_tasks=True, quiet=True)
    done_tasks = sorted((p.name for p in cohort.data_dir.glob('task-*') if (p / 'commits.csv').exists()),
                        key=lambda t: int(t.split('-')[1]))
    dd1337 = [t for t in done_tasks if int(t.split('-')[1]) <= 9]
    if dd1337:
        print(f"[ice] history across cohorts for {', '.join(dd1337)}")
        try:
            history.run(cohort.year, dd1337)
        except SystemExit as e:
            print(f"[ice] history skipped: {e}")

    banner('9. feedback ' + ('(POSTING)' if a.post else '(dry run; add --post to publish)'))
    feedback.run(task, cohort, post=a.post)

    banner(f"done in {time.time() - t0:.0f}s")
    print(f"Review: data/{cohort.year}/{task}/compare.md and nudges.csv")
    print(f"Then:   git add data/{cohort.year} reports docs && git commit -m 'Weekly run {cohort.year} {task}'")
    if not a.post:
        print(f"Post:   python3 scripts/ice.py {task} --no-clone --skip-issues --post   (or feedback.py {task} --post)")


if __name__ == '__main__':
    main()
