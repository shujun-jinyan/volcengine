#!/usr/bin/env python3
"""生成指定 API Key 所属项目的 2026-11 消费账单（原价口径）。"""
import json
import os
import subprocess
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "APIKey消费账单_2026年11月.xlsx")
MONTH = "2026-11"
PAGE = 300

PROJECTS = [
    ("njzc-1105", "南京智创-1105", "api-key-20261105-njzc"),
    ("njzc3-1116", "南京智创3-1116", "api-key-20261116-njzc3"),
]
DETAIL_HEADERS = ["日期", "计费项", "用量", "单位", "原价金额(元)"]
SUMMARY_HEADERS = ["项目归属", "API 名称", "消费总原价金额(元)", "应付金额(元)"]

THIN = Side(style="thin", color="D9DEE7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="1F3B73")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name="Arial", size=10)
ZEBRA = PatternFill("solid", fgColor="F7F9FC")
TOTAL_FONT = Font(name="Arial", bold=True, size=10)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def fetch_detail(project):
    rows, total, offset = [], None, 0
    env = dict(os.environ, VE_CALLER_TYPE="ai_agent", VE_CALLER_NAME="trae-remote-sandbox",
               VE_SKILL_NAME="volcengine-billing-and-cost-management")
    while True:
        p = subprocess.run(
            ["ve", "billing", "ListSplitBillDetail", "--BillPeriod", MONTH,
             "--GroupPeriod", "2", "--Project", json.dumps([project]),
             "--Limit", str(PAGE), "--Offset", str(offset), "--NeedRecordNum", "1",
             "--output", "json"],
            capture_output=True, text=True, env=env, timeout=300)
        res = (json.loads(p.stdout).get("Result") or {})
        batch = res.get("List") or []
        if total is None:
            total = int(res.get("Total") or 0)
        rows.extend(batch)
        print(f"  {project} {len(rows)}/{total}", file=sys.stderr)
        if not batch or len(rows) >= total:
            break
        offset += PAGE
    return rows


def aggregate(rows):
    agg = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in rows:
        key = (r.get("ExpenseDate") or "", r.get("Element") or r.get("ChargeItemCode") or "-",
               r.get("Unit") or "")
        agg[key][0] += num(r.get("Count"))
        agg[key][1] += num(r.get("OriginalBillAmount"))
        agg[key][2] += num(r.get("PayableAmount"))
    out = [[d, e, round(c, 3), u, round(o, 4)] for (d, e, u), (c, o, _) in agg.items()]
    out.sort(key=lambda x: (x[0], x[1]))
    pay_total = round(sum(v[2] for v in agg.values()), 2)
    return out, pay_total


def style_header(ws, headers):
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"


def style_body(ws, nrows, numeric_cols, last_col):
    for r in range(2, 2 + nrows):
        for c in range(1, last_col + 1):
            cell = ws.cell(r, c)
            cell.font = BODY_FONT
            cell.border = BORDER
            if r % 2 == 0:
                cell.fill = ZEBRA
            if c in numeric_cols:
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.00####" if c == 5 else "#,##0.000"
            elif c in (1, 4):
                cell.alignment = Alignment(horizontal="center")
            else:
                cell.alignment = Alignment(vertical="center")


def total_row(ws, nrows, sum_cols, last_col):
    tr = 1 + nrows + 1
    ws.cell(tr, 1, "合计").font = TOTAL_FONT
    for c in range(1, last_col + 1):
        cell = ws.cell(tr, c)
        cell.font = TOTAL_FONT
        cell.border = Border(top=Side(style="medium", color="AAB4C5"),
                             bottom=THIN, left=THIN, right=THIN)
        if c in sum_cols:
            cell.value = f"=SUM({get_column_letter(c)}2:{get_column_letter(c)}{1 + nrows})"
            cell.number_format = "#,##0.00####" if c == 5 else "#,##0.000"
            cell.alignment = Alignment(horizontal="right")
    return tr


def main():
    wb = Workbook()
    ws0 = wb.active
    ws0.title = "总计"
    style_header(ws0, SUMMARY_HEADERS)
    # 先占位，等明细算完回填
    totals = []
    pays = []
    sheets = []
    for pid, pname, api in PROJECTS:
        print(f"fetch {pid}", file=sys.stderr)
        data, pay = aggregate(fetch_detail(pid))
        sheets.append((pid, pname, api, data))
        totals.append(round(sum(r[4] for r in data), 2))
        pays.append(pay)

    for i, (pid, pname, api, data) in enumerate(sheets, start=2):
        label = f"{pid}（{pname}）"
        ws0.cell(i, 1, label)
        ws0.cell(i, 2, api)
        ws0.cell(i, 3, totals[i - 2])
        ws0.cell(i, 4, pays[i - 2])
        for c in (1, 2, 3, 4):
            ws0.cell(i, c).font = BODY_FONT
            ws0.cell(i, c).border = BORDER
            if i % 2 == 1:
                ws0.cell(i, c).fill = ZEBRA
        ws0.cell(i, 3).number_format = "#,##0.00####"
        ws0.cell(i, 3).alignment = Alignment(horizontal="right")
        ws0.cell(i, 4).number_format = "#,##0.00####"
        ws0.cell(i, 4).alignment = Alignment(horizontal="right")

    tr = total_row(ws0, len(sheets), {3, 4}, 4)
    ws0.cell(tr, 1, "合计").font = TOTAL_FONT
    ws0.cell(tr, 2, "").font = TOTAL_FONT
    for col, w in zip("ABCD", (34, 32, 22, 20)):
        ws0.column_dimensions[col].width = w
    note = tr + 2
    ws0.merge_cells(f"A{note}:D{note}")
    ws0[f"A{note}"] = ("统计区间：2026-11-01 ~ 2026-11-26。原价=刊例价(OriginalBillAmount)，应付=优惠后应付(PayableAmount)；"
                       "账号账单默认展示的是应付金额。当日数据 T+1 滚动，可能微调。")
    ws0[f"A{note}"].font = Font(name="Arial", size=9, italic=True, color="667085")
    ws0[f"A{note}"].alignment = Alignment(vertical="center", wrap_text=True)
    ws0.row_dimensions[note].height = 36

    for pid, pname, api, data in sheets:
        ws = wb.create_sheet(pid)
        style_header(ws, DETAIL_HEADERS)
        for r, row in enumerate(data, start=2):
            for c, v in enumerate(row, start=1):
                ws.cell(r, c, v)
        style_body(ws, len(data), {3, 5}, 5)
        ws.auto_filter.ref = f"A1:E{1 + len(data)}"
        total_row(ws, len(data), {3, 5}, 5)
        for col, w in zip("ABCDE", (12, 60, 16, 10, 20)):
            ws.column_dimensions[col].width = w

    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
