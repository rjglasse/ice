#!/usr/bin/env python3
"""Regenerate every table and figure the report depends on, then build report/report.pdf.

    python3 scripts/report.py            # tables + figures + latexmk
    python3 scripts/report.py --no-pdf   # tables + figures only

Runs history.py (2025 vs controls, and the current cohort for tasks done so far),
compare.py --all (weekly table), behaviour.py (behavioural profile, pacing and message
figures) and then latexmk in report/. Prose lives in report/report.tex; do not edit the
generated files under report/tables and report/figures by hand.
"""

import argparse
import shutil
import subprocess

import context
import history
import compare
import behaviour


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--no-pdf', action='store_true')
    p.add_argument('--baseline', type=int, default=2025)
    context.add_cohort_arg(p)
    a = p.parse_args()
    cohort = context.load(a.cohort)
    baseline = context.load(a.baseline)

    history.run(baseline.year, history.DD1337_TASKS)
    done = sorted((d.name for d in cohort.data_dir.glob('task-*') if (d / 'commits.csv').exists()), key=lambda t: int(t.split('-')[1]))
    dd1337 = [t for t in done if int(t.split('-')[1]) <= 9]
    if dd1337:
        history.run(cohort.year, dd1337)
    compare.run(None, cohort, baseline, all_tasks=True, quiet=True)
    years = [y for y in context.available_years() if y <= baseline.year]
    behaviour.run(baseline.year, years, behaviour.TASKS)
    if dd1337 and cohort.year != baseline.year:
        # behaviour of the current cohort so far, against the same tasks in every year
        behaviour.run(cohort.year, context.available_years(), dd1337, tag=f'_{cohort.year}')

    if a.no_pdf:
        return
    if not shutil.which('latexmk'):
        print('[report] latexmk not found; tables and figures are up to date, PDF not built')
        return
    r = subprocess.run(['latexmk', '-pdf', '-interaction=nonstopmode', '-halt-on-error', 'report.tex'],
                       cwd=context.ROOT / 'report', capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout[-3000:])
        raise SystemExit('[report] LaTeX build failed')
    print(f"[report] built {context.ROOT / 'report' / 'report.pdf'}")


if __name__ == '__main__':
    main()
