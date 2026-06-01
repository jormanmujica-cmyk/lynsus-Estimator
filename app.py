import streamlit as st
import math
import datetime
import io
import json
import os
import re
import base64
from pathlib import Path


try:
    from reportlab.lib.pagesizes import letter as _rl_test
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "reportlab"], check=False)

try:
    import pdfplumber as _pdfplumber_test
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pdfplumber"], check=False)

try:
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "plotly"], check=False)
    import plotly.graph_objects as go
    import plotly.express as px

_PRICES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "precios.json")

_DEFAULT_PRICES = {
    "conc_price":    165.0,
    "rebar_3":       0.2295,
    "rebar_4":       0.394,
    "rebar_5":       0.6155,
    "lumber_1x4":    0.252,
    "lumber_2x4":    0.328,
    "exp_joint":     0.441,
    "stakes_bundle": 14.17,
}

def _load_prices():
    if os.path.exists(_PRICES_FILE):
        try:
            with open(_PRICES_FILE, "r") as _f:
                return {**_DEFAULT_PRICES, **json.load(_f)}
        except Exception:
            pass
    return dict(_DEFAULT_PRICES)

def _save_prices(prices):
    try:
        with open(_PRICES_FILE, "w") as _f:
            json.dump(prices, _f, indent=2)
    except Exception:
        pass


def _build_quote_pdf(
    today_str, quote_number,
    client_name, client_address, client_city_state_zip, client_phone, client_email,
    job_location, edited_scope,
    scope_subtotal, client_ppsf,
    use_base, base_type, base_total, base_tons_ord, base_trucks,
    equip_items, equip_total,
    grand_total,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buf    = io.BytesIO()
    margin = 0.75 * inch
    W      = letter[0] - 2 * margin

    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=0.5 * inch, bottomMargin=0.75 * inch)

    DARK  = HexColor("#1a1f2e")
    GOLD  = HexColor("#f0a500")
    SLATE = HexColor("#8892a4")
    LITE  = HexColor("#cbd5e0")
    SEP   = HexColor("#2d3748")
    MUTED = HexColor("#555555")
    RULE  = HexColor("#e0e0e0")

    def sty(name, **kw):
        base = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=black)
        base.update(kw)
        return ParagraphStyle(name, **base)

    story = []

    # ── Header (dark background) ──────────────────────────────────
    bill_parts = [x for x in [
        client_name if client_name and client_name != "—" else "",
        client_address or "",
        client_city_state_zip or "",
        " | ".join(x for x in [client_phone or "", client_email or ""] if x),
    ] if x.strip()]

    date_t = Table(
        [[Paragraph(today_str, sty("dt", fontSize=10, textColor=LITE)),
          Paragraph(f"Quote #: {quote_number or 'LYN-2026-001'}",
                    sty("qn", fontName="Helvetica-Bold", fontSize=11,
                        textColor=GOLD, alignment=TA_RIGHT))]],
        colWidths=[W * 0.55, W * 0.45]
    )
    date_t.setStyle(TableStyle([
        ("LINEABOVE",     (0, 0), (-1, 0), 0.5, SEP),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    loc_t = Table(
        [[Paragraph(f"<b>JOB LOCATION:</b>  {job_location or '—'}",
                    sty("loc", fontSize=9, textColor=SLATE))]],
        colWidths=[W]
    )
    loc_t.setStyle(TableStyle([
        ("LINEABOVE",     (0, 0), (-1, 0), 0.5, SEP),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    hdr = Table([
        [Paragraph("LYNSUS CONTRACTING",
                   sty("co", fontName="Helvetica-Bold", fontSize=20,
                       textColor=GOLD, alignment=TA_CENTER, leading=24))],
        [Paragraph("Flatwork Concrete — Driveways · Sidewalks · Patios",
                   sty("sub", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
        [date_t],
        [Paragraph("BILL TO:", sty("bl", fontName="Helvetica-Bold",
                                   fontSize=8, textColor=GOLD, leading=10))],
        [Paragraph("<br/>".join(bill_parts) if bill_parts else "—",
                   sty("bb", fontSize=10, textColor=LITE, leading=17))],
        [loc_t],
    ], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK),
        ("LEFTPADDING",   (0, 0), (-1, -1), 24),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 24),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING",    (0, 0),  (0,  0), 20),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 14))

    # ── Scope of Work ─────────────────────────────────────────────
    story.append(Paragraph("SCOPE OF WORK",
                           sty("sowh", fontName="Helvetica-Bold", fontSize=9,
                               textColor=GOLD, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=0.5, color=RULE, spaceAfter=6))

    S_SOW  = sty("sowl", fontSize=10, spaceAfter=2, textColor=MUTED)
    S_SOWI = sty("sowi", fontSize=10, spaceAfter=2, textColor=MUTED, leftIndent=18)
    for line in (edited_scope or "").split("\n"):
        if not line.strip():
            story.append(Spacer(1, 3))
            continue
        if line.startswith("    "):
            story.append(Paragraph(line.strip(), S_SOWI))
        else:
            s = line.lstrip()
            txt = line if (s.startswith("-") or s.startswith("•")) else f"• {line}"
            story.append(Paragraph(txt, S_SOW))

    story.append(Spacer(1, 12))
    story.append(HRFlowable(width=W, thickness=0.5, color=RULE, spaceAfter=8))

    # ── Pricing ───────────────────────────────────────────────────
    story.append(Paragraph("PRICING",
                           sty("prh", fontName="Helvetica-Bold", fontSize=9,
                               textColor=GOLD, spaceAfter=6)))

    S_ROW   = sty("row",  fontSize=10)
    S_DET   = sty("det",  fontSize=9, textColor=SLATE)
    S_AMT   = sty("amt",  fontSize=10, alignment=TA_RIGHT)
    S_ROWB  = sty("rowb", fontName="Helvetica-Bold", fontSize=11)
    S_AMTB  = sty("amtb", fontName="Helvetica-Bold", fontSize=11, alignment=TA_RIGHT)

    def prow(label, detail, amount, bold=False):
        return [
            Paragraph(label, S_ROWB if bold else S_ROW),
            Paragraph(detail, S_DET) if detail else Paragraph("", S_DET),
            Paragraph(f"${amount:,.2f}", S_AMTB if bold else S_AMT),
        ]

    rows = [prow("Flatwork Concrete Installation",
                 f"${client_ppsf:.2f}/sqft  ·  Subtotal", scope_subtotal)]
    if use_base and base_total > 0:
        rows.append(prow(
            base_type,
            f"{base_tons_ord:.1f} tons · {base_trucks} truck{'s' if base_trucks != 1 else ''}",
            base_total,
        ))
    if equip_items:
        for eq in equip_items:
            rows.append(prow(eq["name"], "", eq["cost"]))
        rows.append(prow("Equipment Total", "", equip_total, bold=True))

    pt = Table(rows, colWidths=[W * 0.44, W * 0.36, W * 0.20])
    pt.setStyle(TableStyle([
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, RULE),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(pt)
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width=W, thickness=1.2, color=DARK, spaceAfter=6))

    # ── Project Total ─────────────────────────────────────────────
    tot_t = Table([[
        Paragraph("PROJECT TOTAL",
                  sty("tl", fontName="Helvetica-Bold", fontSize=14, textColor=GOLD)),
        Paragraph(f"${grand_total:,.2f}",
                  sty("ta", fontName="Helvetica-Bold", fontSize=18,
                      textColor=DARK, alignment=TA_RIGHT)),
    ]], colWidths=[W * 0.5, W * 0.5])
    tot_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(tot_t)
    story.append(HRFlowable(width=W, thickness=1.2, color=DARK, spaceAfter=24))

    # ── Signatures ────────────────────────────────────────────────
    story.append(Paragraph(
        "By signing below, client agrees to the scope of work and total amount shown.",
        sty("sn", fontName="Helvetica-Oblique", fontSize=9,
            textColor=MUTED, spaceAfter=18)))

    sig_t = Table([
        [Paragraph("Client Signature: _______________________________",
                   sty("s1", fontSize=10)),
         Paragraph("Date: _______________", sty("s2", fontSize=10))],
        [Spacer(1, 14), Spacer(1, 14)],
        [Paragraph("Authorized by: _______________________________",
                   sty("s3", fontSize=10)),
         Paragraph("Date: _______________", sty("s4", fontSize=10))],
    ], colWidths=[W * 0.65, W * 0.35])
    sig_t.setStyle(TableStyle([
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(sig_t)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _build_contract_report_pdf(
    project_name, gc_name, job_number, report_date,
    ca_total, ca_sqft, ca_ppsf,
    line_items,
    mat_cost, labor_cost, equip_cost, overhead_cost, other_costs, total_cost,
    profit, margin_pct, days_req, daily_crew_cost,
    crew_members, on_budget,
    overhead_pct,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    buf    = io.BytesIO()
    margin = 0.75 * inch
    W      = letter[0] - 2 * margin

    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=0.5*inch, bottomMargin=0.75*inch)

    DARK  = HexColor("#1a1f2e")
    GOLD  = HexColor("#f0a500")
    SLATE = HexColor("#8892a4")
    LITE  = HexColor("#cbd5e0")
    RULE  = HexColor("#e0e0e0")
    SEP   = HexColor("#2d3748")
    GREEN = HexColor("#2d6a4f")
    RED   = HexColor("#7b1a1a")
    GTEXT = HexColor("#48bb78")
    RTEXT = HexColor("#fc8181")
    MUTED = HexColor("#555555")

    STATUS_BG   = GREEN if on_budget else RED
    STATUS_TEXT = GTEXT if on_budget else RTEXT

    def sty(name, **kw):
        base = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=black)
        base.update(kw)
        return ParagraphStyle(name, **base)

    story = []

    # ── Header ────────────────────────────────────────────────────
    hdr = Table([
        [Paragraph("LYNSUS CONTRACTING", sty("co", fontName="Helvetica-Bold", fontSize=20,
                   textColor=GOLD, alignment=TA_CENTER, leading=24))],
        [Paragraph("CONTRACT PROFITABILITY REPORT", sty("sub", fontName="Helvetica-Bold",
                   fontSize=12, textColor=LITE, alignment=TA_CENTER))],
        [Paragraph("Internal Management Document — Owner Copy",
                   sty("sub2", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
    ], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), DARK),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("TOPPADDING",    (0,0), (0,0),   20),
        ("TOPPADDING",    (0,1), (-1,-1), 4),
        ("BOTTOMPADDING", (0,-1),(-1,-1), 20),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 12))

    # ── Status Banner ─────────────────────────────────────────────
    status_label = "✅  PROFITABLE CONTRACT" if on_budget else "🚨  UNPROFITABLE CONTRACT"
    status_sub   = (f"Estimated profit: ${profit:,.2f} ({margin_pct:.1f}% margin)"
                    if on_budget else
                    f"Estimated loss: ${abs(profit):,.2f} — review costs before accepting")
    banner = Table([
        [Paragraph(status_label, sty("sl", fontName="Helvetica-Bold", fontSize=14,
                                     textColor=STATUS_TEXT, alignment=TA_CENTER))],
        [Paragraph(status_sub,   sty("ss", fontSize=10, textColor=LITE, alignment=TA_CENTER))],
    ], colWidths=[W])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), STATUS_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
    ]))
    story.append(banner)
    story.append(Spacer(1, 14))

    S_LBL = sty("lbl", fontSize=9,  textColor=SLATE)
    S_VAL = sty("val", fontName="Helvetica-Bold", fontSize=10)
    S_HDR = sty("hh",  fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, spaceAfter=4)

    def section_title(txt):
        story.append(Paragraph(txt, S_HDR))
        story.append(HRFlowable(width=W, thickness=0.5, color=RULE, spaceAfter=6))

    def two_col(pairs):
        rows = []
        for i in range(0, len(pairs), 2):
            l = pairs[i]
            r = pairs[i+1] if i+1 < len(pairs) else ("","")
            rows.append([Paragraph(l[0], S_LBL), Paragraph(l[1], S_VAL),
                         Paragraph(r[0], S_LBL), Paragraph(r[1], S_VAL)])
        t = Table(rows, colWidths=[W*0.20, W*0.30, W*0.20, W*0.30])
        t.setStyle(TableStyle([
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, RULE),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        return t

    # ── Section 1: Project Info ───────────────────────────────────
    section_title("SECTION 1 — PROJECT INFORMATION")
    story.append(two_col([
        ("Project / Job Name",   project_name or "—"),
        ("GC / Owner",           gc_name or "—"),
        ("Job Number",           job_number or "—"),
        ("Report Date",          report_date),
        ("Contract Total",       f"${ca_total:,.2f}"),
        ("Square Footage",       f"{ca_sqft:,.0f} sqft" if ca_sqft > 0 else "Lump Sum"),
        ("Price per SQFT",       f"${ca_ppsf:.2f}" if ca_sqft > 0 else "N/A"),
        ("Estimated Duration",   f"{days_req} days"),
    ]))
    story.append(Spacer(1, 12))

    # ── Section 2: G703 Line Items ────────────────────────────────
    if line_items:
        section_title("SECTION 2 — CONTRACT LINE ITEMS (G703)")
        li_header = [
            Paragraph("Description of Work", sty("lih1", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
            Paragraph("Scheduled Value",      sty("lih2", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, alignment=TA_RIGHT)),
        ]
        li_rows = [li_header]
        for _li in line_items:
            li_rows.append([
                Paragraph(_li["description"], sty(f"lid{id(_li)}", fontSize=9)),
                Paragraph(f"${_li['value']:,.2f}", sty(f"liv{id(_li)}", fontSize=9, alignment=TA_RIGHT)),
            ])
        li_rows.append([
            Paragraph("CONTRACT TOTAL", sty("lit", fontName="Helvetica-Bold", fontSize=10, textColor=GOLD)),
            Paragraph(f"${ca_total:,.2f}", sty("litv", fontName="Helvetica-Bold", fontSize=10,
                      textColor=GOLD, alignment=TA_RIGHT)),
        ])
        li_t = Table(li_rows, colWidths=[W*0.75, W*0.25])
        li_t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  DARK),
            ("BACKGROUND",    (0,-1),(-1,-1), HexColor("#252d3d")),
            ("LINEBELOW",     (0,0), (-1,-1), 0.3, RULE),
            ("TOPPADDING",    (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        story.append(li_t)
        story.append(Spacer(1, 12))

    # ── Section 3: Cost Analysis ──────────────────────────────────
    section_title("SECTION 3 — YOUR COST ANALYSIS")
    story.append(two_col([
        ("Materials Cost",    f"${mat_cost:,.2f}"),
        ("Labor Cost",        f"${labor_cost:,.2f}"),
        ("Equipment Cost",    f"${equip_cost:,.2f}"),
        ("Overhead ({:.0f}%)".format(overhead_pct), f"${overhead_cost:,.2f}"),
        ("Other Costs",       f"${other_costs:,.2f}"),
        ("TOTAL COSTS",       f"${total_cost:,.2f}"),
    ]))
    story.append(Spacer(1, 12))

    # ── Section 4: Bottom Line ────────────────────────────────────
    section_title("SECTION 4 — BOTTOM LINE")
    story.append(two_col([
        ("Contract Amount",   f"${ca_total:,.2f}"),
        ("Total Costs",       f"${total_cost:,.2f}"),
        ("Net Profit / Loss", f"${profit:+,.2f}"),
        ("Profit Margin",     f"{margin_pct:.1f}%"),
        ("Daily Crew Cost",   f"${daily_crew_cost:,.2f}/day"),
        ("Duration",          f"{days_req} days"),
    ]))
    story.append(Spacer(1, 12))

    # ── Section 5: Crew ───────────────────────────────────────────
    section_title("SECTION 5 — CREW ASSIGNED")
    crew_header = [
        Paragraph("Name",       sty("ch1", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Pay Type",   sty("ch2", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Rate",       sty("ch3", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Hrs/Day",    sty("ch4", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Daily Cost", sty("ch5", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, alignment=TA_RIGHT)),
    ]
    crew_rows = [crew_header]
    for m in crew_members:
        dc = m["rate"] * m["hours"] if m["pay_type"] == "Hourly" else m["rate"]
        crew_rows.append([
            Paragraph(m["name"] or "—",     sty(f"cn{id(m)}", fontSize=9)),
            Paragraph(m["pay_type"],         sty(f"ct{id(m)}", fontSize=9)),
            Paragraph(f"${m['rate']:.2f}",  sty(f"cr{id(m)}", fontSize=9)),
            Paragraph(str(m["hours"]) if m["pay_type"] == "Hourly" else "—",
                      sty(f"ch{id(m)}", fontSize=9)),
            Paragraph(f"${dc:,.2f}",        sty(f"cd{id(m)}", fontSize=9, alignment=TA_RIGHT)),
        ])
    crew_rows.append([
        Paragraph("", sty("cf0")), Paragraph("", sty("cf1")),
        Paragraph("", sty("cf2")),
        Paragraph("Daily Total", sty("cft", fontName="Helvetica-Bold", fontSize=9)),
        Paragraph(f"${daily_crew_cost:,.2f}", sty("cfv", fontName="Helvetica-Bold",
                  fontSize=9, alignment=TA_RIGHT)),
    ])
    crew_t = Table(crew_rows, colWidths=[W*0.28, W*0.15, W*0.17, W*0.17, W*0.23])
    crew_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  DARK),
        ("LINEBELOW",     (0,0), (-1,-1), 0.3, RULE),
        ("LINEABOVE",     (0,-1),(-1,-1), 0.8, DARK),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(crew_t)
    story.append(Spacer(1, 16))

    # ── Section 6: Owner Notes ────────────────────────────────────
    section_title("SECTION 6 — OWNER NOTES")
    for _ in range(5):
        story.append(Paragraph("_______________________________________________",
                               sty(f"n{_}", fontSize=10, textColor=MUTED, spaceAfter=14)))

    # ── Recommendation ────────────────────────────────────────────
    rec_txt = (f"ACCEPT — Estimated profit ${profit:,.2f} at {margin_pct:.1f}% margin. "
               f"Crew must complete in {days_req} days."
               if on_budget else
               f"DO NOT ACCEPT — Estimated loss ${abs(profit):,.2f}. "
               f"Negotiate better terms or reduce costs.")
    rec_t = Table([[Paragraph(f"Recommendation: {rec_txt}",
                              sty("rec", fontName="Helvetica-Bold", fontSize=9,
                                  textColor=STATUS_TEXT))]],
                  colWidths=[W])
    rec_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), STATUS_BG),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
    ]))
    story.append(rec_t)

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _build_labor_plan_pdf(
    job_name, quote_number, today_str,
    total_sqft, total_bid, price_per_sqft, labor_budget,
    materials_cost, equipment_cost, overhead_cost, profit_amount,
    speed_label, daily_crew_cost, days_req, actual_labor, labor_psf,
    labor_variance, max_days_budget, on_budget,
    crew_members,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

    buf    = io.BytesIO()
    margin = 0.75 * inch
    W      = letter[0] - 2 * margin

    doc = SimpleDocTemplate(buf, pagesize=letter,
                            leftMargin=margin, rightMargin=margin,
                            topMargin=0.5 * inch, bottomMargin=0.75 * inch)

    DARK   = HexColor("#1a1f2e")
    GOLD   = HexColor("#f0a500")
    SLATE  = HexColor("#8892a4")
    LITE   = HexColor("#cbd5e0")
    SEP    = HexColor("#2d3748")
    MUTED  = HexColor("#555555")
    RULE   = HexColor("#e0e0e0")
    GREEN  = HexColor("#2d6a4f")
    RED    = HexColor("#7b1a1a")
    GTEXT  = HexColor("#48bb78")
    RTEXT  = HexColor("#fc8181")

    STATUS_BG   = GREEN if on_budget else RED
    STATUS_TEXT = GTEXT if on_budget else RTEXT

    def sty(name, **kw):
        base = dict(fontName="Helvetica", fontSize=10, leading=14, textColor=black)
        base.update(kw)
        return ParagraphStyle(name, **base)

    story = []

    # ── Header ────────────────────────────────────────────────────
    hdr = Table([
        [Paragraph("LYNSUS CONTRACTING",
                   sty("co", fontName="Helvetica-Bold", fontSize=18,
                       textColor=GOLD, alignment=TA_CENTER, leading=22))],
        [Paragraph("LABOR PLAN SUMMARY",
                   sty("t1", fontName="Helvetica-Bold", fontSize=13,
                       textColor=LITE, alignment=TA_CENTER))],
        [Paragraph("Crew Planner — Internal Management Report",
                   sty("t2", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
        [Paragraph(
            f"Project: {job_name or '—'}  ·  Quote: {quote_number or '—'}  ·  {today_str}",
            sty("hd", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
    ], colWidths=[W])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), DARK),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0),  (0,  0), 18),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 12))

    # ── Status Banner ─────────────────────────────────────────────
    status_label = "✅  LABOR PLAN ON BUDGET" if on_budget else "🚨  LABOR PLAN OVER BUDGET"
    status_sub   = ("This crew plan protects the labor budget."
                    if on_budget else "This crew plan exceeds the labor budget.")
    banner = Table([
        [Paragraph(status_label, sty("sl", fontName="Helvetica-Bold", fontSize=14,
                                     textColor=STATUS_TEXT, alignment=TA_CENTER))],
        [Paragraph(status_sub,   sty("ss", fontSize=9, textColor=LITE, alignment=TA_CENTER))],
    ], colWidths=[W])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), STATUS_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
    ]))
    story.append(banner)
    story.append(Spacer(1, 14))

    S_LBL = sty("lbl", fontSize=9, textColor=SLATE)
    S_VAL = sty("val", fontName="Helvetica-Bold", fontSize=10)
    S_HDR = sty("hh",  fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, spaceAfter=4)

    def section_title(txt):
        return [
            Paragraph(txt, S_HDR),
            HRFlowable(width=W, thickness=0.5, color=RULE, spaceAfter=6),
        ]

    def two_col_rows(pairs):
        rows = []
        for i in range(0, len(pairs), 2):
            left  = pairs[i]
            right = pairs[i + 1] if i + 1 < len(pairs) else ("", "")
            rows.append([
                Paragraph(left[0],  S_LBL), Paragraph(left[1],  S_VAL),
                Paragraph(right[0], S_LBL), Paragraph(right[1], S_VAL),
            ])
        t = Table(rows, colWidths=[W*0.20, W*0.30, W*0.20, W*0.30])
        t.setStyle(TableStyle([
            ("LINEBELOW",     (0, 0), (-1, -1), 0.3, RULE),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    # ── Section 1: Project Snapshot ───────────────────────────────
    story += section_title("SECTION 1 — PROJECT SNAPSHOT")
    story.append(two_col_rows([
        ("Project Name",     job_name or "—"),
        ("Quote Number",     quote_number or "—"),
        ("Date",             today_str),
        ("Total SQFT",       f"{total_sqft:,.0f} sqft"),
        ("Total Bid Price",  f"${total_bid:,.2f}"),
        ("Price per SQFT",   f"${price_per_sqft:.2f}"),
        ("Labor Budget",     f"${labor_budget:,.2f}"),
        ("Materials Cost",   f"${materials_cost:,.2f}"),
        ("Equipment Cost",   f"${equipment_cost:,.2f}"),
        ("Overhead",         f"${overhead_cost:,.2f}"),
        ("Profit",           f"${profit_amount:,.2f}"),
    ]))
    story.append(Spacer(1, 12))

    # ── Section 2: Crew Plan ──────────────────────────────────────
    story += section_title("SECTION 2 — CREW PLAN")
    story.append(two_col_rows([
        ("Crew Speed",          speed_label.split(" —")[0] if " —" in speed_label else speed_label),
        ("Daily Crew Cost",     f"${daily_crew_cost:,.2f}/day"),
        ("Estimated Duration",  f"{days_req} days"),
        ("Estimated Labor Cost",f"${actual_labor:,.2f}"),
        ("Labor Cost per SQFT", f"${labor_psf:.2f}"),
    ]))
    story.append(Spacer(1, 12))

    # ── Section 3: Labor Budget Status ───────────────────────────
    story += section_title("SECTION 3 — LABOR BUDGET STATUS")
    if on_budget:
        status_pairs = [
            ("Status",               "ON BUDGET"),
            ("Budget Remaining",     f"${labor_variance:,.2f}"),
            ("Maximum Days Allowed", f"{max_days_budget} days"),
        ]
        field_rule = f"Crew must finish within {max_days_budget} days. Every extra day reduces profit."
    else:
        status_pairs = [
            ("Status",               "OVER BUDGET"),
            ("Over Budget By",       f"${abs(labor_variance):,.2f}"),
            ("Maximum Days Allowed", f"{max_days_budget} days"),
        ]
        field_rule = "Crew productivity must increase or labor budget must be revised."
    story.append(two_col_rows(status_pairs))
    story.append(Spacer(1, 6))
    rule_t = Table([[Paragraph(f"Required Field Rule: {field_rule}",
                               sty("fr", fontSize=9, textColor=STATUS_TEXT, fontName="Helvetica-Bold"))]],
                   colWidths=[W])
    rule_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), STATUS_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))
    story.append(rule_t)
    story.append(Spacer(1, 12))

    # ── Section 4: Field Instructions ────────────────────────────
    story += section_title("SECTION 4 — FIELD INSTRUCTIONS")
    if on_budget:
        instructions = [
            "Maintain current production rate.",
            "Avoid unnecessary labor days.",
            "Monitor weather delays.",
            "Monitor inspections.",
            "Monitor concrete delivery schedules.",
            "Monitor access restrictions.",
            "Any additional labor day reduces profit.",
        ]
    else:
        instructions = [
            "Current labor plan exceeds budget.",
            "Increase production rate.",
            "Reduce labor cost if possible.",
            "Revise labor budget if needed.",
            "Additional labor days increase losses.",
        ]
    for inst in instructions:
        story.append(Paragraph(f"• {inst}", sty(f"ins_{inst[:8]}",
                                                  fontSize=9, textColor=MUTED, spaceAfter=3)))
    story.append(Spacer(1, 12))

    # ── Section 5: Crew Members ───────────────────────────────────
    story += section_title("SECTION 5 — CREW MEMBERS")
    crew_header = [
        Paragraph("Name",         sty("ch1", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Pay Type",     sty("ch2", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Rate",         sty("ch3", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Hrs/Day",      sty("ch4", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD)),
        Paragraph("Daily Cost",   sty("ch5", fontName="Helvetica-Bold", fontSize=9, textColor=GOLD, alignment=TA_RIGHT)),
    ]
    crew_rows = [crew_header]
    for m in crew_members:
        dc = m["rate"] * m["hours"] if m["pay_type"] == "Hourly" else m["rate"]
        crew_rows.append([
            Paragraph(m["name"] or "—",      sty(f"cn{id(m)}", fontSize=9)),
            Paragraph(m["pay_type"],          sty(f"ct{id(m)}", fontSize=9)),
            Paragraph(f"${m['rate']:.2f}",   sty(f"cr{id(m)}", fontSize=9)),
            Paragraph(str(m["hours"]) if m["pay_type"] == "Hourly" else "—",
                      sty(f"ch{id(m)}", fontSize=9)),
            Paragraph(f"${dc:,.2f}",         sty(f"cd{id(m)}", fontSize=9, alignment=TA_RIGHT)),
        ])
    crew_rows.append([
        Paragraph("", sty("cf0")), Paragraph("", sty("cf1")),
        Paragraph("", sty("cf2")), Paragraph("Total Daily Cost", sty("cft", fontName="Helvetica-Bold", fontSize=9)),
        Paragraph(f"${daily_crew_cost:,.2f}", sty("cfv", fontName="Helvetica-Bold", fontSize=9, alignment=TA_RIGHT)),
    ])
    crew_t = Table(crew_rows, colWidths=[W*0.28, W*0.15, W*0.17, W*0.17, W*0.23])
    crew_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, RULE),
        ("LINEABOVE",     (0, -1), (-1, -1), 0.8, DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(crew_t)
    story.append(Spacer(1, 16))

    # ── Section 6: Project Manager Signoff ───────────────────────
    story += section_title("SECTION 6 — PROJECT MANAGER SIGNOFF")
    sig_rows = [
        ("Prepared By:",      "________________________"),
        ("Project Manager:",  "________________________"),
        ("Date:",             "________________________"),
        ("Notes:",            "________________________"),
        ("",                  "________________________"),
        ("",                  "________________________"),
    ]
    for lbl, line in sig_rows:
        story.append(Paragraph(
            f"<b>{lbl}</b>  {line}" if lbl else f"{'':40}{line}",
            sty(f"sig{lbl[:3]}", fontSize=10, spaceAfter=12, textColor=MUTED)
        ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


st.set_page_config(page_title="LYNSUS ESTIMATOR", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════
   LYNSUS ESTIMATOR — PREMIUM UI 2026
   UI styling only. No formulas or logic changed.
   ═══════════════════════════════════════════════════════ */

/* ── Global ───────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #0f172a !important;
    color: #f8fafc !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif !important;
}
[data-testid="stAppViewContainer"] > section {
    background-color: #0f172a !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #0f172a 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] h3 {
    color: #f59e0b !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    padding-bottom: 8px !important;
    border-bottom: 1px solid rgba(245,158,11,0.18) !important;
    margin: 20px 0 14px 0 !important;
}

/* ── Header ───────────────────────────────────────────── */
.header {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #0f172a 100%);
    border: 1px solid rgba(245,158,11,0.20);
    border-bottom: 2px solid #f59e0b;
    padding: 30px 44px;
    margin-bottom: 28px;
    border-radius: 16px;
    box-shadow:
        0 4px 40px rgba(245,158,11,0.07),
        0 1px 0 rgba(255,255,255,0.04) inset;
    position: relative;
    overflow: hidden;
}
.header::before {
    content: "";
    position: absolute;
    top: -80px; right: -80px;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(245,158,11,0.10) 0%, transparent 70%);
    pointer-events: none;
}
.header h1 {
    color: #f59e0b;
    font-size: 30px;
    font-weight: 900;
    letter-spacing: 4px;
    margin: 0;
    text-shadow: 0 0 48px rgba(245,158,11,0.35);
}
.header p {
    color: #475569;
    margin: 7px 0 0 0;
    font-size: 12px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

/* ── Section Titles ───────────────────────────────────── */
.section-title {
    display: flex;
    align-items: center;
    background: linear-gradient(90deg, rgba(245,158,11,0.07) 0%, transparent 80%);
    border-left: 3px solid #f59e0b;
    padding: 8px 16px;
    color: #f59e0b;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.5px;
    margin: 24px 0 12px 0;
    border-radius: 0 6px 6px 0;
}

/* ── Line Items ───────────────────────────────────────── */
.line-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 11px 16px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 8px;
    margin: 4px 0;
    transition: background 0.15s ease, border-color 0.15s ease;
}
.line-item:hover {
    background: rgba(255,255,255,0.06);
    border-color: rgba(245,158,11,0.18);
}
.line-item .name  { color: #e2e8f0; font-size: 13.5px; }
.line-item .qty   { color: #475569; font-size: 12px; margin: 0 auto 0 12px; }
.line-item .price { color: #f59e0b; font-weight: 700; font-size: 14px; }

/* ── Subtotal Rows ────────────────────────────────────── */
.subtotal-row {
    display: flex;
    justify-content: space-between;
    padding: 9px 16px;
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.04);
    border-radius: 6px;
    margin: 3px 0;
    font-size: 13px;
}

/* ── Result Rows ──────────────────────────────────────── */
.result-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    font-size: 14px;
}
.result-row:last-child { border-bottom: none; }

/* ── Total Box ────────────────────────────────────────── */
.total-box {
    background: linear-gradient(135deg, rgba(34,197,94,0.07) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(34,197,94,0.30);
    border-radius: 16px;
    padding: 28px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0 0 40px rgba(34,197,94,0.07);
    transition: box-shadow 0.3s ease;
}
.total-box:hover { box-shadow: 0 0 56px rgba(34,197,94,0.12); }
.total-amount {
    color: #22c55e;
    font-size: 48px;
    font-weight: 900;
    margin: 8px 0;
    letter-spacing: -1px;
}
.total-sqft { color: #475569; font-size: 14px; letter-spacing: 1px; }

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%) !important;
    color: #000 !important;
    font-weight: 800 !important;
    font-size: 14px !important;
    letter-spacing: 0.3px !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
    box-shadow: 0 2px 16px rgba(245,158,11,0.22) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 24px rgba(245,158,11,0.38) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* ── Download Buttons ─────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 100%) !important;
    color: #fff !important;
    font-weight: 700 !important;
    border: 1px solid rgba(59,130,246,0.35) !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 12px rgba(59,130,246,0.18) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(59,130,246,0.32) !important;
}

/* ── KPI Metric Cards ─────────────────────────────────── */
[data-testid="metric-container"],
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="metric-container"]:hover,
[data-testid="stMetric"]:hover {
    border-color: rgba(245,158,11,0.25) !important;
    box-shadow: 0 0 24px rgba(245,158,11,0.06) !important;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 800 !important;
    color: #f8fafc !important;
    letter-spacing: -0.5px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    color: #64748b !important;
}
[data-testid="stMetricDelta"] {
    font-size: 11px !important;
    font-weight: 600 !important;
}

/* ── Tabs ─────────────────────────────────────────────── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.025) !important;
    border-radius: 12px !important;
    padding: 4px 6px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    color: #475569 !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.2px !important;
    padding: 8px 22px !important;
    border: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background: rgba(255,255,255,0.05) !important;
    color: #94a3b8 !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(245,158,11,0.16) 0%, rgba(245,158,11,0.07) 100%) !important;
    color: #f59e0b !important;
    box-shadow: 0 0 0 1px rgba(245,158,11,0.28) !important;
}

/* ── Alerts ───────────────────────────────────────────── */
[data-testid="stAlert"] > div,
div[class*="stAlert"] > div {
    border-radius: 10px !important;
}

/* ── Info Boxes ───────────────────────────────────────── */
[data-testid="stInfo"] > div {
    background: rgba(59,130,246,0.06) !important;
    border: 1px solid rgba(59,130,246,0.20) !important;
    border-radius: 10px !important;
}

/* ── Inputs ───────────────────────────────────────────── */
input[type="number"], input[type="text"],
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 6px !important;
    color: #f8fafc !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
input:focus {
    border-color: rgba(245,158,11,0.45) !important;
    box-shadow: 0 0 0 3px rgba(245,158,11,0.07) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.10) !important;
    border-radius: 6px !important;
}

/* ── Caption & Small Text ─────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #334155 !important;
    font-size: 11.5px !important;
}

/* ── Dividers ─────────────────────────────────────────── */
hr { border-color: rgba(255,255,255,0.05) !important; margin: 16px 0 !important; }

/* ── Scrollbar ────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.10);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(245,158,11,0.35); }

/* ── Fade-in animation ────────────────────────────────── */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
[data-testid="stVerticalBlock"] > div:first-child {
    animation: fadeUp 0.28s ease both;
}

/* ── Header — compact strip ───────────────────────────── */
.header {
    background: transparent !important;
    border: none !important;
    border-bottom: 1px solid rgba(245,158,11,0.10) !important;
    padding: 10px 4px !important;
    margin-bottom: 8px !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.header::before { display: none !important; }
.header h1 {
    color: #f59e0b !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 3.5px !important;
    margin: 0 !important;
    text-shadow: none !important;
}
.header p { display: none !important; }

/* ── Hero Banner ──────────────────────────────────────── */
.hero-banner {
    width: 100%;
    min-height: 420px;
    border-radius: 24px;
    background-color: #0d1117;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    box-shadow:
        0 8px 48px rgba(0,0,0,0.55),
        0 0 0 1px rgba(245,158,11,0.14);
    margin-bottom: 28px;
    overflow: hidden;
    position: relative;
}
.hero-banner::after {
    content: "";
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #f59e0b 0%, rgba(245,158,11,0.25) 55%, transparent 100%);
    pointer-events: none;
}
.hero-overlay {
    min-height: 420px;
    background: linear-gradient(90deg,
        rgba(0,0,0,0.88) 0%,
        rgba(0,0,0,0.58) 50%,
        rgba(0,0,0,0.18) 100%);
    padding: 48px 56px;
    display: flex;
    align-items: center;
    border-radius: 24px;
}
.hero-content { max-width: 580px; }
.hero-badge {
    display: inline-block;
    background: rgba(245,158,11,0.13);
    border: 1px solid rgba(245,158,11,0.32);
    color: #f59e0b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    padding: 5px 15px;
    border-radius: 100px;
    margin-bottom: 22px;
}
.hero-headline {
    color: #ffffff !important;
    font-size: 46px !important;
    font-weight: 900 !important;
    line-height: 1.10 !important;
    letter-spacing: -1.5px !important;
    margin: 0 0 18px 0 !important;
    text-shadow: 0 2px 32px rgba(0,0,0,0.55) !important;
}
.hero-subtitle {
    color: rgba(255,255,255,0.68) !important;
    font-size: 17px !important;
    line-height: 1.65 !important;
    margin: 0 0 34px 0 !important;
    font-weight: 400 !important;
    max-width: 460px;
}
.hero-cta {
    display: inline-block;
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: #000 !important;
    font-weight: 800;
    font-size: 15px;
    letter-spacing: 0.3px;
    padding: 14px 34px;
    border: none;
    border-radius: 10px;
    cursor: pointer;
    text-decoration: none !important;
    box-shadow: 0 4px 28px rgba(245,158,11,0.42);
    transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.hero-cta:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 36px rgba(245,158,11,0.58);
    color: #000 !important;
    text-decoration: none !important;
}

/* ── Hero gradient fallback (no image) ────────────────── */
.hero-banner.hero-no-image {
    background: linear-gradient(135deg,
        #0f172a 0%,
        #1e1b4b 40%,
        #0f172a 100%) !important;
}

/* ── Hero responsive ──────────────────────────────────── */
@media (max-width: 768px) {
    .hero-banner, .hero-overlay { min-height: auto; }
    .hero-overlay { padding: 32px 24px; }
    .hero-headline { font-size: 28px !important; letter-spacing: -0.5px !important; }
    .hero-subtitle { font-size: 14px !important; }
    .hero-cta { padding: 12px 24px; font-size: 14px; }
}

/* ── Print ────────────────────────────────────────────── */
@media print {
    section[data-testid="stSidebar"],
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    .stDeployButton,
    [data-testid="stTabs"] > div:first-child,
    [data-testid="stTextInput"],
    [data-testid="stDateInput"],
    [data-testid="stTextArea"],
    .no-print { display: none !important; }
    body { background: white !important; }
}

/* ── All inputs everywhere ────────────────────────────────── */
input[type="text"], input[type="number"], input[type="email"], input[type="tel"] {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
.stTextInput input {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
.stNumberInput input {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
section[data-testid="stSidebar"] input {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
section[data-testid="stMain"] input {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
input::placeholder {
    color: #888888 !important;
    opacity: 1 !important;
}
.stDateInput input {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}
.stTextArea textarea {
    color: #1a1a2e !important;
    background-color: #ffffff !important;
}

/* ── File uploader ────────────────────────────────────────── */
.stFileUploader label { color: #ffffff !important; }
.stFileUploader div   { color: #ffffff !important; }
.stFileUploader span  { color: #ffffff !important; }
[data-testid="stFileUploader"] { color: #ffffff !important; }
[data-testid="stFileUploadDropzone"] {
    background-color: #1e2a3a !important;
    border: 2px dashed #f0a500 !important;
    color: #ffffff !important;
}
[data-testid="stFileUploadDropzone"] span { color: #ffffff !important; }

/* ── Input labels everywhere ──────────────────────────────── */
label { color: #ffffff !important; }
.stTextInput label { color: #ffffff !important; }
.stDateInput label { color: #ffffff !important; }
section[data-testid="stMain"] label { color: #ffffff !important; }

/* ── File uploader button ─────────────────────────────────── */
[data-testid="stFileUploaderDropzoneInstructions"] { color: #ffffff !important; }
[data-testid="baseButton-secondary"] {
    background-color: #f0a500 !important;
    color: #1a1a2e !important;
    border: none !important;
}
.stFileUploader > div > div {
    background-color: #1e2a3a !important;
    border: 2px dashed #f0a500 !important;
}
.stFileUploader > div > div > div { color: #ffffff !important; }
.stFileUploader button {
    background-color: #f0a500 !important;
    color: #1a1a2e !important;
    font-weight: bold !important;
}
.stFileUploader * { color: #ffffff !important; }
.stFileUploader button * { color: #1a1a2e !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header">
    <h1>🏗️ LYNSUS ESTIMATOR</h1>
</div>
""", unsafe_allow_html=True)

# ── Hero Banner ───────────────────────────────────────────────────────
hero_image_url = "http://localhost:8501/app/static/hero_background.png"

st.markdown(f"""
<div class="hero-banner" style="background-image:url('{hero_image_url}');">
  <div class="hero-overlay">
    <div class="hero-content">
      <div class="hero-badge">&#10022; AI-Powered Platform</div>
      <h2 class="hero-headline">AI-Powered Concrete Estimating</h2>
      <p class="hero-subtitle">
        Estimate flatwork, plan labor, protect profit, and generate
        professional quotes in minutes.
      </p>
      <a class="hero-cta" href="#">Start Estimate &rarr;</a>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Price session state ───────────────────────
if "prices" not in st.session_state:
    st.session_state.prices = _load_prices()

if "concrete_price" not in st.session_state:
    st.session_state["concrete_price"] = st.session_state.prices["conc_price"]

# When prices are updated from Tab 3, clear cached widget values so sidebar
# inputs re-render with the new defaults on the next run.
if st.session_state.get("_prices_updated"):
    _reset_keys = (
        ["stakes_bundle_input", "ej_price_input"]
        + [f"rp_{rt}" for rt in ["#3", "#4", "#5"]]
        + [f"lp_{ft}" for ft in [
            "Sidewalk / Patio", "Driveway / Heavy Slab",
            "Mixed (Driveway + Sidewalk)", "Manual"]]
    )
    for _k in _reset_keys:
        st.session_state.pop(_k, None)
    st.session_state["_prices_updated"] = False

# ══════════════════════════════════════════════
# SIDEBAR — ALL INPUTS
# ══════════════════════════════════════════════
with st.sidebar:

    # ── 1: Dimensions ──
    st.markdown("### 1 · Project Dimensions")
    job_name   = st.text_input("Job Name", placeholder="e.g. Smith Driveway")
    zone_setup = st.selectbox("Concrete Zone Setup", [
        "Single Thickness (whole job same thickness)",
        "Driveway + Apron + Sidewalk (different thicknesses)",
        "Custom (up to 4 zones)",
    ])

    THICK_OPTIONS = [4, 6, 8, 12]

    if zone_setup == "Single Thickness (whole job same thickness)":
        sqft      = st.number_input("Total Square Footage", min_value=1.0, value=500.0, step=10.0)
        thickness = st.selectbox("Concrete Thickness", THICK_OPTIONS, format_func=lambda x: f'{x} inches')
        zones     = [{"name": "Slab", "sqft": sqft, "thick": thickness}]

    elif zone_setup == "Driveway + Apron + Sidewalk (different thicknesses)":
        c1, c2 = st.columns([2, 1])
        dw_sqft  = c1.number_input("Driveway SQFT",   min_value=0.0, value=400.0, step=10.0, key="z_dw_sqft")
        dw_thick = c2.selectbox("Thickness", THICK_OPTIONS, index=0, format_func=lambda x: f'{x}"', key="z_dw_thick")
        ap_sqft  = c1.number_input("Apron/Turn SQFT", min_value=0.0, value=50.0,  step=10.0, key="z_ap_sqft")
        ap_thick = c2.selectbox("Thickness", THICK_OPTIONS, index=1, format_func=lambda x: f'{x}"', key="z_ap_thick")
        sw_sqft  = c1.number_input("Sidewalk SQFT",   min_value=0.0, value=50.0,  step=10.0, key="z_sw_sqft")
        sw_thick = c2.selectbox("Thickness", THICK_OPTIONS, index=0, format_func=lambda x: f'{x}"', key="z_sw_thick")
        zones = [
            {"name": "Driveway",   "sqft": dw_sqft,  "thick": dw_thick},
            {"name": "Apron/Turn", "sqft": ap_sqft,  "thick": ap_thick},
            {"name": "Sidewalk",   "sqft": sw_sqft,  "thick": sw_thick},
        ]
        sqft      = dw_sqft + ap_sqft + sw_sqft
        thickness = None

    else:  # Custom (up to 4 zones)
        st.caption("Zone Name  ·  SQFT  ·  Thick")
        zones_raw = []
        for i in range(4):
            c1, c2, c3 = st.columns([2, 2, 1])
            zname  = c1.text_input("Name", value="", placeholder=f"Zone {i+1}", key=f"z_name_{i}", label_visibility="collapsed")
            zsqft  = c2.number_input("SQFT", value=0.0, min_value=0.0, step=10.0, key=f"z_sqft_{i}", label_visibility="collapsed")
            zthick = c3.selectbox("In", THICK_OPTIONS, index=0, format_func=lambda x: f'{x}"', key=f"z_thick_{i}", label_visibility="collapsed")
            zones_raw.append({"name": zname or f"Zone {i+1}", "sqft": zsqft, "thick": zthick})
        zones     = [z for z in zones_raw if z["sqft"] > 0]
        sqft      = sum(z["sqft"] for z in zones) or 1.0
        thickness = None

    waste_pct  = st.number_input("Concrete Waste %", min_value=0.0, max_value=30.0, value=10.0, step=0.5)
    conc_price = st.number_input("Concrete ($/CY)",  min_value=0.0,
                                  value=st.session_state["concrete_price"],
                                  step=1.0, format="%.2f", key="conc_price_input")
    conc_psi   = st.selectbox("Concrete PSI", [2500, 3000, 3500, 4000], index=1, format_func=lambda x: f"{x} PSI")

    for z in zones:
        z["cy_raw"] = z["sqft"] * z["thick"] / 324
    cy_raw = sum(z["cy_raw"] for z in zones)
    cy_ord = math.ceil(cy_raw * (1 + waste_pct / 100))

    if len(zones) == 1:
        st.info(f"**{cy_ord} CY** to order ({cy_raw:.1f} raw + {waste_pct:.0f}%)")
    else:
        zone_lines = "  \n".join(
            f"{z['name']}: {z['sqft']:,.0f} sqft × {z['thick']}\" = {z['cy_raw']:.1f} CY"
            for z in zones if z["sqft"] > 0
        )
        st.info(f"{zone_lines}  \n**Total: {cy_ord} CY** to order ({cy_raw:.1f} raw + {waste_pct:.0f}%)")

    _wc1, _wc2 = st.columns(2)
    dw_width = _wc1.number_input("Driveway Width (ft)", min_value=0.0, value=0.0, step=1.0, format="%.0f",
                                  help="Used for center expansion joint rule (>15 ft triggers center joint)")
    sw_width = _wc2.number_input("Sidewalk Width (ft)", min_value=0.0, value=0.0, step=1.0, format="%.0f",
                                  help="Used to calculate required sidewalk expansion joints every 20 ft")

    st.markdown("---")

    # ── 2: Forming ──
    st.markdown("### 2 · Forming Materials")
    form_type = st.selectbox("Form Type", [
        "Sidewalk / Patio",
        "Driveway / Heavy Slab",
        "Mixed (Driveway + Sidewalk)",
        "Manual",
    ])

    is_mixed = form_type == "Mixed (Driveway + Sidewalk)"

    if is_mixed:
        sqft_driveway = st.number_input("Driveway SQFT", min_value=0.0, value=400.0, step=10.0)
        sqft_sidewalk = st.number_input("Sidewalk SQFT", min_value=0.0, value=100.0, step=10.0)
        lumber_price_driveway = st.session_state.prices["lumber_2x4"]
        lumber_price_sidewalk = st.session_state.prices["lumber_1x4"]
        lumber_lf_driveway = sqft_driveway * 0.13
        lumber_lf_sidewalk = sqft_sidewalk * 0.13
        lumber_lf    = lumber_lf_driveway + lumber_lf_sidewalk
        lumber_price = lumber_price_driveway
    else:
        sqft_driveway = sqft_sidewalk = 0.0
        lumber_price_driveway = lumber_price_sidewalk = 0.0
        lumber_lf_driveway = lumber_lf_sidewalk = 0.0
        if form_type == "Sidewalk / Patio":
            default_lumber_price = st.session_state.prices["lumber_1x4"]
        elif form_type == "Driveway / Heavy Slab":
            default_lumber_price = st.session_state.prices["lumber_2x4"]
        else:
            default_lumber_price = 0.85
        lumber_price = st.number_input("Lumber ($/LF)", min_value=0.0, value=default_lumber_price,
                                       step=0.001, format="%.3f", key=f"lp_{form_type}")
        lumber_lf    = sqft * 0.13

    stake_bundle_price = st.number_input("Stakes ($/bundle)", min_value=0.0,
                                          value=st.session_state.prices["stakes_bundle"],
                                          step=0.01, format="%.2f", key="stakes_bundle_input")
    stakes_per_bundle  = st.number_input("Stakes per bundle", min_value=1,   value=25,   step=1)
    stake_price        = stake_bundle_price / stakes_per_bundle
    st.caption(f"= ${stake_price:.4f} per stake")
    ej_price    = st.number_input("Expansion Joint ($/LF)", min_value=0.0,
                                   value=st.session_state.prices["exp_joint"],
                                   step=0.001, format="%.3f", key="ej_price_input")

    stakes_qty  = math.ceil(lumber_lf / 4)
    ej_lf_base  = sqft / 10
    ej_lf_extra = 0.0
    ej_center_lf = 0.0
    ej_sw_count  = 0
    ej_sw_lf     = 0.0
    dw_center_warning = ""
    sw_count_note     = ""

    if zone_setup == "Driveway + Apron + Sidewalk (different thicknesses)":
        _ej_dw_sqft = dw_sqft
        _ej_sw_sqft = sw_sqft
    elif zone_setup == "Single Thickness (whole job same thickness)":
        _ej_dw_sqft = sqft
        _ej_sw_sqft = 0.0
    else:
        _ej_dw_sqft = 0.0
        _ej_sw_sqft = 0.0

    if dw_width > 0 and _ej_dw_sqft > 0:
        _dw_length = _ej_dw_sqft / dw_width
        if dw_width > 15:
            ej_center_lf = _dw_length
            ej_lf_extra += ej_center_lf
            dw_center_warning = (
                f"Driveway is {dw_width:.0f} ft wide — center expansion joint required "
                f"at {dw_width / 2:.1f} ft to prevent cracking"
            )

    if sw_width > 0 and _ej_sw_sqft > 0:
        _sw_length = _ej_sw_sqft / sw_width
        ej_sw_count = math.floor(_sw_length / 20)
        if ej_sw_count > 0:
            ej_sw_lf = ej_sw_count * sw_width
            ej_lf_extra += ej_sw_lf
            sw_count_note = f"Sidewalk requires expansion joint every 20 ft — {ej_sw_count} joints needed"

    ej_lf = ej_lf_base + ej_lf_extra

    if dw_center_warning:
        st.warning(dw_center_warning)
    if sw_count_note:
        st.info(sw_count_note)

    st.markdown("---")

    # ── 3: Rebar ──
    st.markdown("### 3 · Rebar (Optional)")
    use_rebar = st.checkbox("Include Rebar")
    rebar_lf, rebar_lf_base, rebar_lf_waste, rebar_price, rebar_spacing, rebar_type = 0.0, 0.0, 0.0, 0.0, "", ""
    rebar_waste_pct = 0.0
    rebar_bars = 0
    if use_rebar:
        REBAR_FACTORS = {
            '12" O.C.': 2.000, '14" O.C.': 1.714,
            '15" O.C.': 1.600, '16" O.C.': 1.500,
            '18" O.C.': 1.333, '24" O.C.': 1.000,
        }
        REBAR_PRICES = {
            "#3": st.session_state.prices["rebar_3"],
            "#4": st.session_state.prices["rebar_4"],
            "#5": st.session_state.prices["rebar_5"],
        }
        rebar_type      = st.selectbox("Rebar Type", list(REBAR_PRICES.keys()))
        rebar_spacing   = st.selectbox("Rebar Spacing", list(REBAR_FACTORS.keys()))
        rebar_waste_pct = st.number_input("Rebar Waste %", min_value=0.0, max_value=30.0, value=10.0, step=0.5)
        rebar_lf_base   = sqft * REBAR_FACTORS[rebar_spacing]
        rebar_lf_waste  = rebar_lf_base * (rebar_waste_pct / 100)
        rebar_lf        = rebar_lf_base + rebar_lf_waste
        rebar_price     = st.number_input("Rebar ($/LF)", min_value=0.0, value=REBAR_PRICES[rebar_type],
                                          step=0.0001, format="%.4f", key=f"rp_{rebar_type}")
        st.info(f"**{rebar_lf:.1f} LF** to order ({rebar_lf_base:.1f} base + {rebar_lf_waste:.1f} waste)")
        rebar_bars = math.ceil(rebar_lf / 20)
        st.info(f"**{rebar_bars} bars** of 20ft needed")

    st.markdown("---")

    # ── 4: Base Material ──
    st.markdown("### 4 · Base Material (Optional)")
    use_base = st.checkbox("Include Base Material")
    base_type = ""
    base_sqft_used = 0.0
    base_thick_in = 6
    base_waste_pct = 10.0
    base_price = 0.0
    base_tons_raw = base_tons_ord = base_total = 0.0
    base_trucks = 0
    if use_base:
        BASE_TYPES = ["Crushed Concrete", "Flexible Base (Stabilizer)", "Gravel", "Sand"]
        base_type     = st.selectbox("Material Type", BASE_TYPES)
        base_sqft_in  = st.number_input("Square Footage (0 = use project sqft)", min_value=0.0, value=0.0, step=10.0)
        base_sqft_used = base_sqft_in if base_sqft_in > 0 else sqft
        if base_sqft_in == 0:
            st.caption(f"Using project sqft: {sqft:,.0f} sqft")
        base_thick_in  = st.number_input("Base Thickness (inches)", min_value=1, value=6, step=1)
        base_waste_pct  = st.number_input("Waste %", min_value=0.0, max_value=30.0, value=10.0, step=0.5, key="bwp")
        base_tons_raw   = base_sqft_used * base_thick_in * 0.00309
        base_tons_ord   = base_tons_raw * (1 + base_waste_pct / 100)
        base_trucks     = math.ceil(base_tons_ord / 11)
        base_pricing    = st.radio("Pricing Method", ["Price per Ton", "Price per Truck"], horizontal=True, key="bpm")
        if base_pricing == "Price per Ton":
            base_price  = st.number_input("Price ($/ton)", min_value=0.0, value=0.0, step=1.0, format="%.2f")
            base_total  = base_tons_ord * base_price
            cost_line   = f"Total cost: **${base_total:,.2f}**"
        else:
            base_price_per_truck = st.number_input("Price ($/truck)", min_value=0.0, value=0.0, step=50.0, format="%.2f")
            base_total  = base_trucks * base_price_per_truck
            base_price  = base_total / base_tons_ord if base_tons_ord > 0 else 0.0
            cost_line   = f"{base_trucks} truck{'s' if base_trucks != 1 else ''} × ${base_price_per_truck:,.2f}/truck = **${base_total:,.2f}**"
        st.info(
            f"**{base_tons_ord:.1f} tons** needed ({base_tons_raw:.1f} base + {base_tons_ord - base_tons_raw:.1f} waste)  \n"
            f"**{base_trucks} truck{'s' if base_trucks != 1 else ''}** to order (11 tons per truck - safe load)  \n"
            f"{cost_line}"
        )

    st.markdown("---")

    # ── 5: Equipment ──
    st.markdown("### 5 · Equipment")
    if "equipment" not in st.session_state:
        st.session_state.equipment = [{"name": "", "cost": 0.0}]

    for i, eq in enumerate(st.session_state.equipment):
        c1, c2 = st.columns([2, 1])
        st.session_state.equipment[i]["name"] = c1.text_input(
            f"Name {i+1}", value=eq["name"], placeholder="Pump, Buggy...", key=f"eq_name_{i}", label_visibility="collapsed")
        st.session_state.equipment[i]["cost"] = c2.number_input(
            "$", min_value=0.0, value=float(eq["cost"]), step=50.0, key=f"eq_cost_{i}", format="%.0f", label_visibility="collapsed")

    if st.button("➕ Add Equipment"):
        st.session_state.equipment.append({"name": "", "cost": 0.0})
        st.rerun()

    st.markdown("---")

    # ── 6: Labor ──
    st.markdown("### 6 · Labor")
    labor_method = st.radio("Labor Method", ["By Square Foot", "Flat Total"], horizontal=True)
    if labor_method == "By Square Foot":
        labor_rate = st.number_input("Labor ($/SQFT)", min_value=0.0, value=2.0, step=0.25, format="%.2f")
        labor_cost = sqft * labor_rate
        st.info(f"Labor total: **${labor_cost:,.2f}** ({sqft:,.0f} SQFT × ${labor_rate:.2f})")
    else:
        labor_rate = 0.0
        labor_cost = st.number_input("Labor (flat total $)", min_value=0.0, value=0.0, step=50.0, format="%.2f")

    st.markdown("---")

    # ── 7: Demo ──
    st.markdown("### 7 · Demolition (Optional)")
    use_demo, demo_cost = st.checkbox("Include Demolition"), 0.0
    if use_demo:
        demo_rate = st.number_input("Demo ($/SQFT)", min_value=0.0, value=2.50, step=0.25, format="%.2f")
        demo_cost = sqft * demo_rate
        st.info(f"Demo total: **${demo_cost:,.2f}**")

    st.markdown("---")

    # ── 8: Overhead & Profit ──
    st.markdown("### 8 · Overhead & Profit")
    overhead_pct = st.number_input("Overhead %", min_value=0.0, max_value=50.0, value=15.0, step=0.5)
    profit_pct   = st.number_input("Profit %",   min_value=0.0, max_value=50.0, value=10.0, step=0.5)

    st.markdown("---")
    st.button("🧮 CALCULATE ESTIMATE")


# ══════════════════════════════════════════════
# MAIN — CALCULATIONS
# ══════════════════════════════════════════════
conc_total   = cy_ord * conc_price
if is_mixed:
    lumber_total_dw = lumber_lf_driveway * lumber_price_driveway
    lumber_total_sw = lumber_lf_sidewalk * lumber_price_sidewalk
    lumber_total = lumber_total_dw + lumber_total_sw
else:
    lumber_total_dw = lumber_total_sw = 0.0
    lumber_total = lumber_lf * lumber_price
stakes_total = stakes_qty * stake_price
ej_total     = ej_lf    * ej_price
rebar_total  = rebar_lf * rebar_price if use_rebar else 0.0
equip_items  = [e for e in st.session_state.equipment if e["name"] and e["cost"] > 0]
equip_total  = sum(e["cost"] for e in equip_items)

direct_cost  = conc_total + lumber_total + stakes_total + ej_total + rebar_total + base_total + equip_total + labor_cost + demo_cost
overhead_amt = direct_cost * (overhead_pct / 100)
subtotal     = direct_cost + overhead_amt
profit_amt   = subtotal * (profit_pct / 100)
grand_total  = subtotal + profit_amt
price_per_sf = grand_total / sqft if sqft > 0 else 0

# ── Save values for all tabs (single source of truth) ─────────
st.session_state["total_sqft"]     = sqft
st.session_state["total_bid"]      = grand_total
st.session_state["materials_cost"] = conc_total + lumber_total + stakes_total + ej_total + rebar_total + base_total
st.session_state["equipment_cost"] = equip_total
st.session_state["direct_cost"]    = direct_cost
st.session_state["labor_budget"]   = labor_cost
st.session_state["labor_cost"]     = labor_cost
st.session_state["overhead_cost"]  = overhead_amt
st.session_state["profit_amount"]  = profit_amt
st.session_state["price_per_sqft"] = price_per_sf
st.session_state["concrete_yards"] = cy_ord

# ══════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Estimator", "📄 Client Quote", "💲 Update Prices", "👷 Crew Planner", "📋 Contract Analyzer"])

# ─────────────────────── TAB 1: ESTIMATOR ────────────────────────
with tab1:
    if job_name:
        st.markdown(f"<h3 style='color:#f0a500;margin-bottom:4px;'>{job_name}</h3>", unsafe_allow_html=True)
    thick_label = f'{thickness}"' if thickness is not None else zone_setup.split("(")[0].strip()
    st.markdown(f"<p style='color:#8892a4;margin-bottom:16px;'>Area: <b>{sqft:,.0f} SQFT</b> · <b>{thick_label}</b> · Concrete: <b>{cy_ord} CY</b></p>", unsafe_allow_html=True)

    col1, col2 = st.columns([3, 2])

    with col1:
        # Materials
        st.markdown('<div class="section-title">📦 Materials</div>', unsafe_allow_html=True)
        if thickness is not None:
            items = [(f"Concrete ({thickness}\")", f"{cy_ord} CY × ${conc_price:.2f}/CY", conc_total)]
        else:
            zone_detail = " + ".join(f"{z['name']} {z['cy_raw']:.1f}" for z in zones if z["sqft"] > 0)
            items = [(f"Concrete ({len(zones)} zones)", f"{zone_detail} = {cy_raw:.1f} raw → {cy_ord} CY × ${conc_price:.2f}/CY", conc_total)]
        if is_mixed:
            items += [
                ("Lumber 2x4 (Driveway)", f"{lumber_lf_driveway:.0f} LF × ${lumber_price_driveway:.3f}/LF", lumber_total_dw),
                ("Lumber 1x4 (Sidewalk)", f"{lumber_lf_sidewalk:.0f} LF × ${lumber_price_sidewalk:.3f}/LF", lumber_total_sw),
            ]
        else:
            items.append(("Lumber (Forms)", f"{lumber_lf:.0f} LF × ${lumber_price:.3f}/LF", lumber_total))
        items += [
            ("Stakes",           f"{stakes_qty} pcs × ${stake_price:.2f}/ea", stakes_total),
            ("Expansion Joints", f"{ej_lf:.0f} LF × ${ej_price:.2f}/LF",     ej_total),
        ]
        if use_rebar:
            items.append((f"Rebar ({rebar_spacing})", f"{rebar_lf:.1f} LF ({rebar_lf_base:.1f} + {rebar_lf_waste:.1f} waste) × ${rebar_price:.2f}/LF", rebar_total))
        if use_base and base_total > 0:
            items.append((f"Base Material ({base_type})", f"{base_tons_ord:.1f} tons × ${base_price:.2f}/ton · {base_trucks} truck{'s' if base_trucks != 1 else ''}", base_total))

        for name, qty, price in items:
            st.markdown(f'<div class="line-item"><span class="name">{name}</span><span class="qty">{qty}</span><span class="price">${price:,.2f}</span></div>', unsafe_allow_html=True)

        # Equipment
        if equip_items:
            st.markdown('<div class="section-title">🚜 Equipment</div>', unsafe_allow_html=True)
            for eq in equip_items:
                st.markdown(f'<div class="line-item"><span class="name">{eq["name"]}</span><span class="qty">flat rate</span><span class="price">${eq["cost"]:,.2f}</span></div>', unsafe_allow_html=True)

        # Labor
        if labor_cost > 0:
            st.markdown('<div class="section-title">👷 Labor</div>', unsafe_allow_html=True)
            labor_qty = f"{sqft:,.0f} SQFT × ${labor_rate:.2f}/SQFT" if labor_method == "By Square Foot" else "flat total"
            st.markdown(f'<div class="line-item"><span class="name">Labor</span><span class="qty">{labor_qty}</span><span class="price">${labor_cost:,.2f}</span></div>', unsafe_allow_html=True)

        # Demo
        if use_demo and demo_cost > 0:
            st.markdown('<div class="section-title">🔨 Demolition</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="line-item"><span class="name">Demolition</span><span class="qty">{sqft:,.0f} SQFT</span><span class="price">${demo_cost:,.2f}</span></div>', unsafe_allow_html=True)

        # Overhead & Profit
        st.markdown('<div class="section-title">📊 Overhead & Profit</div>', unsafe_allow_html=True)
        for label, amt in [
            ("Direct Cost Subtotal", direct_cost),
            (f"Overhead ({overhead_pct:.0f}%)", overhead_amt),
            ("Subtotal", subtotal),
            (f"Profit ({profit_pct:.0f}%)", profit_amt),
        ]:
            st.markdown(f'<div class="subtotal-row"><span style="color:#a0aec0;">{label}</span><span style="color:#e0e0e0;font-weight:700;">${amt:,.2f}</span></div>', unsafe_allow_html=True)

    with col2:
        # Grand Total
        st.markdown(f"""
<div class="total-box">
  <div style="color:#8892a4;font-size:12px;text-transform:uppercase;letter-spacing:2px;">Total Bid Price</div>
  <div class="total-amount">${grand_total:,.2f}</div>
  <div class="total-sqft">${price_per_sf:.2f} per square foot</div>
</div>
""", unsafe_allow_html=True)

        # Takeoff
        st.markdown('<div class="section-title">📐 Takeoff Summary</div>', unsafe_allow_html=True)
        summary = [
            ("Square Footage",   f"{sqft:,.0f} SQFT"),
            ("Concrete",         f"{cy_ord} CY  (raw {cy_raw:.1f})"),
            ("Lumber",           f"{lumber_lf:.0f} LF" + (f"  ({lumber_lf_driveway:.0f} DW + {lumber_lf_sidewalk:.0f} SW)" if is_mixed else "")),
            ("Stakes",           f"{stakes_qty} pcs"),
            ("Expansion Joints", f"{ej_lf:.0f} LF"),
        ]
        if use_rebar:
            summary.append(("Rebar", f"{rebar_lf:.1f} LF  ({rebar_lf_base:.1f} base + {rebar_lf_waste:.1f} waste)"))
        if use_base and base_total > 0:
            summary.append(("Base Material", f"{base_tons_ord:.1f} tons  ({base_trucks} truck{'s' if base_trucks != 1 else ''})"))
        if use_demo and demo_cost > 0:
            summary.append(("Demo", f"${demo_cost:,.2f}"))

        for label, value in summary:
            st.markdown(f'<div class="result-row"><span style="color:#a0aec0;">{label}</span><span style="color:#e0e0e0;font-weight:600;">{value}</span></div>', unsafe_allow_html=True)

        # Cost breakdown
        st.markdown('<div class="section-title">💰 Cost Breakdown</div>', unsafe_allow_html=True)
        breakdown = [
            ("Materials",  conc_total + lumber_total + stakes_total + ej_total + rebar_total + base_total, None),
            ("Equipment",  equip_total,   None),
            ("Labor",      labor_cost,    None),
            ("Demo",       demo_cost,     None),
            ("Overhead",   overhead_amt,  overhead_pct),
            ("Profit",     profit_amt,    profit_pct),
        ]
        for label, amt, fixed_pct in breakdown:
            if amt > 0:
                pct = fixed_pct if fixed_pct is not None else amt / grand_total * 100
                st.markdown(f'<div class="result-row"><span style="color:#a0aec0;">{label}</span><span style="color:#e0e0e0;font-weight:600;">${amt:,.2f} <span style="color:#8892a4;font-size:11px;">({pct:.0f}%)</span></span></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.caption("LYNSUS ESTIMATOR — All quantities must be verified before ordering.")


# ─────────────────────── TAB 2: CLIENT QUOTE ─────────────────────
with tab2:
    # ── Aliases from session_state (single source of truth) ──
    _q_sqft      = st.session_state.get("total_sqft",     sqft)
    _q_total_bid = st.session_state.get("total_bid",      grand_total)
    _q_ppsf      = st.session_state.get("price_per_sqft", price_per_sf)

    # ── Client Information ──
    st.markdown(
        '<div class="no-print" style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:2px;color:#f0a500;margin-bottom:12px;">Client Information</div>',
        unsafe_allow_html=True
    )
    ci_col1, ci_col2 = st.columns(2)
    with ci_col1:
        client_first   = st.text_input("Client First Name",  key="ci_first")
        client_address = st.text_input("Property Address",   key="ci_addr")
        client_phone   = st.text_input("Client Phone",       key="ci_phone")
        quote_date     = st.date_input("Quote Date", value=datetime.date.today(), key="ci_date")
    with ci_col2:
        client_last           = st.text_input("Client Last Name",  key="ci_last")
        client_city_state_zip = st.text_input("City, State, Zip",  key="ci_csz")
        client_email          = st.text_input("Client Email",      key="ci_email")
        quote_number          = st.text_input("Quote Number", value="LYN-2026-001", key="ci_qnum")

    st.markdown('<hr class="no-print" style="border-color:#2d3748;margin:20px 0 16px 0;">', unsafe_allow_html=True)

    today_str   = quote_date.strftime("%B %d, %Y")
    client_name = f"{client_first} {client_last}".strip() or "—"

    # ── client-facing price: everything except equipment and base material ──
    scope_subtotal = _q_total_bid - equip_total - base_total
    client_ppsf    = scope_subtotal / _q_sqft if _q_sqft > 0 else 0

    def sec(title):
        return (
            f'<div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:2px;'
            f'color:#f0a500;background:#fdf8ee;border-left:3px solid #f0a500;'
            f'padding:6px 12px;margin:20px 0 4px 0;">{title}</div>'
        )

    def qrow(label, detail, amt, bold=False):
        lweight = "700" if bold else "400"
        aweight = "700" if bold else "600"
        det = f'<div style="font-size:11px;color:#888;margin-top:1px;">{detail}</div>' if detail else ""
        return (
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:9px 0;border-bottom:1px solid #f0f0f0;">'
            f'<div><span style="font-size:14px;font-weight:{lweight};color:#1a1a2e;">{label}</span>{det}</div>'
            f'<span style="font-size:14px;font-weight:{aweight};color:#1a1a2e;'
            f'white-space:nowrap;padding-left:16px;">${amt:,.2f}</span>'
            f'</div>'
        )

    # ── build scope of work text ──
    scope_lines = []

    # 1. Concrete work
    if thickness is not None:
        scope_lines.append(f"Supply and install {_q_sqft:,.0f} sqft of {thickness}-inch flatwork concrete ({conc_psi} PSI)")
    else:
        for z in zones:
            if z["sqft"] > 0:
                scope_lines.append(f"Supply and install {z['sqft']:,.0f} sqft of {z['thick']}-inch flatwork concrete ({conc_psi} PSI)")

    # 2. Base material
    if use_base and base_total > 0:
        scope_lines.append(f"Supply and install {base_type} base at {base_thick_in}-inch depth")

    # 3. Rebar
    if use_rebar:
        scope_lines.append(f"Install {rebar_type} rebar at {rebar_spacing} mesh pattern")

    # 4. Demolition
    if use_demo and demo_cost > 0:
        scope_lines.append(f"Remove and haul existing concrete ({_q_sqft:,.0f} sqft)")

    # 5. Forming (always)
    scope_lines.append("Install and remove concrete forms")

    # 6. Finish (always)
    scope_lines.append("Broom finish and standard curing")

    # 7. Equipment
    for eq in equip_items:
        scope_lines.append(f"- {eq['name']}")

    scope_text = "\n".join(scope_lines)
    if st.session_state.get("_last_scope_text") != scope_text:
        st.session_state["scope_edit"] = scope_text
        st.session_state["_last_scope_text"] = scope_text
    edited_scope = st.text_area("Scope of Work (editable)", value=scope_text, height=300, key="scope_edit")

    def _scope_line_html(line):
        if not line.strip():
            return ""
        if line.startswith("    "):
            return (f'<div style="font-size:13px;color:#444;padding:2px 0 2px 24px;">'
                    f'{line.strip()}</div>')
        stripped = line.lstrip()
        if stripped.startswith("-") or stripped.startswith("•"):
            return (f'<div style="font-size:13px;color:#444;padding:3px 0 3px 8px;">'
                    f'{line}</div>')
        return (f'<div style="font-size:13px;color:#444;padding:3px 0 3px 8px;">'
                f'• {line}</div>')

    bullets_html = "".join(_scope_line_html(l) for l in edited_scope.split("\n"))

    # ── build body HTML ──
    body = ""

    body += sec("Scope of Work")
    body += (
        f'<div style="padding:12px 0;border-bottom:1px solid #f0f0f0;">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
        f'<div style="flex:1;">'
        f'<div style="font-size:14px;font-weight:600;color:#1a1a2e;margin-bottom:8px;">'
        f'Flatwork Concrete Installation</div>'
        f'{bullets_html}'
        f'</div>'
        f'<div style="text-align:right;padding-left:24px;white-space:nowrap;">'
        f'<div style="font-size:11px;color:#888;margin-bottom:2px;">Price per sqft</div>'
        f'<div style="font-size:13px;color:#444;margin-bottom:6px;">${client_ppsf:.2f}/sqft</div>'
        f'<div style="font-size:11px;color:#888;margin-bottom:2px;">Subtotal</div>'
        f'<div style="font-size:14px;font-weight:600;color:#1a1a2e;">${scope_subtotal:,.2f}</div>'
        f'</div>'
        f'</div>'
        f'</div>'
    )

    # Base Material pricing (only if present)
    if use_base and base_total > 0:
        body += sec("Base Material")
        body += qrow(
            base_type,
            f"{base_tons_ord:.1f} tons · {base_trucks} truck{'s' if base_trucks != 1 else ''}",
            base_total
        )

    # Equipment pricing (only if present)
    if equip_items:
        body += sec("Equipment")
        for eq in equip_items:
            body += qrow(eq["name"], "", eq["cost"])
        body += qrow("Equipment Total", "", equip_total, bold=True)

    # Grand total
    body += (
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'margin-top:24px;padding:18px 24px;background:#1a1f2e;border-radius:6px;">'
        f'<span style="font-size:20px;font-weight:900;color:#f0a500;letter-spacing:1px;">PROJECT TOTAL</span>'
        f'<span style="font-size:28px;font-weight:900;color:#ffffff;">${_q_total_bid:,.2f}</span>'
        f'</div>'
    )

    # Signature block
    body += (
        '<div style="margin-top:48px;padding-top:24px;border-top:1px solid #e0e0e0;">'
        '<p style="font-size:12px;color:#555;font-style:italic;margin:0 0 28px 0;">'
        'By signing below, client agrees to the scope of work and total amount shown.</p>'
        '<div style="display:flex;justify-content:space-between;">'
        '<div style="font-size:12px;color:#444;line-height:2.2;">'
        'Client Signature: ______________________&nbsp;&nbsp;&nbsp;&nbsp;Date: __________'
        '</div>'
        '</div>'
        '<div style="display:flex;justify-content:space-between;margin-top:20px;">'
        '<div style="font-size:12px;color:#444;line-height:2.2;">'
        'Authorized by: ______________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Date: __________'
        '</div>'
        '</div>'
        '</div>'
    )

    # ── header with client info ──
    bill_to_lines = []
    if client_name != "—":
        bill_to_lines.append(client_name)
    if client_address:
        bill_to_lines.append(client_address)
    if client_city_state_zip:
        bill_to_lines.append(client_city_state_zip)
    contact_line = " | ".join(x for x in [client_phone, client_email] if x)
    if contact_line:
        bill_to_lines.append(contact_line)
    bill_to_html = "<br>".join(bill_to_lines) if bill_to_lines else "—"
    job_location = client_address or job_name or "—"

    header = (
        f'<div style="background:#1a1f2e;padding:32px 40px;">'
        f'<div style="text-align:center;color:#f0a500;font-size:26px;font-weight:900;'
        f'letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;">LYNSUS CONTRACTING</div>'
        f'<div style="text-align:center;color:#8892a4;font-size:12px;margin-bottom:24px;">'
        f'Flatwork Concrete — Driveways · Sidewalks · Patios</div>'
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'border-top:1px solid #2d3748;padding-top:18px;margin-bottom:20px;">'
        f'<div style="color:#cbd5e0;font-size:13px;">{today_str}</div>'
        f'<div style="color:#f0a500;font-size:14px;font-weight:700;">'
        f'Quote #: {quote_number or "LYN-2026-001"}</div>'
        f'</div>'
        f'<div style="margin-bottom:16px;">'
        f'<div style="color:#f0a500;font-size:10px;font-weight:700;letter-spacing:2px;'
        f'text-transform:uppercase;margin-bottom:8px;">BILL TO:</div>'
        f'<div style="color:#cbd5e0;font-size:14px;line-height:1.8;">{bill_to_html}</div>'
        f'</div>'
        f'<div style="border-top:1px solid #2d3748;padding-top:14px;">'
        f'<span style="color:#f0a500;font-size:11px;font-weight:700;text-transform:uppercase;'
        f'letter-spacing:1px;">JOB LOCATION: </span>'
        f'<span style="color:#cbd5e0;font-size:13px;">{job_location}</span>'
        f'</div>'
        f'</div>'
    )

    # ── PDF download ──
    _pdf_name = (
        f"Quote_{(quote_number or 'LYN').replace(' ', '_')}"
        f"_{(client_last or 'Client').replace(' ', '_')}.pdf"
    )
    try:
        _pdf_bytes = _build_quote_pdf(
            today_str=today_str,
            quote_number=quote_number,
            client_name=client_name,
            client_address=client_address,
            client_city_state_zip=client_city_state_zip,
            client_phone=client_phone,
            client_email=client_email,
            job_location=job_location,
            edited_scope=edited_scope,
            scope_subtotal=scope_subtotal,
            client_ppsf=client_ppsf,
            use_base=use_base,
            base_type=base_type,
            base_total=base_total,
            base_tons_ord=base_tons_ord,
            base_trucks=base_trucks,
            equip_items=equip_items,
            equip_total=equip_total,
            grand_total=_q_total_bid,
        )
        st.download_button(
            label="📥 Download Quote as PDF",
            data=_pdf_bytes,
            file_name=_pdf_name,
            mime="application/pdf",
        )
    except Exception as _pdf_err:
        st.error(f"PDF generation failed: {_pdf_err}")

    # ── print button ──
    st.markdown(
        '<button onclick="window.print()" class="no-print" style="background:#f0a500;color:#000;'
        'font-weight:700;border:none;border-radius:6px;padding:10px 28px;font-size:14px;'
        'cursor:pointer;margin-bottom:16px;">🖨️ Print Quote</button>',
        unsafe_allow_html=True
    )

    # ── render quote ──
    st.markdown(
        f'<div style="max-width:800px;margin:0 auto;font-family:Arial,sans-serif;'
        f'box-shadow:0 4px 24px rgba(0,0,0,0.3);border-radius:8px;overflow:hidden;">'
        f'{header}'
        f'<div style="background:#ffffff;padding:32px 40px;color:#1a1a2e;">{body}</div>'
        f'</div>',
        unsafe_allow_html=True
    )


# ─────────────────────── TAB 3: UPDATE PRICES ────────────────────────
with tab3:
    # ── Concrete Price ────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:2px;color:#f0a500;margin-bottom:8px;">Concrete Price ($/CY)</div>',
        unsafe_allow_html=True
    )
    _cp_col1, _cp_col2 = st.columns([2, 1])
    with _cp_col1:
        _new_conc = st.number_input(
            "Concrete Price ($/CY)",
            min_value=0.0,
            value=float(st.session_state.prices["conc_price"]),
            step=1.0,
            format="%.2f",
            label_visibility="collapsed",
            key="tab3_conc_input",
        )
    with _cp_col2:
        if st.button("Update Concrete Price", type="primary"):
            st.session_state["concrete_price"]   = _new_conc
            st.session_state["conc_price_input"] = _new_conc
            st.session_state.prices["conc_price"] = _new_conc
            _save_prices(st.session_state.prices)
            st.success(f"Concrete price updated to ${_new_conc:.2f}/CY")
            st.rerun()

    st.markdown(
        f'<div style="color:#8892a4;font-size:12px;margin-bottom:4px;">'
        f'Current: <b style="color:#e0e0e0;">${st.session_state.prices["conc_price"]:.2f}/CY</b></div>',
        unsafe_allow_html=True
    )
    st.caption("Concrete prices change frequently — update before each estimate.")

    st.markdown("---")

    # ── PDF Price Sheet ───────────────────────────────────────────
    st.markdown(
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:2px;color:#f0a500;margin-bottom:4px;">Update Material Prices</div>',
        unsafe_allow_html=True
    )
    st.caption("Upload a supplier PDF price sheet to extract and update material prices. "
               "Updated prices apply to all tabs immediately.")

    uploaded_pdf = st.file_uploader("Upload Supplier Price Sheet (PDF)", type="pdf")

    if uploaded_pdf is not None:
        try:
            import pdfplumber
        except ImportError:
            import subprocess as _sp
            _sp.run(["pip", "install", "pdfplumber"], check=False)
            import pdfplumber

        try:
            _pdf_raw = uploaded_pdf.read()
            _pdf_text = ""
            with pdfplumber.open(io.BytesIO(_pdf_raw)) as _pdf:
                for _page in _pdf.pages:
                    _pdf_text += (_page.extract_text() or "") + "\n"
        except Exception as _pe:
            st.error(f"Could not read PDF: {_pe}")
            _pdf_text = ""

        if _pdf_text.strip():
            def _find_price(text, patterns):
                for pat in patterns:
                    for m in re.finditer(pat, text, re.IGNORECASE):
                        snippet = text[m.start(): m.start() + 120]
                        pm = re.search(r'\$?\s*(\d{1,5}\.\d{1,2})', snippet)
                        if pm:
                            return float(pm.group(1))
                return None

            _SEARCH = {
                "rebar_3":       ([r'#3\s*[Xx]\s*20', r'#3\s+REBAR', r'REBAR\s*#3'],           20,  "#3 Rebar (20ft piece → $/LF)"),
                "rebar_4":       ([r'#4\s*[Xx]\s*20', r'#4\s+REBAR', r'REBAR\s*#4'],           20,  "#4 Rebar (20ft piece → $/LF)"),
                "rebar_5":       ([r'#5\s*[Xx]\s*20', r'#5\s+REBAR', r'REBAR\s*#5'],           20,  "#5 Rebar (20ft piece → $/LF)"),
                "lumber_1x4":    ([r'1\s*[Xx]\s*4\s*[Xx]\s*16'],                               16,  "Lumber 1x4x16 (→ $/LF)"),
                "lumber_2x4":    ([r'2\s*[Xx]\s*4\s*[Xx]\s*16'],                               16,  "Lumber 2x4x16 (→ $/LF)"),
                "exp_joint":     ([r'EXP(?:ANSION)?\s*J(?:OIN)?T', r'1/2.{0,8}4.{0,8}10'],    10,  "Expansion Joint 10ft (→ $/LF)"),
                "stakes_bundle": ([r'1\s*[Xx]\s*2\s*[Xx]\s*18', r'\bSTAKES?\b'],               1,   "Stakes (bundle)"),
            }

            _found_rows = []
            for _key, (_patterns, _divisor, _label) in _SEARCH.items():
                _raw = _find_price(_pdf_text, _patterns)
                if _raw is not None:
                    _per_unit = _raw / _divisor if _divisor > 1 else _raw
                    _current  = st.session_state.prices[_key]
                    _pct      = abs(_per_unit - _current) / _current * 100 if _current > 0 else 0
                    _found_rows.append({
                        "key":          _key,
                        "Product":      _label,
                        "current":      _current,
                        "new":          _per_unit,
                        "pct":          _pct,
                        "large":        _pct > 20,
                    })

            if not _found_rows:
                st.warning(
                    "No recognizable prices found in this PDF. "
                    "The file may use image-based text or different product naming conventions."
                )
            else:
                st.markdown(f"**{len(_found_rows)} price(s) found** in `{uploaded_pdf.name}`")

                try:
                    import pandas as _pd
                    _df = _pd.DataFrame([{
                        "Accept":           True,
                        "Product":          r["Product"] + ("  ⚠️" if r["large"] else ""),
                        "Current ($/unit)": f"${r['current']:.4f}",
                        "New ($/unit)":     f"${r['new']:.4f}",
                        "Change":           f"{r['pct']:+.1f}%",
                    } for r in _found_rows])

                    _edited = st.data_editor(
                        _df,
                        column_config={
                            "Accept": st.column_config.CheckboxColumn("Accept", default=True),
                        },
                        disabled=["Product", "Current ($/unit)", "New ($/unit)", "Change"],
                        hide_index=True,
                        key="price_editor",
                    )
                except Exception:
                    # pandas not available — fall back to checkboxes
                    _edited = None
                    _manual_accept = []
                    for _r in _found_rows:
                        _chk = st.checkbox(
                            f"{_r['Product']}  |  current: ${_r['current']:.4f}  →  new: ${_r['new']:.4f}"
                            + (f"  ⚠️ +{_r['pct']:.0f}%" if _r["large"] else f"  ({_r['pct']:+.1f}%)"),
                            value=True,
                            key=f"chk_{_r['key']}",
                        )
                        _manual_accept.append(_chk)

                _large = [r["Product"] for r in _found_rows if r["large"]]
                if _large:
                    st.warning(
                        f"⚠️ Large price change (>20%) detected — verify before accepting: "
                        + ", ".join(_large)
                    )

                if st.button("✅ Update Selected Prices", type="primary"):
                    _updated = 0
                    for _i, _row in enumerate(_found_rows):
                        if _edited is not None:
                            _accepted = bool(_edited.iloc[_i]["Accept"])
                        else:
                            _accepted = _manual_accept[_i]
                        if _accepted:
                            st.session_state.prices[_row["key"]] = _row["new"]
                            _updated += 1
                    _save_prices(st.session_state.prices)
                    if _updated:
                        st.session_state["_prices_updated"] = True
                        st.success(
                            f"{_updated} price{'s' if _updated != 1 else ''} updated "
                            f"successfully from `{uploaded_pdf.name}`"
                        )
                        st.rerun()
                    else:
                        st.info("No prices were selected for update.")
        elif uploaded_pdf is not None:
            st.warning("Could not extract text from this PDF. It may be image-based (scanned).")

    # ── Current prices table ──────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<div style="font-size:11px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:2px;color:#f0a500;margin-bottom:8px;">Current Active Prices</div>',
        unsafe_allow_html=True
    )
    _p = st.session_state.prices
    _price_rows = [
        ("#3 Rebar",        f"${_p['rebar_3']:.4f}/LF",        f"(${_p['rebar_3']*20:.2f} per 20ft piece)"),
        ("#4 Rebar",        f"${_p['rebar_4']:.4f}/LF",        f"(${_p['rebar_4']*20:.2f} per 20ft piece)"),
        ("#5 Rebar",        f"${_p['rebar_5']:.4f}/LF",        f"(${_p['rebar_5']*20:.2f} per 20ft piece)"),
        ("Lumber 1x4x16",  f"${_p['lumber_1x4']:.4f}/LF",     f"(${_p['lumber_1x4']*16:.2f} per 16ft piece)"),
        ("Lumber 2x4x16",  f"${_p['lumber_2x4']:.4f}/LF",     f"(${_p['lumber_2x4']*16:.2f} per 16ft piece)"),
        ("Expansion Joint",f"${_p['exp_joint']:.4f}/LF",      f"(${_p['exp_joint']*10:.2f} per 10ft piece)"),
        ("Stakes",         f"${_p['stakes_bundle']:.2f}/bundle", ""),
    ]
    for _name, _price, _detail in _price_rows:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:7px 0;'
            f'border-bottom:1px solid #2d3748;">'
            f'<span style="color:#a0aec0;">{_name}</span>'
            f'<span style="color:#e0e0e0;font-weight:600;">{_price}'
            f'<span style="color:#8892a4;font-size:11px;margin-left:8px;">{_detail}</span>'
            f'</span></div>',
            unsafe_allow_html=True
        )

    st.markdown("")
    if st.button("↩ Reset to Ready Cable Defaults (12-1-2025)"):
        st.session_state.prices = dict(_DEFAULT_PRICES)
        _save_prices(st.session_state.prices)
        st.session_state["_prices_updated"] = True
        st.success("Prices reset to Ready Cable 12-1-2025 defaults.")
        st.rerun()


# ─────────────────────── TAB 4: CREW PLANNER ─────────────────────
with tab4:
    if "crew_members" not in st.session_state:
        st.session_state.crew_members = [
            {"name": "Foreman", "pay_type": "Hourly", "rate": 25.0, "hours": 8.0},
            {"name": "Laborer", "pay_type": "Hourly", "rate": 18.0, "hours": 8.0},
        ]

    _cp_left, _cp_right = st.columns([2, 3])

    # ═══════════════════════════════════════════════
    # LEFT COLUMN — INPUTS
    # ═══════════════════════════════════════════════
    with _cp_left:

        # ── A: Crew Members ──────────────────────────────────────────
        st.markdown('<div class="section-title">👷 Crew Members</div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;gap:4px;padding:0 2px;margin-bottom:2px;">'
            '<span style="color:#8892a4;font-size:10px;flex:3;">Name</span>'
            '<span style="color:#8892a4;font-size:10px;flex:2;">Type</span>'
            '<span style="color:#8892a4;font-size:10px;flex:2;">Rate&nbsp;($)</span>'
            '<span style="color:#8892a4;font-size:10px;flex:2;">Hrs/Day</span>'
            '<span style="flex:1;"></span>'
            '</div>', unsafe_allow_html=True
        )

        _to_remove = None
        for _ci, _cm in enumerate(st.session_state.crew_members):
            _ca, _cb, _cc, _cd, _ce = st.columns([3, 2, 2, 2, 1])
            st.session_state.crew_members[_ci]["name"] = _ca.text_input(
                "n", value=_cm["name"], placeholder=f"Worker {_ci+1}",
                key=f"cm_name_{_ci}", label_visibility="collapsed")
            _pt = _cb.selectbox(
                "t", ["Hourly", "Daily"],
                index=0 if _cm["pay_type"] == "Hourly" else 1,
                key=f"cm_type_{_ci}", label_visibility="collapsed")
            st.session_state.crew_members[_ci]["pay_type"] = _pt
            st.session_state.crew_members[_ci]["rate"] = _cc.number_input(
                "r", value=float(_cm["rate"]), min_value=0.0, step=1.0, format="%.2f",
                key=f"cm_rate_{_ci}", label_visibility="collapsed")
            if _pt == "Hourly":
                st.session_state.crew_members[_ci]["hours"] = _cd.number_input(
                    "h", value=float(_cm["hours"]), min_value=0.0, max_value=24.0, step=0.5,
                    key=f"cm_hrs_{_ci}", label_visibility="collapsed")
            else:
                _cd.markdown(
                    '<div style="color:#8892a4;font-size:11px;padding-top:10px;text-align:center;">flat</div>',
                    unsafe_allow_html=True)
                st.session_state.crew_members[_ci]["hours"] = 8.0
            if _ce.button("✕", key=f"cm_rem_{_ci}", help="Remove crew member"):
                _to_remove = _ci

        if _to_remove is not None:
            st.session_state.crew_members.pop(_to_remove)
            st.rerun()

        if st.button("➕ Add Crew Member", key="cp_add_crew"):
            st.session_state.crew_members.append(
                {"name": "", "pay_type": "Hourly", "rate": 18.0, "hours": 8.0})
            st.rerun()

        _daily_crew_cost = sum(
            (_m["rate"] * _m["hours"] if _m["pay_type"] == "Hourly" else _m["rate"])
            for _m in st.session_state.crew_members
        )
        st.markdown(
            f'<div style="background:#1c2333;border-left:4px solid #f0a500;padding:8px 14px;'
            f'margin:10px 0 4px 0;border-radius:0 4px 4px 0;">'
            f'<span style="color:#a0aec0;font-size:13px;">Daily Crew Cost: </span>'
            f'<span style="color:#f0a500;font-weight:800;font-size:18px;">${_daily_crew_cost:,.2f}</span>'
            f'</div>', unsafe_allow_html=True)

        st.markdown("---")

        # ── B: Production Settings ───────────────────────────────────
        st.markdown('<div class="section-title">⚙️ Production Settings</div>', unsafe_allow_html=True)

        # 1. Total Project SQFT — read-only from session_state
        _cp_sqft = float(st.session_state.get("total_sqft", 0.0))
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;align-items:center;'
            f'padding:10px 14px;background:#1c2333;border-radius:6px;margin-bottom:10px;">'
            f'<span style="color:#a0aec0;font-size:13px;">Total Project SQFT</span>'
            f'<span style="color:#e0e0e0;font-weight:700;font-size:16px;">{_cp_sqft:,.0f} sqft</span>'
            f'</div>', unsafe_allow_html=True)

        # 2. Crew Speed dropdown
        _speed_map = {
            "Slow Crew — 400 SQFT/day":        400.0,
            "Average Crew — 700 SQFT/day":      700.0,
            "Fast Crew — 1,000 SQFT/day":      1000.0,
            "Very Fast Crew — 1,500 SQFT/day": 1500.0,
            "Custom":                           None,
        }
        _speed_sel = st.selectbox("Crew Speed", list(_speed_map.keys()), index=1, key="cp_speed")
        if _speed_map[_speed_sel] is None:
            _prod_rate = float(st.number_input("Custom SQFT/day", min_value=1.0,
                                               value=700.0, step=50.0, key="cp_custom_rate"))
        else:
            _prod_rate = _speed_map[_speed_sel]

        # 3-5. Core calculations
        _days_req  = max(math.ceil(_cp_sqft / _prod_rate), 1) if _cp_sqft > 0 and _prod_rate > 0 else 1
        _labor_tot = _days_req * _daily_crew_cost
        _labor_psf = _labor_tot / _cp_sqft if _cp_sqft > 0 else 0.0

        for _lbl, _val, _col in [
            ("Estimated Days",       str(_days_req),         "#f0a500"),
            ("Estimated Labor Cost", f"${_labor_tot:,.2f}",  "#63b3ed"),
            ("Labor per SQFT",       f"${_labor_psf:.2f}",   "#68d391"),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:7px 12px;background:#1c2333;border-radius:6px;margin:3px 0;">'
                f'<span style="color:#a0aec0;font-size:13px;">{_lbl}</span>'
                f'<span style="color:{_col};font-weight:700;font-size:14px;">{_val}</span></div>',
                unsafe_allow_html=True)

        st.markdown("---")

        # ── C: Labor Budget Comparison ───────────────────────────────
        st.markdown('<div class="section-title">💰 Labor Budget Comparison</div>', unsafe_allow_html=True)

        _labor_budget    = float(st.session_state.get("labor_budget", 0.0))
        _actual_labor    = _labor_tot
        _labor_variance  = _labor_budget - _actual_labor
        _max_days_budget = math.floor(_labor_budget / _daily_crew_cost) if _daily_crew_cost > 0 else 0

        # Silently computed for charts
        _sale_price = float(st.session_state.get("total_bid",      0.0))
        _total_cost = float(st.session_state.get("direct_cost",    0.0))
        _exp_profit = _sale_price - _total_cost

        _lv_col = "#48bb78" if _labor_variance >= 0 else "#fc8181"
        _mb_col = ("#48bb78" if _max_days_budget > _days_req + 2
                   else "#f6e05e" if _max_days_budget >= _days_req else "#fc8181")

        for _lbl, _val, _col in [
            ("Labor Budget (Estimator)", f"${_labor_budget:,.2f}",    "#63b3ed"),
            ("Estimated Labor Cost",     f"${_actual_labor:,.2f}",    "#ed8936"),
            ("Difference",               f"${_labor_variance:+,.2f}", _lv_col),
            ("Max Days Within Budget",   f"{_max_days_budget} days",  _mb_col),
        ]:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:7px 12px;background:#1c2333;border-radius:6px;margin:3px 0;">'
                f'<span style="color:#a0aec0;font-size:13px;">{_lbl}</span>'
                f'<span style="color:{_col};font-weight:700;font-size:14px;">{_val}</span></div>',
                unsafe_allow_html=True)

        st.caption("These are planning estimates. Actual production may change because of "
                   "weather, access, demolition, inspection delays, base preparation, "
                   "concrete delivery, and crew efficiency.")

        # ── Feature 3: Profit Protection Summary ─────────────────────
        st.markdown("---")
        st.markdown('<div class="section-title">🛡️ Profit Protection Summary</div>',
                    unsafe_allow_html=True)
        _pps_rows = [
            ("Current Crew Cost",           f"${_daily_crew_cost:,.2f}/day"),
            ("Estimated Duration",          f"{_days_req} Days"),
            ("Maximum Days Allowed",        f"{_max_days_budget} Days"),
            ("Budget Remaining" if _labor_variance >= 0 else "Over Budget",
             f"${abs(_labor_variance):,.2f}"),
            ("Cost of One Additional Day",  f"${_daily_crew_cost:,.2f}"),
        ]
        for _pps_lbl, _pps_val in _pps_rows:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:6px 12px;background:#1c2333;border-radius:6px;margin:3px 0;">'
                f'<span style="color:#a0aec0;font-size:13px;">{_pps_lbl}</span>'
                f'<span style="color:#e0e0e0;font-weight:700;font-size:13px;">{_pps_val}</span>'
                f'</div>', unsafe_allow_html=True)
        if _labor_variance >= 0:
            st.success("🟢 PROFIT PROTECTED — Current labor plan is within budget.")
        else:
            st.error("🔴 PROFIT AT RISK — Current labor plan exceeds labor budget.")

        # ── Feature 4: Manager Quick Decision Box ────────────────────
        st.markdown("---")
        _dec_col = "#48bb78" if _labor_variance >= 0 else "#fc8181"
        _dec_msg = ("Project can be completed within labor budget."
                    if _labor_variance >= 0 else "Current labor plan exceeds budget.")
        _dec_rec = "Proceed." if _labor_variance >= 0 else "Revise labor budget or increase production rate."
        _dec_var_lbl = "Budget Remaining" if _labor_variance >= 0 else "Over Budget"
        st.markdown(
            f'<div style="background:#1c2333;border:1px solid {_dec_col};'
            f'border-radius:8px;padding:16px 18px;">'
            f'<div style="color:{_dec_col};font-weight:700;font-size:12px;'
            f'letter-spacing:1px;margin-bottom:10px;">📋 MANAGEMENT DECISION</div>'
            f'<div style="color:#e0e0e0;font-size:13px;line-height:1.9;">'
            f'{_dec_msg}<br>'
            f'Crew must maintain at least <b>{_prod_rate:,.0f} SQFT/day</b>.<br>'
            f'Maximum duration allowed: <b>{_max_days_budget} Days</b>.<br>'
            f'Current plan: <b>{_days_req} Days</b>.<br>'
            f'{_dec_var_lbl}: <b style="color:{_dec_col};">${abs(_labor_variance):,.2f}</b>.<br>'
            f'<span style="color:{_dec_col};font-weight:700;">Recommendation: {_dec_rec}</span>'
            f'</div></div>',
            unsafe_allow_html=True)

    # ═══════════════════════════════════════════════
    # RIGHT COLUMN — DASHBOARD
    # ═══════════════════════════════════════════════
    with _cp_right:

        # ── Feature 1: Labor Status Card ─────────────────────────────
        _on_budget = _labor_variance >= 0
        if _on_budget:
            _sc_bg     = "#0d2b1e"
            _sc_border = "#48bb78"
            _sc_icon   = "✅"
            _sc_title  = "LABOR PLAN ON BUDGET"
            _sc_sub    = "This crew plan protects the labor budget."
            _sc_rows   = [
                ("Labor Budget",          f"${_labor_budget:,.2f}"),
                ("Estimated Labor Cost",  f"${_actual_labor:,.2f}"),
                ("Budget Remaining",      f"${_labor_variance:,.2f}"),
                ("Estimated Duration",    f"{_days_req} Days"),
                ("Maximum Days Allowed",  f"{_max_days_budget} Days"),
            ]
            _sc_rule = f"Crew must finish in {_max_days_budget} days or less to protect labor budget."
        else:
            _sc_bg     = "#2b0d0d"
            _sc_border = "#fc8181"
            _sc_icon   = "🚨"
            _sc_title  = "LABOR PLAN OVER BUDGET"
            _sc_sub    = "This crew plan exceeds the labor budget."
            _sc_rows   = [
                ("Labor Budget",          f"${_labor_budget:,.2f}"),
                ("Estimated Labor Cost",  f"${_actual_labor:,.2f}"),
                ("Over Budget",           f"${abs(_labor_variance):,.2f}"),
                ("Estimated Duration",    f"{_days_req} Days"),
                ("Maximum Days Allowed",  f"{_max_days_budget} Days"),
            ]
            _sc_rule = "Crew must increase production or labor budget must be revised."

        _sc_rows_html = "".join(
            f'<div style="display:flex;justify-content:space-between;padding:7px 0;'
            f'border-bottom:1px solid {_sc_border}33;">'
            f'<span style="color:#a0aec0;font-size:13px;">{_l}</span>'
            f'<span style="color:#ffffff;font-weight:700;font-size:14px;">{_v}</span>'
            f'</div>'
            for _l, _v in _sc_rows
        )
        st.markdown(
            f'<div style="background:{_sc_bg};border:2px solid {_sc_border};'
            f'border-radius:10px;padding:20px 24px;margin-bottom:14px;">'
            f'<div style="color:{_sc_border};font-size:20px;font-weight:900;'
            f'letter-spacing:1px;margin-bottom:4px;">{_sc_icon} {_sc_title}</div>'
            f'<div style="color:#a0aec0;font-size:12px;margin-bottom:14px;">{_sc_sub}</div>'
            f'{_sc_rows_html}'
            f'<div style="margin-top:12px;padding:9px 14px;background:{_sc_border}22;'
            f'border-radius:6px;color:{_sc_border};font-size:12px;font-weight:600;">'
            f'📋 Field Rule: {_sc_rule}'
            f'</div></div>',
            unsafe_allow_html=True)

        # ── Feature 2: Download Labor Plan PDF ───────────────────────
        try:
            _lp_qnum = st.session_state.get("ci_qnum", "") or ""
            _lp_bytes = _build_labor_plan_pdf(
                job_name=job_name,
                quote_number=_lp_qnum,
                today_str=datetime.date.today().strftime("%B %d, %Y"),
                total_sqft=_cp_sqft,
                total_bid=float(st.session_state.get("total_bid",      0.0)),
                price_per_sqft=float(st.session_state.get("price_per_sqft", 0.0)),
                labor_budget=_labor_budget,
                materials_cost=float(st.session_state.get("materials_cost", 0.0)),
                equipment_cost=float(st.session_state.get("equipment_cost", 0.0)),
                overhead_cost=float(st.session_state.get("overhead_cost",   0.0)),
                profit_amount=float(st.session_state.get("profit_amount",   0.0)),
                speed_label=_speed_sel,
                daily_crew_cost=_daily_crew_cost,
                days_req=_days_req,
                actual_labor=_actual_labor,
                labor_psf=_labor_psf,
                labor_variance=_labor_variance,
                max_days_budget=_max_days_budget,
                on_budget=_on_budget,
                crew_members=list(st.session_state.crew_members),
            )
            _lp_name = (f"labor_plan_summary_{_lp_qnum.replace(' ', '_')}.pdf"
                        if _lp_qnum else "labor_plan_summary.pdf")
            st.download_button(
                label="📄 Download Labor Plan PDF",
                data=_lp_bytes,
                file_name=_lp_name,
                mime="application/pdf",
                key="download_labor_plan",
            )
        except Exception as _lp_err:
            st.error(f"Labor Plan PDF error: {_lp_err}")

        st.markdown("---")

        # ── KPI Cards ────────────────────────────────────────────────
        _kc1, _kc2, _kc3, _kc4 = st.columns(4)
        _kc1.metric("💼 Labor Budget",       f"${_labor_budget:,.0f}",
                    delta="from Estimator")
        _kc2.metric("🏗️ Actual Labor Cost",  f"${_actual_labor:,.0f}",
                    delta=f"{_days_req} days × ${_daily_crew_cost:,.0f}/day")
        _kc3.metric("📊 Labor Variance",     f"${_labor_variance:+,.0f}",
                    delta="under budget" if _labor_variance >= 0 else "over budget",
                    delta_color="normal" if _labor_variance >= 0 else "inverse")
        _kc4.metric("📅 Max Days Budget",    str(_max_days_budget),
                    delta="days within budget",
                    delta_color="normal" if _max_days_budget >= _days_req else "inverse")

        # ── Warning System ────────────────────────────────────────────
        if _labor_variance > _labor_budget * 0.10:
            st.success(f"✅ Crew cost is within labor budget. "
                       f"You have ${_labor_variance:,.2f} remaining.")
        elif _labor_variance >= 0:
            st.warning(f"⚠️ Crew cost is close to labor budget. "
                       f"Only ${_labor_variance:,.2f} remaining.")
        else:
            st.error(f"🚨 WARNING: Crew cost exceeds labor budget by ${abs(_labor_variance):,.2f}. "
                     f"Project loses money on labor.")

        # ── Charts row 1: Donut + Gauge ───────────────────────────────
        _ch1, _ch2 = st.columns(2)

        with _ch1:
            _mat_v    = float(st.session_state.get("materials_cost", 0.0))
            _eqp_v    = float(st.session_state.get("equipment_cost", 0.0))
            _ovh_v    = float(st.session_state.get("overhead_cost",  0.0))
            _bid_v    = float(st.session_state.get("total_bid",      0.0))
            _actual_labor = _days_req * _daily_crew_cost
            _profit_v = max(_bid_v - _mat_v - _eqp_v - _actual_labor - _ovh_v, 0)
            _lbl_all  = ["Materials", "Labor",        "Equipment", "Profit"]
            _val_all  = [_mat_v,      _actual_labor,  _eqp_v,     _profit_v]
            _clr_map  = {"Materials": "#4299e1", "Labor": "#ed8936",
                         "Equipment": "#9f7aea", "Profit": "#48bb78"}
            _pairs    = [(l, v) for l, v in zip(_lbl_all, _val_all) if v > 0]
            if _pairs:
                _pl, _pv = zip(*_pairs)
                fig_donut = go.Figure(go.Pie(
                    labels=list(_pl), values=list(_pv), hole=0.4,
                    marker_colors=[_clr_map[l] for l in _pl],
                    textinfo="label+percent", textfont_size=11,
                ))
                fig_donut.update_layout(
                    title=dict(text="Project Cost Breakdown", font_color="#e0e0e0", font_size=13),
                    paper_bgcolor="#0e1117", font_color="#e0e0e0",
                    showlegend=False, margin=dict(t=45, b=0, l=0, r=0), height=270,
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.info("Enter project data to see cost breakdown.")

        with _ch2:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=_prod_rate,
                title={"text": "Crew Efficiency<br>Rating", "font": {"color": "#e0e0e0", "size": 12}},
                gauge={
                    "axis": {"range": [0, 600], "tickcolor": "#8892a4",
                             "tickfont": {"color": "#8892a4", "size": 9}},
                    "bar":  {"color": "#63b3ed"},
                    "bgcolor": "#1c2333", "bordercolor": "#2d3748",
                    "steps": [
                        {"range": [0,   200], "color": "#7b1a1a"},
                        {"range": [200, 350], "color": "#6b4c00"},
                        {"range": [350, 500], "color": "#1a3a6b"},
                        {"range": [500, 600], "color": "#1a4d2e"},
                    ],
                    "threshold": {"line": {"color": "#f0a500", "width": 3},
                                  "thickness": 0.75, "value": 400},
                },
                number={"suffix": " sqft/d", "font": {"color": "#e0e0e0", "size": 20}},
            ))
            fig_gauge.update_layout(
                paper_bgcolor="#0e1117", font_color="#e0e0e0",
                margin=dict(t=10, b=0, l=10, r=10), height=270,
            )
            st.plotly_chart(fig_gauge, use_container_width=True)

        # ── Chart 2: Bar — Remaining Labor Budget by Day ─────────────
        _bar_end  = max(_max_days_budget, _days_req) + 3
        _bar_days = list(range(1, _bar_end + 1))
        _bar_rem  = [_labor_budget - _daily_crew_cost * d for d in _bar_days]
        _bar_cols = ["#48bb78" if r >= 0 else "#fc8181" for r in _bar_rem]
        fig_bar = go.Figure(go.Bar(
            x=[f"Day {d}" for d in _bar_days],
            y=_bar_rem,
            marker_color=_bar_cols,
            text=[f"${r:,.0f}" for r in _bar_rem],
            textposition="outside",
            textfont_size=10,
        ))
        fig_bar.add_hline(y=0, line_color="#fc8181", line_dash="dash", line_width=1.5)
        if _days_req <= _bar_end:
            fig_bar.add_vline(x=_days_req, line_color="#f0a500", line_dash="dot", line_width=1.5,
                              annotation_text=f"Target: Day {_days_req}",
                              annotation_font_color="#f0a500",
                              annotation_position="top right")
        fig_bar.update_layout(
            title=dict(text="Remaining Labor Budget by Day", font_color="#e0e0e0"),
            xaxis_title="Day", yaxis_title="Remaining Budget ($)",
            paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
            font_color="#e0e0e0", margin=dict(t=50, b=30, l=10, r=10), height=290,
            yaxis=dict(zeroline=False),
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # ── Chart 3: Line — Profitability Curve ──────────────────────
        _ln_total_bid  = float(st.session_state.get("total_bid",      0.0))
        _ln_mat        = float(st.session_state.get("materials_cost",  0.0))
        _ln_equip      = float(st.session_state.get("equipment_cost",  0.0))
        _ln_overhead   = float(st.session_state.get("overhead_cost",   0.0))
        _ln_days = list(range(1, _days_req + 6))
        _ln_prof = [_ln_total_bid - _ln_mat - _ln_equip - _ln_overhead - (_daily_crew_cost * d)
                    for d in _ln_days]
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=_ln_days, y=_ln_prof,
            mode="lines+markers",
            line=dict(color="#63b3ed", width=2),
            marker=dict(size=5, color="#63b3ed"),
            name="Profit",
            fill="tozeroy",
            fillcolor="rgba(99,179,237,0.1)",
        ))
        fig_line.add_hline(y=0, line_color="#fc8181", line_dash="dash", line_width=1.5,
                           annotation_text="Break-even",
                           annotation_font_color="#fc8181",
                           annotation_position="bottom left")
        fig_line.add_vline(x=_days_req, line_color="#48bb78", line_dash="dash", line_width=1.5,
                           annotation_text=f"Target: Day {_days_req}",
                           annotation_font_color="#48bb78",
                           annotation_position="top right")
        fig_line.update_layout(
            title=dict(text="Profitability Curve", font_color="#e0e0e0"),
            xaxis_title="Days", yaxis_title="Profit ($)",
            paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
            font_color="#e0e0e0", showlegend=False,
            margin=dict(t=50, b=30, l=10, r=10), height=290,
        )
        st.plotly_chart(fig_line, use_container_width=True)

        st.caption("All projections based on estimated production rates. Actual results may vary.")


# ─────────────────────── TAB 5: CONTRACT ANALYZER ────────────────────────
with tab5:

    st.markdown(
        '<div style="font-size:13px;font-weight:700;text-transform:uppercase;'
        'letter-spacing:2px;color:#f0a500;margin-bottom:4px;">GC Contract Analyzer</div>',
        unsafe_allow_html=True
    )
    st.caption(
        "Upload a GC contract PDF or G703 Excel. The app extracts scope and price. "
        "Enter your crew to see if you profit or lose money."
    )

    # ── Project Info ──────────────────────────────────────────────
    st.markdown('<div class="section-title">📋 Project Information</div>', unsafe_allow_html=True)
    _ca_pi1, _ca_pi2, _ca_pi3 = st.columns(3)
    ca_project_name = _ca_pi1.text_input("Project / Job Name",
                                          placeholder="e.g. Smith Driveway", key="ca_proj_name")
    ca_gc_name      = _ca_pi2.text_input("GC / Owner Name",
                                          placeholder="e.g. ABC Construction", key="ca_gc_name")
    ca_job_number   = _ca_pi3.text_input("Job Number",
                                          placeholder="e.g. 63724", key="ca_job_num")

    # ── Step 1: Upload PDF ────────────────────────────────────────
    st.markdown('<div class="section-title">📁 Step 1 — Upload GC Contract PDF or XLS</div>', unsafe_allow_html=True)
    st.caption("Supports: AIA G703 Continuation Sheet (.xls/.xlsx), generic contract PDFs. "
               "If auto-extract fails, enter numbers manually in Step 2.")

    _ca_col_up1, _ca_col_up2 = st.columns(2)
    with _ca_col_up1:
        contract_pdf = st.file_uploader("Upload Contract PDF", type=["pdf"], key="contract_pdf_upload")
    with _ca_col_up2:
        contract_xls = st.file_uploader("Upload G703 Excel (.xls/.xlsx)", type=["xls","xlsx"], key="contract_xls_upload")

    # ── Extracted values (editable) ──────────────────────────────
    if "ca_sqft" not in st.session_state:
        st.session_state["ca_sqft"]       = 0.0
        st.session_state["ca_total"]      = 0.0
        st.session_state["ca_ppsf"]       = 0.0
        st.session_state["ca_scope_text"] = ""
        st.session_state["ca_line_items"] = []
    # Initialize project info keys separately so they persist independently
    if "ca_proj_name" not in st.session_state:
        st.session_state["ca_proj_name"] = ""
    if "ca_gc_name" not in st.session_state:
        st.session_state["ca_gc_name"] = ""
    if "ca_job_num" not in st.session_state:
        st.session_state["ca_job_num"] = ""

    # ── G703 Excel Parser ─────────────────────────────────────────
    if contract_xls is not None:
        try:
            import xlrd as _xlrd
        except ImportError:
            import subprocess as _sp_xls
            _sp_xls.run(["pip", "install", "xlrd"], check=False)
            import xlrd as _xlrd

        try:
            _xls_raw = contract_xls.read()
            _wb      = _xlrd.open_workbook(file_contents=_xls_raw)
            _ws      = _wb.sheets()[0]

            # Detect header row — look for "SCHEDULED" or "VALUE" in any cell
            _header_row = None
            for _r in range(_ws.nrows):
                _row_vals = [str(_ws.cell_value(_r, _c)).upper() for _c in range(_ws.ncols)]
                if any("SCHEDULED" in v or "VALUE" in v for v in _row_vals):
                    _header_row = _r
                    break

            # G703: Description=col1, Scheduled Value=col3
            _item_col  = 1   # col1 = item number
            _desc_col  = 2   # col2 = description text
            _value_col = 3   # col3 = scheduled value
            _g703_items = []
            _g703_total = 0.0

            for _r in range(_ws.nrows):
                _item_num = _ws.cell_value(_r, _item_col)
                _desc = str(_ws.cell_value(_r, _desc_col)).strip() if _ws.ncols > _desc_col else ""
                try:
                    _val = float(_ws.cell_value(_r, _value_col)) if _ws.ncols > _value_col else 0.0
                except (ValueError, TypeError):
                    _val = 0.0
                if (isinstance(_item_num, float) and _item_num > 0
                        and _desc and _val > 0
                        and "TOTAL" not in _desc.upper()):
                    _g703_items.append({"description": _desc, "value": _val})
                    _g703_total += _val

            # Look for TOTAL row in col2
            for _r in range(_ws.nrows):
                _cell_desc = str(_ws.cell_value(_r, _desc_col)).strip().upper()
                if _cell_desc == "TOTAL":
                    try:
                        _tot_val = float(_ws.cell_value(_r, _value_col))
                        if _tot_val > 0:
                            _g703_total = _tot_val
                    except (ValueError, TypeError):
                        pass

            if _g703_items or _g703_total > 0:
                st.session_state["ca_total"]       = _g703_total
                st.session_state["ca_total_input"] = _g703_total
                st.session_state["ca_line_items"]  = _g703_items
                st.session_state["_ca_loaded"]     = True

                # Extract project info from G703 header
                # Row 4 Col 9 = Owner's Project No (project name)
                # Row 5 Col 9 = Job Number
                # Row 7 Col 5 = Contractor/GC name
                try:
                    _proj = str(_ws.cell_value(4, 9)).strip()
                    if _proj and _proj != "0.0":
                        st.session_state["ca_proj_name"] = _proj
                except Exception:
                    pass
                try:
                    _job = _ws.cell_value(5, 9)
                    if _job:
                        st.session_state["ca_job_num"] = str(int(_job)) if isinstance(_job, float) else str(_job).strip()
                except Exception:
                    pass
                try:
                    _gc = str(_ws.cell_value(7, 5)).strip()
                    if _gc and _gc != "0.0":
                        st.session_state["ca_gc_name"] = _gc
                except Exception:
                    pass

        except Exception as _xls_err:
            st.error(f"Could not read XLS: {_xls_err}")

    # Show G703 results from session state (persists after rerun)
    _ca_loaded_items = st.session_state.get("ca_line_items", [])
    _ca_loaded_total = st.session_state.get("ca_total", 0.0)
    if _ca_loaded_items:
        st.success(f"✅ G703 loaded — {len(_ca_loaded_items)} line items — Contract Total: **${_ca_loaded_total:,.2f}**")
        st.markdown('<div class="section-title">📋 G703 Line Items</div>', unsafe_allow_html=True)
        for _li in _ca_loaded_items:
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:7px 12px;'
                f'background:#1c2333;border-radius:6px;margin:2px 0;">'
                f'<span style="color:#e0e0e0;font-size:13px;">{_li["description"]}</span>'
                f'<span style="color:#f0a500;font-weight:700;font-size:13px;">${_li["value"]:,.2f}</span>'
                f'</div>', unsafe_allow_html=True
            )
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:9px 12px;'
            f'background:#252d3d;border-radius:6px;margin:4px 0;border-left:3px solid #f0a500;">'
            f'<span style="color:#f0a500;font-weight:700;">CONTRACT TOTAL</span>'
            f'<span style="color:#f0a500;font-weight:900;font-size:16px;">${_ca_loaded_total:,.2f}</span>'
            f'</div>', unsafe_allow_html=True
        )
    elif contract_xls is not None:
        st.warning("Could not find G703 line items. Verify the file is AIA G703 format.")

    # ── PDF Parser ────────────────────────────────────────────────
    if contract_pdf is not None:
        try:
            import pdfplumber as _pdfplumber_ca
        except ImportError:
            import subprocess as _sp_ca
            _sp_ca.run(["pip", "install", "pdfplumber"], check=False)
            import pdfplumber as _pdfplumber_ca

        try:
            _ca_raw  = contract_pdf.read()
            _ca_text = ""
            with _pdfplumber_ca.open(io.BytesIO(_ca_raw)) as _ca_pdf:
                for _ca_page in _ca_pdf.pages:
                    _ca_text += (_ca_page.extract_text() or "") + "\n"

            # Detect G703 in PDF
            _is_g703 = "G703" in _ca_text.upper() or "CONTINUATION SHEET" in _ca_text.upper() or "SCHEDULED VALUE" in _ca_text.upper()

            # Extract SQFT
            _sqft_found = None
            for _pat in [r'(\d[\d,]+)\s*(?:sq\.?\s*ft|square\s*feet|sqft)', r'(\d[\d,]+)\s*SF\b']:
                _m = re.search(_pat, _ca_text, re.IGNORECASE)
                if _m:
                    _sqft_found = float(_m.group(1).replace(",", ""))
                    break

            # Extract Total — G703 looks for TOTAL row value
            _total_found = None
            if _is_g703:
                for _pat in [
                    r'TOTAL[^\d\$]*\$?\s*([\d,]+(?:\.\d{2})?)',
                    r'CONTRACT\s*AMOUNT[^\d\$]*\$?\s*([\d,]+(?:\.\d{2})?)',
                ]:
                    _m = re.search(_pat, _ca_text, re.IGNORECASE)
                    if _m:
                        _val = float(_m.group(1).replace(",", ""))
                        if _val > 1000:
                            _total_found = _val
                            break
            else:
                for _pat in [
                    r'(?:total|contract\s*(?:amount|price|value)|lump\s*sum|bid\s*amount)[^\d\$]*\$?\s*([\d,]+(?:\.\d{2})?)',
                    r'\$\s*([\d,]+\.\d{2})',
                ]:
                    _m = re.search(_pat, _ca_text, re.IGNORECASE)
                    if _m:
                        _val = float(_m.group(1).replace(",", ""))
                        if _val > 1000:
                            _total_found = _val
                            break

            if _sqft_found:
                st.session_state["ca_sqft"] = _sqft_found
            if _total_found:
                st.session_state["ca_total"] = _total_found

            _scope_preview = _ca_text[:800].strip()
            st.session_state["ca_scope_text"] = _scope_preview

            _format_label = "AIA G703" if _is_g703 else "Generic Contract"
            if _sqft_found or _total_found:
                st.success(f"✅ {_format_label} detected — "
                           f"{'SQFT: ' + f'{_sqft_found:,.0f}' if _sqft_found else 'SQFT: not found'}  |  "
                           f"{'Total: $' + f'{_total_found:,.2f}' if _total_found else 'Total: not found'}")
            else:
                st.warning(f"{_format_label} detected but could not extract numbers. Enter manually below.")

        except Exception as _ca_err:
            st.error(f"Could not read PDF: {_ca_err}")

    # ── Step 2: Confirm / Enter Contract Numbers ──────────────────
    st.markdown('<div class="section-title">✏️ Step 2 — Confirm Contract Numbers</div>', unsafe_allow_html=True)
    st.caption("Review and correct values. These are what the GC is paying you.")

    # Sync session_state into widget keys so inputs show extracted values
    if st.session_state["ca_total"] > 0:
        st.session_state["ca_total_input"] = float(st.session_state["ca_total"])
    if st.session_state["ca_sqft"] > 0:
        st.session_state["ca_sqft_input"] = float(st.session_state["ca_sqft"])

    _ca_c1, _ca_c2 = st.columns(2)
    with _ca_c1:
        ca_sqft = st.number_input(
            "Contract Square Footage",
            min_value=0.0,
            value=float(st.session_state.get("ca_sqft_input", 0.0)),
            step=10.0,
            format="%.0f",
            key="ca_sqft_input",
        )
        ca_total = st.number_input(
            "Total Contract Amount ($)",
            min_value=0.0,
            value=float(st.session_state.get("ca_total_input", 0.0)),
            step=100.0,
            format="%.2f",
            key="ca_total_input",
        )
    with _ca_c2:
        ca_ppsf_calc = ca_total / ca_sqft if ca_sqft > 0 else 0.0
        st.markdown(
            f'<div style="background:#1c2333;border-left:4px solid #f0a500;padding:14px 18px;'
            f'border-radius:0 6px 6px 0;margin-top:28px;">'
            f'<div style="color:#a0aec0;font-size:11px;text-transform:uppercase;letter-spacing:1px;">GC is paying you</div>'
            f'<div style="color:#f0a500;font-weight:900;font-size:32px;">${ca_ppsf_calc:.2f}</div>'
            f'<div style="color:#8892a4;font-size:12px;">per square foot</div>'
            f'</div>',
            unsafe_allow_html=True
        )
    
    # If G703 was loaded, show total from line items and note
    _ca_line_items = st.session_state.get("ca_line_items", [])
    if _ca_line_items and ca_total == 0:
        _auto_total = sum(i["value"] for i in _ca_line_items)
        st.info(f"G703 line items total: **${_auto_total:,.2f}** — enter this in Total Contract Amount above.")


    # ── Step 3: Your Crew for this contract ──────────────────────
    st.markdown('<div class="section-title">👷 Step 3 — Your Crew for This Contract</div>', unsafe_allow_html=True)

    if "ca_crew" not in st.session_state:
        st.session_state["ca_crew"] = [
            {"name": "Foreman",  "pay_type": "Hourly", "rate": 25.0, "hours": 8.0},
            {"name": "Laborer",  "pay_type": "Hourly", "rate": 18.0, "hours": 8.0},
        ]

    st.markdown(
        '<div style="display:flex;gap:4px;padding:0 2px;margin-bottom:2px;">'
        '<span style="color:#8892a4;font-size:10px;flex:3;">Name</span>'
        '<span style="color:#8892a4;font-size:10px;flex:2;">Type</span>'
        '<span style="color:#8892a4;font-size:10px;flex:2;">Rate ($)</span>'
        '<span style="color:#8892a4;font-size:10px;flex:2;">Hrs/Day</span>'
        '<span style="flex:1;"></span>'
        '</div>', unsafe_allow_html=True
    )

    _ca_remove = None
    for _ci, _cm in enumerate(st.session_state["ca_crew"]):
        _ca_a, _ca_b, _ca_c, _ca_d, _ca_e = st.columns([3, 2, 2, 2, 1])
        st.session_state["ca_crew"][_ci]["name"] = _ca_a.text_input(
            "n", value=_cm["name"], placeholder=f"Worker {_ci+1}",
            key=f"ca_cm_name_{_ci}", label_visibility="collapsed")
        _ca_pt = _ca_b.selectbox("t", ["Hourly", "Daily"],
            index=0 if _cm["pay_type"] == "Hourly" else 1,
            key=f"ca_cm_type_{_ci}", label_visibility="collapsed")
        st.session_state["ca_crew"][_ci]["pay_type"] = _ca_pt
        st.session_state["ca_crew"][_ci]["rate"] = _ca_c.number_input(
            "r", value=float(_cm["rate"]), min_value=0.0, step=1.0, format="%.2f",
            key=f"ca_cm_rate_{_ci}", label_visibility="collapsed")
        if _ca_pt == "Hourly":
            st.session_state["ca_crew"][_ci]["hours"] = _ca_d.number_input(
                "h", value=float(_cm["hours"]), min_value=0.0, max_value=24.0, step=0.5,
                key=f"ca_cm_hrs_{_ci}", label_visibility="collapsed")
        else:
            _ca_d.markdown('<div style="color:#8892a4;font-size:11px;padding-top:10px;text-align:center;">flat</div>',
                           unsafe_allow_html=True)
            st.session_state["ca_crew"][_ci]["hours"] = 8.0
        if _ca_e.button("✕", key=f"ca_cm_rem_{_ci}"):
            _ca_remove = _ci

    if _ca_remove is not None:
        st.session_state["ca_crew"].pop(_ca_remove)
        st.rerun()

    if st.button("➕ Add Worker", key="ca_add_crew"):
        st.session_state["ca_crew"].append({"name": "", "pay_type": "Hourly", "rate": 18.0, "hours": 8.0})
        st.rerun()

    # Crew production speed
    _ca_speed_map = {
        "Slow — 400 SQFT/day":       400.0,
        "Average — 700 SQFT/day":    700.0,
        "Fast — 1,000 SQFT/day":    1000.0,
        "Very Fast — 1,500 SQFT/day":1500.0,
        "Custom":                     None,
    }
    _ca_speed_sel = st.selectbox("Crew Production Speed", list(_ca_speed_map.keys()),
                                  index=1, key="ca_speed")
    if _ca_speed_map[_ca_speed_sel] is None:
        _ca_prod_rate = float(st.number_input("Custom SQFT/day", min_value=1.0,
                                               value=700.0, step=50.0, key="ca_custom_rate"))
    else:
        _ca_prod_rate = _ca_speed_map[_ca_speed_sel]

    # Other costs
    _ca_oc1, _ca_oc2 = st.columns(2)
    with _ca_oc1:
        ca_materials_override = st.number_input(
            "Materials Cost ($) — leave 0 to auto-calculate",
            min_value=0.0, value=0.0, step=100.0, format="%.2f", key="ca_mat_override"
        )
        ca_equipment_cost = st.number_input(
            "Equipment Cost ($)",
            min_value=0.0, value=0.0, step=50.0, format="%.2f", key="ca_equip"
        )
    with _ca_oc2:
        ca_overhead_pct = st.number_input("Overhead %", min_value=0.0, max_value=50.0,
                                           value=15.0, step=0.5, key="ca_overhead")
        ca_other_costs  = st.number_input("Other Costs ($)", min_value=0.0, value=0.0,
                                           step=50.0, format="%.2f", key="ca_other")

    # ── Step 4: Analysis ─────────────────────────────────────────
    st.markdown("---")
    st.markdown('<div class="section-title">📊 Step 4 — Profitability Analysis</div>', unsafe_allow_html=True)

    if ca_total > 0:
        # Materials — use what user entered directly
        _ca_mat_cost = ca_materials_override if ca_materials_override > 0 else 0.0

        # Crew calcs
        _ca_daily_crew = sum(
            (m["rate"] * m["hours"] if m["pay_type"] == "Hourly" else m["rate"])
            for m in st.session_state["ca_crew"]
        )
        # Days: use sqft if available, otherwise ask user for days directly
        if ca_sqft > 0:
            _ca_days_req = max(math.ceil(ca_sqft / _ca_prod_rate), 1)
        else:
            _ca_days_req = st.number_input(
                "Estimated Days to Complete (no SQFT entered)",
                min_value=1, value=5, step=1, key="ca_days_manual"
            )
        _ca_labor_cost = _ca_daily_crew * _ca_days_req
        _ca_overhead   = (_ca_mat_cost + _ca_labor_cost + ca_equipment_cost) * (ca_overhead_pct / 100)
        _ca_total_cost = _ca_mat_cost + _ca_labor_cost + ca_equipment_cost + _ca_overhead + ca_other_costs
        _ca_profit     = ca_total - _ca_total_cost
        _ca_margin_pct = (_ca_profit / ca_total * 100) if ca_total > 0 else 0
        _ca_cost_psf   = _ca_total_cost / ca_sqft if ca_sqft > 0 else 0
        _ca_labor_psf  = _ca_labor_cost / ca_sqft if ca_sqft > 0 else 0

        _ca_win = _ca_profit > 0

        # ── Verdict Banner ────────────────────────────────────────
        _ca_verdict_bg     = "#0d2b1e" if _ca_win else "#2b0d0d"
        _ca_verdict_border = "#48bb78" if _ca_win else "#fc8181"
        _ca_verdict_icon   = "✅" if _ca_win else "🚨"
        _ca_verdict_title  = "YOU PROFIT ON THIS CONTRACT" if _ca_win else "YOU LOSE MONEY ON THIS CONTRACT"
        _ca_verdict_sub    = (f"You keep ${_ca_profit:,.2f} ({_ca_margin_pct:.1f}% margin)"
                              if _ca_win else
                              f"You lose ${abs(_ca_profit):,.2f} — do not accept at these numbers")

        st.markdown(
            f'<div style="background:{_ca_verdict_bg};border:2px solid {_ca_verdict_border};'
            f'border-radius:10px;padding:22px 28px;margin-bottom:20px;text-align:center;">'
            f'<div style="color:{_ca_verdict_border};font-size:26px;font-weight:900;'
            f'letter-spacing:1px;margin-bottom:6px;">{_ca_verdict_icon} {_ca_verdict_title}</div>'
            f'<div style="color:#ffffff;font-size:16px;">{_ca_verdict_sub}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Numbers Grid ──────────────────────────────────────────
        _ca_col1, _ca_col2 = st.columns(2)

        with _ca_col1:
            st.markdown('<div class="section-title">💵 Revenue</div>', unsafe_allow_html=True)
            for _lbl, _val, _col in [
                ("GC Contract Total",    f"${ca_total:,.2f}",         "#48bb78"),
                ("Price per SQFT",       f"${ca_ppsf_calc:.2f}",      "#48bb78"),
                ("Square Footage",       f"{ca_sqft:,.0f} SQFT",      "#e0e0e0"),
            ]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:8px 12px;'
                    f'background:#1c2333;border-radius:6px;margin:3px 0;">'
                    f'<span style="color:#a0aec0;font-size:13px;">{_lbl}</span>'
                    f'<span style="color:{_col};font-weight:700;font-size:14px;">{_val}</span>'
                    f'</div>', unsafe_allow_html=True
                )

            st.markdown('<div class="section-title">💸 Your Costs</div>', unsafe_allow_html=True)
            for _lbl, _val in [
                ("Materials Total",    f"${_ca_mat_cost:,.2f}"),
                ("Labor",              f"${_ca_labor_cost:,.2f}  ({_ca_days_req} days × ${_ca_daily_crew:,.2f}/day)"),
                ("Equipment",          f"${ca_equipment_cost:,.2f}"),
                ("Overhead",           f"${_ca_overhead:,.2f}  ({ca_overhead_pct:.0f}%)"),
                ("Other",              f"${ca_other_costs:,.2f}"),
                ("TOTAL COSTS",        f"${_ca_total_cost:,.2f}"),
            ]:
                _is_total = "TOTAL" in _lbl
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:8px 12px;'
                    f'background:{"#252d3d" if _is_total else "#1c2333"};'
                    f'border-radius:6px;margin:3px 0;'
                    f'{"border-left:3px solid #fc8181;" if _is_total else ""}">'
                    f'<span style="color:{"#e0e0e0" if _is_total else "#a0aec0"};'
                    f'font-size:13px;font-weight:{"700" if _is_total else "400"};">{_lbl}</span>'
                    f'<span style="color:{"#fc8181" if _is_total else "#e0e0e0"};'
                    f'font-weight:700;font-size:14px;">{_val}</span>'
                    f'</div>', unsafe_allow_html=True
                )

        with _ca_col2:
            st.markdown('<div class="section-title">📈 Bottom Line</div>', unsafe_allow_html=True)
            for _lbl, _val, _col in [
                ("Net Profit / Loss",     f"${_ca_profit:+,.2f}",    "#48bb78" if _ca_win else "#fc8181"),
                ("Profit Margin",         f"{_ca_margin_pct:.1f}%",  "#48bb78" if _ca_margin_pct > 10 else "#f6e05e" if _ca_margin_pct > 0 else "#fc8181"),
                ("Your Cost per SQFT",    f"${_ca_cost_psf:.2f}",    "#63b3ed"),
                ("GC Paying per SQFT",    f"${ca_ppsf_calc:.2f}",    "#63b3ed"),
                ("Labor per SQFT",        f"${_ca_labor_psf:.2f}",   "#ed8936"),
                ("Duration",              f"{_ca_days_req} days",     "#e0e0e0"),
                ("Daily Crew Cost",       f"${_ca_daily_crew:,.2f}", "#e0e0e0"),
            ]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:8px 12px;'
                    f'background:#1c2333;border-radius:6px;margin:3px 0;">'
                    f'<span style="color:#a0aec0;font-size:13px;">{_lbl}</span>'
                    f'<span style="color:{_col};font-weight:700;font-size:14px;">{_val}</span>'
                    f'</div>', unsafe_allow_html=True
                )

            # ── Decision Box ──────────────────────────────────────
            st.markdown("---")
            _ca_rec_col = "#48bb78" if _ca_win else "#fc8181"
            _ca_rec = (
                f"Accept this contract. You profit ${_ca_profit:,.2f} ({_ca_margin_pct:.1f}% margin). "
                f"Crew must maintain {_ca_prod_rate:,.0f} SQFT/day and finish in {_ca_days_req} days."
                if _ca_win else
                f"DO NOT accept at current terms. You lose ${abs(_ca_profit):,.2f}. "
                f"Negotiate a higher rate or reduce your costs before accepting."
            )
            st.markdown(
                f'<div style="background:#1c2333;border:1px solid {_ca_rec_col};'
                f'border-radius:8px;padding:16px 18px;">'
                f'<div style="color:{_ca_rec_col};font-weight:700;font-size:11px;'
                f'letter-spacing:1px;margin-bottom:8px;">📋 RECOMMENDATION</div>'
                f'<div style="color:#e0e0e0;font-size:13px;line-height:1.8;">{_ca_rec}</div>'
                f'</div>',
                unsafe_allow_html=True
            )

        # ── Profitability Chart ───────────────────────────────────
        st.markdown("---")
        _ca_days_range = list(range(1, _ca_days_req + 8))
        _ca_profit_curve = [ca_total - _ca_mat_cost - ca_equipment_cost - _ca_overhead - ca_other_costs - (_ca_daily_crew * d)
                             for d in _ca_days_range]
        fig_ca = go.Figure()
        fig_ca.add_trace(go.Scatter(
            x=_ca_days_range, y=_ca_profit_curve,
            mode="lines+markers",
            line=dict(color="#63b3ed", width=2),
            marker=dict(size=6, color="#63b3ed"),
            fill="tozeroy",
            fillcolor="rgba(99,179,237,0.10)",
            name="Profit"
        ))
        fig_ca.add_hline(y=0, line_color="#fc8181", line_dash="dash", line_width=1.5,
                          annotation_text="Break-even", annotation_font_color="#fc8181",
                          annotation_position="bottom left")
        fig_ca.add_vline(x=_ca_days_req, line_color="#48bb78", line_dash="dot", line_width=1.5,
                          annotation_text=f"Target: Day {_ca_days_req}",
                          annotation_font_color="#48bb78",
                          annotation_position="top right")
        fig_ca.update_layout(
            title=dict(text="Profit by Day — Contract Profitability Curve", font_color="#e0e0e0"),
            xaxis_title="Days on Job", yaxis_title="Net Profit ($)",
            paper_bgcolor="#0e1117", plot_bgcolor="#1c2333",
            font_color="#e0e0e0", showlegend=False,
            margin=dict(t=50, b=30, l=10, r=10), height=300,
        )
        st.plotly_chart(fig_ca, use_container_width=True)
        st.caption("Every day over target reduces profit. Stay on schedule.")

        # ── Download Contract Report PDF ──────────────────────────
        st.markdown("---")
        try:
            _cr_bytes = _build_contract_report_pdf(
                project_name   = st.session_state.get("ca_proj_name", ""),
                gc_name        = st.session_state.get("ca_gc_name", ""),
                job_number     = st.session_state.get("ca_job_num", ""),
                report_date    = datetime.date.today().strftime("%B %d, %Y"),
                ca_total       = ca_total,
                ca_sqft        = ca_sqft,
                ca_ppsf        = ca_ppsf_calc,
                line_items     = st.session_state.get("ca_line_items", []),
                mat_cost       = _ca_mat_cost,
                labor_cost     = _ca_labor_cost,
                equip_cost     = ca_equipment_cost,
                overhead_cost  = _ca_overhead,
                other_costs    = ca_other_costs,
                total_cost     = _ca_total_cost,
                profit         = _ca_profit,
                margin_pct     = _ca_margin_pct,
                days_req       = _ca_days_req,
                daily_crew_cost= _ca_daily_crew,
                crew_members   = list(st.session_state["ca_crew"]),
                on_budget      = _ca_win,
                overhead_pct   = ca_overhead_pct,
            )
            _cr_fname = (
                f"contract_report_{(st.session_state.get('ca_proj_name','job') or 'job').replace(' ','_')}.pdf"
            )
            st.download_button(
                label="📥 Download Contract Report PDF",
                data=_cr_bytes,
                file_name=_cr_fname,
                mime="application/pdf",
                key="download_contract_report",
            )
        except Exception as _cr_err:
            st.error(f"PDF generation error: {_cr_err}")

    else:
        st.info("Enter the Total Contract Amount in Step 2 to see the analysis.")
