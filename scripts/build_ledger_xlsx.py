#!/usr/bin/env python3
"""导出指定火山方舟项目 2026-11 账单明细到 Excel（按项目分 Sheet）。"""
import json
import os
import subprocess
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "方舟项目账单_2026年11月.xlsx")
MONTH = "2026-11"
PAGE = 300

PROJECTS = [
    ("api-key-20261105ttlt", "ttlt-1105"),
    ("api-key-20261106-1t2", "lt2-1106"),
    ("api-key-20261109-灵通3", None),
]
HEADERS = ["日期", "模型", "计费项", "用量", "单位", "原价", "应付金额"]


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def ve_call(project, offset):
    body = {
        "BillPeriod": MONTH,
        "GroupPeriod": 2,
        "Product": ["ark_open_source_llm"],
        "Project": [project],
        "Limit": PAGE,
        "Offset": offset,
        "NeedRecordNum": 1,
    }
    env = dict(os.environ)
    env.update({
        "VE_CALLER_TYPE": "ai_agent",
        "VE_CALLER_NAME": "trae-remote-sandbox",
        "VE_SKILL_NAME": "volcengine-billing-and-cost-management",
    })
    p = subprocess.run(
        ["ve", "billing", "ListSplitBillDetail", "--body", json.dumps(body, ensure_ascii=False),
         "--output", "json"],
        capture_output=True, text=True, env=env, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[:400])
    return json.loads(p.stdout).get("Result") or {}


def fetch_project(project):
    rows, total, offset = [], None, 0
    while True:
        res = ve_call(project, offset)
        batch = res.get("List") or []
        if total is None:
            total = res.get("Total", 0)
        rows.extend(batch)
        print(f"  {project} {len(rows)}/{total}", file=sys.stderr)
        if not batch or len(rows) >= total:
            break
        offset += PAGE
    return rows


def aggregate(rows):
    agg = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in rows:
        key = (r.get("ExpenseDate") or "", r.get("ConfigName") or "-",
               r.get("Element") or r.get("ChargeItemCode") or "-", r.get("Unit") or "")
        a = agg[key]
        a[0] += num(r.get("Count"))
        a[1] += num(r.get("OriginalBillAmount"))
        a[2] += num(r.get("PayableAmount"))
    out = []
    for (date, model, element, unit), (cnt, orig, pay) in agg.items():
        out.append([date, model, element, round(cnt, 3), unit, round(orig, 8), round(pay, 8)])
    out.sort(key=lambda x: (x[0], x[1], x[2]))
    return out


THIN = Side(style="thin", color="D9DEE7")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEADER_FILL = PatternFill("solid", fgColor="1F3B73")
HEADER_FONT = Font(name="Arial", bold=True, color="FFFFFF", size=10)
BODY_FONT = Font(name="Arial", size=10)
ZEBRA = PatternFill("solid", fgColor="F7F9FC")
TOTAL_FONT = Font(name="Arial", bold=True, size=10)


def style_sheet(ws, data_rows):
    widths = [12, 28, 54, 14, 10, 18, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for c, h in enumerate(HEADERS, 1):
        cell = ws.cell(1, c, h)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER
    ws.row_dimensions[1].height = 24
    for r in range(2, 2 + data_rows):
        for c in range(1, len(HEADERS) + 1):
            cell = ws.cell(r, c)
            cell.font = BODY_FONT
            cell.border = BORDER
            if r % 2 == 0:
                cell.fill = ZEBRA
            if c in (1, 5):
                cell.alignment = Alignment(horizontal="center")
            elif c in (4, 6, 7):
                cell.alignment = Alignment(horizontal="right")
                cell.number_format = "#,##0.00####"
            else:
                cell.alignment = Alignment(vertical="center", wrap_text=False)
    last = 1 + data_rows
    ws.freeze_panes = "A2"
    if data_rows:
        ws.auto_filter.ref = f"A1:G{last}"
        tr = last + 1
        ws.cell(tr, 1, "合计").font = TOTAL_FONT
        for c in range(2, 8):
            cell = ws.cell(tr, c)
            cell.font = TOTAL_FONT
            cell.border = Border(top=Side(style="medium", color="AAB4C5"),
                                 bottom=THIN, left=THIN, right=THIN)
            if c == 4:
                cell.value = f"=SUM(D2:D{last})"
                cell.number_format = "#,##0.000"
                cell.alignment = Alignment(horizontal="right")
            elif c in (6, 7):
                cell.value = f"=SUM({get_column_letter(c)}2:{get_column_letter(c)}{last})"
                cell.number_format = "#,##0.00####"
                cell.alignment = Alignment(horizontal="right")


def main():
    wb = Workbook()
    wb.remove(wb.active)
    for name, pid in PROJECTS:
        ws = wb.create_sheet(name[:31])
        if not pid:
            style_sheet(ws, 0)
            ws.merge_cells("A2:G2")
            ws["A2"] = "该名称未匹配到 2026-11 的账单项目，暂无消费数据。"
            ws["A2"].font = Font(name="Arial", size=10, italic=True, color="667085")
            ws["A2"].alignment = Alignment(horizontal="center", vertical="center")
            ws.row_dimensions[2].height = 30
            continue
        rows = fetch_project(pid)
        data = aggregate(rows)
        for i, row in enumerate(data, start=2):
            for c, v in enumerate(row, start=1):
                ws.cell(i, c, v)
        style_sheet(ws, len(data))
        print(f"{name} <- {pid}: {len(rows)} rows -> {len(data)}", file=sys.stderr)
    wb.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
