#!/usr/bin/env python3
"""Compare the exercise structure of a task between two cohorts to build the task mapping.

For each cohort the task README is taken from the first local clone found under
repos/<year>; if none exists yet, the template repo README is fetched from the
template organisation (inda-master) through `gh api` (only meaningful for the
current year). Exercise headings ("Exercise 2.3 -- Title", "Warmup 1 -- ...") are
listed side by side and matched by title similarity, then written to
docs/task-mapping/<task>.md for you to edit (mark which exercises are comparable).
"""

import argparse
import base64
import difflib
import json
import re
import subprocess
from pathlib import Path

import context
from common import find_task_repos

HEADING_RE = re.compile(r'^#{2,5}\s+((?:Exercise|Warmup|Uppgift|Task)\s+\d+[\d.]*\b.*?)\s*$', re.MULTILINE)
DEADLINE_RE = re.compile(r'#{2,4}\s+.*Deadline.*?\n+(.*?)\n', re.DOTALL)


def readme_from_repos(cohort, task):
    for repo_path, _ in find_task_repos(cohort.repos_dir, task):
        p = Path(repo_path) / 'README.md'
        if p.exists():
            return p.read_text(encoding='utf-8', errors='replace'), f"{repo_path}/README.md"
    return None, None


def readme_from_template(cohort, task, template_org='inda-master'):
    cmd = ['gh', 'api', '--hostname', cohort.host, f'repos/{template_org}/{task}/readme']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return None, None
    content = json.loads(r.stdout).get('content', '')
    return base64.b64decode(content).decode('utf-8', errors='replace'), f"{cohort.host}/{template_org}/{task}/README.md"


def exercises(readme):
    items = []
    for m in HEADING_RE.finditer(readme):
        heading = re.sub(r'\s+', ' ', m.group(1)).strip('` ')
        num = re.search(r'([\d.]+)', heading).group(1).rstrip('.')
        rest = heading[re.search(r'[\d.]+', heading).end():]
        title = re.sub(r'^[\s\-–—:]+', '', rest).strip('` ') or heading
        items.append((num, title, heading))
    return items


def deadline_text(readme):
    m = DEADLINE_RE.search(readme)
    return m.group(1).strip() if m else ''


def similarity(a, b):
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


def match(base_items, new_items, threshold=0.6):
    """Greedy best-match of new exercises to baseline exercises by title similarity."""
    pairs = []
    used = set()
    for n_num, n_title, _ in new_items:
        best, best_score = None, 0
        for b_num, b_title, _ in base_items:
            if b_num in used:
                continue
            s = similarity(n_title, b_title)
            if s > best_score:
                best, best_score = b_num, s
        if best is not None and best_score >= threshold:
            used.add(best)
            pairs.append((n_num, best, best_score))
        else:
            pairs.append((n_num, None, best_score))
    removed = [b for b, _, _ in base_items if b not in used]
    return pairs, removed


def run(task, cohort, baseline, out_dir, template_org):
    base_readme, base_src = readme_from_repos(baseline, task)
    new_readme, new_src = readme_from_repos(cohort, task)
    if new_readme is None:
        new_readme, new_src = readme_from_template(cohort, task, template_org)
    if base_readme is None or new_readme is None:
        raise SystemExit(f"[task_diff] README not found (baseline: {base_src}, {cohort.year}: {new_src})")

    base_items, new_items = exercises(base_readme), exercises(new_readme)
    pairs, removed = match(base_items, new_items)
    base_by = {n: t for n, t, _ in base_items}
    new_by = {n: t for n, t, _ in new_items}

    lines = [f"# {task}: {baseline.year} vs {cohort.year}", "",
             f"- {baseline.year} README: `{base_src}` ({len(base_items)} exercises, deadline text: {deadline_text(base_readme) or 'n/a'})",
             f"- {cohort.year} README: `{new_src}` ({len(new_items)} exercises, deadline text: {deadline_text(new_readme) or 'n/a'})",
             "", "Edit the `comparable` column: `yes` if the exercise is essentially unchanged, `changed` if it",
             "was reworked, `no` for new/removed exercises. `compare.py` reads this file only for the note;",
             "the per-task comparison itself is on whole-task metrics.", "",
             f"| {cohort.year} exercise | {baseline.year} exercise | similarity | comparable | note |",
             "|---|---|---|---|---|"]
    for n_num, b_num, score in pairs:
        n_title = new_by[n_num]
        if b_num is None:
            lines.append(f"| {n_num} {n_title} | (new) | {score:.2f} | no | |")
        else:
            flag = 'yes' if score >= 0.95 else 'changed?'
            lines.append(f"| {n_num} {n_title} | {b_num} {base_by[b_num]} | {score:.2f} | {flag} | |")
    for b_num in removed:
        lines.append(f"| (removed) | {b_num} {base_by[b_num]} | | no | |")
    lines += ["", f"Expected exercises in cohorts/{cohort.year}.json: {cohort.expected_exercises(task)}"
              f"{' (PROVISIONAL)' if cohort.is_provisional(task) else ''}; README lists {len([i for i in new_items if i[2].startswith('Exercise')])} exercises"
              f" + {len([i for i in new_items if not i[2].startswith('Exercise')])} warmups."]

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f'{task}.md'
    out.write_text("\n".join(lines) + "\n", encoding='utf-8')
    print("\n".join(lines))
    print(f"\n[task_diff] wrote {out}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task')
    p.add_argument('--baseline', type=int, default=2025, help='baseline cohort year (default 2025)')
    p.add_argument('--template-org', default='inda-master')
    p.add_argument('--out-dir', default=str(context.ROOT / 'docs' / 'task-mapping'))
    context.add_cohort_arg(p)
    a = p.parse_args()
    run(a.task, context.load(a.cohort), context.load(a.baseline), a.out_dir, a.template_org)


if __name__ == '__main__':
    main()
