# Held-out grades, cases 11-13 (graded 2026-11-06)

Each case was run once on 2026-11-06 with the frozen code (same `agent.py`, `chart.py`, `run.py` and `report_html.py` as commit 7a08828).
Graded against `cases11_13_key.md`, written before the runs. Its SHA-256 still matches the fingerprint published in the README before the runs:
`643cbaba5a3063fc0ea65ef79a25c6789793ac3e636fdbf01fb9c37a53a0f841`. Quotes below are translated from the Persian outputs.

**Total: 8.5 / 9**

## case11, hotel cancellations (owner wrong): 3 / 3

| Point | Score | Evidence |
|---|---|---|
| 1. Mix shift is the main driver | 1 | Summary: "Bookings made more than 120 days ahead grew a lot, and this group cancels more than the others. The cancellation rate inside each group did not go up after the new website." Report: 121+ day bookings rose from 98.4 to 291.7 a week (tool numbers). |
| 2. Does not blame the website or support switching back | 1 | Summary: "Do not bring back the old site until these checks are done." The critic adds that there is no evidence the site caused the cancellations. A small website effect is called "not ruled out", which is fair. |
| 3. Uses last year + gives a direct check | 1 | Summary: "Last year, with the old site, in the same weeks the rate went from about 34% to 42%." Direct check: count cancellations by booking channel (new site vs. intermediaries). |

Process flags (not in the key, reported anyway):
- The diagnoser compared cancellation **counts** instead of rates inside the groups, and wrongly said the owner's 40% and 47% could not be reproduced. The critic caught both.
- The correct within-group rates (24.5% to 25%, 50% to 46%, 61% to 63%) came from the critic **dividing by hand**, which breaks the system's own "no mental arithmetic" rule. The critic said so openly, and the number auditor flagged three of its numbers. The numbers are correct (checked by code). Missing tool: a ratio over a whole period, by group.
- The summary says the far-ahead bookings "nearly doubled". Their **share** doubled (16% to 32%); their **count** tripled.
- The run was recorded as "no-decision": `approve` was typed into the note prompt instead of the decision prompt.

## case12, "best week ever" (owner wrong): 3 / 3

| Point | Score | Evidence |
|---|---|---|
| 1. Links the jump to cancellations and to buyers not rising | 1 | Summary: "In that same week almost half of the units (51.66%) were cancelled or returned; in other weeks at most 3.11%." Customers fell from 212 to 185, orders fell too: "this fits one very large order, not more buyers." The critic: the cancellation spike (~73 thousand) is the same size as the units jump (~78 thousand). |
| 2. Does not credit the discount or support tripling stock | 1 | Summary: "probably one unusual bulk order, not the discount", "do not triple the stock until the cause is clear", first step: pull the five largest invoices of that week and check whether they were cancelled. |
| 3. Discount not measurable, tool numbers only, holiday gap handled | 1 | "The data has no information about the discount, so we neither confirm nor reject it." No invented net figure (the critic notes the tools cannot subtract). Missing week 4 explained by the stated holiday closure. |

Minor: the diagnoser first said sales in pounds barely rose; the critic corrected it (the same order inflated sales too).

## case13, autumn growth (owner right): 2.5 / 3

| Point | Score | Evidence |
|---|---|---|
| 1. Confirms real, broad growth | 1 | Summary: "Real customer growth: high confidence. Customers, orders and sales rose together and by similar amounts." "Value per order did not rise, so the growth is not from a few very large orders." |
| 2. Handles the jump warnings correctly | 1 | The critic re-checked weeks 12 and 14: customers and orders rose in those weeks too, and growth stays large without relying on them (+51% with a conservative split). The summary does not call them errors. |
| 3. Supports the hiring plan without unsupported doubts | 0.5 | It says temporary hiring is "probably reasonable, because orders doubled" and asks to size it to packing capacity (fine). But its first recommendation is to re-verify the two flagged weeks and "not finalize the number of hires until then", although its own critic had just shown the conclusion does not depend on them. That is an unsupported doubt delaying a sound decision. |

Minor: the summary says growth was ~51% "even after setting those two weeks aside"; the critic actually kept them in the "before" period, which makes the 51% a conservative figure, not an exclusion.

## Number auditor false alarms seen in these runs
- Persian thousands separators split one number into two: "172,910.57" written as «۱۷۲،۹۱۰.۵۷» was read as 172 and 910.57.
- Dates and years were flagged (27 December, 2010).
- "About 73 thousand" was flagged as 73.
