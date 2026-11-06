# Navas agent

An AI agent that investigates a business problem from data, and shows its work.

Most AI tools answer confidently, even when the data behind the answer is broken. Navas agent is built around one rule: **an AI answer is only useful if you can check it.** Code computes every number, an independent critic tries to break the conclusion, and a human approves before anything is final.

This is an early, learning-in-public project by Patrick Navasartian (applied AI engineering).

## How it works

1. **Data health check (code, not a model).** Before any analysis it flags duplicate rows, empty cells, missing or partial weeks, tiny weeks, and sudden jumps or drops.
2. **Diagnoser agent** (Claude Haiku) reads the owner's problem and calls tools. It may not do mental arithmetic: every number must come from a tool output.
3. **Number auditor (code).** Flags any number in a report that does not appear in the tool outputs.
4. **Independent critic** (a different model, Claude Sonnet) re-checks the data with the same tools and tries to weaken the conclusion.
5. **Plain-language summary** for the business owner (problem in one sentence, confidence, three conditional next steps) plus a chart computed by code.
6. **Human approval gate.** Nothing final is written without an explicit `approve`. Every tool call is logged in a trace file.

## Test cases

Each case is a weekly CSV table plus the owner's claim (`problem.txt`). Some owners are right, some are wrong, and some datasets contain traps. The detailed answer keys are kept private so the tests stay honest.

| Case | Data | Owner's claim | A good answer must | Result |
|---|---|---|---|---|
| case7 | Olist e-commerce (real) | "Sellers ship poor-quality products" | Find the late-delivery link, and not confirm a guess the data cannot test | 3/3, re-run 3/3 |
| case8 | Bike sharing, Washington DC 2012 (real) | "The storm caused the drop" | Agree when the evidence supports it, and flag the missing recorded hours | 2.5/3, then 2/3, then 2.5/3 after a fix (see notes) |
| case9 | Olist, with injected duplicate rows | "Our campaign doubled orders" | Catch the duplicates, and not support tripling the budget | 3/3 |
| case10 | Olist 2018 (real) | "Orders collapsed, cut marketing" | Flag the incomplete end of the export, and not support cutting the budget | 3/3 |
| case1-6 | Synthetic practice cases | various | various | early tests |

**Score so far on real-data cases: 19 / 21 over 7 runs** (2026-11-05 and 2026-11-06). This is a small set of cases that I built myself, so it is not yet a reliable error rate. The same case can also get a different score on a different run, so each case needs several runs.

What went wrong, and what changed:
- **case8:** the diagnoser's report was cut off (too long). The critic noticed it and still reached a sound answer: the storm explains part of the drop, and rentals also stayed lower afterwards (season). But the summary understated the storm's share and wrongly called the Christmas week "incomplete" (it was a real holiday dip). Fix: the agent now retries once with a compact report when its output is cut off, and the summary must keep the critic's "probably" instead of turning it into a fact. case8 will be re-run.
- **case8, re-run:** the report was complete this time and the Christmas week was described correctly, but the agent decided that the storm days' missing hours were "only a recording problem, not a real drop". The data cannot tell a closed service from a broken log. The cause was my own wording in the data health check, which called those weeks "not fully recorded". Fix: the warning now names both explanations and tells the agent not to pick one without evidence.
- **case8, third run (after the fix):** the summary now gives both explanations for the missing hours, and says the drop is real. It still under-credits the storm: it calls the cause "unknown" instead of saying the storm explains most of that week's extra drop. The critic pushed back on the diagnoser's "the storm is not the main cause". Pattern so far: the system is better at catching wrong claims than at confirming right ones. Next idea: a tool that computes how much of a drop a known event explains.
- **case7, re-run:** still 3/3, but long tool outputs were cut at 8,000 characters, so the agent and the critic saw only part of the weeks. Fix: tool outputs now go up to 30,000 characters and say clearly when they are cut.
- **Number auditor:** it flagged integers that were simply rounded from a tool's decimal (228 from 228.21). Fix: rounding to a whole number is now accepted.
- **case9:** the summary halved the duplicated weeks by itself. The numbers were right, but the number auditor still flagged them, because they did not come from a tool. That is the auditor doing its job.

## Run it

Requirements: Python 3.9+, `pip install -r requirements.txt`, and an Anthropic API key in the `ANTHROPIC_API_KEY` environment variable.

```
python3 run.py case8
```

At the end the program asks for your decision (`approve` / `reject`). Outputs are written next to `run.py`: `report_<case>.md`, `critique_<case>.md`, `summary_<case>.md`, `audit_<case>.txt`, `trace_<case>.json`, `approval_<case>.json`, `chart_<case>.svg`, and, after approval, `final_<case>.html`.

## Honest limits

- Early build. Four real-data cases so far (11.5/12, one run each); a reliable error rate needs many more cases and repeated runs.
- Works on weekly CSV tables only.
- Diagnosis, not a guarantee: the summary gives conditional next steps, and a human decides.

## Data sources and licenses

- **Brazilian E-Commerce Public Dataset by Olist** (Kaggle, `olistbr/brazilian-ecommerce`), licensed **CC BY-NC-SA 4.0**. Cases 7, 9 and 10 are weekly aggregates derived from it; case 9 contains deliberately duplicated rows as a test. These derived files are shared under the same license (non-commercial, share-alike).
- **Bike Sharing Dataset**, UCI Machine Learning Repository. Case 8 is a weekly aggregate of the hourly data. Please cite: Fanaee-T, Hadi, and Gama, Joao, "Event labeling combining ensemble detectors and background knowledge", *Progress in Artificial Intelligence* (2013), pp. 1-15, Springer, doi:10.1007/s13748-013-0040-3.
- Cases 1-6 are synthetic.

A license for the code has not been chosen yet.
