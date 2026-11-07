# Navas agent

An AI agent that investigates a business problem from data, and shows its work.

Most AI tools answer confidently, even when the data behind the answer is broken. Navas agent is built around one rule: **an AI answer is only useful if you can check it.** Code computes every number, an independent critic tries to break the conclusion, and a human approves before anything is final.

This is an early, learning-in-public project by Patrick Navasartian (applied AI engineering).

## How it works

1. **Data health check (code, not a model).** Before any analysis it flags duplicate rows, empty cells, missing or partial weeks, tiny weeks, and sudden jumps or drops. It also checks **freshness**: the newest week in each file is compared with the date of the owner's question (`as_of` in the case's `meta.json`, otherwise today's date). A file can look complete and still be old; then the agent must not report an old week as "this week". Every owner summary starts with a "data up to" stamp computed by code. (This check came from a reader's comment on LinkedIn.)
2. **Diagnoser agent** (Claude Haiku) reads the owner's problem and calls tools. It may not do mental arithmetic: every number must come from a tool output.
3. **Event impact (code).** When the owner blames a specific event (a storm, a campaign, a closure), the agent measures how much of the change happened only in the event weeks and how much lasted afterwards, using 2, 3 and 4 weeks before and after. It reports a range, not a single magic number.
4. **Number auditor (code).** Flags any number in a report that does not appear in the tool outputs.
5. **Independent critic** (a different model, Claude Sonnet) re-checks the data with the same tools and tries to weaken the conclusion.
6. **Plain-language summary** for the business owner (problem in one sentence, confidence, three conditional next steps) plus a chart computed by code.
7. **Human approval gate.** Nothing final is written without an explicit `approve`. Every tool call is logged in a trace file.

## Test cases

Each case is a weekly CSV table plus the owner's claim (`problem.txt`). Some owners are right, some are wrong, and some datasets contain traps. The detailed answer keys are kept private so the tests stay honest.

| Case | Data | Owner's claim | A good answer must | Result |
|---|---|---|---|---|
| case7 | Olist e-commerce (real) | "Sellers ship poor-quality products" | Find the late-delivery link, and not confirm a guess the data cannot test | 3/3, re-run 3/3 |
| case8 | Bike sharing, Washington DC 2012 (real) | "The storm caused the drop" | Credit the storm's real extra dip, see the seasonal decline, and flag the missing recorded hours | 3/3, 2/3, 2.5/3, 2.5/3 (re-graded, see notes) |
| case9 | Olist, with injected duplicate rows | "Our campaign doubled orders" | Catch the duplicates, and not support tripling the budget | 3/3 |
| case10 | Olist 2018 (real) | "Orders collapsed, cut marketing" | Flag the incomplete end of the export, and not support cutting the budget | 3/3 |
| case14 | UK online gift wholesaler, Apr-Aug 2011 (real); the file stops 11 days before the owner's question | "This week's sales dropped; give 20% off from tomorrow" | Notice that the newest week in the file is not this week, and ask for a fresh export before any discount | not run yet (practice case for the freshness check) |
| case1-6 | Synthetic practice cases | various | various | early tests |

**Score so far on real-data cases: 22 / 24 over 8 runs** (2026-11-05 and 2026-11-06).

**Important caveat: these cases are now "practice" cases, not a clean test.** I changed the prompts and tools several times after looking at case8 results. A system tuned on its own test cases will look better than it really is. The next honest measurement has to use new cases the system has never been tuned on.

**A correction to my own grading (case8).** After building the event impact tool, I ran it on case8 myself. My answer key said "the storm is the main cause". The tool shows that the storm week's extra dip explains roughly a third to a half of the drop (32-50%, depending on the comparison window), and the rest lasted into November (season). So the agent's first answer, "the storm is only part of the story", was closer to the truth than my key, and I re-graded that run from 2.5 to 3. Lesson: the answer key needs the same checking as the agent. This is a small set of cases that I built myself, so it is not yet a reliable error rate. The same case can also get a different score on a different run, so each case needs several runs.

What went wrong, and what changed:
- **case8:** the diagnoser's report was cut off (too long). The critic noticed it and still reached a sound answer: the storm explains part of the drop, and rentals also stayed lower afterwards (season). But the summary understated the storm's share and wrongly called the Christmas week "incomplete" (it was a real holiday dip). Fix: the agent now retries once with a compact report when its output is cut off, and the summary must keep the critic's "probably" instead of turning it into a fact. case8 will be re-run.
- **case8, re-run:** the report was complete this time and the Christmas week was described correctly, but the agent decided that the storm days' missing hours were "only a recording problem, not a real drop". The data cannot tell a closed service from a broken log. The cause was my own wording in the data health check, which called those weeks "not fully recorded". Fix: the warning now names both explanations and tells the agent not to pick one without evidence.
- **case8, third run (after the fix):** the summary now gives both explanations for the missing hours, and says the drop is real. It still under-credits the storm: it calls the cause "unknown" instead of saying the storm explains most of that week's extra drop. The critic pushed back on the diagnoser's "the storm is not the main cause". Pattern so far: the system is better at catching wrong claims than at putting a size on right ones. Fix: the event impact tool (step 3 above), which turns "the storm is part of it" into a measured range.
- **case8, fourth run (with event impact):** the diagnoser used the new tool correctly and said the storm explains about 32-50% of the drop. The critic then re-measured per recorded hour, found the rainy days normal per open hour, and treated "the system was closed during the storm" as a separate cause, which pushed the summary to "we cannot put a number on the storm". But a closure during a storm is part of the storm's effect. Root cause: the critic's instructions told it to "reject or weaken" the report, so it weakened a correct conclusion. Fix: the critic now verifies instead of weakening, says "accept" when the evidence holds, and counts missing data that coincides with the event as part of the event's effect (while still asking the owner to confirm).
- **case7, re-run:** still 3/3, but long tool outputs were cut at 8,000 characters, so the agent and the critic saw only part of the weeks. Fix: tool outputs now go up to 30,000 characters and say clearly when they are cut.
- **Number auditor:** it flagged integers that were simply rounded from a tool's decimal (228 from 228.21). Fix: rounding to a whole number is now accepted.
- **case9:** the summary halved the duplicated weeks by itself. The numbers were right, but the number auditor still flagged them, because they did not come from a tool. That is the auditor doing its job.

## Held-out test (pre-registered on 2026-11-06)

Cases 1-10 were used while building the system, so their scores are optimistic. Cases 11-13 are new: built from two real public datasets the system has never seen, after the last change to the code. The rules:

- The code and prompts stay frozen until all three cases have been run.
- Each case is run once, and the result is reported as it is, good or bad.
- The answer key was written before any run. Its SHA-256 fingerprint is published here first, so anyone can check later that the key was not edited after seeing the results. The key itself will be published after grading.

| Case | Data | Owner's claim | Result |
|---|---|---|---|
| case11 | Hotel bookings, Lisbon, Jan-May 2017, plus the same weeks of 2016 (real) | "Our new booking website made cancellations jump; switch back" | 3/3 |
| case12 | UK online gift wholesaler, Dec 2010 - Mar 2011 (real) | "Our January discount almost doubled units sold; triple the stock" | 3/3 |
| case13 | Same shop, Jul - Nov 2011 (real) | "Autumn growth is real and broad; hire two temporary packers" | 2.5/3 |

**Held-out score: 8.5 / 9** (one run each, 2026-11-06). The answer key is now published in [`evals/cases11_13_key.md`](evals/cases11_13_key.md); its SHA-256 still matches the fingerprint published before the runs:
`643cbaba5a3063fc0ea65ef79a25c6789793ac3e636fdbf01fb9c37a53a0f841`. Point-by-point grades: [`evals/cases11_13_grades.md`](evals/cases11_13_grades.md).

What the held-out test showed:
- **The right conclusion in all three cases.** The hotel's rise in cancellations came from a change in booking mix (more bookings made months ahead, which always cancel more), and the same rise happened last year with the old website. The "best week ever" was one huge order cancelled the same week. The autumn growth was real and broad.
- **Lost half a point on the owner-is-right case.** It confirmed the growth, then still told the owner to re-check two flagged weeks before fixing the number of hires, although its own critic had shown the growth holds without them. Same pattern as before: better at catching wrong claims than at backing right ones.
- **A right answer reached partly by breaking a rule.** In case11 the correct rates inside each booking group came from the critic dividing by hand, against the system's "no mental arithmetic" rule (it said so openly, and the number auditor flagged the numbers). The diagnoser had compared counts instead of rates. Missing tool: a ratio over a whole period, by group.
- **Number auditor false alarms:** Persian thousands separators split one number into two, and dates, years and "about 73 thousand" were flagged.
- **Small sample.** Three cases, one run each. This is a first honest measurement, not a reliable error rate. These cases have now been seen, so the next honest test needs new cases again.

The owners and their stories in these three cases (the website launch, the January discount, the hiring plan) are invented; the numbers come from the real datasets.

## Run it

Requirements: Python 3.9+, `pip install -r requirements.txt`, and an Anthropic API key in the `ANTHROPIC_API_KEY` environment variable.

```
python3 run.py case8
```

A case is a folder in `cases/` with one or more weekly CSV files, `problem.txt` (the owner's words), and optionally `meta.json`: `{"as_of": "YYYY-MM-DD"}` is the date of the owner's question (without it, today's date is used), and `"not_current": ["file.csv"]` marks comparison files, such as last year's data, that are not expected to be up to date.

At the end the program asks for your decision (`approve` / `reject`). Outputs are written next to `run.py`: `report_<case>.md`, `critique_<case>.md`, `summary_<case>.md`, `audit_<case>.txt`, `trace_<case>.json`, `approval_<case>.json`, `chart_<case>.svg`, and, after approval, `final_<case>.html`.

## Honest limits

- Early build. Four real-data practice cases (22/24 over 8 runs, but the system was tuned on them) and three held-out cases (8.5/9, one run each). A reliable error rate needs many more cases and repeated runs.
- Works on weekly CSV tables only.
- Diagnosis, not a guarantee: the summary gives conditional next steps, and a human decides.

## Data sources and licenses

- **Brazilian E-Commerce Public Dataset by Olist** (Kaggle, `olistbr/brazilian-ecommerce`), licensed **CC BY-NC-SA 4.0**. Cases 7, 9 and 10 are weekly aggregates derived from it; case 9 contains deliberately duplicated rows as a test. These derived files are shared under the same license (non-commercial, share-alike).
- **Bike Sharing Dataset**, UCI Machine Learning Repository. Case 8 is a weekly aggregate of the hourly data. Please cite: Fanaee-T, Hadi, and Gama, Joao, "Event labeling combining ensemble detectors and background knowledge", *Progress in Artificial Intelligence* (2013), pp. 1-15, Springer, doi:10.1007/s13748-013-0040-3.
- **Hotel booking demand datasets**: Nuno Antonio, Ana de Almeida and Luis Nunes, *Data in Brief* 22 (2019), pp. 41-49, doi:10.1016/j.dib.2018.11.126, an open-access article under the CC BY license, with the data supplied with the paper (I used the copy in the TidyTuesday project, 2020-02-11). Case 11 is a weekly aggregate of the City Hotel bookings by booking window.
- **Online Retail**: Chen, D. (2015), UCI Machine Learning Repository, doi:10.24432/C5BW33, licensed **CC BY 4.0** (I used the copy in `databricks/Spark-The-Definitive-Guide`). Cases 12, 13 and 14 are weekly aggregates of product sales (postage and fees excluded).
- Cases 1-6 are synthetic.

A license for the code has not been chosen yet.
