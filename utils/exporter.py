"""
Filter-aware export utility.
Every exporter takes the SAME rows that were already filtered/rendered on
screen (never the whole table) and writes them to CSV, XLSX or PDF.
"""
import io
import csv
from datetime import datetime

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


def build_filename(prefix, fmt):
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{prefix}_{ts}.{fmt}"


def export_csv(rows, columns):
    """rows: list[dict]; columns: list[(key, header)] -> returns BytesIO"""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([h for _, h in columns])
    for row in rows:
        writer.writerow([row.get(k, "") for k, _ in columns])
    out = io.BytesIO(buf.getvalue().encode("utf-8"))
    out.seek(0)
    return out


def export_xlsx(rows, columns, sheet_name="Report"):
    df = pd.DataFrame(rows)
    ordered_keys = [k for k, _ in columns if k in df.columns] if not df.empty else [k for k, _ in columns]
    if not df.empty:
        df = df[ordered_keys]
    df.columns = [h for k, h in columns if k in ordered_keys] if not df.empty else [h for _, h in columns]
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31] or "Report")
    out.seek(0)
    return out


def export_pdf(rows, columns, title="Report"):
    out = io.BytesIO()
    doc = SimpleDocTemplate(out, pagesize=landscape(A4))
    styles = getSampleStyleSheet()
    elements = [Paragraph(title, styles["Title"]), Spacer(1, 12)]

    headers = [h for _, h in columns]
    data = [headers]
    for row in rows:
        data.append([str(row.get(k, "") if row.get(k) is not None else "") for k, _ in columns])

    if len(data) == 1:
        data.append(["No records match the current filters."] + [""] * (len(headers) - 1))

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    elements.append(table)
    doc.build(elements)
    out.seek(0)
    return out
