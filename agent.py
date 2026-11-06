import csv
import json
import os
import sys
import anthropic

MODEL = "claude-haiku-5-5"        # تشخیص‌دهنده
CRITIC_MODEL = "claude-sonnet-5-5"  # منتقد: مدل متفاوت، تا اشتباه مشترک نکنند
MAX_STEPS = 12               # محافظ: عامل حق ندارد بی‌نهایت بچرخد

# پرونده‌ی مورد بررسی از ورودی ترمینال می‌آید: python3 lesson5.py case1
case = sys.argv[1] if len(sys.argv) > 1 else "case1"
if case != os.path.basename(case):
    sys.exit("نام پرونده مجاز نیست")
DATA_DIR = os.path.join("cases", case)
if not os.path.isdir(DATA_DIR):
    sys.exit("چنین پرونده‌ای نیست: " + DATA_DIR)

client = anthropic.Anthropic()


# ====================== ابزارها (کدِ ما حساب می‌کند) ======================
def load(name):
    """فقط فایل‌های csv داخل پوشه‌ی همین پرونده؛ هیچ مسیر دیگری مجاز نیست."""
    if not isinstance(name, str) or name != os.path.basename(name) or not name.endswith(".csv"):
        raise ValueError("نام فایل مجاز نیست")
    if name not in os.listdir(DATA_DIR):
        raise ValueError("چنین فایلی نیست: " + name)
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames, rows


def check_columns(fields, *cols):
    for c in cols:
        if c is not None and c not in fields:
            raise ValueError("ستون «" + str(c) + "» نیست. ستون‌ها: " + str(fields))


def list_files():
    files = [n for n in sorted(os.listdir(DATA_DIR)) if n.endswith(".csv")]
    return {"files": files}


def describe_file(name):
    fields, rows = load(name)
    empty = {c: sum(1 for r in rows if r[c] == "") for c in fields}
    return {"columns": fields, "rows": len(rows), "empty_cells_per_column": empty, "first_rows": rows[:3]}


def weekly_ratio(name, numerator, denominator, group_by=None, as_percent=True):
    """نسبت (مثل سفارش ÷ بازدید) هر هفته؛ به درصد، یا اگر as_percent=False نسبت ساده (مثل اجاره در هر روز)."""
    fields, rows = load(name)
    check_columns(fields, "week", numerator, denominator, group_by)
    sums = {}
    skipped = []
    for row in rows:
        group = row[group_by] if group_by else "all"
        week = int(row["week"])
        if row[numerator] == "" or row[denominator] == "":
            skipped.append({"week": week, "group": group})  # صفر حسابش نمی‌کنیم
            continue
        s = sums.setdefault((week, group), [0.0, 0.0])
        s[0] += float(row[numerator])
        s[1] += float(row[denominator])
    out = [
        {"week": w, "group": g, ("ratio_percent" if as_percent else "ratio"): round(n / d * (100 if as_percent else 1), 2) if d else None}
        for (w, g), (n, d) in sorted(sums.items())
    ]
    return {"rows": out, "skipped_missing": skipped}


def compare_periods(name, column, split_week, group_by=None):
    """میانگین هفتگی یک ستون، قبل و بعد از یک هفته؛ اختیاری به تفکیک یک ستون."""
    fields, rows = load(name)
    check_columns(fields, "week", column, group_by)
    split = int(split_week)
    per_week = {}
    skipped = []
    for row in rows:
        group = row[group_by] if group_by else "all"
        week = int(row["week"])
        if row[column] == "":
            skipped.append({"week": week, "group": group})
            continue
        per_week[(group, week)] = per_week.get((group, week), 0.0) + float(row[column])
    result = {}
    for g in sorted({g for g, _ in per_week}):
        before = [v for (gg, w), v in per_week.items() if gg == g and w < split]
        after = [v for (gg, w), v in per_week.items() if gg == g and w >= split]
        if not before or not after:
            result[g] = "داده‌ی کافی نیست"
            continue
        mb, ma = sum(before) / len(before), sum(after) / len(after)
        result[g] = {
            "mean_before": round(mb, 2),
            "mean_after": round(ma, 2),
            "percent_change": round((ma - mb) / mb * 100, 1) if mb else None,
            "weeks_before": len(before),
            "weeks_after": len(after),
        }
    return {"column": column, "split_week": split, "groups": result, "skipped_missing": skipped}


def weekly_values(name, column, group_by=None):
    """مقدار هر هفته‌ی یک ستون (جمع در هفته)؛ اختیاری به تفکیک یک ستون."""
    fields, rows = load(name)
    check_columns(fields, "week", column, group_by)
    sums = {}
    skipped = []
    for row in rows:
        group = row[group_by] if group_by else "all"
        week = int(row["week"])
        if row[column] == "":
            skipped.append({"week": week, "group": group})
            continue
        sums[(week, group)] = sums.get((week, group), 0.0) + float(row[column])
    out = [{"week": w, "group": g, "value": round(v, 2)} for (w, g), v in sorted(sums.items())]
    return {"column": column, "rows": out, "skipped_missing": skipped}


def _is_number(v):
    try:
        float(v)
        return True
    except ValueError:
        return False


def _median(vals):
    vals = sorted(vals)
    n = len(vals)
    if n == 0:
        return None
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def data_health(name):
    """چکاپ داده با کد (نه مدل): ردیف تکراری، خانه‌ی خالی، هفته‌ی گم‌شده، هفته‌ی ناقص یا خیلی کم، جهش یا سقوط ناگهانی."""
    fields, rows = load(name)
    numeric = [c for c in fields if c != "week" and rows and all(_is_number(r[c]) for r in rows if r[c] != "")]
    keys = [c for c in fields if c not in numeric]
    warnings = []
    result = {"rows": len(rows), "columns": fields, "numeric_columns": numeric,
              "group_columns": [k for k in keys if k not in ("week", "week_start")]}

    empty = {c: sum(1 for r in rows if r[c] == "") for c in fields}
    empty = {c: n for c, n in empty.items() if n}
    result["empty_cells"] = empty
    if empty:
        warnings.append("خانه‌ی خالی پیدا شد (" + ", ".join(c + ": " + str(n) for c, n in empty.items()) + "). خالی را صفر حساب نکن.")

    seen_row, seen_key, exact, dup_weeks = set(), set(), 0, []
    for r in rows:
        t = tuple(r[c] for c in fields)
        k = tuple(r[c] for c in keys)
        if t in seen_row:
            exact += 1
        if k in seen_key:
            dup_weeks.append(r.get("week", "?"))
        seen_row.add(t)
        seen_key.add(k)
    dup_weeks_sorted = sorted(set(dup_weeks), key=lambda w: float(w) if _is_number(w) else 0)
    result["duplicate_rows"] = {"extra_rows": len(dup_weeks), "exact_copies": exact, "weeks": dup_weeks_sorted}
    if dup_weeks:
        warnings.append("ردیف تکراری: " + str(len(dup_weeks)) + " ردیف اضافه (همان هفته و همان گروه بیش از یک بار؛ "
                        + str(exact) + " تای آن‌ها دقیقاً یکسان‌اند) در هفته‌های " + ", ".join(dup_weeks_sorted)
                        + ". جمع این هفته‌ها احتمالاً بیشتر از واقعیت است. تا منبع داده تأیید نکرده، درباره‌ی این هفته‌ها نتیجه نگیر.")

    if "week" in fields and rows and all(_is_number(r["week"]) for r in rows):
        weeks = sorted({int(float(r["week"])) for r in rows})
        present = set(weeks)
        missing = [w for w in range(weeks[0], weeks[-1] + 1) if w not in present]
        result["missing_weeks"] = missing
        if missing:
            warnings.append("هفته‌های گم‌شده (هیچ ردیفی ندارند): " + ", ".join(str(w) for w in missing) + ". گم‌شده را صفر حساب نکن.")
        totals = {c: {} for c in numeric}
        for r in rows:
            w = int(float(r["week"]))
            for c in numeric:
                if r[c] != "":
                    totals[c][w] = totals[c].get(w, 0.0) + float(r[c])
        tiny, jumps, drops, partial = {}, {}, {}, {}
        for c in numeric:
            series = totals[c]
            med = _median(list(series.values()))
            if not med or med <= 0:
                continue
            t = [w for w in weeks if series.get(w, 0) < 0.10 * med]
            if t:
                tiny[c] = t
            up, down = [], []
            for i, w in enumerate(weeks):
                prev = [series[x] for x in weeks[max(0, i - 8):i] if x in series]
                if len(prev) < 4 or w not in series:
                    continue
                base = _median(prev)
                if base and series[w] > 1.6 * base:
                    up.append(w)
                if base and series[w] < 0.4 * base:
                    down.append(w)
            if up:
                jumps[c] = up
            if down:
                drops[c] = down
            if c.startswith("days"):
                full = max(series.values())
                below = [w for w in weeks if series.get(w, 0) < full]
                if below:
                    partial[c] = {"full_week_value": full, "weeks_below": below}
        if "hours_recorded" in numeric and "days" in numeric:
            below = [w for w in weeks if totals["hours_recorded"].get(w, 0) < 22 * totals["days"].get(w, 0)]
            if below:
                partial["hours_recorded"] = {"normal_per_day": 24, "weeks_below": below}
        result.update({"tiny_weeks": tiny, "sudden_jumps": jumps, "sudden_drops": drops, "partial_weeks": partial})
        for c, ws in tiny.items():
            warnings.append("هفته‌های با داده‌ی خیلی کم در «" + c + "» (کمتر از ۱۰٪ میانه): " + ", ".join(str(w) for w in ws)
                            + ". نسبت‌های این هفته‌ها پر از نویز است؛ شاید شروع یا پایان داده یا داده‌ی ناقص باشد.")
        for c, ws in jumps.items():
            warnings.append("جهش ناگهانی در «" + c + "» (بیش از ۱.۶ برابر میانه‌ی ۸ هفته‌ی قبل): هفته‌های " + ", ".join(str(w) for w in ws)
                            + ". ممکن است واقعی باشد (تخفیف، فصل) یا خطای داده (ردیف تکراری). قبل از نتیجه‌گیری بررسی کن.")
        for c, ws in drops.items():
            warnings.append("سقوط ناگهانی در «" + c + "» (کمتر از ۴۰٪ میانه‌ی ۸ هفته‌ی قبل): هفته‌های " + ", ".join(str(w) for w in ws)
                            + ". ممکن است واقعی باشد یا داده‌ی ناقص (مثلاً پایان خروجی گرفتن از سیستم).")
        for c, info in partial.items():
            warnings.append("هفته‌های ناقص طبق «" + c + "»: " + ", ".join(str(w) for w in info["weeks_below"])
                            + ". این هفته‌ها کامل ثبت نشده‌اند؛ مقایسه‌شان با هفته‌های کامل گمراه‌کننده است.")
    result["warnings"] = warnings if warnings else ["مشکل آشکاری در داده پیدا نشد (این تضمین درستی نیست)."]
    return result


FUNCS = {
    "data_health": data_health,
    "weekly_values": weekly_values,
    "list_files": list_files,
    "describe_file": describe_file,
    "weekly_ratio": weekly_ratio,
    "compare_periods": compare_periods,
}


def run_tool(name, args):
    """خطا هم نتیجه است: به‌جای کرش کردن، پیغام خطا را به مدل برمی‌گردانیم."""
    try:
        result = FUNCS[name](**args)
    except Exception as e:
        result = {"error": str(e)}
    return json.dumps(result, ensure_ascii=False)[:8000]


# ====================== توصیف ابزارها برای مدل ======================
STR = {"type": "string"}
TOOLS = [
    {"name": "list_files", "description": "فهرست فایل‌های داده‌ی این پرونده.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "data_health",
     "description": "چکاپ داده با کد، قبل از هر تحلیل: ردیف تکراری، خانه‌ی خالی، هفته‌ی گم‌شده، هفته‌ی ناقص، هفته‌ی با داده‌ی خیلی کم، جهش یا سقوط ناگهانی. خروجی warnings را جدی بگیر.",
     "input_schema": {"type": "object", "properties": {"name": STR}, "required": ["name"]}},
    {"name": "describe_file",
     "description": "ستون‌ها، تعداد ردیف، تعداد خانه‌ی خالی هر ستون و سه ردیف اول یک فایل. قبل از هر تحلیل کیفیت داده را با این بسنج.",
     "input_schema": {"type": "object", "properties": {"name": STR}, "required": ["name"]}},
    {"name": "weekly_ratio",
     "description": "نسبت دو ستون (numerator ÷ denominator) برای هر هفته، به درصد. برای میانگین‌هایی مثل «اجاره در هر روز» as_percent=false بده تا نسبت ساده برگردد. اختیاری: به تفکیک یک ستون (group_by). ردیف‌های خالی صفر حساب نمی‌شوند و جدا گزارش می‌شوند.",
     "input_schema": {"type": "object",
                      "properties": {"name": STR, "numerator": STR, "denominator": STR, "group_by": STR,
                                     "as_percent": {"type": "boolean"}},
                      "required": ["name", "numerator", "denominator"]}},
    {"name": "weekly_values",
     "description": "مقدار خام هر هفته‌ی یک ستون (جمع در هفته). اختیاری: به تفکیک یک ستون (group_by). برای دیدن شکل واقعی سری، مثلاً افت پله‌ای یا تدریجی.",
     "input_schema": {"type": "object",
                      "properties": {"name": STR, "column": STR, "group_by": STR},
                      "required": ["name", "column"]}},
    {"name": "compare_periods",
     "description": "میانگین هفتگی یک ستون قبل و بعد از یک هفته (هفته‌های کمتر از split_week در برابر بقیه) و درصد تغییر. اختیاری: به تفکیک یک ستون (group_by).",
     "input_schema": {"type": "object",
                      "properties": {"name": STR, "column": STR, "split_week": {"type": "integer"}, "group_by": STR},
                      "required": ["name", "column", "split_week"]}},
]

SYSTEM = """تو «تشخیص‌دهنده» هستی. کارت پیدا کردن علت مشکل است، نه راه‌حل دادن.
قوانین:
1. جمله‌ی صاحب کسب‌وکار یک «علامت» است، نه علت.
2. اول برای هر فایل data_health را صدا بزن. هر هشداری داد (ردیف تکراری، هفته‌ی ناقص یا گم‌شده، جهش یا سقوط ناگهانی) را جدی بگیر: قبل از هر نتیجه بگو کدام هفته‌ها قابل اعتماد نیستند و چرا. بعد احتمال خرابی اندازه‌گیری را هم بسنج (منبع مستقل، تغییر روش شمارش).
3. چند فرضیه بساز و هر کدام را با ابزار آزمایش کن. بعد از هر نتیجه بگو کدام فرضیه تضعیف یا تقویت شد.
4. هر عددی که می‌گویی باید عیناً در خروجی ابزار باشد؛ جمع، تفریق یا تقسیم ذهنی ممنوع است (اگر محاسبه‌ای لازم است، بگو چه چیزی لازم است، نه عدد آن). اگر داده‌ای نیست، بگو نیست؛ هیچ‌وقت صفر فرضش نکن.
5. توضیح «راحت» (بازار، اقتصاد، فصل) تا مدرک مستقیم نداری مشکوک است؛ ولی اگر مدرک داشت فقط چون ساده است رد نکن.
6. خروجی نهایی دقیقاً این بخش‌ها را داشته باشد:
   - بهترین فرضیه
   - درجه‌ی اطمینان (کم / متوسط / زیاد) و دلیلش
   - مدرک (فقط اعداد ابزار)
   - مدرکی که اگر دیده شود فرضیه را رد می‌کند
   - درخواست مدرک (حداکثر ۳، کوچک و آسان)
7. راه‌حل پیشنهاد نده.
8. اگر مدرک با حدس صاحب کسب‌وکار می‌خواند، صادقانه بگو حدسش درست است. مخالفت بدون مدرک هم خطاست، درست مثل موافقت بدون مدرک."""


# ====================== حلقه‌ی عامل (برای تشخیص‌دهنده و منتقد مشترک) ======================
def run_agent(model, system, first_message, max_steps, label):
    messages = [{"role": "user", "content": first_message}]
    trace = []
    for step in range(max_steps):
        response = client.messages.create(
            model=model, max_tokens=6000, system=system, tools=TOOLS, messages=messages)
        if response.stop_reason != "tool_use":
            text = "\n".join(b.text for b in response.content if b.type == "text")
            if response.stop_reason == "max_tokens":
                text += "\n\n[هشدار: متن بریده شد]"
            return text, trace
        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type == "tool_use":
                output = run_tool(block.name, block.input)
                print(label, "قدم", step + 1, "->", block.name, json.dumps(block.input, ensure_ascii=False))
                print("    ", output[:110], "...")
                trace.append({"agent": label, "step": step + 1, "tool": block.name,
                              "args": block.input, "result": output})
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})
    return "(به سقف قدم‌ها رسید؛ گزارش کامل نشد)", trace


# ====================== بازرس عددها (کد، نه مدل) ======================
import re

def to_numbers(text):
    text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩٫", "01234567890123456789."))
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]


def audit_numbers(report, evidence_text):
    """هر عددی در گزارش که در خروجی ابزارها (یا متن علامت) نیست، علامت می‌خورد."""
    evidence = {round(x, 2) for x in to_numbers(evidence_text)}
    suspicious = []
    for x in to_numbers(report):
        if x == int(x) and x <= 12:   # شماره‌ی هفته و شمارش‌های کوچک
            continue
        close = any(abs(x - e) <= 0.051 for e in evidence) if x != int(x) else (round(x, 2) in evidence)
        if not close and x not in suspicious:
            suspicious.append(x)
    return suspicious


CRITIC_SYSTEM = """تو «منتقد مستقل» هستی. گزارش یک تشخیص‌دهنده را می‌بینی. کارت رد کردن یا ضعیف کردن آن است، نه تأیید.
با ابزارها خودت دوباره داده را بررسی کن. دنبال این‌ها بگرد:
1. ادعایی که با مدرک نمی‌خواند، یا نتیجه‌ای که از مدرک بیشتر است.
2. توضیح جایگزینی که تشخیص‌دهنده آزمایش نکرده (به‌خصوص خرابی اندازه‌گیری).
3. استدلال سردرگم یا دور از منطق.
4. هشدارهای چکاپ داده: خودت data_health را صدا بزن و ببین تشخیص‌دهنده هشدارها را جدی گرفته یا نه.
5. مخالفت یا موافقت بی‌دلیل با حدس صاحب کسب‌وکار؛ هر دو خطاست.
هر عدد باید از ابزار باشد، حساب ذهنی نکن.
خروجی دقیقاً:
- حکم: قبول / قبول با شرط / رد
- مشکل‌ها (کوتاه، شماره‌دار)
- آزمونی که خودت انجام دادی و نتیجه‌اش
- آیا درجه‌ی اطمینان باید تغییر کند؟ (بالاتر / همان / پایین‌تر) و چرا"""

problem = open(os.path.join(DATA_DIR, "problem.txt"), encoding="utf-8").read().strip()

print("\n##### مرحله ۱: تشخیص‌دهنده (" + MODEL + ") #####")
report, trace = run_agent(
    MODEL, SYSTEM,
    "علامتی که صاحب کسب‌وکار گفته:\n" + problem + "\n\nبا ابزارها داده‌ی این پرونده را بررسی کن و گزارش بده.",
    MAX_STEPS, "[تشخیص]")
print("\n=== گزارش تشخیص‌دهنده ===\n" + report)
open("report_" + case + ".md", "w", encoding="utf-8").write(report)

print("\n##### مرحله ۲: بازرس عددها (کد) #####")
evidence_text = problem + " " + " ".join(t["result"] for t in trace)
bad = audit_numbers(report, evidence_text)
if bad:
    print("این عددها در گزارش هستند ولی در خروجی هیچ ابزاری نیستند (ذهنی حساب شده یا ساختگی):", bad)
else:
    print("همه‌ی عددهای گزارش در خروجی ابزارها پیدا شد.")

print("\n##### مرحله ۳: منتقد مستقل (" + CRITIC_MODEL + ") #####")
trace_summary = "\n".join(
    "- " + t["tool"] + " " + json.dumps(t["args"], ensure_ascii=False) + " => " + t["result"][:1500] for t in trace)
critic_msg = ("علامت: " + problem + "\n\n=== گزارش تشخیص‌دهنده ===\n" + report +
              "\n\n=== ابزارهایی که تشخیص‌دهنده صدا زد و نتیجه‌شان ===\n" + trace_summary +
              ("\n\n=== عددهای مشکوک طبق بازرس کد ===\n" + str(bad) if bad else ""))
critique, trace2 = run_agent(CRITIC_MODEL, CRITIC_SYSTEM, critic_msg, 8, "[منتقد]")
print("\n=== نقد منتقد ===\n" + critique)
bad2 = audit_numbers(critique, evidence_text + " " + report + " " + " ".join(t["result"] for t in trace2))
print("\nبازرس عددها روی نقد:", bad2 if bad2 else "همه‌ی عددها پیدا شد.")
open("audit_" + case + ".txt", "w", encoding="utf-8").write("گزارش: " + str(bad) + "\nنقد: " + str(bad2))
open("critique_" + case + ".md", "w", encoding="utf-8").write(critique)

with open("trace_" + case + ".json", "w", encoding="utf-8") as f:
    json.dump(trace + trace2, f, ensure_ascii=False, indent=2)
print("\nذخیره شد: report_" + case + ".md ، critique_" + case + ".md ، trace_" + case + ".json")
# ====================== خلاصه‌ی ساده برای صاحب کسب‌وکار ======================
OWNER_SYSTEM = """تو نویسنده‌ی «خلاصه برای صاحب کسب‌وکار» هستی. خواننده آدم عادی است و آمار بلد نیست.
ورودی: علامت مشکل، گزارش تشخیص‌دهنده، و نقد منتقد. بر پایه‌ی هر دو بنویس؛ هر جا منتقد گزارش را اصلاح کرده، نسخه‌ی اصلاح‌شده را بیاور.
قوانین:
1. فارسی ساده، جمله‌های کوتاه، بدون اصطلاح. اگر اصطلاح لازم است یک بار با کلمه‌ی ساده توضیح بده.
2. هیچ عددی از خودت نساز؛ فقط عددهایی که در گزارش یا نقد هست. بیش از ۵ عدد نیاور و هر عدد را با معنایش بگو (نه «هفته ۷»؛ بگو «از میانه‌ی دوره»).
3. این بخش‌ها را دقیقاً بنویس:
## مشکل در یک جمله
## چه اتفاقی افتاده (۳ نکته‌ی کوتاه)
## چقدر مطمئنیم
(کم/متوسط/زیاد و یک دلیل ساده. اگر داده مشکل داشت، مثل ردیف تکراری یا هفته‌ی ناقص، همین‌جا ساده بگو کدام بخش داده قابل اعتماد نیست.)
## چه کار کنیم (۳ پیشنهاد)
هر پیشنهاد: چه کار، چرا، چقدر کار دارد (کم/متوسط/زیاد). اول کارهای ارزان و بی‌خطر برای اینکه علت روشن شود (مثلاً چک کردن سفارش‌های واقعی)، بعد اصلاح. اگر داده خراب یا ناقص است، پیشنهاد اول باید درست کردن یا تأیید داده باشد و تا آن موقع هیچ تصمیم پولی بزرگ (مثل بیشتر یا قطع کردن بودجه) گرفته نشود. چون علت هنوز قطعی نیست، پیشنهادها را شرطی بنویس («اگر معلوم شد که...»). حکم قطعی نده.
## چه چیزی را هنوز نمی‌دانیم
(۱ تا ۳ مورد)
حداکثر ۲۰۰ کلمه."""
print("\n##### مرحله ۳.۵: خلاصه‌ی ساده برای صاحب کسب‌وکار #####")
owner_msg = ("علامت: " + problem + "\n\n=== گزارش تشخیص‌دهنده ===\n" + report +
             "\n\n=== نقد منتقد مستقل ===\n" + critique)
owner_summary, _ = run_agent(CRITIC_MODEL, OWNER_SYSTEM, owner_msg, 3, "[خلاصه]")
print("\n" + owner_summary)
open("summary_" + case + ".md", "w", encoding="utf-8").write(owner_summary)

bad3 = audit_numbers(owner_summary, evidence_text + " " + " ".join(t["result"] for t in trace2))  # فقط خروجی ابزارها، نه متن مدل‌ها
print("\nبازرس عددها روی خلاصه:", bad3 if bad3 else "همه‌ی عددها پیدا شد.")
open("audit_" + case + ".txt", "a", encoding="utf-8").write("\nخلاصه: " + str(bad3))
if bad3:
    owner_summary += "\n\n> توجه: بازرس این عددها را در خروجی ابزارها پیدا نکرد، پس قبل از استفاده بررسی شوند: " + ", ".join(str(x) for x in bad3)
    open("summary_" + case + ".md", "w", encoding="utf-8").write(owner_summary)

from chart import make_chart
chart_file, chart_note = make_chart(DATA_DIR, case)
print("نمودار:", chart_file if chart_file else "ساخته نشد (" + chart_note + ")")
if chart_file:
    print("  ", chart_note)
    owner_summary += "\n\n![chart](" + chart_file + ")"

# ====================== دروازه‌ی تأیید انسان ======================
import datetime
print("\n##### مرحله ۴: تأیید انسان #####")
print("گزارش و نقد را بخوان. بدون تأیید تو هیچ نسخه‌ی نهایی ساخته نمی‌شود.")
try:
    answer = input("تصمیم تو؟  approve (تأیید) / reject (رد): ").strip().lower()
    note = input("یادداشت کوتاه (اختیاری، Enter برای رد کردن): ").strip()
except EOFError:
    answer, note = "no-decision", ""
decision = "approved" if answer in ("approve", "a", "y", "yes") else (
    "rejected" if answer in ("reject", "r", "n", "no") else "no-decision")
record = {"case": case, "decision": decision, "note": note,
          "time": datetime.datetime.now().isoformat(timespec="seconds"),
          "agent_model": MODEL, "critic_model": CRITIC_MODEL,
          "unverified_numbers_in_report": bad, "unverified_numbers_in_critique": bad2}
with open("approval_" + case + ".json", "w", encoding="utf-8") as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
if decision == "approved":
    with open("final_" + case + ".md", "w", encoding="utf-8") as f:
        f.write(owner_summary + "\n\n---\n## گزارش کامل تشخیص‌دهنده\n" + report + "\n\n---\n## نقد منتقد مستقل\n" + critique +
                "\n\n---\nتأیید انسان: " + record["time"] + (" | " + note if note else "") + "\n")
    from report_html import build_html
    page = build_html(case, "گزارش بررسی: " + case, owner_summary, report, critique,
                      chart_file, record)
    open("final_" + case + ".html", "w", encoding="utf-8").write(page)
    print("تأیید شد. نسخه‌ی نهایی: final_" + case + ".md و final_" + case + ".html (این را در مرورگر باز کن)")
else:
    print("نسخه‌ی نهایی ساخته نشد (تصمیم: " + decision + "). ثبت شد: approval_" + case + ".json")
