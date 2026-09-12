#!/usr/bin/env python3
"""Cohort-level history: commits per student per year, the paper's RQ1 view, extended to 2026.

For every cohort with data under data/<year>/task-1..task-9 (DD1337 only, as in the paper),
sum each student's commits over the tasks, keep students with at least one commit, and report
the distribution per year plus Mann-Whitney U (Bonferroni-corrected over the number of
comparisons) and Cliff's delta of the focal cohort against every other year. With --tasks you
can restrict to the tasks completed so far in the focal year, so a mid-course 2026 can be
compared like-for-like (e.g. --tasks task-1 task-2).

Output: reports/history-commits.md (and the same for issues with --metric issues).
"""

import argparse
import statistics
from collections import defaultdict

import context
from common import read_csv
from compare import mann_whitney, cliffs_delta, quartiles, fmt

DD1337_TASKS = [f'task-{i}' for i in range(1, 10)]


def per_student(cohort, tasks, metric):
    totals = defaultdict(int)
    present = []
    for t in tasks:
        f = cohort.task_data_dir(t) / ('commits.csv' if metric == 'commits' else 'issues.csv')
        if not f.exists():
            continue
        present.append(t)
        for r in read_csv(f):
            totals[r['author']] += 1
    return {a: n for a, n in totals.items() if n > 0}, present


def run(focal_year, tasks, metric='commits', years=None):
    years = years or context.available_years()
    focal = context.load(focal_year)
    data = {}
    skipped = []
    for y in years:
        c = context.load(y)
        vals, present = per_student(c, tasks, metric)
        if not vals:
            continue
        if len(present) < len(tasks):
            skipped.append(f"{y} (has {len(present)} of {len(tasks)} tasks)")
            continue
        data[y] = (sorted(vals.values()), present)
    if focal_year not in data:
        raise SystemExit(f"[history] no {metric} data for {focal_year} in tasks {tasks}")
    fv = data[focal_year][0]
    n_comp = max(1, len(data) - 1)
    L = [f"# {metric.capitalize()} per student by cohort", '',
         f"Tasks: {', '.join(data[focal_year][1])}. Students with ≥1 {metric[:-1]} in those tasks. "
         f"Tests: {focal_year} vs each year, two-sided Mann-Whitney U, Bonferroni × {n_comp}.", '',
         f"| Year | n | median (IQR) | mean | max | Cliff's δ vs {focal_year} | p (adj) |", '|---|---|---|---|---|---|---|']
    for y in sorted(data):
        v, present = data[y]
        q1, med, q3 = quartiles(v)
        if y == focal_year:
            L.append(f"| **{y}** | {len(v)} | {fmt(med)} ({fmt(q1)}–{fmt(q3)}) | {fmt(statistics.mean(v))} | {max(v)} | | |")
        else:
            _, p = mann_whitney(fv, v)
            d = cliffs_delta(fv, v)
            L.append(f"| {y} | {len(v)} | {fmt(med)} ({fmt(q1)}–{fmt(q3)}) | {fmt(statistics.mean(v))} | {max(v)} | {fmt(d, 2)} | {fmt(min(1.0, p * n_comp), 4)} |")
    L += ['', "δ > 0: the focal year tends to be higher. 2025 introduced the nudges; 2020–2024 are un-nudged controls."]
    if skipped:
        L.append(f"Cohorts without all of these tasks were left out: {', '.join(skipped)}.")
    text = '\n'.join(L) + '\n'
    tex = ["\\begin{tabular}{lrrrrr}", "\\toprule", f"Year & $n$ & median (IQR) & mean & Cliff's $\\delta$ vs {focal_year} & $p$ (adj.) \\\\", "\\midrule"]
    for y in sorted(data):
        v, present = data[y]
        q1, m, q3 = quartiles(v)
        if y == focal_year:
            tex.append(f"\\textbf{{{y}}} & {len(v)} & {fmt(m)} ({fmt(q1)}--{fmt(q3)}) & {fmt(statistics.mean(v))} & -- & -- \\\\")
        else:
            _, p = mann_whitney(fv, v)
            tex.append(f"{y} & {len(v)} & {fmt(m)} ({fmt(q1)}--{fmt(q3)}) & {fmt(statistics.mean(v))} & {fmt(cliffs_delta(fv, v), 2)} & {fmt(min(1.0, p * n_comp), 4)} \\\\")
    tex += ["\\bottomrule", "\\end{tabular}"]
    tdir = context.ROOT / 'report' / 'tables'
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f'history_{metric}_{focal_year}.tex').write_text('\n'.join(tex) + '\n', encoding='utf-8')
    out = context.ROOT / 'reports' / f'history-{metric}.md'
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding='utf-8')
    print(text)
    print(f"[history] wrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--tasks', nargs='+', default=DD1337_TASKS, help='tasks to sum over (default task-1..task-9)')
    p.add_argument('--metric', choices=['commits', 'issues'], default='commits')
    p.add_argument('--years', nargs='+', type=int, help='cohorts to include (default: all with configs)')
    context.add_cohort_arg(p)
    a = p.parse_args()
    run(a.cohort or context.current_year(), a.tasks, a.metric, a.years)


if __name__ == '__main__':
    main()
