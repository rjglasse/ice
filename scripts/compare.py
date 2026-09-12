#!/usr/bin/env python3
"""Compare one task (or all tasks) of a cohort against a baseline cohort.

By default per-student metrics for BOTH cohorts are recomputed from the stored raw
data (commits.csv + issues.csv) with the current effort.py/nudges.py code, so that
both years are measured with identical definitions ("recomputed baseline"). The
stored 2025 effort/nudges files are what students actually received and are left
untouched; pass --as-delivered to compare against those instead. Note that during
tasks 1-8 of 2025 the closing-keyword regex did not count bare `fix #N`/`close #N`,
which is why the two views differ slightly for those tasks (docs/improvements.md).

Outputs: data/<year>/<task>/compare.md (single task) or
reports/compare-<year>-vs-<baseline>.md (--all).
"""

import argparse
import math
import statistics
from pathlib import Path

import context
import effort
import nudges
from common import read_csv

METRICS = [('commits', 'Commits'), ('issues', 'Issues'), ('closed_issues', 'Closed issues'),
           ('closing_references', 'Closing references'), ('references', 'Issue references')]


# --- statistics (pure python, no scipy dependency) ---------------------------
def _normal_sf(z):
    return 0.5 * math.erfc(z / math.sqrt(2))


def mann_whitney(x, y):
    """Two-sided Mann-Whitney U with tie correction (normal approximation). Returns (U, p)."""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float('nan'), float('nan')
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(allv)
    i = 0
    tie_term = 0.0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        t = j - i + 1
        if t > 1:
            tie_term += t ** 3 - t
        i = j + 1
    r1 = sum(r for r, (v, g) in zip(ranks, allv) if g == 0)
    u1 = r1 - n1 * (n1 + 1) / 2
    n = n1 + n2
    mu = n1 * n2 / 2
    sigma_sq = n1 * n2 / 12 * ((n + 1) - tie_term / (n * (n - 1)))
    if sigma_sq <= 0:
        return u1, 1.0
    z = (u1 - mu) / math.sqrt(sigma_sq)
    return u1, min(1.0, 2 * _normal_sf(abs(z)))


def cliffs_delta(x, y):
    """P(x > y) - P(x < y); positive means x tends to be larger."""
    if not x or not y:
        return float('nan')
    ys = sorted(y)
    import bisect
    gt = lt = 0
    for v in x:
        lt += len(ys) - bisect.bisect_right(ys, v)
        gt += bisect.bisect_left(ys, v)
    return (gt - lt) / (len(x) * len(y))


def quartiles(values):
    if not values:
        return (float('nan'),) * 3
    s = sorted(values)
    q = statistics.quantiles(s, n=4) if len(s) > 1 else [s[0], s[0], s[0]]
    return q[0], statistics.median(s), q[2]


# --- data loading -------------------------------------------------------------
def load_students(cohort, task, as_delivered=False):
    """Per-student metric rows (ints) for cohort/task, plus provenance string."""
    d = cohort.task_data_dir(task)
    commits_f, issues_f, effort_f = d / 'commits.csv', d / 'issues.csv', d / 'effort.csv'
    if not as_delivered and commits_f.exists() and issues_f.exists():
        rows = effort.calculate(read_csv(commits_f), read_csv(issues_f), strict=True)
        prov = 'recomputed from commits.csv + issues.csv, commits after the deadline excluded'
    elif effort_f.exists():
        rows = read_csv(effort_f)
        prov = 'stored effort.csv (as delivered)'
    else:
        return [], 'no data'
    out = []
    for r in rows:
        out.append({k: int(r[k]) for k in ['commits', 'issues', 'open_issues', 'closed_issues', 'references', 'closing_references']}
                   | {'author': r['author']})
    return out, prov


def load_inactive(cohort, task):
    f = cohort.task_data_dir(task) / 'inactive.csv'
    if not f.exists():
        return None
    rows = read_csv(f)
    return len(rows), sum(1 for r in rows if r['has_commits'].lower() != 'true')


def summarise(students, expected):
    n = len(students)
    if n == 0:
        return {}
    active = [s for s in students if s['commits'] > 0]
    def pct(cond):
        return 100 * sum(1 for s in students if cond(s)) / n
    s = {'n': n, 'n_active': len(active)}
    for key, _ in METRICS:
        vals = [x[key] for x in students]
        q1, med, q3 = quartiles(vals)
        s[key] = {'mean': statistics.mean(vals), 'median': med, 'q1': q1, 'q3': q3, 'values': vals}
    s['pct_any_issue'] = pct(lambda x: x['issues'] > 0)
    s['pct_planned'] = pct(lambda x: x['issues'] >= expected)
    s['pct_all_closed'] = pct(lambda x: x['issues'] > 0 and x['open_issues'] == 0)
    s['pct_closing_ref'] = pct(lambda x: x['closing_references'] > 0)
    s['pct_ref'] = pct(lambda x: x['references'] > 0)
    ratios = [x['commits'] / x['issues'] for x in students if x['issues'] > 0]
    s['median_commits_per_issue'] = statistics.median(ratios) if ratios else float('nan')
    cats = {c: 0 for c in nudges.CATEGORIES}
    for x in students:
        cats[nudges.classify_workflow_performance(x, expected)] += 1
    s['classes'] = {c: 100 * v / n for c, v in cats.items()}
    return s


def fmt(v, nd=1):
    if isinstance(v, float):
        if math.isnan(v):
            return 'n/a'
        return f'{v:.{nd}f}'
    return str(v)


def compare_task(task, cohort, baseline, baseline_task=None, as_delivered=False):
    baseline_task = baseline_task or task
    new, new_prov = load_students(cohort, task, as_delivered)
    old, old_prov = load_students(baseline, baseline_task, as_delivered)
    if not new or not old:
        return None, f"[compare] missing data: {cohort.year}/{task} ({new_prov}), {baseline.year}/{baseline_task} ({old_prov})"
    ne, oe = cohort.expected_exercises(task), baseline.expected_exercises(baseline_task)
    S, B = summarise(new, ne), summarise(old, oe)
    tests = {}
    for key, _ in METRICS:
        u, p = mann_whitney(S[key]['values'], B[key]['values'])
        tests[key] = (p, cliffs_delta(S[key]['values'], B[key]['values']))
    result = {'task': task, 'baseline_task': baseline_task, 'new': S, 'old': B, 'tests': tests,
              'new_expected': ne, 'old_expected': oe, 'new_prov': new_prov, 'old_prov': old_prov,
              'new_inactive': load_inactive(cohort, task), 'old_inactive': load_inactive(baseline, baseline_task),
              'mapping': mapping_note(task, cohort)}
    return result, None


def mapping_note(task, cohort):
    f = context.ROOT / 'docs' / 'task-mapping' / f'{task}.md'
    if not f.exists():
        return f'no mapping file (run `python3 scripts/task_diff.py {task}`)'
    yes = changed = no = 0
    for line in f.read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) >= 4 and cells[0] not in ('', f'{cohort.year} exercise') and not cells[0].startswith('---'):
            flag = cells[3].lower()
            if flag.startswith('yes'):
                yes += 1
            elif flag.startswith('changed'):
                changed += 1
            elif flag.startswith('no'):
                no += 1
    return f'exercises: {yes} comparable, {changed} changed, {no} new/removed (docs/task-mapping/{task}.md)'


def render_task(r, cohort, baseline):
    S, B = r['new'], r['old']
    y, b = cohort.year, baseline.year
    L = [f"# {r['task']}: {y} vs {b}" + (f" ({b} {r['baseline_task']})" if r['baseline_task'] != r['task'] else ''), '',
         f"- {y}: {S['n']} students with activity ({S['n_active']} with commits), expected exercises {r['new_expected']}; {r['new_prov']}",
         f"- {b}: {B['n']} students with activity ({B['n_active']} with commits), expected exercises {r['old_expected']}; {r['old_prov']}"]
    for label, inact in ((y, r['new_inactive']), (b, r['old_inactive'])):
        if inact:
            L.append(f"- {label}: {inact[1]} of {inact[0]} repositories had no commits (inactive.csv)")
    L += [f"- Task mapping: {r['mapping']}", '',
          f"| Metric | {y} median (IQR) | {b} median (IQR) | {y} mean | {b} mean | Cliff's δ | MWU p |", '|---|---|---|---|---|---|---|']
    for key, label in METRICS:
        s, o = S[key], B[key]
        p, d = r['tests'][key]
        L.append(f"| {label} | {fmt(s['median'])} ({fmt(s['q1'])}–{fmt(s['q3'])}) | {fmt(o['median'])} ({fmt(o['q1'])}–{fmt(o['q3'])}) "
                 f"| {fmt(s['mean'])} | {fmt(o['mean'])} | {fmt(d, 2)} | {fmt(p, 3)} |")
    L += ['', f"| Share of students | {y} | {b} |", '|---|---|---|']
    for key, label in [('pct_any_issue', '≥1 issue'), ('pct_planned', 'issues ≥ expected exercises'),
                       ('pct_all_closed', 'all issues closed'), ('pct_ref', '≥1 commit referencing an issue'),
                       ('pct_closing_ref', '≥1 closing keyword')]:
        L.append(f"| {label} | {fmt(S[key])}% | {fmt(B[key])}% |")
    L.append(f"| median commits per issue | {fmt(S['median_commits_per_issue'], 2)} | {fmt(B['median_commits_per_issue'], 2)} |")
    L += ['', f"| Workflow category | {y} | {b} |", '|---|---|---|']
    for c in nudges.CATEGORIES:
        L.append(f"| {c} | {fmt(S['classes'][c])}% | {fmt(B['classes'][c])}% |")
    L += ['', "Cliff's δ > 0 means the new cohort tends to be higher. The p-value is a two-sided Mann-Whitney U",
          "(normal approximation, tie-corrected), uncorrected for multiple tasks; the paper used Bonferroni across cohorts."]
    return '\n'.join(L) + '\n'


def render_overview(results, cohort, baseline, as_delivered):
    y, b = cohort.year, baseline.year
    L = [f"# Weekly comparison {y} vs {b}", '',
         f"Baseline view: {'as delivered (stored effort.csv)' if as_delivered else 'recomputed from raw data with current code'}. "
         f"Per-task detail: `data/{y}/<task>/compare.md`.", '',
         f"| Task | n {y} | n {b} | commits med {y}/{b} | issues med {y}/{b} | closing refs med {y}/{b} | ≥1 closing kw {y}/{b} | Master {y}/{b} | δ commits | p commits | mapping |",
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for r in results:
        S, B = r['new'], r['old']
        p, d = r['tests']['commits']
        L.append(f"| {r['task']} | {S['n']} | {B['n']} | {fmt(S['commits']['median'])}/{fmt(B['commits']['median'])} "
                 f"| {fmt(S['issues']['median'])}/{fmt(B['issues']['median'])} | {fmt(S['closing_references']['median'])}/{fmt(B['closing_references']['median'])} "
                 f"| {fmt(S['pct_closing_ref'], 0)}%/{fmt(B['pct_closing_ref'], 0)}% | {fmt(S['classes'][nudges.CATEGORIES[0]], 0)}%/{fmt(B['classes'][nudges.CATEGORIES[0]], 0)}% "
                 f"| {fmt(d, 2)} | {fmt(p, 3)} | {r['mapping'].split(' (')[0]} |")
    return '\n'.join(L) + '\n'


def run(task, cohort, baseline, baseline_task=None, as_delivered=False, all_tasks=False, quiet=False):
    if all_tasks:
        tasks = sorted((p.name for p in cohort.data_dir.glob('task-*') if (p / 'commits.csv').exists() or (p / 'effort.csv').exists()),
                       key=lambda t: int(t.split('-')[1]))
    else:
        tasks = [task]
    results = []
    for t in tasks:
        r, err = compare_task(t, cohort, baseline, baseline_task if not all_tasks else None, as_delivered)
        if err:
            print(err)
            continue
        results.append(r)
        out = cohort.task_data_dir(t) / 'compare.md'
        out.parent.mkdir(parents=True, exist_ok=True)
        text = render_task(r, cohort, baseline)
        out.write_text(text, encoding='utf-8')
        if not quiet:
            print(text)
        print(f"[compare] wrote {out}")
    if all_tasks and results:
        rep = context.ROOT / 'reports' / f'compare-{cohort.year}-vs-{baseline.year}.md'
        rep.parent.mkdir(exist_ok=True)
        rep.write_text(render_overview(results, cohort, baseline, as_delivered), encoding='utf-8')
        print(f"[compare] wrote {rep}")
        y, b = cohort.year, baseline.year
        tex = ["\\begin{tabular}{lrrrrrrr}", "\\toprule",
               f"Task & $n$ {y}/{b} & commits {y}/{b} & issues {y}/{b} & closing refs {y}/{b} & $\\geq$1 closing kw {y}/{b} & Master {y}/{b} & $\\delta$, $p$ (commits) \\\\", "\\midrule"]
        for r in results:
            S, B = r['new'], r['old']
            p_, d = r['tests']['commits']
            tex.append(f"{r['task']} & {S['n']}/{B['n']} & {fmt(S['commits']['median'])}/{fmt(B['commits']['median'])} & {fmt(S['issues']['median'])}/{fmt(B['issues']['median'])} "
                       f"& {fmt(S['closing_references']['median'])}/{fmt(B['closing_references']['median'])} & {fmt(S['pct_closing_ref'], 0)}\\%/{fmt(B['pct_closing_ref'], 0)}\\% "
                       f"& {fmt(S['classes'][nudges.CATEGORIES[0]], 0)}\\%/{fmt(B['classes'][nudges.CATEGORIES[0]], 0)}\\% & {fmt(d, 2)}, {fmt(p_, 3)} \\\\")
        tex += ["\\bottomrule", "\\end{tabular}"]
        tdir = context.ROOT / 'report' / 'tables'
        tdir.mkdir(parents=True, exist_ok=True)
        (tdir / f'weekly_{y}_vs_{b}.tex').write_text('\n'.join(tex) + '\n', encoding='utf-8')
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', nargs='?', help='task name, e.g. task-1 (omit with --all)')
    p.add_argument('--all', action='store_true', help='every task with data for the cohort; also writes reports/')
    p.add_argument('--baseline', type=int, default=2025)
    p.add_argument('--baseline-task', help='compare against a different task of the baseline (tasks moved)')
    p.add_argument('--as-delivered', action='store_true', help='use stored effort.csv instead of recomputing')
    p.add_argument('-q', '--quiet', action='store_true')
    context.add_cohort_arg(p)
    a = p.parse_args()
    if not a.task and not a.all:
        p.error('give a task or --all')
    run(a.task, context.load(a.cohort), context.load(a.baseline), a.baseline_task, a.as_delivered, a.all, a.quiet)


if __name__ == '__main__':
    main()
