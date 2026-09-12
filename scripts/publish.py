#!/usr/bin/env python3
"""Sync the tooling (and only the tooling) onto the public branch.

The working repository holds student data (data/, students/, feedback/, reports/) and
is never pushed as is. The public remote (origin) receives a separate branch, ``public``,
that contains the allowlisted files below, copied from the current checkout. Cohort
configs are copied without their ``teachers`` list (discover.py refills it locally).

    python3 scripts/publish.py            # build the public branch in .public/, commit, show diff
    python3 scripts/publish.py --push     # ...and push it to origin main

Guards: the publish is refused if any student username (from students/*/*.txt) or any
CSV file ends up in the public tree.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKTREE = ROOT / '.public'
BRANCH = 'public'
REMOTE = 'origin'
REMOTE_BRANCH = 'main'

# What the public repository is: paths relative to ROOT (directories are copied whole).
ALLOW = [
    'scripts',
    'README.md',
    'ice-guide.md',
    'CLAUDE.md',
    'docs/runbook.md',
    'docs/study-2026.md',
    'docs/improvements.md',
    'docs/analysis-ideas.md',
    'docs/task-mapping/README.md',
    'survey/README.md',
    'survey/survey-2026.md',
    'cohorts/current',
]
COHORT_JSON_DROP = ('teachers',)          # names; discovered again on the next weekly run
PUBLIC_GITIGNORE_EXTRA = """
# never in the public repository: student data and everything derived from it
/data/
/students/
/feedback/
/reports/
/report/
/paper/
/.public/
"""


def git(*args, cwd=ROOT, check=True, capture=True):
    r = subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=capture)
    if check and r.returncode != 0:
        sys.exit(f"[publish] git {' '.join(args)} failed:\n{r.stderr or r.stdout}")
    return (r.stdout or '').strip()


def ensure_worktree():
    git('fetch', '-q', REMOTE)
    branches = git('branch', '--list', BRANCH)
    if not branches:
        base = f'{REMOTE}/{REMOTE_BRANCH}'
        git('branch', BRANCH, base)
        print(f'[publish] created branch {BRANCH} from {base}')
    if not (WORKTREE / '.git').exists():
        if WORKTREE.exists():
            shutil.rmtree(WORKTREE)
        git('worktree', 'add', '-q', str(WORKTREE), BRANCH)
        print(f'[publish] worktree {WORKTREE} on branch {BRANCH}')


def clear_worktree():
    for p in WORKTREE.iterdir():
        if p.name == '.git':
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()


def copy_allowlist():
    for rel in ALLOW:
        src = ROOT / rel
        dst = WORKTREE / rel
        if not src.exists():
            print(f'[publish] skip (missing): {rel}')
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        else:
            shutil.copy2(src, dst)
    for cfg in sorted((ROOT / 'cohorts').glob('*.json')):
        raw = json.loads(cfg.read_text(encoding='utf-8'))
        for key in COHORT_JSON_DROP:
            raw.pop(key, None)
        out = WORKTREE / 'cohorts' / cfg.name
        out.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    ignore = (ROOT / '.gitignore').read_text(encoding='utf-8').rstrip('\n') + '\n' + PUBLIC_GITIGNORE_EXTRA
    (WORKTREE / '.gitignore').write_text(ignore, encoding='utf-8')


def student_usernames():
    names = set()
    for f in (ROOT / 'students').glob('*/*.txt'):
        for line in f.read_text(encoding='utf-8', errors='replace').splitlines():
            line = line.strip().split('@')[0].lower()
            if line and not line.startswith('#'):
                names.add(line)
    return names


def guard():
    problems = []
    csvs = [p for p in WORKTREE.rglob('*.csv') if '.git' not in p.parts]
    if csvs:
        problems.append(f'{len(csvs)} CSV file(s) in the public tree, e.g. {csvs[0].relative_to(WORKTREE)}')
    names = student_usernames()
    if not names:
        problems.append('no student lists under students/; run publish.py from the private working copy')
    if names:
        word = re.compile(r'[A-Za-z0-9_-]+')
        for p in WORKTREE.rglob('*'):
            if p.is_dir() or '.git' in p.parts:
                continue
            try:
                text = p.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            hits = sorted({w for w in word.findall(text) if w.lower() in names})
            if hits:
                problems.append(f'{p.relative_to(WORKTREE)}: student username(s) {", ".join(hits[:5])}')
    if problems:
        sys.exit('[publish] REFUSED, the public tree would contain data:\n  ' + '\n  '.join(problems))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--push', action='store_true', help=f'push {BRANCH} to {REMOTE} {REMOTE_BRANCH} after committing')
    p.add_argument('-m', '--message', help='commit message (default: tooling sync from the current main commit)')
    a = p.parse_args()

    ensure_worktree()
    clear_worktree()
    copy_allowlist()
    guard()

    git('add', '-A', cwd=WORKTREE)
    status = git('status', '--porcelain', cwd=WORKTREE)
    if not status:
        print('[publish] public branch already up to date')
    else:
        src = git('rev-parse', '--short', 'HEAD')
        msg = a.message or f'Tooling sync from {src}'
        git('commit', '-q', '-m', msg, cwd=WORKTREE)
        print(f'[publish] committed on {BRANCH}: {msg}')
        print(git('show', '--stat', '--format=', 'HEAD', cwd=WORKTREE))
    ahead = git('rev-list', '--count', f'{REMOTE}/{REMOTE_BRANCH}..{BRANCH}')
    if a.push:
        git('push', REMOTE, f'{BRANCH}:{REMOTE_BRANCH}', capture=False)
        print(f'[publish] pushed {BRANCH} to {REMOTE} {REMOTE_BRANCH}')
    else:
        print(f'[publish] {ahead} commit(s) ahead of {REMOTE}/{REMOTE_BRANCH}; push with: '
              f'python3 scripts/publish.py --push   (or: git push {REMOTE} {BRANCH}:{REMOTE_BRANCH})')


if __name__ == '__main__':
    main()
