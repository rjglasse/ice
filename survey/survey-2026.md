# ICE student survey 2026 (draft)

Post-course survey for the 2026 cohort, built on the 2025 instrument
(`feedback/feedback-y1.csv`, n=103, 52% response). Items marked **repeat** keep the 2025
wording verbatim so the Likert distributions can be compared year on year (the 2025 column
index is given). Items marked **new** ask about what changed in 2026. Items marked
**dropped** were removed and why. Scale for all agreement items: 1 = strongly disagree,
5 = strongly agree, as in 2025.

Suggested timing: the week after task 9 (end of DD1337), same as 2025. Informed consent
first; participation voluntary; no grading consequence. **Anonymous, as in 2025**: no
username or identifying field is collected, so responses are compared with the repository
data at cohort level only.

## 0. Consent

| # | Item | Status |
|---|---|---|
| S1 | Do you agree to participate? (Yes / No) | repeat (2025 col 1) |

## 1. Git skills

| # | Item | Status |
|---|---|---|
| S2 | Before this course, I felt confident using Git and GitHub. | repeat (col 2) |
| S3 | During the course, my understanding of how to use Git/GitHub improved. | repeat (col 3) |

## 2. The expected workflow (nudge 1)

| # | Item | Status |
|---|---|---|
| S4 | The workflow (open issues + make commits + close with issue references) helped me structure my work. | repeat (col 4) |
| S5 | The expectations for how to use issues and commits were clear to me. | repeat (col 9) |
| S6 | Following this workflow helped me stay organised while working on each task. | repeat (col 10) |
| S7 | These expectations felt supportive rather than restrictive. | repeat (col 11) |
| S8 | What part of the expected workflow (issues, commits, references) was most or least helpful? (free text) | repeat (col 12) |
| S9 | When you wrote a commit message, what did you usually put in it? (single choice: only "Fixes #N" / "Fixes #N" plus a short description / a description without the issue number / it varied) | new: 2025 data shows half of all subjects were only "Fixes #N" |
| S10 | I knew whether a commit message should describe the change or whether "Fixes #N" was enough. | new: survey 2025 free text raised this |

## 3. Issue links (nudge 2)

| # | Item | Status |
|---|---|---|
| S11 | Did you use the issue links? (Yes / No / I don't remember) | repeat (col 5) |
| S12 | The issue links made it easier to follow the expected workflow. | repeat (col 6) |
| S13 | Using the issue links reduced friction or stress when starting a subtask. | repeat (col 7) |
| S14 | If you used the issue links, what worked well? If you didn't use them, why not? (free text) | repeat (col 8) |
| S15 | How did you usually plan a task? (single choice: opened the link for every exercise / opened some links / wrote my own issues / a mix of links and my own / I did not open issues) | new: matches the plan styles measured in the repositories |
| S16 | If you wrote your own issues or grouped exercises, did the feedback recognise that as a plan? (Yes / No / Not sure / Not applicable) | new: tests the v2 planning wording |

## 4. Individual feedback (nudge 3)

| # | Item | Status |
|---|---|---|
| S17 | The individual feedback helped me understand how well I planned my work. | repeat (col 13) |
| S18 | The feedback motivated me to improve how I structured future tasks. | repeat (col 14) |
| S19 | The tone of the feedback felt supportive. | repeat (col 15) |
| S20 | The feedback described what I had actually done. | new: catches mismatches (cutoff, identity, detection) |
| S21 | How often did you read the weekly feedback issue? (every week / most weeks / the first weeks only / rarely or never) | new: 2025 free text suggested habituation |
| S22 | Did the feedback ever say something that contradicted what you thought you had done? If so, what? (free text) | new |
| S23 | What kind of planning-related feedback would help you the most in the future? (free text) | repeat (col 16) |

## 5. Where you are (nudge 4, reformulated)

In 2025 this block showed the class distribution across five categories with your own marked.
In 2026 it showed your own category, your movement since the previous week with a reason, and
three class figures.

| # | Item | Status |
|---|---|---|
| S24 | Do you remember seeing your category and how it compared to the cohort? (Yes / Not sure / No) | repeat (col 17), wording kept |
| S25 | Seeing my category motivated me to improve my workflow. | repeat (col 18) |
| S26 | Seeing this comparison made me feel positive about my progress. | repeat (col 19) |
| S27 | Seeing how I had moved since the previous week was more useful to me than seeing where I stood in the class. | new: the option-2 hypothesis |
| S28 | The reason given for my movement ("you closed 5 of 6 issues with keywords") matched what I had done. | new |
| S29 | If you ignored or disliked this comparison, what was the reason? (free text) | repeat (col 20) |

## 6. Overall

| # | Item | Status |
|---|---|---|
| S30 | Give a score for the following from least helpful (1) to most helpful (5): Issue links for exercises | repeat (col 21) |
| S31 | ... Expected workflow (issue, commits, closing references) | repeat (col 22) |
| S32 | ... Individual planning feedback | repeat (col 23) |
| S33 | ... Weekly "where you are" comparison | repeat (col 24), label updated from "Course category comparison" |
| S34 | If the course could keep only one of these nudges next year, which should it be? | repeat (col 25); option label for the comparison updated as in S33 |
| S35 | What was the single most helpful part of the version-control workflow for your learning? (free text) | repeat (col 26) |
| S36 | What is one thing we should improve or remove next year? (free text) | repeat (col 27) |
| S37 | Had you heard about the workflow feedback from students who took the course last year before you started? (Yes / No / Not sure) | new: word-of-mouth threat named in docs/study-2026.md |

## Dropped

Nothing dropped. All 27 substantive 2025 items are repeated; 10 items are new, which puts
the survey at about 37 items, a few minutes longer than 2025. If it needs trimming, S10 and
S28 are the first candidates (S9 and S27 carry the same questions in a stronger form).

## Analysis plan

- Repeat items: compare 2025 and 2026 distributions item by item (Mann-Whitney on the
  1-5 scores, share agreeing 4-5), with the caveat that S24-S26 and S33-S34 refer to a
  reformulated nudge.
- S15 against the distribution of plan styles measured in the repositories, and S9 against
  the measured share of bare "Fixes #N" subjects: both at cohort level, since the survey is
  anonymous and cannot be linked to individual repositories.
- Free text (S8, S14, S22, S23, S29, S35, S36): thematic coding with the 2025 themes
  (`docs/feedback-2025-themes.md`, T1-T8) as the starting codebook, plus new codes as needed.
