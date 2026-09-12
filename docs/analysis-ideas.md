# Analysis ideas (open, not yet done)

Candidate questions beyond the current report, noted 2026-09-05. All are computable from
`data/` unless stated. The two marked ★ are the ones to add to the report first.

| # | Question | Data needed | Notes |
|---|---|---|---|
| ★ A1 | **Who moved?** Did the nudges lift the bottom, the top, or everyone? Compare the 10th/25th/75th percentiles of commits per student across cohorts. | commits, all years | Reframes the "median rose" headline. |
| A2 | **The persistent low-engagement subgroup.** Who are they: late starters, commits without issues, students who vanish after task 3? | commits, issues, inactive.csv | Tells whether a different nudge is needed or they are not doing the course. |
| ★ A3 | **Does the feedback cause next week's behaviour?** Per dimension: students told "use closing keywords" in task t vs students with the same starting share who were not told; compare the change in t+1. Threshold version: students just below vs just above a category boundary get different messages while behaving almost identically (regression-discontinuity flavour). | nudges.csv (as delivered) + effort per task, 2025 and 2026 | Closest this design gets to a per-message causal estimate. |
| A4 | **Trajectories.** Stickiness of Workflow Master, escapes from Getting Started, and when. 2026: do own/mixed planners stop converging on the default links under the v2 wording? | nudges per task, plan.py --trend | History folder has a 2025 alluvial and transitions heatmap as a start. |
| A5 | **Exercise level.** Which exercises get skipped (no issue, or never referenced), do students work in order, how long does an issue stay open (2026 has closedAt). Task 8's dip made concrete. | issues titles + commits refs; cohort link_titles | |
| A6 | **Process and product.** TA Pass/Komp issues (currently filtered out) as outcome: first-time pass by workflow category, komplettering rate by plan style, time from Komp to fix. | issues incl. teacher-created; repobee grades files | Course evaluation; report with care, aggregate only. |
| A7 | **Persistence beyond DD1337.** 2025 tasks 10-18: did the shape hold through spring, did message quality recover or keep hollowing out? Compare with earlier DD1338 data if any exists. | data/2025/task-10..18 | |
| A8 | **Goodhart signature over time.** Weekly trend of bare "Fixes #N", micro-commits, exactly one commit per issue, copied default titles, while category share stays high. | behaviour.py per task | Answers the ChatGPT critique directly. |
| A9 | **Cheap descriptives.** Day-of-week and hour patterns per cohort (Thursday vs Friday exercise groups); 2020 as pandemic anomaly (67% early starts); web-UI default messages as terminal-adoption proxy (17% -> 4%). | commits | |
| — | **Not possible.** Individual survey-to-behaviour linkage (survey is anonymous); whether feedback was read rather than reacted to; squashes and rebases. | | |
