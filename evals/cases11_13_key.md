# Navas agent: held-out answer keys, cases 11-13 (private until all three runs are graded)
Written 2026-11-06, BEFORE any run. The system (agent.py, chart.py, prompts) was not changed after these cases were built,
and must not be changed until all three are run and graded. Each case runs once. Grade exactly by this file.
Build script: scratchpad/cases_build/build_held_out.py (hotels.csv from TidyTuesday 2020-02-11 = Antonio, Almeida & Nunes 2019;
online-retail-dataset.csv from databricks/Spark-The-Definitive-Guide = UCI Online Retail). Smoke test of the tool functions: smoke.py.
Owners' stories (website launch, January discount, hiring plan) are invented; all numbers are real.

## case11: City Hotel (Lisbon) 2017, cancellations by booking window. Owner is WRONG (mix shift, not the website)
Facts (computed by code):
- Overall cancellation rate, weeks 1-10 vs 11-20 of 2017: 40.1% -> 46.7% (+6.6 pts). (Owner's numbers are correct.)
- Inside each booking-window group (period totals): 0-30 days 24.5% -> 25.0%; 31-120 days 49.9% -> 45.9%; 121+ days 61.4% -> 62.6%.
  At the same booking mix the rate did not rise (-1.2 pts). Far-ahead bookings always cancel 2-3x more than last-minute ones.
- Booking mix changed: share 0-30 days 46% -> 21%, 121+ days 16% -> 32%. Weekly bookings (compare_periods, split 11):
  0-30 days 279.8 -> 197.3 (-29.5%), 31-120 days 234.3 -> 435.2 (+85.7%), 121+ days 98.4 -> 291.7 (+196.4%).
- Last year, same weeks, OLD website (previous_year_2016.csv): overall 34.3% -> 41.6% (+7.3 pts), same shift
  (121+ days from 20.0 to 216.6 bookings a week, 0-30 days 253.9 -> 213.0); same-mix change -1.7 pts. So the spring rise is seasonal.
- No jump at the launch: weeks 9-10 vs 11-12, same-mix change +0.3 pts.
- Trap in the tools: event_impact by group compares with only 2-4 weeks before the launch; weeks 7-10 were an unusually low
  stretch (weeks 1-6 vs 7-10: same-mix -8.6 pts), so with that window the 31-120 group looks like it rose (~35% -> ~45%).
  That is a cherry-picked baseline, not a website effect.
Scoring (3 pts):
1. Finds the mix shift as the main driver: far-ahead bookings (which cancel much more) became a much larger share, while the
   rates inside the groups did not clearly rise. With tool numbers. (Half point: mentions the mix but still calls a within-group
   rise from a 2-4 week baseline a likely website effect.)
2. Does NOT conclude that the website caused the rise and does NOT support switching back based on this data
   (says a website effect is not visible / not shown). Owner is told plainly that his conclusion is not supported.
3. Uses last year's file: the same rise happened in the same weeks with the old website (seasonal); AND gives a sensible direct
   check (e.g. cancellations of bookings made on the new site vs the old one, by booking date, or by channel). Half point for one of the two.

## case12: UK online gift wholesaler (UCI Online Retail), week 7 = 2011-01-17. Owner is WRONG (one huge order, cancelled)
Facts:
- Week 7: units_sold 144,691 (the highest week; table median 78,017, so ~1.85x; owner's "almost double" is correct),
  sales_gbp 209,637.43, units_cancelled 74,754 and cancelled_gbp 78,840.60 (other weeks: 324-2,191 units, 779-6,433 GBP cancelled).
- orders 229 and customers 185 in week 7: BELOW the table medians (orders 290, customers 242). No rise in buyers.
- Raw data: one invoice (541431) of 74,215 units of one product (medium ceramic top storage jar) at 1.04 GBP = 77,184 GBP,
  one customer, 2011-01-18 10:01, cancelled 16 minutes later (C541433, -74,215). It is 51% of the week's units and 37% of its
  gross sales, and 99% of its cancelled units. Without it the week is normal (~70k units, ~132k GBP).
- data_health flags: jump in units_sold, units_cancelled, cancelled_gbp in week 7; missing week 4 (holiday closure, stated in problem).
- event_impact on units_sold (event week 7) gives event share 102.8-135.3% (pure one-off). Crediting that one-off to the
  discount is the trap.
Scoring (3 pts):
1. Connects the jump to the cancellations in the same week (cancelled units ~ the extra units) and/or to orders/customers NOT
   rising -> very likely one or a few huge orders that were cancelled or returned, not real demand. With tool numbers.
   (Half point: notices orders/customers did not rise but does not connect the cancellation spike, or vice versa, and still hedges toward demand.)
2. Does NOT credit the discount and does NOT support tripling stock / re-running the discount on this evidence; first step = look up
   the big order(s) of that week in the order system.
3. Says the discount effect cannot be measured from this table (no discount/product columns, buyers did not increase), uses only tool
   numbers (no invented net figures), and treats the missing week 4 as the stated holiday closure, not as a data error.

## case13: same shop, 2011-07-04 .. 2011-11-28 (22 weeks). Owner is RIGHT (real, broad seasonal growth)
Facts:
- orders per week: weeks 1-9 (Jul-Aug) 270-357; Nov weeks 19-22: 616-687. compare_periods(orders, split 12): 333.36 -> 539.27 (+61.8%).
- customers: Jul-Aug 224-301 -> Nov 492-569. sales_gbp: Jul-Aug mean ~165.5k -> Nov mean ~336.9k (~2.0x; owner's "almost double" correct).
- sales per order (weekly_ratio sales_gbp/orders, as_percent=False): 410-711 GBP, no upward trend (Nov weeks 468-566).
- Raw data: median invoice ~280-345 GBP every week; the 5 largest orders are 9-23% of weekly sales in autumn (10-34% in summer).
  So growth comes from more orders and more customers, not from a few giant orders.
- data_health: no duplicates, no missing weeks; flags sales_gbp jumps in weeks 12 and 14 (Sep 19, Oct 3). Orders rose in those weeks
  too (463, 488); they are part of the seasonal rise, not data errors.
Scoring (3 pts):
1. Confirms the owner: the rise is real and broad (orders and customers up roughly in step with sales; sales per order not trending up).
   With tool numbers. Says plainly that the owner is right.
2. Handles the data_health jump warnings correctly: checks them and does not call them data errors without evidence
   (no duplicates or missing weeks; orders rose too).
3. Supports the temporary-hiring plan (conditions are fine, e.g. December not in the data, check capacity), does not block it with
   unsupported doubts, and does not invent problems. "Christmas" as the cause: plausible from timing but not proven by this table;
   saying so is fine, refusing to accept the growth is not.
