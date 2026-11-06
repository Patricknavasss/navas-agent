"""Builds one clean HTML page for the business owner: summary, chart, details, approval stamp.
No extra libraries. Opens by double-click in any browser."""
import html
import os
import re


def _inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md_to_html(md):
    out, in_ul, in_ol = [], False, False

    def close():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>"); in_ul = False
        if in_ol:
            out.append("</ol>"); in_ol = False

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close(); continue
        if line.startswith("![") or line.startswith("---"):
            close(); continue
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            close(); n = min(len(m.group(1)) + 1, 4)
            out.append("<h%d>%s</h%d>" % (n, _inline(m.group(2)), n)); continue
        m = re.match(r"^\s*[-*]\s+(.*)", line)
        if m:
            if in_ol: out.append("</ol>"); in_ol = False
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append("<li>%s</li>" % _inline(m.group(1))); continue
        m = re.match(r"^\s*\d+[.)]\s+(.*)", line)
        if m:
            if in_ul: out.append("</ul>"); in_ul = False
            if not in_ol: out.append("<ol>"); in_ol = True
            out.append("<li>%s</li>" % _inline(m.group(1))); continue
        if line.startswith(">"):
            close(); out.append("<p class='warn'>%s</p>" % _inline(line.lstrip("> "))); continue
        close(); out.append("<p>%s</p>" % _inline(line))
    close()
    return "\n".join(out)


def build_html(case, title, summary_md, report_md, critique_md, chart_svg_path, record):
    svg = ""
    if chart_svg_path and os.path.exists(chart_svg_path):
        svg = open(chart_svg_path, encoding="utf-8").read()
    status = {"approved": "تأیید انسان", "rejected": "رد شده", "no-decision": "بدون تصمیم"}.get(record["decision"], "")
    note = (" — " + html.escape(record["note"])) if record.get("note") else ""
    warn = ""
    if record.get("unverified_numbers_in_report") or record.get("unverified_numbers_in_critique"):
        warn = ("<p class='warn'>بازرس عددها این عددها را در خروجی ابزارها پیدا نکرد (در جزئیات فنی): %s %s</p>"
                % (record.get("unverified_numbers_in_report"), record.get("unverified_numbers_in_critique")))
    return """<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>
 body{font-family:-apple-system,'Segoe UI',Tahoma,sans-serif;max-width:820px;margin:32px auto;padding:0 18px;color:#1f2937;line-height:1.9}
 h1{font-size:26px;margin-bottom:4px} h2{font-size:20px;margin-top:30px;border-bottom:2px solid #e5e7eb;padding-bottom:4px}
 .meta{color:#6b7280;font-size:14px} .chart{margin:20px 0;direction:ltr;text-align:center}
 .chart svg{max-width:100%%;height:auto;border:1px solid #e5e7eb;border-radius:8px}
 .warn{background:#fff7ed;border-right:4px solid #f97316;padding:8px 12px;border-radius:6px;font-size:14px}
 details{margin-top:24px;border:1px solid #e5e7eb;border-radius:8px;padding:8px 14px} summary{cursor:pointer;font-weight:600}
 code{background:#f3f4f6;padding:1px 5px;border-radius:4px;direction:ltr;unicode-bidi:embed}
 .stamp{margin-top:30px;font-size:13px;color:#6b7280;border-top:1px solid #e5e7eb;padding-top:10px}
</style></head><body>
<h1>%(title)s</h1>
<div class="meta">پرونده: %(case)s</div>
%(summary)s
<div class="chart">%(svg)s</div>
<details><summary>جزئیات فنی: گزارش کامل تشخیص‌دهنده</summary>%(report)s</details>
<details><summary>جزئیات فنی: نقد منتقد مستقل</summary>%(critique)s</details>
%(warn)s
<div class="stamp">%(status)s — %(time)s%(note)s<br>
ساخته‌شده با Navas agent. اعداد را کد حساب کرده، منتقدی مستقل بررسی کرده، و انسان تأیید کرده است. هنوز روی داده‌ی تمرینی آزمایش شده و نرخ خطا اندازه‌گیری نشده.</div>
</body></html>""" % {
        "title": html.escape(title), "case": html.escape(case), "summary": md_to_html(summary_md),
        "svg": svg, "report": md_to_html(report_md), "critique": md_to_html(critique_md), "warn": warn,
        "status": status, "time": html.escape(record.get("time", "")), "note": note}
