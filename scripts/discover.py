#!/usr/bin/env python3
"""Infer the cohort configuration from the data instead of typing it in.

What gets discovered, and the guardrail for each:

  teachers   org admins of the cohort organisation (gh api), plus the git author names
             of template commits: authors of commits dated before course start that
             appear in at least --min-share of the task repositories. A student who
             committed early only shows up in their own repo, so they are not caught.
  students   owners of <user>-<task> repositories in the organisation, minus teachers.
  tasks      exercise list and deadline from the task README. Every local clone's
             README is parsed and the majority version wins (students who edited their
             README are outvoted); with no clones, the template repo README
             (inda-master/<task>) is used. The deadline sentence ("Friday 4th September")
             is turned into the cutoff used since 2025: midnight at the END of that day.

    python3 scripts/discover.py task-2            # show what would change
    python3 scripts/discover.py task-2 --write    # update cohorts/<year>.json (+ students file)
    python3 scripts/discover.py --teachers --students --write

Manual values in cohorts/<year>.json win over discovery unless the task entry is
missing or flagged "provisional"; use --force to overwrite anyway.
"""

import argparse
import base64
import json
import re
import subprocess
from collections import Counter
from datetime import date, datetime as dt, timedelta
from pathlib import Path

import context
from common import find_task_repos

# "Exercise 2.3 -- Title", "Exercise 13.3.1", "Task 15.1 - Title" (DD1338 style); not "Task 1" course headings
EXERCISE_RE = re.compile(r'^#{2,5}\s+(Exercise|Uppgift|Task)\s+(\d+\.[\d.]*)\s*(.*?)\s*$', re.MULTILINE)
DEADLINE_RE = re.compile(r'#{2,4}[^\n]*Deadline[^\n]*\n+(.*?)(?:\n\s*\n|\n#{2,4}\s)', re.DOTALL | re.IGNORECASE)
MONTHS = {m.lower(): i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July',
                                              'August', 'September', 'October', 'November', 'December'], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})


# --- gh helpers ---------------------------------------------------------------
def gh_api(host, path, paginate=True):
    cmd = ['gh', 'api', '--hostname', host, path]
    if paginate:
        cmd.append('--paginate')
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh api {path} failed: {r.stderr.strip()[:200]}")
    # --paginate concatenates JSON arrays; make it one list
    text = r.stdout.strip()
    if not text:
        return []
    chunks = re.split(r'\]\s*\[', text)
    items = []
    for i, c in enumerate(chunks):
        if not c.startswith('['):
            c = '[' + c
        if not c.endswith(']'):
            c = c + ']'
        items.extend(json.loads(c))
    return items


def org_admins(cohort):
    return sorted(m['login'] for m in gh_api(cohort.host, f'orgs/{cohort.org}/members?role=admin&per_page=100'))


def org_repo_names(cohort):
    return sorted(r['name'] for r in gh_api(cohort.host, f'orgs/{cohort.org}/repos?per_page=100'))


def template_readme(cohort, task, template_org='inda-master'):
    r = subprocess.run(['gh', 'api', '--hostname', cohort.host, f'repos/{template_org}/{task}/readme'],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return base64.b64decode(json.loads(r.stdout).get('content', '')).decode('utf-8', errors='replace')


# --- teachers -----------------------------------------------------------------
def template_authors(cohort, tasks=None, min_share=0.5):
    """Git author names of pre-course commits present in >= min_share of repos."""
    tasks = tasks or sorted(cohort.tasks) or ['task-1']
    repos = []
    for t in tasks:
        repos += [p for p, _ in find_task_repos(cohort.repos_dir, t)]
    if not repos:
        return {}
    counts = Counter()
    for repo in repos:
        r = subprocess.run(['git', '-C', repo, 'log', f'--before={cohort.course_start_date}', '--format=%an'],
                           capture_output=True, text=True)
        for name in set(r.stdout.split('\n')) - {''}:
            counts[name] += 1
    return {name: n for name, n in counts.items() if n >= min_share * len(repos)}


def discover_teachers(cohort, verbose=True):
    found = {}
    try:
        admins = org_admins(cohort)
        found.update({a: 'org admin' for a in admins})
    except RuntimeError as e:
        print(f"[discover] could not list org admins: {e}")
    for name, n in template_authors(cohort).items():
        found.setdefault(name, f'template author in {n} repos')
    if verbose:
        for name, why in sorted(found.items()):
            print(f"  teacher {name!r}: {why}")
    return sorted(found)


# --- students -----------------------------------------------------------------
def discover_students(cohort, teachers):
    names = org_repo_names(cohort)
    owners = Counter(re.sub(r'-task-\d+$', '', n) for n in names if re.search(r'-task-\d+$', n))
    lowered = {t.lower() for t in teachers}
    return sorted(o for o in owners if o.lower() not in lowered)


# --- tasks --------------------------------------------------------------------
def parse_exercises(readme):
    """[(number, title)] for every 'Exercise N.M[.K] [-- title]' heading (title may be empty)."""
    items = []
    for m in EXERCISE_RE.finditer(readme):
        title = re.sub(r'^[\s\-–—:]+', '', m.group(3))
        items.append((m.group(2).rstrip('.'), re.sub(r'\s+', ' ', title).strip('` ')))
    return items


LINK_RE = re.compile(r'issues/new\?title=([^\s"\'<>]+)')


def parse_link_titles(readme):
    """Pre-filled issue titles from the README's issue links: the default plan, verbatim.
    Markdown wraps the URL in (...), so trailing unbalanced ')' are the link syntax, not the title."""
    from urllib.parse import unquote_plus
    titles = []
    for m in LINK_RE.findall(readme):
        while m.endswith(')') and m.count(')') > m.count('('):
            m = m[:-1]
        m = m.split('&')[0]
        titles.append(re.sub(r'\s+', ' ', unquote_plus(m)).strip())
    return titles


def parse_deadline(readme, cohort):
    """Return (exercise_date, cutoff, sentence) or (None, None, sentence)."""
    m = DEADLINE_RE.search(readme)
    if not m:
        return None, None, ''
    sentence = re.sub(r'\s+', ' ', m.group(1)).strip()
    start = date.fromisoformat(cohort.course_start_date)
    candidates = [date.fromisoformat(m) for m in re.findall(r'(\d{4}-\d{2}-\d{2})', sentence)]
    for day, month in re.findall(r'(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([A-Za-z]+)', sentence):
        if month.lower() in MONTHS:
            mon = MONTHS[month.lower()]
            year = start.year if mon >= start.month else start.year + 1
            try:
                candidates.append(date(year, mon, int(day)))
            except ValueError:
                pass
    if not candidates:
        return None, None, sentence
    # Some tasks name two exercise days (Thursday/Friday groups): the later one is the deadline.
    d = max(candidates)
    return d, d + timedelta(days=1), sentence


def discover_task(cohort, task, template_org='inda-master', verbose=True):
    readmes = []
    for repo_path, _ in find_task_repos(cohort.repos_dir, task):
        p = Path(repo_path) / 'README.md'
        if p.exists():
            readmes.append(p.read_text(encoding='utf-8', errors='replace'))
    source = f'{len(readmes)} local READMEs (majority vote)'
    if not readmes:
        t = template_readme(cohort, task, template_org)
        if t is None:
            return None
        readmes = [t]
        source = f'template {template_org}/{task}'

    ex_votes = Counter(tuple(parse_exercises(r)) for r in readmes)
    link_votes = Counter(tuple(parse_link_titles(r)) for r in readmes)
    link_titles = list(link_votes.most_common(1)[0][0])
    dl_votes = Counter(parse_deadline(r, cohort)[:2] for r in readmes)
    exercises, ex_n = ex_votes.most_common(1)[0]
    (ex_date, cutoff), dl_n = dl_votes.most_common(1)[0]
    sentence = next((parse_deadline(r, cohort)[2] for r in readmes if parse_deadline(r, cohort)[:2] == (ex_date, cutoff)), '')

    result = {
        'deadline': cutoff.isoformat() if cutoff else None,
        'exercise_date': ex_date.isoformat() if ex_date else None,
        'deadline_text': sentence,
        'exercises': len(exercises),
        'exercise_list': [f'{n} {t}' for n, t in exercises],
        'link_titles': link_titles,
        'source': source,
        'agreement': {'exercises': f'{ex_n}/{len(readmes)}', 'deadline': f'{dl_n}/{len(readmes)}'},
    }
    if verbose:
        print(f"[discover] {task}: {result['exercises']} exercises, exercise day {result['exercise_date']}, "
              f"cutoff {result['deadline']} ('{sentence}'); {source}; agreement {result['agreement']}")
        if ex_n < len(readmes):
            print(f"[discover]   {len(readmes) - ex_n} README(s) differ on exercises (students edited them?)")
    return result


def apply_task(cohort, task, found, force=False):
    """Merge a discovered task into the cohort config. Returns a change description or None."""
    current = cohort.tasks.get(task)
    manual = current is not None and not current.get('provisional')
    if manual and not force:
        diffs = []
        if found['deadline'] and current.get('deadline') != found['deadline']:
            diffs.append(f"deadline config {current.get('deadline')} vs README {found['deadline']}")
        if current.get('exercises') != found['exercises']:
            diffs.append(f"exercises config {current.get('exercises')} vs README {found['exercises']}")
        return ('KEPT manual config; ' + '; '.join(diffs)) if diffs else None
    entry = {'deadline': found['deadline'] or (current or {}).get('deadline'),
             'exercises': found['exercises'],
             'exercise_date': found['exercise_date'],
             'exercise_list': found['exercise_list'],
             'link_titles': found['link_titles'],
             'discovered': f"{dt.now().date().isoformat()} from {found['source']}"}
    cohort.tasks[task] = {k: v for k, v in entry.items() if v is not None}
    return f"set {task} = deadline {entry['deadline']}, {entry['exercises']} exercises"


def apply_teachers(cohort, teachers):
    """Record discovered teachers in the cohort config (exact-match list). Returns the new ones."""
    existing = set(cohort.raw.get('teachers', []))
    new = sorted(set(teachers) - existing)
    if new:
        cohort.raw['teachers'] = sorted(existing | set(new))
        cohort.cohort_teachers = cohort.raw['teachers']
    return new


def write_students(cohort, students):
    path = cohort.students_file or (context.ROOT / 'students' / str(cohort.year) / 'students.txt')
    path.parent.mkdir(parents=True, exist_ok=True)
    old = set(path.read_text().split()) if path.exists() else set()
    path.write_text('\n'.join(students) + '\n', encoding='utf-8')
    return sorted(set(students) - old), sorted(old - set(students)), path


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', nargs='?', help='task to discover (README exercises + deadline)')
    p.add_argument('--teachers', action='store_true', help='discover teachers (org admins + template authors)')
    p.add_argument('--students', action='store_true', help='discover students from org repo names')
    p.add_argument('--write', action='store_true', help='write results to cohorts/<year>.json and students file')
    p.add_argument('--force', action='store_true', help='overwrite manual task config too')
    p.add_argument('--template-org', default='inda-master')
    context.add_cohort_arg(p)
    a = p.parse_args()
    cohort = context.load(a.cohort)
    if not (a.task or a.teachers or a.students):
        p.error('give a task and/or --teachers/--students')

    changed = False
    if a.teachers or a.students:
        teachers = discover_teachers(cohort)
        new = apply_teachers(cohort, teachers)
        if new:
            print(f"[discover] new teachers for cohorts/{cohort.year}.json: {' '.join(new)}")
            changed = True
        if a.students:
            students = discover_students(cohort, teachers + cohort.teachers)
            print(f"[discover] {len(students)} students own task repos in {cohort.org}")
            if a.write:
                added, removed, path = write_students(cohort, students)
                print(f"[discover] wrote {path} (+{len(added)} / -{len(removed)})")
    if a.task:
        found = discover_task(cohort, a.task, a.template_org)
        if found is None:
            raise SystemExit(f"[discover] no README found for {a.task}")
        msg = apply_task(cohort, a.task, found, a.force)
        if msg:
            print(f"[discover] {msg}")
            changed = changed or not msg.startswith('KEPT')
    if a.write and changed:
        cohort.save()
        print(f"[discover] saved cohorts/{cohort.year}.json")
    elif changed:
        print("[discover] (dry run: add --write to save)")


if __name__ == '__main__':
    main()
