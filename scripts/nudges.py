#!/usr/bin/env python3
"""Classify each student's workflow for one task and generate the nudge message.

Two models live here, selected by "nudge_model" in cohorts/<year>.json:

  v1  the 2025 model (paper). Planning = issue count / exercises, with a 50% penalty when
      issues < exercises/2; five categories; message lists planning, coding, completion,
      automation; cohort block = the five-rung class distribution.
  v2  from 2026 (docs/improvements.md IMP-18). Planning judges the plan the student chose:
      the default links, a partial use of them, their own issues, or a mix (scripts/plan.py).
      An own or mixed plan that is used (referenced from commits or closed) counts as a full
      plan; the underplanning penalty applies only to a partially used default plan or no
      plan. Cohort block = "Where you are": the student's own movement since the previous
      task plus three class numbers (IMP-12, option 2).

compare.py always uses v1 so that years stay comparable; nudges.csv records both scores.
Output: data/<year>/<task>/nudges.csv.
"""

import argparse

import context
from common import read_csv, write_csv

FIELDS = ['author', 'commits', 'issues', 'open_issues', 'closed_issues', 'references', 'closing_references',
          'plan_style', 'covered', 'linked_issues', 'score_v1', 'classification_v1', 'score', 'classification',
          'previous_classification', 'streak', 'nudge_message', 'issue_created', 'issue_url']

CATEGORIES = ["🌟 Workflow Master", "🚀 Strong Practitioner", "📈 Developing Process",
              "🌱 Learning Workflow", "🎯 Getting Started"]

GUIDE_URL = "https://gits-15.sys.kth.se/inda-26/course-instructions/blob/master/ice-guide.md"
# v1 footer wording (2025) is kept in the v1 renderer; v2 links the published guide (IMP-5).
GUIDE_NOTE = f"\n\nSee the [ICE workflow guide]({GUIDE_URL}) for the full explanation."


def read_effort_data(effort_file):
    rows = []
    for r in read_csv(effort_file):
        ratio = r['commits_to_issues_ratio']
        rows.append({
            'author': r['author'],
            'commits': int(r['commits']),
            'issues': int(r['issues']),
            'commits_to_issues_ratio': float('inf') if ratio == 'inf' else float(ratio),
            'total_changes': int(r['total_changes']),
            'avg_changes_per_commit': float(r['avg_changes_per_commit']),
            'open_issues': int(r['open_issues']),
            'closed_issues': int(r['closed_issues']),
            'references': int(r['references']),
            'closing_references': int(r['closing_references']),
        })
    return rows


# ----------------------------------------------------------------------------- v1 (2025)
def workflow_score(a, expected_exercises):
    """2025 model. Kept unchanged for cross-year comparison."""
    commits, issues = a['commits'], a['issues']
    closed_issues, closing_references = a['closed_issues'], a['closing_references']
    issue_score = min(issues / expected_exercises, 1.0) if expected_exercises > 0 else 0
    commit_score = min(commits / max(issues, 1), 1.0) if issues > 0 else (1.0 if commits > 0 else 0)
    closing_score = closing_references / max(closed_issues, 1) if closed_issues > 0 else 0
    overall = issue_score * 0.45 + commit_score * 0.25 + closing_score * 0.3
    if issues < (expected_exercises / 2):   # n.b. task-1 of 2025 did not have the "/ 2"
        overall *= 0.5
    return overall


def classify_score(score):
    if score >= 0.95:
        return CATEGORIES[0]
    elif score >= 0.75:
        return CATEGORIES[1]
    elif score >= 0.50:
        return CATEGORIES[2]
    elif score >= 0.25:
        return CATEGORIES[3]
    return CATEGORIES[4]


def classify_workflow_performance(a, expected_exercises):
    return classify_score(workflow_score(a, expected_exercises))


def coding_completion_automation_lines(a, plural=False):
    """The three lines shared by both models (2025 wording). With plural=True (v2, IMP-25)
    the commit/issue counts are pluralised correctly ("1 commit"); v1 keeps the 2025 text."""
    commits, issues = a['commits'], a['issues']
    open_issues, closed_issues, closing_references = a['open_issues'], a['closed_issues'], a['closing_references']
    n_commits = f"{commits} commit" + ("" if plural and commits == 1 else "s")
    n_issues = f"{issues} issue" + ("" if plural and issues == 1 else "s")
    L = []
    if commits == 0 and issues > 0:
        L.append(f"💻 **Coding**: Start coding - issues need commits ({n_commits}, {n_issues})")
    elif commits < issues:
        L.append(f"💻 **Coding**: More commits needed ({commits}/{issues}, target: ≥1 commit per issue)")
    elif commits >= issues and issues > 0:
        L.append(f"💻 **Coding**: Good commit frequency ({n_commits} for {n_issues}, ratio: {round(commits / issues, 1)})")
    elif commits > 0 and issues == 0:
        L.append(f"💻 **Coding**: Active coding but consider planning with issues first ({n_commits})")

    if open_issues > 0 and closed_issues > 0:
        L.append(f"🎯 **Completion**: Close remaining issues to finish tasks ({open_issues} open, {closed_issues} closed)")
    elif open_issues > 0 and closed_issues == 0:
        L.append(f"🎯 **Completion**: Start completing issues ({open_issues} open, {closed_issues} closed)")
    elif closed_issues > 0 and open_issues == 0:
        L.append(f"✅ **Completion**: Excellent - all issues completed ({closed_issues} closed)")
    else:
        L.append("🎯 **Completion**: No issues to track completion yet")

    if closing_references == 0 and closed_issues > 0:
        L.append(f"⚡ **Automation**: Use closing keywords like 'Fixes # 1' to automate workflow ({closing_references}/{closed_issues} issues properly closed)")
    elif closing_references > 0 and closed_issues > 0:
        pct = int((closing_references / closed_issues) * 100)
        if pct >= 80:
            L.append(f"⚡ **Automation**: Perfect use of closing keywords ({closing_references}/{closed_issues} issues, {pct}%)")
        else:
            L.append(f"⚡ **Automation**: Good start, use closing keywords more often ({closing_references}/{closed_issues} issues, {pct}%)")
    else:
        L.append("⚡ **Automation**: Complete some issues to practice using closing keywords")
    return L


def planning_line_v1(a, expected):
    issues = a['issues']
    if issues == 0:
        return f"📝 **Planning**: Create issues for each exercise to track progress ({issues}/{expected} issues)"
    elif issues < expected:
        return f"📝 **Planning**: Nice that you've made your own plan, but try making more issues ({issues}/{expected}, default: ~{expected})"
    elif issues > expected + 2:
        return f"📝 **Planning**: Good issue tracking! ({issues}/{expected})"
    return f"📝 **Planning**: Well-balanced issue planning ({issues}/{expected} issues)"


def generate_nudge_message(a, task_name, expected):
    """v1 message body (2025)."""
    lines = [planning_line_v1(a, expected)] + coding_completion_automation_lines(a)
    return "Here's how it went for your plan and process:\n" + "\n".join(f"- {n}" for n in lines)


def format_distribution_summary(classification_counts, user_classification):
    """v1 cohort block: the five-rung class distribution."""
    total = sum(classification_counts.values())
    if total <= 1:
        return ""
    parts = []
    for category in CATEGORIES:
        count = classification_counts.get(category, 0)
        if count > 0:
            pct = int(count / total * 100)
            parts.append(f"**{category}: {pct}%** (<< you)" if category == user_classification else f"{category}: {pct}%")
    return "\n\n📊 **Class Distribution**:\nHere's how the rest of the course did:\n" + "\n".join(f"- {p}" for p in parts)


# ----------------------------------------------------------------------------- v2 (2026)
def plan_breadth(p, expected):
    """(real_issues, covered, units, narrow): a plan is narrow when it is a single issue that
    covers less than half of the exercises, i.e. most of the task was done without a plan."""
    real = int(p['issues']) - int(p['warmup_issues'])
    covered = int(p['covered'])
    units = max(real, covered)
    narrow = real < 2 and covered < expected / 2 and expected > 1  # a one-exercise task is covered by one issue
    return real, covered, units, narrow


def plan_components_v2(a, p, expected):
    """(plan_score, penalty) for the v2 model from effort row `a` and plan row `p`.

    A plan that is *used* (at least one issue referenced from a commit, or closed) counts as a
    full plan whatever its style, provided it has some breadth: two or more issues, or coverage
    of at least half the exercises. A single used issue for one exercise gets partial credit
    (0.6) without the penalty. An unused plan scores by coverage of the exercises, and the 50%
    underplanning penalty applies only when it covers less than half of them. No plan: 0.
    """
    style = p['plan_style']
    real, covered, units, narrow = plan_breadth(p, expected)
    coverage = min(units / expected, 1.0) if expected > 0 else 0
    used = int(p['linked_issues']) > 0 or a['closed_issues'] > 0
    if style == 'none' or real <= 0:
        return 0.0, 0.5
    if style == 'default-complete':
        return 1.0, 1.0
    if used:
        return (max(coverage, 0.6), 1.0) if narrow else (1.0, 1.0)
    return coverage, (0.5 if units < expected / 2 else 1.0)


def workflow_score_v2(a, p, expected):
    commits, issues = a['commits'], a['issues']
    closed_issues, closing_references = a['closed_issues'], a['closing_references']
    plan_score, penalty = plan_components_v2(a, p, expected)
    commit_score = min(commits / max(issues, 1), 1.0) if issues > 0 else (1.0 if commits > 0 else 0)
    closing_score = closing_references / max(closed_issues, 1) if closed_issues > 0 else 0
    return (plan_score * 0.45 + commit_score * 0.25 + closing_score * 0.3) * penalty


def planning_line_v2(p, expected, default_plan=True):
    style = p['plan_style']
    real, covered, units, narrow = plan_breadth(p, expected)
    s = 's' if real != 1 else ''
    if not default_plan:  # cohort without pre-filled issue links (IMP-27): the plan is always the student's own
        if style == 'none':
            return ("📝 **Planning**: No plan yet. Before you start, open an issue for each part of the task "
                    "in your own words; that is the plan we look for.")
        cov = f", covering {covered} of the {expected} parts" if covered and expected > 1 else ""
        if narrow:
            return (f"📝 **Planning**: You made a plan: {real} issue{s}{cov}. Good start; most of the task ran "
                    f"without an issue, so next time give each part of the task one too and your progress will show.")
        return f"📝 **Planning**: You made your own plan: {real} issue{s}{cov}. That's the idea, a plan in your words that you then work through."
    if style == 'none':
        return (f"📝 **Planning**: No plan yet. The {expected} exercise links give you a ready-made one, "
                f"or write your own issues, whichever suits you.")
    cov = f", covering {covered} of the {expected} exercises" if covered else ""
    if style == 'own' and narrow:
        return (f"📝 **Planning**: You made your own plan: {real} issue{s}{cov}. Your own issues are welcome; "
                f"the rest of the task ran without one, so next time give the other exercises an issue too and your progress will show.")
    if style == 'own':
        return (f"📝 **Planning**: You made your own plan: {real} issue{s}{cov}. "
                f"That's the idea, the default links are only a suggestion.")
    if style == 'mixed' and narrow:
        return (f"📝 **Planning**: One link and a plan of your own ({real} issue{s}{cov}). Good start; "
                f"most of the task ran without an issue, so next time give the other exercises one too.")
    if style == 'mixed':
        return (f"📝 **Planning**: A mix of the default links and your own issues ({real} issue{s}, "
                f"{covered} of {expected} exercises covered). Good, the plan is yours to shape.")
    if style == 'default-complete':
        return f"📝 **Planning**: You used the default plan, one issue per exercise ({expected} of {expected})."
    return (f"📝 **Planning**: You used {real} of the {expected} default links. If that's the plan you needed, fine. "
            f"If exercises got done without an issue, next time either open the link first or write one issue that covers them.")


def movement_reason(a, p, prev):
    """One clause naming the component that changed most since the previous task (v2)."""
    if not prev:
        return ""
    def comps(a_, p_):
        expected = int(p_['expected']) or 1
        plan, pen = plan_components_v2(a_, p_, expected)
        issues = a_['issues']
        commit = min(a_['commits'] / max(issues, 1), 1.0) if issues > 0 else (1.0 if a_['commits'] > 0 else 0)
        closing = a_['closing_references'] / max(a_['closed_issues'], 1) if a_['closed_issues'] > 0 else 0
        return {'plan': plan * pen, 'commit': commit, 'closing': closing}
    now, before = comps(a, p), comps(prev['effort'], prev['plan'])
    key = max(now, key=lambda k: abs(now[k] - before[k]))
    delta = now[key] - before[key]
    if abs(delta) < 0.1:
        return "small changes across the board" if a is not None and prev else "same footing as last week"
    up = delta > 0
    if key == 'plan':
        return "your plan covered the whole task this week" if up else "the plan covered less of the task this week"
    if key == 'commit':
        return "you made at least one commit per issue" if up else "several issues had no commit this week"
    c, n = a['closing_references'], a['closed_issues']
    return (f"you closed {min(c, n)} of {n} issues with keywords" if up
            else f"fewer issues were closed with keywords ({min(c, n)} of {n})")


def class_sentence(counts):
    """One picture of the class (IMP-26): top share, the next rung, the cumulative share computed
    from counts (not from rounded percentages), and the bottom share."""
    total = sum(counts.values()) or 1
    n = {c: counts.get(c, 0) for c in CATEGORIES}
    top = round(100 * n[CATEGORIES[0]] / total)
    second = round(100 * n[CATEGORIES[1]] / total)
    upper = round(100 * (n[CATEGORIES[0]] + n[CATEGORIES[1]]) / total)
    low = round(100 * n[CATEGORIES[4]] / total)
    return (f"Class this week: {top}% are Workflow Master and another {second}% Strong Practitioner, "
            f"so {upper}% are at that level or above. {low}% are still Getting Started.")


def where_you_are_v2(classification, counts, previous_classification, reason, streak):
    total = sum(counts.values()) or 1
    top = round(100 * counts.get(CATEGORIES[0], 0) / total)
    head = "\n\n📊 **Where you are**\n"
    if previous_classification is None:
        return (head + f"You start in **{classification}**. {class_sentence(counts)} "
                f"Next week's feedback will show how you moved.")
    if classification == previous_classification:
        if classification == CATEGORIES[0] and streak >= 2:
            line = f"**{classification}**, {streak} weeks running. {top}% of the class are here with you."
        elif reason == "same footing as last week":
            line = f"**{classification}**, as last week. {class_sentence(counts)}"
        else:
            line = f"**{classification}**, as last week ({reason}). {class_sentence(counts)}"
        return head + line
    arrow = f"**{previous_classification} → {classification}** since last week ({reason})."
    return head + arrow + "\n" + class_sentence(counts)


def previous_task(cohort, task):
    n = int(task.split('-')[1])
    prev = f'task-{n - 1}'
    return prev if n > 1 and cohort.task(prev) is not None else None


def load_previous(cohort, task):
    """{author: {'classification', 'streak', 'effort', 'plan'}} from the previous task, or {}."""
    prev = previous_task(cohort, task)
    if not prev:
        return {}
    d = cohort.task_data_dir(prev)
    if not (d / 'nudges.csv').exists():
        return {}
    out = {}
    plan_rows = {r['author']: r for r in read_csv(d / 'plan.csv')} if (d / 'plan.csv').exists() else {}
    effort_rows = {r['author']: r for r in read_effort_data(d / 'effort.csv')} if (d / 'effort.csv').exists() else {}
    for r in read_csv(d / 'nudges.csv'):
        a = r['author']
        streak = int(r.get('streak', 1) or 1)
        out[a] = {'classification': r['classification'], 'streak': streak,
                  'effort': effort_rows.get(a), 'plan': plan_rows.get(a)}
    return out


def build_nudges(effort_data, task, expected, model='v1', plan_rows=None, previous=None, default_plan=True):
    plan_rows = plan_rows or {}
    previous = previous or {}
    rows = []
    counts = {}
    for a in effort_data:
        p = plan_rows.get(a['author'])
        s1 = workflow_score(a, expected)
        if model == 'v2' and p:
            s = workflow_score_v2(a, p, expected)
        else:
            s = s1
        c = classify_score(s)
        counts[c] = counts.get(c, 0) + 1
        rows.append((a, p, s1, s, c))

    out = []
    for a, p, s1, s, c in rows:
        prev = previous.get(a['author'])
        prev_c = prev['classification'] if prev else None
        streak = (prev['streak'] + 1) if prev and prev_c == c else 1
        if model == 'v2' and p:
            body = "Here's how it went for your plan and process:\n" + "\n".join(
                f"- {l}" for l in [planning_line_v2(p, expected, default_plan)] + coding_completion_automation_lines(a, plural=True))
            reason = movement_reason(a, p, prev if prev and prev.get('effort') and prev.get('plan') else None)
            if reason == "small changes across the board" and prev_c == c:
                reason = "same footing as last week"
            block = where_you_are_v2(c, counts, prev_c, reason, streak)
            message = body + block + GUIDE_NOTE
        else:
            message = generate_nudge_message(a, task, expected) + format_distribution_summary(counts, c) + GUIDE_NOTE
        out.append({
            'author': a['author'], 'commits': a['commits'], 'issues': a['issues'],
            'open_issues': a['open_issues'], 'closed_issues': a['closed_issues'],
            'references': a['references'], 'closing_references': a['closing_references'],
            'plan_style': p['plan_style'] if p else '', 'covered': p['covered'] if p else '',
            'linked_issues': p['linked_issues'] if p else '',
            'score_v1': round(s1, 4), 'classification_v1': classify_score(s1),
            'score': round(s, 4), 'classification': c,
            'previous_classification': prev_c or '', 'streak': streak,
            'nudge_message': message, 'issue_created': False, 'issue_url': '',
        })
    return out, counts


def run(task, cohort, quiet=False):
    expected = cohort.expected_exercises(task)
    model = cohort.raw.get('nudge_model', 'v1')
    if not cohort.default_plan and model != 'v2':
        print(f"[nudges] cohorts/{cohort.name}.json has default_plan false: the v1 model assumes the exercise links, using v2")
        model = 'v2'
    if cohort.task(task) is None:
        print(f"[nudges] WARNING: {task} not in cohorts/{cohort.name}.json, using {expected} expected exercises")
    elif cohort.is_provisional(task):
        print(f"[nudges] WARNING: exercise count for {task} is PROVISIONAL ({expected}) - verify against the task README")
    d = cohort.task_data_dir(task)
    effort_file = d / 'effort.csv'
    if not effort_file.exists():
        raise SystemExit(f"[nudges] missing {effort_file}; run effort.py first")
    effort_data = read_effort_data(effort_file)

    plan_rows = {}
    if model == 'v2':
        import plan
        plan_rows = {r['author']: r for r in plan.run(task, cohort, quiet=True)}
    previous = load_previous(cohort, task) if model == 'v2' else {}

    rows, counts = build_nudges(effort_data, task, expected, model, plan_rows, previous, cohort.default_plan)
    out = d / 'nudges.csv'
    if out.exists():  # keep what has already been posted
        posted = {r['author']: r for r in read_csv(out) if str(r.get('issue_created', '')).lower() == 'true'}
        for r in rows:
            if r['author'] in posted:
                r['issue_created'] = True
                r['issue_url'] = posted[r['author']].get('issue_url', '')
        if posted:
            print(f"[nudges] {len(posted)} students already posted; flags kept (use feedback.py --edit to update their issue)")
    write_csv(out, rows, FIELDS)
    print(f"[nudges] {cohort.name}/{task}: {len(rows)} students, model {model}, expected exercises {expected}"
          + (f", previous task {previous_task(cohort, task)} ({len(previous)} students)" if previous else "") + f" -> {out}")
    total = sum(counts.values()) or 1
    for c in CATEGORIES:
        if counts.get(c):
            print(f"  {c}: {counts[c]} ({int(counts[c] / total * 100)}%)")
    if not quiet:
        for r in rows:
            print(f"  {r['author']} ({r['classification']}): {r['nudge_message'][:60]}...")
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('task', help='task name, e.g. task-1')
    p.add_argument('-q', '--quiet', action='store_true')
    context.add_cohort_arg(p)
    args = p.parse_args()
    run(args.task, context.load(args.cohort), args.quiet)


if __name__ == '__main__':
    main()
