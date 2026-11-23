#!/usr/bin/env python3
"""拉取火山方舟（ARK）分账明细（按天 × 项目）并生成台账数据。

数据源：billing.ListSplitBillDetail，GroupPeriod=1（按天），产品过滤 ark_open_source_llm
凭证：环境变量 VOLCENGINE_ACCESS_KEY / VOLCENGINE_SECRET_KEY
产物：
  data/ark_daily_rows.json  原始按天×项目明细
  data/ledger.json          台账聚合数据（供网站直接引用）
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

MONTHS = os.environ.get("BILL_MONTHS", "2026-10,2026-11").split(",")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
PAGE = 300
ARK_PRODUCTS = ["ark_open_source_llm", "ark_subscription", "ark_batch", "ark"]


def ve_call(body):
    cmd = ["ve", "billing", "ListSplitBillDetail", "--body",
           json.dumps(body, ensure_ascii=False), "--output", "json"]
    env = dict(os.environ)
    env.update({
        "VE_CALLER_TYPE": "ai_agent",
        "VE_CALLER_NAME": "trae-remote-sandbox",
        "VE_SKILL_NAME": "volcengine-billing-and-cost-management",
    })
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"ve failed: {p.stderr[:500]}")
    return json.loads(p.stdout)


def fetch_month(month):
    rows, total, offset = [], None, 0
    while True:
        res = ve_call({
            "BillPeriod": month,
            "GroupPeriod": 1,
            "Product": ARK_PRODUCTS,
            "Limit": PAGE,
            "Offset": offset,
            "NeedRecordNum": 1,
        }).get("Result") or {}
        batch = res.get("List") or []
        if total is None:
            total = res.get("Total", -1)
        rows.extend(batch)
        print(f"{month} offset={offset} got={len(batch)} total={total}", file=sys.stderr)
        if not batch or (isinstance(total, int) and total >= 0 and len(rows) >= total):
            break
        offset += PAGE
        if offset > 30000:
            break
    return rows


def fetch_account_month(month):
    """拉取账号全产品分账明细（按天聚合），用于“全账号消费”口径。"""
    rows, total, offset = [], None, 0
    while True:
        res = ve_call({
            "BillPeriod": month,
            "GroupPeriod": 1,
            "Limit": PAGE,
            "Offset": offset,
            "NeedRecordNum": 1,
        }).get("Result") or {}
        batch = res.get("List") or []
        if total is None:
            total = res.get("Total", -1)
        rows.extend(batch)
        print(f"[account] {month} offset={offset} got={len(batch)} total={total}", file=sys.stderr)
        if not batch or (isinstance(total, int) and total >= 0 and len(rows) >= total):
            break
        offset += PAGE
        if offset > 30000:
            break
    return rows


def account_summary(rows, date_range):
    """按产品汇总同一日期区间的全账号消费。"""
    start, end = date_range.get("start") or "", date_range.get("end") or ""
    agg = {}
    for r in rows:
        d = r.get("ExpenseDate") or ""
        if not d or (start and d < start) or (end and d > end):
            continue
        p = r.get("Product") or "-"
        o = agg.setdefault(p, {"product": p, "name": (r.get("ProductZh") or p),
                               "pretax": 0.0, "payable": 0.0})
        o["pretax"] += num(r.get("PretaxAmount"))
        o["payable"] += num(r.get("PayableAmount"))
    items = [{**o, "pretax": round(o["pretax"], 2), "payable": round(o["payable"], 2)}
             for o in agg.values()]
    items.sort(key=lambda x: -x["pretax"])
    return {"total": round(sum(i["pretax"] for i in items), 2),
            "payable": round(sum(i["payable"] for i in items), 2),
            "byProduct": items,
            "range": date_range}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def tokens_of(r):
    """把账单 Count 按计费单位换算为 token 数。"""
    c = num(r.get("Count"))
    if not c:
        return 0.0
    u = (r.get("Unit") or r.get("PriceUnit") or "").replace(" ", "").lower()
    if "千tokens" in u or "千token" in u:
        return c * 1000
    if "万tokens" in u or "万token" in u:
        return c * 10000
    if u in ("tokens", "token"):
        return c
    return 0.0


def aggregate(rows):
    projects, dates = {}, set()
    # key: (date, project) -> {pretax, payable, bill, rows}
    cells = {}
    model_cells = {}
    for r in rows:
        d = r.get("ExpenseDate") or ""
        proj = r.get("Project") or "-"
        pname = (r.get("ProjectDisplayName") or "").strip() or ("未归属项目" if proj == "-" else proj)
        if not d:
            continue
        dates.add(d)
        projects.setdefault(proj, {"id": proj, "name": pname})
        c = cells.setdefault(f"{d}|{proj}", {"date": d, "project": proj, "projectName": pname,
                                             "pretax": 0.0, "payable": 0.0,
                                             "original": 0.0, "tokens": 0.0, "rows": 0})
        c["pretax"] += num(r.get("PretaxAmount"))
        c["payable"] += num(r.get("PayableAmount"))
        c["original"] += num(r.get("OriginalBillAmount"))
        c["tokens"] += tokens_of(r)
        c["rows"] += 1
        m = r.get("ConfigName") or r.get("ConfigurationCode") or "-"
        mk = f"{d}|{proj}|{m}"
        mc = model_cells.setdefault(mk, {"date": d, "project": proj, "projectName": pname,
                                         "model": m, "pretax": 0.0, "payable": 0.0,
                                         "original": 0.0, "tokens": 0.0})
        mc["pretax"] += num(r.get("PretaxAmount"))
        mc["payable"] += num(r.get("PayableAmount"))
        mc["original"] += num(r.get("OriginalBillAmount"))
        mc["tokens"] += tokens_of(r)

    cells = [c for c in cells.values()]
    for c in cells:
        c["pretax"] = round(c["pretax"], 2)
        c["payable"] = round(c["payable"], 2)
        c["original"] = round(c["original"], 2)
        c["discount"] = round(c["original"] - c["pretax"], 2)
        c["tokens"] = round(c["tokens"], 2)
    model_cells = [m for m in model_cells.values()]
    for m in model_cells:
        m["pretax"] = round(m["pretax"], 2)
        m["payable"] = round(m["payable"], 2)
        m["original"] = round(m["original"], 2)
        m["discount"] = round(m["original"] - m["pretax"], 2)
        m["tokens"] = round(m["tokens"], 2)

    dates = sorted(dates)
    proj_list = sorted(projects.values(), key=lambda p: p["name"])
    total_pretax = round(sum(c["pretax"] for c in cells), 2)
    total_original = round(sum(c["original"] for c in cells), 2)
    total_tokens = round(sum(c["tokens"] for c in cells), 2)
    per_project = []
    for p in proj_list:
        vals = [c for c in cells if c["project"] == p["id"]]
        per_project.append({
            **p,
            "pretax": round(sum(v["pretax"] for v in vals), 2),
            "payable": round(sum(v["payable"] for v in vals), 2),
            "original": round(sum(v["original"] for v in vals), 2),
            "discount": round(sum(v["discount"] for v in vals), 2),
            "tokens": round(sum(v["tokens"] for v in vals), 2),
            "days": len({v["date"] for v in vals}),
        })
    per_project.sort(key=lambda p: -p["pretax"])
    per_date = []
    for d in dates:
        vals = [c for c in cells if c["date"] == d]
        per_date.append({"date": d, "pretax": round(sum(v["pretax"] for v in vals), 2),
                         "payable": round(sum(v["payable"] for v in vals), 2),
                         "original": round(sum(v["original"] for v in vals), 2),
                         "discount": round(sum(v["discount"] for v in vals), 2),
                         "tokens": round(sum(v["tokens"] for v in vals), 2),
                         "projects": len(vals)})
    return {
        "generatedAt": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
        "currency": "CNY",
        "source": "火山引擎账单中心 · 分账明细（ListSplitBillDetail，按天×项目）",
        "note": "分账明细存在 T+2 延迟；当日数据可能仍在滚动更新。消费金额=税前应付(PretaxAmount)，原价=刊例价(OriginalBillAmount)，优惠=原价-税前应付。",
        "periods": MONTHS,
        "dateRange": {"start": dates[0] if dates else "", "end": dates[-1] if dates else ""},
        "totalPretax": total_pretax,
        "totalOriginal": total_original,
        "totalDiscount": round(total_original - total_pretax, 2),
        "totalTokens": total_tokens,
        "cells": sorted(cells, key=lambda c: (c["date"], c["project"])),
        "models": sorted(model_cells, key=lambda m: (m["date"], m["project"], m["model"])),
        "projects": per_project,
        "dates": per_date,
        "monthly": monthly_summary(cells),
    }


def monthly_summary(cells):
    out = {}
    for c in cells:
        m = c["date"][:7]
        o = out.setdefault(m, {"month": m, "pretax": 0.0, "original": 0.0, "discount": 0.0,
                               "tokens": 0.0, "projects": set(), "days": set(), "byProject": {}})
        o["pretax"] += c["pretax"]
        o["original"] += c["original"]
        o["discount"] += c["discount"]
        o["tokens"] += c["tokens"]
        o["projects"].add(c["project"])
        o["days"].add(c["date"])
        o["byProject"][c["project"]] = o["byProject"].get(c["project"], 0) + c["pretax"]
    res = []
    for m in sorted(out):
        o = out[m]
        res.append({"month": m, "pretax": round(o["pretax"], 2),
                    "original": round(o["original"], 2),
                    "discount": round(o["discount"], 2),
                    "tokens": round(o["tokens"], 2),
                    "projectCount": len(o["projects"]), "dayCount": len(o["days"]),
                    "byProject": {k: round(v, 2) for k, v in o["byProject"].items()}})
    return res


def main():
    os.makedirs(DATA, exist_ok=True)
    all_rows = []
    for m in MONTHS:
        all_rows.extend(fetch_month(m))
    # 去重（同月重复分页保护）
    seen, rows = set(), []
    for r in all_rows:
        k = (r.get("ExpenseDate"), r.get("Project"), r.get("BillDetailId") or r.get("SplitBillDetailId"),
             r.get("ChargeItemCode"), r.get("PretaxAmount"), r.get("InstanceNo"), r.get("SplitItemID"))
        if k in seen:
            continue
        seen.add(k)
        rows.append(r)
    with open(os.path.join(DATA, "ark_daily_rows.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)
    ledger = aggregate(rows)
    acc_rows = []
    for m in MONTHS:
        acc_rows.extend(fetch_account_month(m))
    seen_a, acc = set(), []
    for r in acc_rows:
        k = (r.get("ExpenseDate"), r.get("Product"), r.get("Project"),
             r.get("BillDetailId") or r.get("SplitBillDetailId"),
             r.get("ChargeItemCode"), r.get("PretaxAmount"))
        if k in seen_a:
            continue
        seen_a.add(k)
        acc.append(r)
    ledger["account"] = account_summary(acc, ledger["dateRange"])
    with open(os.path.join(DATA, "ledger.json"), "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=1)
    print(json.dumps({
        "rows": len(rows),
        "totalPretax": ledger["totalPretax"],
        "projects": len(ledger["projects"]),
        "dateRange": ledger["dateRange"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
