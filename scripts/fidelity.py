#!/usr/bin/env python3
"""Fidelity to the worked-example task variants: did students do what the variant asks?

Read-only. For each student repository of a task, judged at the deadline (the last
commit at or before the cohort deadline, the same cut-off as commits.py), five signals:

  1 prompts   🧠 self-explanation prompts in docs/README.md answered (>= 3 words, not the
              "Submit your answer here" placeholder), per prompt, with word counts
  2 labels    the starter's 🏷 subgoal comments still present in the code; and for each
              method the student writes: subgoal labels in their own words (own labels),
              worked-example labels kept or copied into the body (reused labels), other
              comments (commented), none (bare), or no method (absent)
  3 order     first commit with a prompt answer versus first commit touching the code:
              answers first, code first, same commit; and "answers at the end" (no answer
              committed before the last code commit)
  4 plan      the plan-in-an-issue exercise: is there an issue for it, is its body a plan
              (list or >= 20 words), and was it opened before the method first appeared
  5 tests     the instructor's JUnit tests (from the task's solutions branch) run against
              the student's files at the deadline; "api" = the file compiles but the test
              does not (a tested method missing or with another signature)

Nothing a student wrote is stored: only counts and flags. Outputs:
data/<year>/<task>/fidelity.csv (one row per repository) and reports/fidelity.md
(aggregates for every task that has a fidelity.csv).

Issue bodies come from `gh issue list` (read-only) and are cached in
repos/<year>/.fidelity-issues-<task>.json, next to the clones (gitignored).
The tests are read with `git show solutions:src/*Test.java` from the task's instructor
repository (--tasks-dir, default ~/dev/workedexample/tasks).
"""

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime as dt
from pathlib import Path

import context
from common import find_task_repos, parse_git_datetime, read_csv, write_csv

ROOT = Path(__file__).resolve().parent.parent
M2 = Path.home() / '.m2' / 'repository'
CLASSPATH = [M2 / 'junit/junit/4.13.2/junit-4.13.2.jar', M2 / 'org/hamcrest/hamcrest-core/1.3/hamcrest-core-1.3.jar']

# What each variant asks for. stage: plan = subgoal comments given, body yours;
# own = same subgoals as the worked example, nothing given; solo = no plan at all.
VARIANTS = {
    'task-1': {
        'code': ['Arithmetic.java'],
        'methods': [('Arithmetic.java', 'difference', 'own'), ('Arithmetic.java', 'average', 'own')],
        'plan_issue': ('1.5', 'Arithmetic.java', 'average'),
    },
    'task-2': {
        'code': ['Indamon.java'],
        'methods': [('Indamon.java', 'printInfo', 'plan'), ('Indamon.java', 'attack', 'solo')],
        'plan_issue': ('2.4', 'Indamon.java', 'attack'),
    },
    'task-3': {
        'code': ['Triangle.java', 'Rectangle.java'],
        'methods': [('Triangle.java', 'getTriangleType', 'plan'), ('Triangle.java', 'getArea', 'plan'),
                    ('Rectangle.java', None, 'solo')],
        'plan_issue': ('3.3', 'Rectangle.java', None),
    },
}

# Known limits of a measure for one task, printed under its section of the report.
NOTES = {
    'task-1': ['Order: 1.2 creates `Arithmetic.java` before the worked example, so "code first" is '
               'partly expected here.'],
    'task-3': ['Tests: `RectangleTest` compares `area()` with `assertEquals` and no delta, which '
               'always fails when `area()` returns a `double` (the README fixes no type): the '
               '`testRectangleArea`/`testSquareArea` failures are largely that, not wrong areas.'],
}
COMMON_NOTES = [
    'Prompts: "answered" means at least 3 words besides the placeholder; it says nothing about '
    'quality, and AI-written or copied answers are not distinguished.',
    'Labels: a given plan line with its 🏷 removed counts as the student\'s own comment.',
    'Plan issue: matched by the exercise number in the title; an issue named only by topic counts '
    'as "none". "plan" = at least two list items or 20 words; "title only" includes issues opened '
    'from the pre-filled link and left empty.',
]

PROMPT_RE = re.compile(r'^#{2,4}\s*🧠?\s*Prompt\s+(\d+)', re.M)
PLACEHOLDER = 'submit your answer here'
OWN_LABEL_RE = re.compile(r'🏷|subgoal|\bstep\s*\d', re.I)
LIST_ITEM_RE = re.compile(r'^\s*(?:[-*+]|\d+[.)]|- \[[ xX]\])\s+\S', re.M)


def git(repo, *args):
    r = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ''


def words(text):
    return len(re.findall(r'\w+', text))


# --- 1 prompts ------------------------------------------------------------------

def prompt_answers(docs):
    """{prompt number: words in the answer} for every 🧠 prompt heading in docs."""
    out = {}
    heads = list(PROMPT_RE.finditer(docs))
    for i, m in enumerate(heads):
        end = len(docs)
        nxt = re.search(r'^#', docs[m.end():], re.M)
        if nxt:
            end = m.end() + nxt.start()
        section = docs[m.end():end].split('\n', 1)[1] if '\n' in docs[m.end():end] else ''
        if "Student's Answer" in section:
            section = section.split("Student's Answer", 1)[1].lstrip('*:')
        text = '\n'.join(l.strip().lstrip('>').strip() for l in section.split('\n'))
        text = re.sub(re.escape(PLACEHOLDER), '', text, flags=re.I)
        out[int(m.group(1))] = words(text)
    return out


def answered(counts):
    return sum(1 for w in counts.values() if w >= 3)


# --- 2 labels -------------------------------------------------------------------

def label_lines(src):
    return {re.sub(r'\s+', ' ', l.strip()) for l in src.split('\n') if '🏷' in l}


def method_region(src, name):
    """(comment block directly above, header + body) of a method; None if absent."""
    m = re.search(r'^[ \t]*(?:(?:public|private|protected|static|final)\s+)*[\w<>\[\], ]+\s+%s\s*\([^)]*\)\s*\{' % re.escape(name), src, re.M)
    if not m:
        return None
    depth, i = 0, src.index('{', m.start())
    for j in range(i, len(src)):
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                break
    body = src[m.start():j + 1]
    above = []
    for line in reversed(src[:m.start()].rstrip('\n').split('\n')):
        s = line.strip()
        if s.startswith(('//', '*', '/*')):
            above.append(line)
        else:
            break
    return '\n'.join(reversed(above)), body


def norm(line):
    return re.sub(r'\s+', ' ', line.strip().lstrip('/*').strip()).lower()


def classify_region(region, starter):
    """own labels   a subgoal-style comment the student wrote (not verbatim starter text)
    reused labels  starter/worked-example labels copied or kept inside the method body
    commented      other comments of the student's own; bare = none; absent = no method.
    Starter comments above the method (the exercise banner) are ignored."""
    if region is None:
        return 'absent'
    above, body = region
    lines = [l for l in (above + body).split('\n') if l.strip()]
    mine = [l for l in lines if norm(l) not in starter]
    if any(OWN_LABEL_RE.search(l) for l in mine):
        return 'own labels'
    if any(OWN_LABEL_RE.search(l) for l in body.split('\n')):
        return 'reused labels'
    if any(re.search(r'//|/\*', l) for l in mine):
        return 'commented'
    return 'bare'


# --- snapshot helpers ---------------------------------------------------------------

def commits(repo, cohort, task):
    """Student commits at or before the deadline, oldest first: [(hash, when, author, files)]."""
    deadline = cohort.deadline(task)
    out = git(repo, 'log', '--no-merges', '--reverse', '--name-only', '--pretty=format:@@%H|%an|%ai')
    rows = []
    for block in out.split('@@')[1:]:
        head, *files = block.strip().split('\n')
        h, author, when = head.split('|', 2)
        when = parse_git_datetime(when)
        if deadline and when > deadline:
            continue
        rows.append((h, when, author, [f for f in files if f.strip()], cohort.is_teacher(author)))
    return rows


def find_file(repo, rev, name):
    paths = [p for p in git(repo, 'ls-tree', '-r', '--name-only', rev).split('\n') if p.split('/')[-1] == name]
    paths.sort(key=lambda p: (not p.startswith('src/'), len(p)))
    return paths[0] if paths else None


def show(repo, rev, path):
    return git(repo, 'show', f'{rev}:{path}') if path else ''


# --- 4 plan issue -------------------------------------------------------------------

def load_issues(repo_path, cohort, cache):
    key = Path(repo_path).name
    if key in cache:
        return cache[key]
    from issues import ensure_remote
    issues = []
    if ensure_remote(repo_path, cohort):
        r = subprocess.run(['gh', 'issue', 'list', '--state', 'all', '--limit', '500',
                            '--json', 'number,title,body,createdAt,author'],
                           capture_output=True, text=True, cwd=repo_path)
        if r.returncode == 0 and r.stdout.strip():
            issues = [i for i in json.loads(r.stdout)
                      if not cohort.is_teacher((i.get('author') or {}).get('login', ''))]
    cache[key] = issues
    return issues


def plan_class(body):
    body = re.sub(r'<!--.*?-->', '', body or '', flags=re.S)
    n = words(body)
    if n < 5:
        return 'title only'
    if len(LIST_ITEM_RE.findall(body)) >= 2 or n >= 20:
        return 'plan'
    return 'brief'


# --- 5 tests ------------------------------------------------------------------------

def load_tests(tasks_dir, task):
    repo = Path(tasks_dir) / task
    names = [p.split('/')[-1] for p in git(repo, 'ls-tree', '-r', '--name-only', 'solutions', 'src').split('\n')
             if p.endswith('Test.java')]
    return {n[:-len('Test.java')]: git(repo, 'show', f'solutions:src/{n}') for n in sorted(names)}


def run_test(test_name, test_src, student_src):
    """(passed, total, status) — status ok / fail / missing / compile / api / timeout."""
    if not student_src:
        return 0, 0, 'missing'
    cp = os.pathsep.join(str(p) for p in CLASSPATH)
    d = tempfile.mkdtemp(prefix='fidelity-')
    try:
        under = test_name[:-4]
        Path(d, f'{under}.java').write_text(student_src, encoding='utf-8')
        Path(d, f'{test_name}.java').write_text(test_src, encoding='utf-8')
        javac = ['javac', '-nowarn', '-encoding', 'UTF-8', '-cp', d + os.pathsep + cp, '-d', d]
        if subprocess.run(javac + [f'{under}.java'], cwd=d, capture_output=True).returncode != 0:
            return 0, 0, 'compile'  # the student's file does not compile on its own
        if subprocess.run(javac + [f'{test_name}.java'], cwd=d, capture_output=True).returncode != 0:
            return 0, 0, 'api'  # it compiles, but a tested method is missing or has another signature
        try:
            r = subprocess.run(['java', '-cp', d + os.pathsep + cp, 'org.junit.runner.JUnitCore', test_name],
                               cwd=d, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            return 0, 0, 'timeout'
        m = re.search(r'OK \((\d+) tests?\)', r.stdout)
        if m:
            return int(m.group(1)), int(m.group(1)), 'ok'
        m = re.search(r'Tests run: (\d+),\s+Failures: (\d+)', r.stdout)
        if m:
            total, failed = int(m.group(1)), int(m.group(2))
            return total - failed, total, 'fail'
        return 0, 0, 'compile'
    finally:
        shutil.rmtree(d, ignore_errors=True)


# --- per repository -------------------------------------------------------------------

def analyse(repo, student, task, cohort, spec, tests, issues_cache, use_issues):
    row = {'author': student, 'repository': Path(repo).name}
    all_commits = commits(repo, cohort, task)
    mine = [c for c in all_commits if not c[4]]
    row['student_commits'] = len(mine)
    row['active'] = bool(mine)
    if not all_commits:
        return row
    snap = all_commits[-1][0]
    # the starter as distributed: the last template (teacher) commit before the student's first
    template = [c for c in all_commits if c[4] and (not mine or c[1] <= mine[0][1])]
    first = (template or all_commits)[-1][0]

    # 1 prompts
    docs = show(repo, snap, 'docs/README.md')
    counts = prompt_answers(docs)
    row['prompts'] = len(counts)
    row['prompts_answered'] = answered(counts)
    row['prompt_words'] = ' '.join(f'{k}:{v}' for k, v in sorted(counts.items()))

    # 2 labels
    kept = []
    for name in spec['code']:
        start = show(repo, first, find_file(repo, first, name))
        now = show(repo, snap, find_file(repo, snap, name))
        given = label_lines(start)
        if given:
            kept.append((len(given & label_lines(now)), len(given)))
    if kept:
        row['labels_given'] = sum(g for _, g in kept)
        row['labels_kept'] = sum(k for k, _ in kept)
    starter = {norm(l) for name in spec['code'] for l in show(repo, first, find_file(repo, first, name)).split('\n')}
    for fname, method, stage in spec['methods']:
        src = show(repo, snap, find_file(repo, snap, fname))
        region = (('', src) if src else None) if method is None else (method_region(src, method) if src else None)
        row[f'm_{method or fname[:-5]}'] = classify_region(region, starter)

    # 3 order
    code_times = [c[1] for c in mine if any(f.split('/')[-1] in spec['code'] for f in c[3])]
    answer_time = answer_commit = None
    for c in mine:
        if 'docs/README.md' in c[3] and answered(prompt_answers(show(repo, c[0], 'docs/README.md'))):
            answer_time, answer_commit = c[1], c[0]
            break
    code_commit = next((c[0] for c in mine if any(f.split('/')[-1] in spec['code'] for f in c[3])), None)
    if answer_time and code_times:
        if answer_commit == code_commit:
            row['order'] = 'same commit'
        else:
            row['order'] = 'answers first' if answer_time < code_times[0] else 'code first'
        row['answers_at_end'] = answer_time >= code_times[-1]
    else:
        row['order'] = 'answers only' if answer_time else ('code only' if code_times else 'neither')

    # 4 plan issue
    ex, pfile, pmethod = spec['plan_issue']
    if use_issues:
        ex_re = re.compile(r'(?<![\d.])%s(?!\d)' % re.escape(ex))
        cands = [i for i in load_issues(repo, cohort, issues_cache) if ex_re.search(i.get('title', ''))]
        if not cands:
            row['plan_issue'] = 'none'
        else:
            best = max(cands, key=lambda i: words(i.get('body') or ''))
            row['plan_issue'] = plan_class(best.get('body'))
            opened = parse_git_datetime(best['createdAt'].replace('T', ' ').rstrip('Z'))
            appeared = None
            for c in mine:
                src = show(repo, c[0], find_file(repo, c[0], pfile)) if pfile.split('/')[-1] in [f.split('/')[-1] for f in c[3]] else ''
                if src and (pmethod is None or method_region(src, pmethod)):
                    appeared = c[1]
                    break
            # createdAt is UTC and commit times are local (CEST, +2 h in September)
            row['plan_before_code'] = '' if appeared is None else bool(opened.timestamp() + 7200 <= appeared.timestamp())

    # 5 tests
    passed = total = 0
    for under, src in tests.items():
        name = f'{under}Test'
        student_src = show(repo, snap, find_file(repo, snap, f'{under}.java'))
        p, t, status = run_test(name, src, student_src)
        row[f't_{under}'] = f'{p}/{t}' if t else status
        passed += p
        total += t
    row['tests_passed'] = passed
    return row


def run(task, cohort, tasks_dir, use_issues=True, workers=8, quiet=False):
    spec = VARIANTS.get(task)
    if not spec:
        raise SystemExit(f'fidelity: no variant spec for {task} (have {", ".join(VARIANTS)})')
    tests = load_tests(tasks_dir, task)
    if not tests:
        raise SystemExit(f'fidelity: no *Test.java on {tasks_dir}/{task}:solutions')
    repos = [(r, s) for r, s in find_task_repos(cohort.repos_dir, task) if not cohort.is_teacher(s)]
    cache_path = cohort.repos_dir / f'.fidelity-issues-{task}.json'
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    if use_issues:  # fill the cache serially: gh and ensure_remote are not worth racing
        for r, _ in repos:
            load_issues(r, cohort, cache)
        cache_path.write_text(json.dumps(cache))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(lambda rs: analyse(rs[0], rs[1], task, cohort, spec, tests, cache, use_issues), repos))
    fields = ['author', 'repository', 'active', 'student_commits', 'prompts', 'prompts_answered', 'prompt_words',
              'labels_given', 'labels_kept'] + \
             [f'm_{m or f[:-5]}' for f, m, _ in spec['methods']] + \
             ['order', 'answers_at_end', 'plan_issue', 'plan_before_code'] + \
             [f't_{u}' for u in tests] + ['tests_passed']
    out = cohort.task_data_dir(task) / 'fidelity.csv'
    write_csv(out, rows, fields)
    if not quiet:
        print(f'{task}: {len(rows)} repositories, {sum(1 for r in rows if r.get("active"))} active -> {out.relative_to(ROOT)}')
    return rows


# --- report ---------------------------------------------------------------------------

def pct(n, d):
    return f'{100 * n / d:.0f}%' if d else '–'


def report(cohort):
    lines = [f'# Worked-example fidelity, {cohort.name}', '',
             'Generated by `scripts/fidelity.py`. Aggregates only; the unit is the student repository '
             'judged at the deadline, and percentages are of *active* repositories (at least one '
             'student commit by the deadline) unless stated.', '']
    for task in VARIANTS:
        path = cohort.task_data_dir(task) / 'fidelity.csv'
        if not path.exists():
            continue
        rows = read_csv(path)
        act = [r for r in rows if r['active'] == 'True']
        n = len(act)
        lines += [f'## {task}', '', f'{len(rows)} repositories, {n} active.', '']

        # 1
        k = max((int(r['prompts'] or 0) for r in act), default=0)
        dist = {'none': 0, 'some': 0, 'all': 0}
        per = {i: [] for i in range(1, k + 1)}
        for r in act:
            a = int(r['prompts_answered'] or 0)
            dist['none' if a == 0 else 'all' if a >= k else 'some'] += 1
            for part in (r['prompt_words'] or '').split():
                i, w = part.split(':')
                per.setdefault(int(i), []).append(int(w))
        lines += ['**1. Prompts answered** — '
                  + ', '.join(f'{key} {pct(v, n)}' for key, v in dist.items()), '',
                  '| Prompt | answered | median words (answered) |', '| ---: | ---: | ---: |']
        for i in sorted(per):
            ans = [w for w in per[i] if w >= 3]
            lines.append(f'| {i} | {pct(len(ans), n)} | {statistics.median(ans) if ans else "–"} |')
        lines.append('')

        # 2
        given = [r for r in act if r.get('labels_given')]
        if given:
            full = sum(1 for r in given if r['labels_kept'] == r['labels_given'])
            frac = statistics.median(int(r['labels_kept']) / int(r['labels_given']) for r in given)
            lines += [f'**2. Subgoal labels** — starter 🏷 lines all kept in {pct(full, len(given))}; '
                      f'median share kept {frac:.0%}.', '']
        mcols = [c for c in rows[0] if c.startswith('m_')]
        lines += ['| Method (stage) | own labels | reused labels | commented | bare | absent |',
                  '| --- | ---: | ---: | ---: | ---: | ---: |']
        stages = {f'm_{m or f[:-5]}': s for f, m, s in VARIANTS[task]['methods']}
        for c in mcols:
            vals = [r[c] for r in act]
            lines.append(f'| `{c[2:]}` ({stages[c]}) | ' + ' | '.join(pct(vals.count(v), n) for v in
                                                                      ('own labels', 'reused labels', 'commented', 'bare', 'absent')) + ' |')
        lines.append('')

        # 3
        orders = [r['order'] for r in act]
        both = [r for r in act if r['answers_at_end'] in ('True', 'False')]
        lines += ['**3. Order** — ' + ', '.join(f'{o} {pct(orders.count(o), n)}' for o in
                                                  ('answers first', 'same commit', 'code first', 'code only', 'answers only', 'neither')),
                  f'Of students with both, {pct(sum(1 for r in both if r["answers_at_end"] == "True"), len(both))} '
                  f'committed no answer before their last code commit (answers at the end).', '']

        # 4
        pi = [r['plan_issue'] for r in act if r.get('plan_issue')]
        if pi:
            timed = [r for r in act if r.get('plan_issue') not in ('', 'none') and r['plan_before_code'] in ('True', 'False')]
            ex = VARIANTS[task]['plan_issue'][0]
            lines += [f'**4. Plan in an issue (Exercise {ex})** — ' +
                      ', '.join(f'{c} {pct(pi.count(c), n)}' for c in ('plan', 'brief', 'title only', 'none')) +
                      f'. Opened before the code appeared: {pct(sum(1 for r in timed if r["plan_before_code"] == "True"), len(timed))} '
                      f'of {len(timed)} with an issue.', '']

        # 5
        tcols = [c for c in rows[0] if c.startswith('t_')]
        lines += ['**5. Instructor tests at the deadline**', '',
                  '| Test class | all pass | some fail | API mismatch | compile error | missing | timeout |',
                  '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for c in tcols:
            vals = [r[c] for r in act]
            allp = sum(1 for v in vals if '/' in v and v.split('/')[0] == v.split('/')[1])
            some = sum(1 for v in vals if '/' in v) - allp
            lines.append(f'| `{c[2:]}Test` | {pct(allp, n)} | {pct(some, n)} | {pct(vals.count("api"), n)} | '
                         f'{pct(vals.count("compile"), n)} | '
                         f'{pct(vals.count("missing"), n)} | {pct(vals.count("timeout"), n)} |')
        lines += ['', '| Prompts answered | n | mean tests passed |', '| --- | ---: | ---: |']
        for band in ('none', 'some', 'all'):
            grp = [r for r in act if ('none' if int(r['prompts_answered'] or 0) == 0 else
                                      'all' if int(r['prompts_answered'] or 0) >= k else 'some') == band]
            mean = statistics.mean(int(r['tests_passed'] or 0) for r in grp) if grp else 0
            lines.append(f'| {band} | {len(grp)} | {mean:.1f} |')
        lines.append('')
        for note in NOTES.get(task, []):
            lines += [f'> {note}', '']
    lines += ['## Notes on the measures', ''] + [f'* {n}' for n in COMMON_NOTES] + ['']
    out = ROOT / 'reports' / 'fidelity.md'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'-> {out.relative_to(ROOT)}')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('tasks', nargs='*', help='task names, e.g. task-1 task-2 (default: all with a spec)')
    p.add_argument('--tasks-dir', default=str(Path.home() / 'dev' / 'workedexample' / 'tasks'),
                   help='instructor task repositories holding the solutions branch (for the tests)')
    p.add_argument('--skip-issues', action='store_true', help='no gh calls; signal 4 left empty')
    p.add_argument('--report-only', action='store_true', help='rebuild reports/fidelity.md from existing CSVs')
    p.add_argument('--workers', type=int, default=8)
    context.add_cohort_arg(p)
    a = p.parse_args()
    cohort = context.load(a.cohort)
    if not a.report_only:
        for task in a.tasks or list(VARIANTS):
            if not any(True for _ in find_task_repos(cohort.repos_dir, task)):
                print(f'{task}: no clones under {cohort.repos_dir}, skipped')
                continue
            run(task, cohort, a.tasks_dir, use_issues=not a.skip_issues, workers=a.workers)
    report(cohort)


if __name__ == '__main__':
    main()
