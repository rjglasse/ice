#!/usr/bin/env python3
"""Plan features: how a student planned, not just how much.

Reads commits.csv and issues.csv for a task and derives per student:
  issues            number of issues
  default_issues    titles that are the README exercise heading (opened via the issue links)
  custom_issues     titles in the student's own words (warmup issues excluded)
  covered           exercises referenced in issue titles, ranges included ("1.1-1.3")
  linked_issues     issues that at least one commit references (#N)
  planned_ahead     issues created before the student's first commit of the task
  plan_style        default-complete | default-partial | own | mixed | none

Output: data/<year>/<task>/plan.csv. The style is meant to preserve agency: a student who
grouped exercises or wrote their own issues is not told to "make more issues".
"""

import argparse
import re
from collections import defaultdict
from datetime import datetime as dt

import context
from common import read_csv, write_csv, parse_git_datetime

FIELDS = ['author', 'issues', 'default_issues', 'custom_issues', 'grouped_issues', 'warmup_issues',
          'covered', 'expected', 'linked_issues', 'planned_ahead', 'plan_style']


def exercise_numbers(task):
    return task.split('-')[1]


def make_classifier(cohort, task):
    t = cohort.task(task) or {}
    n_task = exercise_numbers(task)
    link_titles = t.get('link_titles')
    listed = t.get('exercise_list')
    if not link_titles or not listed:  # manual config: discover from clones or the template README
        import discover
        found = discover.discover_task(cohort, task, verbose=False) or {}
        link_titles = link_titles or found.get('link_titles', [])
        listed = listed or found.get('exercise_list', [])
    norm = lambda x: re.sub(r'[^a-z0-9]+', '', x.lower())
    defaults = {norm(x) for x in link_titles}
    titles = {}
    for e in listed:
        num, _, title = e.partition(' ')
        titles[num] = title
    expected = cohort.expected_exercises(task)
    num_re = re.compile(rf'\b{n_task}\.(\d+(?:\.\d+)?)\b')
    range_re = re.compile(rf'\b{n_task}\.(\d+)\s*[-–]\s*(?:{n_task}\.)?(\d+)\b')

    def classify(title):
        s = title.strip()
        low = s.lower()
        found = set()
        for a, b in range_re.findall(s):
            found |= {f'{n_task}.{i}' for i in range(int(a), int(b) + 1)}
        found |= {f'{n_task}.{m}' for m in num_re.findall(s)}
        if 'warmup' in low or 'code of conduct' in low or 'my first issue' in low or low.startswith('task ' + n_task):
            return 'warmup', found
        if len(found) >= 2:
            return 'grouped', found
        ns = norm(s)
        if ns in defaults or (s.startswith('"') and any(d.startswith(ns) for d in defaults)):
            return 'default', found
        if len(found) == 1 and not defaults:  # no link titles known: fall back to heading match
            ref = titles.get(next(iter(found)), '')
            core = re.sub(r'^exercise\s+[\d.]+\s*(--|-|—|:)?\s*', '', low)
            if ref and core.strip('`') == ref.lower().strip('`'):
                return 'default', found
        return 'custom', found

    return classify, expected


def features(commits, issues, classify, expected):
    by = defaultdict(lambda: {'issues': 0, 'default_issues': 0, 'custom_issues': 0, 'grouped_issues': 0,
                              'warmup_issues': 0, 'covered': set(), 'numbers': set(), 'created': []})
    first_commit = {}
    refs = defaultdict(set)
    for c in commits:
        a = c['author']
        when = parse_git_datetime(c['datetime'])
        first_commit[a] = min(first_commit.get(a, when), when)
        refs[a] |= {int(n) for n in re.findall(r'#(\d+)', c['subject'])}
    for i in issues:
        a = i['author']
        kind, found = classify(i['title'])
        f = by[a]
        f['issues'] += 1
        f[f'{kind}_issues'] += 1
        f['covered'] |= found
        f['numbers'].add(int(i['number']))
        try:
            f['created'].append(dt.fromisoformat(i['createdAt'].replace('Z', '+00:00')).replace(tzinfo=None))
        except (ValueError, AttributeError, KeyError):
            pass
    rows = []
    for a in sorted(set(by) | set(first_commit)):
        f = by[a]
        n = f['issues']
        linked = len(f['numbers'] & refs[a])
        fc = first_commit.get(a)
        ahead = sum(1 for t in f['created'] if fc and t <= fc) if fc else 0
        real = n - f['warmup_issues']
        if real == 0:
            style = 'none'
        elif f['custom_issues'] + f['grouped_issues'] == 0:
            style = 'default-complete' if f['default_issues'] >= expected else 'default-partial'
        elif f['default_issues'] == 0:
            style = 'own'
        else:
            style = 'mixed'
        rows.append({'author': a, 'issues': n, 'default_issues': f['default_issues'], 'custom_issues': f['custom_issues'],
                     'grouped_issues': f['grouped_issues'], 'warmup_issues': f['warmup_issues'],
                     'covered': len(f['covered']), 'expected': expected, 'linked_issues': linked,
                     'planned_ahead': ahead, 'plan_style': style})
    return rows


def run(task, cohort, quiet=False):
    d = cohort.task_data_dir(task)
    classify, expected = make_classifier(cohort, task)
    # a first run with --skip-issues (or no clones yet) may lack one of the files: treat as empty
    commits = read_csv(d / 'commits.csv') if (d / 'commits.csv').exists() else []
    issues = read_csv(d / 'issues.csv') if (d / 'issues.csv').exists() else []
    rows = features(commits, issues, classify, expected)
    out = d / 'plan.csv'
    write_csv(out, rows, FIELDS)
    from collections import Counter
    styles = Counter(r['plan_style'] for r in rows)
    n = len(rows) or 1
    print(f"[plan] {cohort.year}/{task}: {len(rows)} students -> {out}")
    for s in ['default-complete', 'default-partial', 'mixed', 'own', 'none']:
        print(f"  {s:17} {styles[s]:4} ({100 * styles[s] // n}%)")
    with_issues = [r for r in rows if r['issues'] > 0]
    if with_issues:
        ahead = sum(1 for r in with_issues if r['planned_ahead'] == r['issues'])
        linked = sum(1 for r in with_issues if r['linked_issues'] > 0)
        print(f"  all issues opened before first commit: {100 * ahead // len(with_issues)}%; "
              f"at least one issue referenced by a commit: {100 * linked // len(with_issues)}%")
    return rows


STYLES = ['default-complete', 'default-partial', 'mixed', 'own', 'none']


def trend(cohort, tasks):
    """Plan style per task and week-to-week transitions for a cohort; nothing is written under data/."""
    from collections import Counter
    per_task = {}
    for t in tasks:
        d = cohort.task_data_dir(t)
        if not (d / 'issues.csv').exists() or not (d / 'commits.csv').exists():
            continue
        classify, expected = make_classifier(cohort, t)
        rows = features(read_csv(d / 'commits.csv'), read_csv(d / 'issues.csv'), classify, expected)
        per_task[t] = {r['author']: r for r in rows}
    tasks = [t for t in tasks if t in per_task]
    L = [f"# Plan styles by task, {cohort.year}", '',
         "Style from issue titles versus the README's pre-filled link titles (`plan.py`). Students with ≥1 commit or issue.", '',
         "| Task | n | " + " | ".join(STYLES) + " | all issues before first commit | ≥1 issue referenced by a commit |",
         "|---|---|" + "---|" * (len(STYLES) + 2)]
    for t in tasks:
        rows = list(per_task[t].values())
        n = len(rows) or 1
        c = Counter(r['plan_style'] for r in rows)
        wi = [r for r in rows if r['issues'] > 0] or [None]
        ahead = sum(1 for r in wi if r and r['planned_ahead'] == r['issues'])
        linked = sum(1 for r in wi if r and r['linked_issues'] > 0)
        L.append(f"| {t} | {len(rows)} | " + " | ".join(f"{100 * c[s] // n}%" for s in STYLES)
                 + f" | {100 * ahead // len(wi)}% | {100 * linked // len(wi)}% |")
    L += ['', "## Week-to-week transitions (row: style in task N, column: style in task N+1, all consecutive pairs pooled)", '']
    trans = Counter()
    for a, b in zip(tasks, tasks[1:]):
        for author, r in per_task[a].items():
            nxt = per_task[b].get(author)
            if nxt:
                trans[(r['plan_style'], nxt['plan_style'])] += 1
    L.append("| from \\ to | " + " | ".join(STYLES) + " | n |")
    L.append("|---|" + "---|" * (len(STYLES) + 1))
    for s in STYLES:
        n = sum(trans[(s, t)] for t in STYLES) or 1
        L.append(f"| {s} | " + " | ".join(f"{100 * trans[(s, t)] // n}%" for t in STYLES) + f" | {n} |")
    stay_own = sum(trans[(s, t)] for s in ('own', 'mixed') for t in ('own', 'mixed'))
    to_default = sum(trans[(s, t)] for s in ('own', 'mixed') for t in ('default-complete', 'default-partial'))
    L += ['', f"Own/mixed planners next week: stayed own/mixed {stay_own}, switched to the default links {to_default}, "
          f"no plan {sum(trans[(s, 'none')] for s in ('own', 'mixed'))}."]
    text = '\n'.join(L) + '\n'
    out = context.ROOT / 'reports' / f'plan-styles-{cohort.year}.md'
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding='utf-8')
    print(text)
    print(f"[plan] wrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', nargs='?')
    p.add_argument('--trend', action='store_true', help='style per task and transitions for the cohort -> reports/')
    p.add_argument('--tasks', nargs='+', help='tasks for --trend (default: all in the cohort config)')
    p.add_argument('-q', '--quiet', action='store_true')
    context.add_cohort_arg(p)
    a = p.parse_args()
    cohort = context.load(a.cohort)
    if a.trend:
        tasks = a.tasks or sorted(cohort.tasks, key=lambda t: int(t.split('-')[1]))
        trend(cohort, tasks)
    elif a.task:
        run(a.task, cohort, a.quiet)
    else:
        p.error('give a task or --trend')


if __name__ == '__main__':
    main()
