"""Chart for the owner summary, written as a plain SVG file (no extra libraries needed).
A case can describe its own chart in cases/<case>/chart.json; otherwise a known table shape is used.
English labels on purpose (no right-to-left problems). All values are computed by code from the data file."""
import csv
import glob
import json
import os

COLORS = ["#2563eb", "#f97316", "#16a34a", "#9333ea"]

# Known table shapes (used when a case has no chart.json)
SPECS = [
    {"num": "purchases", "den": "sessions", "group": "device", "title": "Share of visits that end in a purchase",
     "foot": "Purchases per 100 sessions", "direction": "drop", "scale": 100, "unit": "%"},
    {"num": "low_reviews", "den": "reviews", "group": "delivery", "title": "Share of reviews that are 1-2 stars",
     "foot": "1-2 star reviews per 100 reviews", "direction": "rise", "scale": 100, "unit": "%"},
]


def _load(data_dir, spec):
    num, den, grp = spec["num"], spec.get("den"), spec.get("group")
    need = {"week", num} | ({den} if den else set())
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        with open(path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if not need <= set(reader.fieldnames or []):
                continue
            rows = list(reader)
        series, total = {}, {}
        for r in rows:
            if r[num] == "" or (den and r[den] == ""):
                continue
            g = (r.get(grp) if grp else None) or "all"
            w = int(float(r["week"]))
            p, s = float(r[num]), (float(r[den]) if den else 1.0)
            a = series.setdefault(g, {}).setdefault(w, [0.0, 0.0])
            a[0] += p
            a[1] += s
            t = total.setdefault(w, [0.0, 0.0])
            t[0] += p
            t[1] += s
        if len(total) >= 4:
            return series, total
    return None, None


def make_chart(data_dir, case):
    specs = list(SPECS)
    custom = os.path.join(data_dir, "chart.json")
    if os.path.exists(custom):
        specs = [json.load(open(custom, encoding="utf-8"))]
    for spec in specs:
        series, total = _load(data_dir, spec)
        if series:
            break
    else:
        return None, "no suitable table for a chart"

    den, grp, scale, unit = spec.get("den"), spec.get("group"), spec.get("scale", 1), spec.get("unit", "")
    direction, title, foot = spec.get("direction", "abs"), spec["title"], spec["foot"]
    value = (lambda ps: ps[0] / ps[1] * scale if ps[1] else 0.0) if den else (lambda ps: ps[0] * scale)
    weeks = sorted(total)
    all_den = sum(v[1] for v in total.values())
    shown = {g: v for g, v in series.items()
             if len(series) == 1 or grp != "device" or sum(x[1] for x in v.values()) >= 0.10 * all_den}

    # where to put the red marker (computed by code)
    if den:
        dens = sorted(v[1] for v in total.values())
        floor = dens[len(dens) // 2] * 0.25      # ignore tiny, noisy weeks for ratios
        ok = [w for w in weeks if total[w][1] >= floor]
    else:
        ok = weeks
    changes = [(value(total[ok[i]]) - value(total[ok[i - 1]]), ok[i]) for i in range(1, len(ok))]
    if direction == "drop":
        change, mark_week = min(changes)
        mark = "Biggest weekly drop (all)"
    elif direction == "rise":
        change, mark_week = max(changes)
        mark = "Biggest weekly rise (all)"
    else:
        change, mark_week = max(changes, key=lambda c: abs(c[0]))
        mark = "Biggest weekly change (all)"

    W, H, L, R, T, B = 800, 460, 80, 30, 84, 60
    allvals = [value(v) for d in shown.values() for v in d.values()] + [value(v) for v in total.values()]
    ymax = max(allvals) * 1.12 or 1
    x = lambda w: L + (w - weeks[0]) / max(1, (weeks[-1] - weeks[0])) * (W - L - R)
    y = lambda v: H - B - v / ymax * (H - T - B)

    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
         'font-family="Helvetica, Arial, sans-serif">' % (W, H, W, H),
         '<rect width="100%" height="100%" fill="white"/>',
         '<text x="%d" y="32" font-size="20" font-weight="bold">%s</text>' % (L, title)]
    steps = (0.25, 0.5, 1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000)
    step = next((c for c in steps if ymax / c <= 7), steps[-1])
    g = 0.0
    while g <= ymax:
        o.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" stroke="#e5e7eb"/>' % (L, y(g), W - R, y(g)))
        o.append('<text x="%d" y="%.1f" font-size="12" text-anchor="end" fill="#555">%s%s</text>'
                 % (L - 8, y(g) + 4, ("{:,.0f}".format(g) if g >= 1000 else "%g" % g), unit))
        g += step
    every = max(1, len(weeks) // 13)
    for w in weeks[::every]:
        o.append('<text x="%.1f" y="%d" font-size="12" text-anchor="middle" fill="#555">%d</text>' % (x(w), H - B + 20, w))
    o.append('<text x="%d" y="%d" font-size="13" text-anchor="middle" fill="#333">Week of the period</text>' % ((L + W - R) // 2, H - 15))
    o.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="6 4"/>'
             % (x(mark_week), T - 8, x(mark_week), H - B))
    near_right = x(mark_week) > W - R - 190
    o.append('<text x="%.1f" y="%d" font-size="12" fill="#dc2626" text-anchor="%s">%s</text>'
             % (x(mark_week) + (-6 if near_right else 6), T + 4, "end" if near_right else "start", mark))

    def line(data, color, dash=""):
        ws = sorted(data)
        pts = " ".join("%.1f,%.1f" % (x(w), y(value(data[w]))) for w in ws)
        o.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5" %s/>' % (pts, color, dash))
        if not dash:
            for w in ws:
                o.append('<circle cx="%.1f" cy="%.1f" r="3.5" fill="%s"/>' % (x(w), y(value(data[w])), color))

    names = []
    for i, (name, data) in enumerate(sorted(shown.items())):
        line(data, COLORS[i % len(COLORS)])
        names.append((name.replace('_', ' ').capitalize() if name != "all" else "All", COLORS[i % len(COLORS)], ""))
    if len(shown) > 1:
        line(total, "#111827", 'stroke-dasharray="2 4"')
        names.append(("All", "#111827", 'stroke-dasharray="2 4"'))
    lx, yy = L, 58                               # legend in one row under the title, never on top of the data
    for n, c, d in names:
        o.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="2.5" %s/>' % (lx, yy, lx + 24, yy, c, d))
        o.append('<text x="%d" y="%d" font-size="13" fill="#222">%s</text>' % (lx + 30, yy + 4, n))
        lx += 30 + 9 * len(n) + 26
    hidden = ' Small device groups hidden.' if grp == 'device' and len(shown) < len(series) else ''
    o.append('<text x="%d" y="%d" font-size="11" fill="#777">%s. Source: data file, computed by code.%s</text>' % (L, H - 2, foot, hidden))
    o.append("</svg>")
    out = "chart_" + case + ".svg"
    open(out, "w", encoding="utf-8").write("\n".join(o))
    return out, "%s at week %d (%.2f)" % (mark, mark_week, change)
