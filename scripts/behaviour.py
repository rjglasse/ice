#!/usr/bin/env python3
"""Behavioural profile of a cohort's commits and issues, comparable across years.

Answers "how did their commits look, and did they stay true to the issues?" with
per-cohort tables over tasks 1-9 (the DD1337 course studied in the paper):

  commit shape     commits per student-task, lines changed per commit, tiny/large commits
  messages         words per subject, generic messages ("done", "a"), GitHub web-UI defaults
                   ("Update Foo.java"), issue references, closing keywords, bare "Fixes #N"
                   messages, batch closes (one commit closing several issues)
  issue fidelity   (cohorts with issues) commits referencing an issue, issues referenced by
                   at least one commit, issues closed with a keyword, referenced issues that
                   were opened only after the referencing commit (retrofitted plan)
  pacing           active days and work sessions per student-task, share of commits in the
                   last 24 h before the deadline, first commit >= 3 days before the deadline,
                   night commits (00-06)

Per-student-task metrics are tested with Mann-Whitney U, focal year vs the pooled other
years (Cliff's delta reported). Outputs: reports/behaviour.md, report/tables/behaviour_*.tex,
and the per-student-task rows as data/<year>/behaviour.csv for further analysis.
"""

import argparse
import re
import statistics
from collections import defaultdict
from datetime import datetime as dt

import context
from common import read_csv, write_csv, parse_git_datetime
from compare import mann_whitney, cliffs_delta, fmt
from effort import CLOSING_RE, REFERENCE_RE

TASKS = [f'task-{i}' for i in range(1, 10)]
GENERIC = {'a', 'asd', 'asdf', 'test', 'tests', 'done', 'update', 'updated', 'fix', 'fixed', 'fixes', 'commit',
           'changes', 'change', 'stuff', 'wip', 'work', 'save', 'hej', 'hello', 'first commit', 'initial commit',
           'final', 'klar', 'färdig', 'ok', 'yes', 'x', '.', '-', 'push', 'upload', 'added', 'add', 'new', 'things'}
WEB_UI_RE = re.compile(r'^(add files via upload|update [^ ]+|create [^ ]+|delete [^ ]+|rename [^ ]+( to [^ ]+)?)$', re.IGNORECASE)
BARE_CLOSE_RE = re.compile(r'^\W*(?:(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#?\s*\d+(?:\s*(?:,|and|&|\+)?\s*#?\d+)*\W*)+$', re.IGNORECASE)
SESSION_GAP_H = 2


def student_task_rows(cohort, task):
    """Per commit and per student rows for one task, strict window (<= deadline), teachers excluded upstream."""
    d = cohort.task_data_dir(task)
    if not (d / 'commits.csv').exists():
        return [], {}, []
    commits = [c for c in read_csv(d / 'commits.csv') if str(c.get('after_deadline', 'False')).lower() != 'true']
    issues = read_csv(d / 'issues.csv') if (d / 'issues.csv').exists() else []
    deadline = cohort.deadline(task)
    by_student = defaultdict(list)
    for c in commits:
        c['_t'] = parse_git_datetime(c['datetime'])
        c['_lines'] = int(c['total'])
        subj = c['subject'].strip()
        c['_refs'] = [int(n) for n in REFERENCE_RE.findall(subj)]
        c['_closing'] = [int(n) for n in CLOSING_RE.findall(subj)]
        stripped = re.sub(r'(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#?\s*\d+', ' ', subj, flags=re.IGNORECASE)
        stripped = re.sub(r'#\d+|\b(?:and|&|\+|,)\b', ' ', stripped)
        c['_words'] = len([w for w in re.split(r'[\s,]+', stripped) if re.search(r'[A-Za-zÅÄÖåäö0-9]', w)])
        c['_multi_ref'] = len(set(c['_refs'])) >= 2
        low = subj.lower().strip(' .!')
        c['_generic'] = low in GENERIC or len(low) <= 2
        c['_web'] = bool(WEB_UI_RE.match(subj))
        c['_bare_close'] = bool(c['_closing']) and bool(BARE_CLOSE_RE.match(subj))
        by_student[c['author']].append(c)
    issues_by_student = defaultdict(dict)
    for i in issues:
        try:
            created = dt.fromisoformat(i['createdAt'].replace('Z', '+00:00')).replace(tzinfo=None)
            created = created + (dt.now() - dt.utcnow())  # UTC -> local, coarse
        except (ValueError, AttributeError):
            created = None
        issues_by_student[i['author']][int(i['number'])] = {'state': i['state'], 'created': created}

    per_student = []
    for s, cs in by_student.items():
        cs.sort(key=lambda c: c['_t'])
        days = {c['_t'].date() for c in cs}
        sessions = 1 + sum(1 for a, b in zip(cs, cs[1:]) if (b['_t'] - a['_t']).total_seconds() > SESSION_GAP_H * 3600)
        last24 = sum(1 for c in cs if deadline and (deadline - c['_t']).total_seconds() <= 24 * 3600) / len(cs) if deadline else float('nan')
        early = bool(deadline) and (deadline - cs[0]['_t']).days >= 3
        night = sum(1 for c in cs if c['_t'].hour < 6) / len(cs)
        med_lines = statistics.median(c['_lines'] for c in cs)
        my_issues = issues_by_student.get(s, {})
        referenced = {n for c in cs for n in c['_refs']}
        ref_own = referenced & set(my_issues)
        retro = 0
        for n in ref_own:
            first_ref = min(c['_t'] for c in cs if n in c['_refs'])
            if my_issues[n]['created'] and my_issues[n]['created'] > first_ref:
                retro += 1
        per_student.append({
            'year': cohort.year, 'task': task, 'author': s, 'commits': len(cs),
            'median_lines_per_commit': med_lines, 'active_days': len(days), 'sessions': sessions,
            'share_last24h': round(last24, 3) if last24 == last24 else '', 'first_commit_3d_early': early,
            'share_night': round(night, 3), 'median_subject_words': statistics.median(c['_words'] for c in cs),
            'issues': len(my_issues), 'issues_referenced': len(ref_own), 'refs_outside_own_issues': len(referenced - set(my_issues)),
            'retrofitted_issues': retro,
        })
    return commits, issues_by_student, per_student


def profile(cohort, tasks):
    all_commits, all_students = [], []
    deadline_of = {t: cohort.deadline(t) for t in tasks}
    issue_total = issue_referenced = issue_closed = issue_closed_kw = retro = 0
    n_issue_students = 0
    for t in tasks:
        commits, issues_by_student, per_student = student_task_rows(cohort, t)
        for c in commits:
            c['_task'] = t
        all_commits += commits
        all_students += per_student
        for s, its in issues_by_student.items():
            issue_total += len(its)
            issue_closed += sum(1 for v in its.values() if v['state'].upper() != 'OPEN')
        for r in per_student:
            issue_referenced += r['issues_referenced']
            retro += r['retrofitted_issues']
            if r['issues']:
                n_issue_students += 1
        closing_nums = {}
        for c in commits:
            for n in set(c['_closing']):
                closing_nums.setdefault((c['author'], n), 1)
        issue_closed_kw += sum(1 for (a, n) in closing_nums if n in issues_by_student.get(a, {}))
    if not all_commits:
        return None
    n = len(all_commits)
    closing_commits = [c for c in all_commits if c['_closing']]
    P = {
        'year': cohort.year, 'commits': n, 'student_tasks': len(all_students),
        'commits_per_student_task': [r['commits'] for r in all_students],
        'lines_per_commit_median': statistics.median(c['_lines'] for c in all_commits),
        'share_tiny': sum(1 for c in all_commits if c['_lines'] <= 5) / n,
        'share_large': sum(1 for c in all_commits if c['_lines'] >= 200) / n,
        'subject_words_median': statistics.median(c['_words'] for c in all_commits),
        'share_generic': sum(1 for c in all_commits if c['_generic']) / n,
        'share_web': sum(1 for c in all_commits if c['_web']) / n,
        'share_ref': sum(1 for c in all_commits if c['_refs']) / n,
        'share_closing': len(closing_commits) / n,
        'share_bare_close': sum(1 for c in all_commits if c['_bare_close']) / n,
        'share_descriptive': sum(1 for c in all_commits if c['_words'] >= 3) / n,
        'share_multi_ref': sum(1 for c in all_commits if c['_multi_ref']) / n,
        'days_before': [max(0, min(6, int((deadline_of[c['_task']] - c['_t']).total_seconds() // 86400))) for c in all_commits if deadline_of.get(c['_task'])],
        'msg_mix': {
            'only Fixes #N': sum(1 for c in all_commits if c['_bare_close']) / n,
            'reference + words': sum(1 for c in all_commits if c['_refs'] and not c['_bare_close']) / n,
            'words, no reference': sum(1 for c in all_commits if not c['_refs'] and not c['_web'] and not c['_generic']) / n,
            'web-UI default': sum(1 for c in all_commits if c['_web'] and not c['_refs']) / n,
            'generic': sum(1 for c in all_commits if c['_generic'] and not c['_refs'] and not c['_web']) / n,
        },
        'share_batch_close': (sum(1 for c in closing_commits if len(set(c['_closing'])) >= 2) / len(closing_commits)) if closing_commits else float('nan'),
        'issues': issue_total,
        'share_issues_referenced': issue_referenced / issue_total if issue_total else float('nan'),
        'share_issues_closed': issue_closed / issue_total if issue_total else float('nan'),
        'share_issues_closed_kw': issue_closed_kw / issue_total if issue_total else float('nan'),
        'share_retrofitted': retro / issue_referenced if issue_referenced else float('nan'),
        'active_days': [r['active_days'] for r in all_students],
        'sessions': [r['sessions'] for r in all_students],
        'share_last24h': [r['share_last24h'] for r in all_students if r['share_last24h'] != ''],
        'early_start': sum(1 for r in all_students if r['first_commit_3d_early']) / len(all_students),
        'share_night': sum(1 for c in all_commits if c['_t'].hour < 6) / n,
        'lines_student': [r['median_lines_per_commit'] for r in all_students],
        'words_student': [r['median_subject_words'] for r in all_students],
    }
    return P, all_students


def pct(x):
    return 'n/a' if x != x else f'{100 * x:.0f}%'


def med(v):
    return fmt(statistics.median(v)) if v else 'n/a'


ROWS = [
    ('Commit shape', None),
    ('commits per student-task (median)', lambda P: med(P['commits_per_student_task'])),
    ('lines changed per commit (median)', lambda P: fmt(P['lines_per_commit_median'])),
    ('commits changing ≤5 lines', lambda P: pct(P['share_tiny'])),
    ('commits changing ≥200 lines', lambda P: pct(P['share_large'])),
    ('Messages', None),
    ('words per subject beyond refs/keywords (median)', lambda P: fmt(P['subject_words_median'])),
    ('subjects with ≥3 such words', lambda P: pct(P['share_descriptive'])),
    ('generic subjects ("done", "a", ...)', lambda P: pct(P['share_generic'])),
    ('GitHub web-UI default subjects', lambda P: pct(P['share_web'])),
    ('subjects referencing an issue (#N)', lambda P: pct(P['share_ref'])),
    ('subjects with a closing keyword', lambda P: pct(P['share_closing'])),
    ('subjects that are only "Fixes #N"', lambda P: pct(P['share_bare_close'])),
    ('subjects referencing ≥2 issues', lambda P: pct(P['share_multi_ref'])),
    ('Issue fidelity', None),
    ('issues (total)', lambda P: str(P['issues'])),
    ('issues referenced by ≥1 commit', lambda P: pct(P['share_issues_referenced'])),
    ('issues closed', lambda P: pct(P['share_issues_closed'])),
    ('issues closed with a keyword', lambda P: pct(P['share_issues_closed_kw'])),
    ('referenced issues opened after the commit', lambda P: pct(P['share_retrofitted'])),
    ('Pacing', None),
    ('active days per student-task (median)', lambda P: med(P['active_days'])),
    ('work sessions per student-task (median, 2 h gap)', lambda P: med(P['sessions'])),
    ('commits on the deadline day', lambda P: pct(sum(1 for d in P['days_before'] if d == 0) / len(P['days_before'])) if P['days_before'] else 'n/a'),
    ('commits on the day before', lambda P: pct(sum(1 for d in P['days_before'] if d == 1) / len(P['days_before'])) if P['days_before'] else 'n/a'),
    ('student-tasks starting ≥3 days early', lambda P: pct(P['early_start'])),
    ('night commits (00–06)', lambda P: pct(P['share_night'])),
]

TESTS = [('commits', 'commits_per_student_task'), ('lines/commit', 'lines_student'),
         ('subject words', 'words_student'), ('active days', 'active_days'),
         ('sessions', 'sessions'), ('deadline-day share', 'share_last24h')]


def render(profiles, focal):
    years = sorted(profiles)
    md = [f"# Behavioural profile by cohort (tasks 1–9)", '',
          "Commits within the course window up to each task deadline, teachers excluded. Percentages are of commits unless stated.", '',
          "| | " + " | ".join(str(y) for y in years) + " |", "|---|" + "---|" * len(years)]
    tex = ["\\begin{tabular}{l" + "r" * len(years) + "}", "\\toprule", " & " + " & ".join(str(y) for y in years) + " \\\\", "\\midrule"]
    for label, f in ROWS:
        if f is None:
            md.append(f"| **{label}** | " + " | ".join('' for _ in years) + " |")
            tex.append(f"\\multicolumn{{{len(years) + 1}}}{{l}}{{\\textit{{{label}}}}} \\\\")
        else:
            vals = [f(profiles[y]) for y in years]
            md.append(f"| {label} | " + " | ".join(vals) + " |")
            tex.append(label.replace('≤', '$\\leq$').replace('≥', '$\\geq$').replace('–', '--').replace('#', '\\#').replace('%', '\\%')
                       + " & " + " & ".join(v.replace('%', '\\%') for v in vals) + " \\\\")
    tex += ["\\bottomrule", "\\end{tabular}"]
    others = [y for y in years if y != focal]
    if others and focal in profiles:
        md += ['', f"## {focal} vs pooled {others[0]}–{others[-1]} (Mann–Whitney U, Cliff's δ; per student-task)", '',
               "| Metric | " + f"{focal} median | pooled median | δ | p |", "|---|---|---|---|---|"]
        ttex = ["\\begin{tabular}{lrrrr}", "\\toprule", f"Per student-task & {focal} & {others[0]}--{others[-1]} & $\\delta$ & $p$ \\\\", "\\midrule"]
        for label, key in TESTS:
            fv = [v for v in profiles[focal][key] if v != '']
            pv = [v for y in others for v in profiles[y][key] if v != '']
            if not fv or not pv:
                continue
            _, p = mann_whitney(fv, pv)
            d = cliffs_delta(fv, pv)
            row = (label, fmt(statistics.median(fv), 2), fmt(statistics.median(pv), 2), fmt(d, 2), fmt(p, 4))
            md.append("| " + " | ".join(row) + " |")
            ttex.append(" & ".join(row) + " \\\\")
        ttex += ["\\bottomrule", "\\end{tabular}"]
    else:
        ttex = []
    return "\n".join(md) + "\n", "\n".join(tex) + "\n", "\n".join(ttex) + "\n"


YEAR_GREY, FOCAL_BLUE, NEW_ORANGE = '#9a9a94', '#2a78d6', '#eb6834'
MIX_COLORS = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4']   # validated categorical palette, fixed order


def figures(profiles, focal, tag=''):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('[behaviour] matplotlib not available, skipping figures')
        return
    fdir = context.ROOT / 'report' / 'figures'
    fdir.mkdir(parents=True, exist_ok=True)
    years = sorted(profiles)
    plt.rcParams.update({'font.size': 9, 'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.edgecolor': '#c3c2b7', 'axes.labelcolor': '#52514e', 'xtick.color': '#52514e', 'ytick.color': '#52514e'})

    # Pacing: share of commits by days before the deadline, one line per cohort
    fig, ax = plt.subplots(figsize=(4.6, 2.8))
    for y in years:
        db = profiles[y]['days_before']
        if not db:
            continue
        counts = [sum(1 for d in db if d == k) / len(db) * 100 for k in range(7)]
        color = FOCAL_BLUE if y == focal else (NEW_ORANGE if y > focal else YEAR_GREY)
        lw = 2 if y >= focal else 1.2
        ax.plot(range(7), counts, color=color, lw=lw, marker='o', ms=4 if y >= focal else 3, alpha=1 if y >= focal else 0.8)
        ax.annotate(str(y), (6, counts[6]), xytext=(4, 0), textcoords='offset points', color=color if y >= focal else '#52514e', fontsize=8, va='center')
    ax.set_xticks(range(7)); ax.set_xticklabels(['deadline day', '1', '2', '3', '4', '5', '6+'])
    ax.set_xlabel('days before the task deadline'); ax.set_ylabel('share of commits (%)')
    ax.grid(axis='y', color='#eeeeea', lw=0.8); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(fdir / f'pacing{tag}.pdf'); fig.savefig(fdir / f'pacing{tag}.png', dpi=200); plt.close(fig)

    # Message mix: stacked horizontal bars per cohort
    cats = list(profiles[years[0]]['msg_mix'])
    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    left = [0] * len(years)
    for ci, cat in enumerate(cats):
        vals = [profiles[y]['msg_mix'][cat] * 100 for y in years]
        ax.barh([str(y) for y in years], vals, left=left, color=MIX_COLORS[ci], height=0.6, label=cat, edgecolor='#fcfcfb', linewidth=1.5)
        for yi, (l, v) in enumerate(zip(left, vals)):
            if v >= 12:
                ax.text(l + v / 2, yi, f'{v:.0f}', ha='center', va='center', color='white', fontsize=7)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_xlim(0, 100); ax.set_xlabel('share of commit subjects (%)'); ax.invert_yaxis()
    ax.legend(ncol=3, fontsize=7, frameon=False, loc='upper center', bbox_to_anchor=(0.5, -0.28))
    ax.grid(axis='x', color='#eeeeea', lw=0.8); ax.set_axisbelow(True)
    fig.tight_layout(); fig.savefig(fdir / f'messages{tag}.pdf'); fig.savefig(fdir / f'messages{tag}.png', dpi=200); plt.close(fig)
    print(f"[behaviour] wrote {fdir}/pacing{tag}.* and messages{tag}.*")


def run(focal, years, tasks, tag=''):
    """tag suffixes the output files, e.g. '_2026' for the current cohort's tasks so far."""
    profiles = {}
    for y in years:
        c = context.load(y)
        res = profile(c, tasks)
        if not res:
            continue
        P, students = res
        profiles[y] = P
        write_csv(c.data_dir / 'behaviour.csv', students, list(students[0].keys()))
    md, tex, ttex = render(profiles, focal)
    figures(profiles, focal, tag)
    (context.ROOT / 'reports').mkdir(exist_ok=True)
    (context.ROOT / 'reports' / f'behaviour{tag}.md').write_text(md, encoding='utf-8')
    tdir = context.ROOT / 'report' / 'tables'
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / f'behaviour_profile{tag}.tex').write_text(tex, encoding='utf-8')
    (tdir / f'behaviour_tests{tag}.tex').write_text(ttex, encoding='utf-8')
    print(md)
    print(f"[behaviour] wrote reports/behaviour{tag}.md and report/tables/behaviour_*{tag}.tex")
    return profiles


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--focal', type=int, default=2025, help='cohort tested against the pooled others (default 2025)')
    p.add_argument('--years', nargs='+', type=int, help='cohorts to include (default: all)')
    p.add_argument('--tasks', nargs='+', default=TASKS)
    p.add_argument('--tag', default='', help='suffix for output files')
    a = p.parse_args()
    run(a.focal, a.years or context.available_years(), a.tasks, a.tag)


if __name__ == '__main__':
    main()
