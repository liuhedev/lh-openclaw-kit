#!/usr/bin/env python3
"""高考志愿冲稳保 + 五维匹配度 打分引擎。

输入院校专业组录取位次 CSV（列见 data/sample.csv）+ 考生省份/选科/位次/偏好，
输出：硬门槛过滤（选科 + 排斥方向）→ 冲稳保三档 → 五维匹配度成绩单 → text 或 HTML。

五维：分数匹配 / 就业前景 / 兴趣适配 / 城市地域 / 院校平台。
硬门槛：① 选科符合度 ② 排斥方向(--reject 一票否决)。
兴趣适配用「排除法」而非「兴趣加分」：可接受集(--accept)外的降权但保留兜底；
只有家境宽裕(--family-economy ample，有试错成本)才把可接受方向放开成加分。
调节器：风险偏好 / 家庭经济 / 读研意愿（调权重，不单列维度）。
数据由调用方按 SKILL.md 现查官方历年投档位次整理；data/sample.csv 仅演示，非真实填报。
方向标签依据见 references/employment-direction.md。位次「高」= 数值小。
"""
import argparse
import csv
import datetime
import html
import os
import sys

HERE = os.path.dirname(__file__)
DEFAULT_DATA = os.path.join(HERE, "..", "data", "sample.csv")
TEMPLATE = os.path.join(HERE, "..", "references", "report-template.html")

DIR_LABEL = {"green": "🟢绿牌急需", "rush": "🚀国家急需可冲", "good": "✅工科稳就业",
             "safe": "🛡师范保底", "weak": "🟡就业偏弱", "red": "🔴红牌预警"}
DIR_HTMLCLASS = {"green": "d-green", "rush": "d-rush", "good": "d-good",
                 "safe": "d-safe", "weak": "d-weak", "red": "d-red"}
DIR_BASE = {"green": 0, "rush": 1, "good": 2, "safe": 3, "weak": 8, "red": 9}
DIR_QUALITY = {"green": 95, "rush": 88, "good": 82, "safe": 75, "weak": 50, "red": 35}
TIER_LEVEL = {"985": 100, "211": 85, "双一流": 80, "双非": 60}
_WARN_DIRS = {"weak", "red"}
TIERS = ("冲", "稳", "保")
TIER_BADGE = {"冲": "b-chong", "稳": "b-wen", "保": "b-bao"}
TIER_DESC = {"冲": "院校位次比你高 1~12%，搏一搏",
             "稳": "院校位次和你相当（±5%），实力匹配",
             "保": "院校位次比你低 5~25%，兜底不滑档"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def subject_ok(combo, required):
    if not required or required == "不限":
        return True
    return set(required) <= set(combo)


def keyword_match(row, kws):
    """关键词(可接受/排斥)是否命中该专业。
    师范是「当老师」的独立职业轨：学科名(如「化学」)不波及师范专业，
    只有排斥/接受词点名「师范/教师」时才命中——避免 --reject 化学 误删化学(师范)。"""
    if not kws:
        return False
    major = row["major_group"]
    field = row.get("interest_field", "")
    is_normal = "师范" in major or field == "师范"
    hay = major + " " + field
    for kw in kws:
        if not kw:
            continue
        if is_normal and "师范" not in kw and "教师" not in kw:
            continue
        if kw in hay:
            return True
    return False


def classify(my_rank, school_rank):
    delta = (my_rank - school_rank) / my_rank
    if delta > 0.12:
        return None
    if delta > 0.01:
        return "冲"
    if delta >= -0.05:
        return "稳"
    if delta >= -0.25:
        return "保"
    return None


def score(row, args):
    """排序分，越小越靠前。方向基线 + 调节器。"""
    d, tier = row["direction"], row.get("school_tier", "双非")
    s = DIR_BASE.get(d, 5)
    if args.risk == "certainty":
        s += 2 if d in _WARN_DIRS else (1 if d == "rush" else 0)
    else:
        s += -1 if d == "rush" else (-0.5 if d in _WARN_DIRS else 0)
    if args.grad_school == "yes":            # 读研→看平台，名校调剂也认
        s -= {"985": 1.5, "211": 1.0, "双一流": 0.8}.get(tier, 0)
    elif args.grad_school == "no":           # 直接就业→就业型优先
        s -= 0.5 if d in ("green", "good") else 0
    if args.family_economy == "tight":       # 经济紧→稳就业省成本
        s -= 0.3 if d in ("green", "safe") else 0
    if args.city and row.get("city_tier") == args.city:
        s -= 0.5
    # 兴趣适配：排除法。可接受集之外降权(留作兜底，不剔除)；
    # 只有家境宽裕(有试错成本)才把可接受方向放开成轻度加分。
    if args.accepts and not keyword_match(row, args.accepts):
        s += 1.0
    if args.family_economy == "ample" and keyword_match(row, args.accepts):
        s -= 0.4
    return s


def build(rows, args):
    eligible, excluded = [], []   # excluded: [(row, 原因)]
    for r in rows:
        if r["province"] != args.province or r["combo"] != args.combo:
            continue
        if not subject_ok(args.combo, r.get("required", "")):
            excluded.append((r, "选科"))
            continue
        if keyword_match(r, args.rejects):
            excluded.append((r, "排斥"))
            continue
        eligible.append(r)
    buckets = {t: [] for t in TIERS}
    for r in eligible:
        r["min_rank"] = int(r["min_rank"])
        t = classify(args.rank, r["min_rank"])
        if t:
            buckets[t].append(r)
    for t in TIERS:
        buckets[t].sort(key=lambda x: (score(x, args), x["min_rank"]))
    return buckets, excluded


def pool_of(buckets):
    return [r for t in TIERS for r in buckets[t]]


def dimensions(buckets, args, reject_count):
    """五维匹配度：(名称, 0-100 或 None, 依据)。None = 待填/未设限。"""
    pool = pool_of(buckets)
    n = len(pool) or 1
    present = {t: bool(buckets[t]) for t in TIERS}
    score_fit = 50 + (15 if present["冲"] else 0) + (20 if present["稳"] else 0) + (15 if present["保"] else 0)
    gap = "梯度完整" if all(present.values()) else "梯度有缺口(注意兜底)"
    career = round(sum(DIR_QUALITY.get(r["direction"], 60) for r in pool) / n)
    good_pct = round(100 * sum(1 for r in pool if r["direction"] in ("green", "rush", "good")) / n)
    platform = round(sum(TIER_LEVEL.get(r.get("school_tier", "双非"), 60) for r in pool) / n)
    elite_pct = round(100 * sum(1 for r in pool if r.get("school_tier") in ("985", "211")) / n)
    dims = [
        ("分数匹配", score_fit, f"冲{len(buckets['冲'])}/稳{len(buckets['稳'])}/保{len(buckets['保'])}，{gap}"),
        ("就业前景", career, f"绿牌/急需/稳就业占比 {good_pct}%"),
    ]
    if args.accepts:   # 兴趣适配（排除法口径）
        m = sum(1 for r in pool if keyword_match(r, args.accepts))
        dims.append(("兴趣适配", round(100 * m / n), f"{m}/{n} 在可接受方向「{'/'.join(args.accepts)}」"))
    elif reject_count:
        dims.append(("兴趣适配", 100, f"已剔除 {reject_count} 个排斥方向，其余均可接受"))
    else:
        dims.append(("兴趣适配", None, "未设限，可补 --accept/--reject 表达能接受/排斥的方向"))
    if args.city:
        m = sum(1 for r in pool if r.get("city_tier") == args.city)
        dims.append(("城市地域", round(100 * m / n), f"{m}/{n} 在「{args.city}」"))
    else:
        dims.append(("城市地域", None, "未填城市偏好，补 --city"))
    dims.append(("院校平台", platform, f"985/211 占 {elite_pct}%"))
    return dims


def verdict_text(args, buckets):
    pool = pool_of(buckets)
    pick = lambda dirs: next((r["major_group"] for r in pool if r["direction"] in dirs), None)
    stable, rush, safe = pick({"green", "good"}), pick({"rush"}), pick({"safe"})
    warn = sum(1 for r in pool if r["direction"] in _WARN_DIRS)
    parts = []
    if stable:
        parts.append(f"主攻{stable}这类稳就业工科")
    if rush:
        parts.append(f"{rush}冲好学校")
    if safe:
        parts.append(f"{safe}保底")
    tail = f"；{warn}个生化环材类分够也建议绕开" if warn else ""
    return f"{args.combo}考生，" + "、".join(parts) + tail + "。"


def reason_of(r):
    return {"green": "绿牌急需、技术壁垒高，就业确定", "rush": "热门高薪但波动，放冲档，冲上赚到",
            "good": "工科就业稳，留京面宽", "safe": "师范稳定、待遇好，这个分报很轻松",
            "weak": "生化环材，历史多次就业红黄牌，不打算读研建议绕开",
            "red": "就业预警专业，避开"}.get(r["direction"], "")


SELF_CHECK = [
    ("不可替代性", "这专业的活，AI 或新人多久能顶替？越难替代越值钱。"),
    ("500 强测试", "你想去的大厂，往年来这个学校这个专业招人吗？"),
    ("10 年后", "能接受十年后收入不如当年分数比你低的同学吗？不能就往确定性靠。"),
]


def _excluded_lines(excluded):
    lines = []
    for why, label in (("选科", "选科门槛"), ("排斥", "按你排斥剔除")):
        items = [r for r, w in excluded if w == why]
        if items:
            names = "、".join(f"{r['school']}{r['major_group']}" for r in items)
            lines.append((label, len(items), names))
    return lines


def render_text(args, buckets, dims, excluded):
    out = ["判断：" + verdict_text(args, buckets),
           f"考生：{args.province} {args.combo} 位次 {args.rank}"
           f"｜风险 {args.risk}｜经济 {args.family_economy}｜读研 {args.grad_school}"
           + (f"｜城市 {args.city}" if args.city else "")
           + (f"｜可接受 {args.accept}" if args.accept else "")
           + (f"｜排斥 {args.reject}" if args.reject else ""), ""]
    out.append("【匹配度成绩单】")
    for name, val, basis in dims:
        bar = ("█" * (val // 10) + "░" * (10 - val // 10)) if val is not None else "──────────"
        out.append(f"  {name}  {bar} {str(val) if val is not None else '待填':>3}   {basis}")
    out.append("")
    for t in TIERS:
        out.append(f"【{t}】{len(buckets[t])} 个")
        for r in buckets[t]:
            out.append(f"  {DIR_LABEL.get(r['direction'],'')} {r['school']}({r.get('school_tier','')}/{r.get('city_tier','')}) "
                       f"/ {r['major_group']}（位次{r['min_rank']}｜就业率{r.get('employ_rate','?')}% "
                       f"5年{r.get('salary_5y','?')}元）— {reason_of(r)}")
        out.append("")
    for label, cnt, names in _excluded_lines(excluded):
        out.append(f"🚦 {label}：剔除 {cnt} 个 — {names}")
    out.append("决策自查（对每个稳/保志愿逐个过）：")
    out += [f"  {i}. {k}：{v}" for i, (k, v) in enumerate(SELF_CHECK, 1)]
    return "\n".join(out)


def render_html(args, buckets, dims, excluded):
    e = html.escape
    tpl = open(TEMPLATE, encoding="utf-8").read()

    dim_rows = ""
    for name, val, basis in dims:
        if val is None:
            dim_rows += (f'<div class="row"><div class="dim">{e(name)}<small>{e(basis)}</small></div>'
                         f'<div class="bar"><i style="width:0%"></i></div>'
                         f'<div class="num" style="font-size:13px;color:#5b6573">待填</div></div>')
        else:
            dim_rows += (f'<div class="row"><div class="dim">{e(name)}<small>{e(basis)}</small></div>'
                         f'<div class="bar"><i style="width:{val}%"></i></div>'
                         f'<div class="num">{val}</div></div>')

    tier_sections = ""
    for t in TIERS:
        cards = ""
        for r in buckets[t]:
            d = r["direction"]
            warn = " warn" if d in _WARN_DIRS else ""
            salary = str(r.get("salary_5y", ""))
            sal = f"{int(salary)/10000:.2g}万" if salary.isdigit() else "—"
            cards += (
                f'<div class="card{warn}">'
                f'<div class="school">{e(r["school"])}<span class="city">{e(r.get("city_tier",""))}</span></div>'
                f'<div class="stats"><span class="dirtag {DIR_HTMLCLASS.get(d,"")}">{e(DIR_LABEL.get(d,""))}</span>'
                f'<br>位次 <b>{r["min_rank"]}</b> · 就业率 <b>{e(str(r.get("employ_rate","?")))}%</b> · 5年 <b>{sal}</b></div>'
                f'<div class="major">{e(r["major_group"])} · {e(r.get("school_tier",""))}</div>'
                f'<div class="reason">{e(reason_of(r))}</div></div>')
        if not cards:
            cards = '<div class="card"><div class="major">（无候选，需补充该档院校数据）</div></div>'
        tier_sections += (f'<div class="tier"><div class="tier-h">'
                          f'<span class="tier-badge {TIER_BADGE[t]}">{t}</span>'
                          f'<span class="lbl">{TIER_DESC[t]}</span></div>{cards}</div>')

    notes = _excluded_lines(excluded)
    filter_note = ""
    if notes:
        body = "<br>".join(f"<b>🚦 {e(label)}</b>：剔除 {cnt} 个 — {e(names)}" for label, cnt, names in notes)
        filter_note = (f'<div class="checklist" style="background:#fdf2f2;border:1px solid #f3c4c0">{body}</div>')

    repl = {
        "{{report_id}}": e(f"{args.province}{args.rank}"),
        "{{date}}": datetime.date.today().isoformat(),
        "{{province}}": e(args.province), "{{combo}}": e(args.combo),
        "{{score}}": e(str(args.score)) if args.score else "—",
        "{{rank}}": str(args.rank),
        "{{above_line}}": e(str(args.above_line)) if args.above_line else "—",
        "{{verdict}}": e(verdict_text(args, buckets)),
        "{{dim_rows}}": dim_rows, "{{tier_sections}}": tier_sections, "{{filter_note}}": filter_note,
    }
    for k, v in repl.items():
        tpl = tpl.replace(k, v)
    return tpl


def main():
    ap = argparse.ArgumentParser(description="高考志愿 冲稳保+五维匹配度 引擎")
    ap.add_argument("--province", required=True)
    ap.add_argument("--combo", required=True, help="选科组合，如 物化生")
    ap.add_argument("--rank", required=True, type=int, help="官方一分一段位次")
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--score", type=int, help="分数（仅展示用）")
    ap.add_argument("--above-line", dest="above_line", help="高出特控线多少（仅展示）")
    ap.add_argument("--risk", choices=["certainty", "explore"], default="certainty", help="风险偏好(调节器)")
    ap.add_argument("--family-economy", dest="family_economy", choices=["tight", "normal", "ample"],
                    default="normal", help="家庭经济(调节器)；ample 才把可接受方向放开成加分")
    ap.add_argument("--grad-school", dest="grad_school", choices=["yes", "no", "maybe"],
                    default="maybe", help="读研意愿(调节器)")
    ap.add_argument("--city", help="城市层级偏好，如 一线/新一线")
    ap.add_argument("--accept", help="可接受方向关键词(逗号分隔)，如 工科,计算机；集外降权不剔除")
    ap.add_argument("--reject", help="强烈排斥方向关键词(逗号分隔)，如 生物,化学；一票否决直接剔除")
    ap.add_argument("--format", choices=["text", "html"], default="text")
    ap.add_argument("--out", help="HTML 输出路径（--format html 必填）")
    args = ap.parse_args()

    args.accepts = [x.strip() for x in args.accept.split(",")] if args.accept else []
    args.rejects = [x.strip() for x in args.reject.split(",")] if args.reject else []
    rows = load(args.data)
    buckets, excluded = build(rows, args)
    if not pool_of(buckets) and not excluded:
        print(f"[无数据] {args.data} 无 {args.province}/{args.combo} 记录。"
              f"按 SKILL.md 先查官方历年投档位次整理成 CSV 再传 --data。", file=sys.stderr)
        sys.exit(2)
    reject_count = sum(1 for _, w in excluded if w == "排斥")
    dims = dimensions(buckets, args, reject_count)

    if args.format == "html":
        if not args.out:
            print("[错误] --format html 需配 --out", file=sys.stderr)
            sys.exit(2)
        open(args.out, "w", encoding="utf-8").write(render_html(args, buckets, dims, excluded))
        print(f"已生成 HTML：{args.out}")
    else:
        print(render_text(args, buckets, dims, excluded))


if __name__ == "__main__":
    main()
