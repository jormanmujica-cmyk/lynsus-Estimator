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
    company_name="LYNSUS CONTRACTING",
    tagline="Flatwork Concrete — Driveways · Sidewalks · Patios",
    scope_label="Flatwork Concrete Installation",
    logo_bytes=None,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
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

    # ── Header ────────────────────────────────────────────────────
    bill_parts = [x for x in [
        client_name if client_name and client_name != "—" else "",
        client_address or "",
        client_city_state_zip or "",
        " | ".join(x for x in [client_phone or "", client_email or ""] if x),
    ] if x.strip()]

    if logo_bytes:
        # Logo replaces the entire dark header — letterhead style
        try:
            from PIL import Image as PILImage
            _pil = PILImage.open(io.BytesIO(logo_bytes))
            _lw, _lh = _pil.size
            _render_h = _lh * (W / _lw)
            if _render_h > 1.8 * inch:
                _render_h = 1.8 * inch
                _render_w = _lw * (_render_h / _lh)
            else:
                _render_w = W
        except Exception:
            _render_w, _render_h = W * 0.5, inch
        _logo_img = Image(io.BytesIO(logo_bytes), width=_render_w, height=_render_h)
        _logo_img.hAlign = "CENTER"
        story.append(_logo_img)
        story.append(HRFlowable(width=W, thickness=1.5, color=GOLD, spaceAfter=6))
        _dt = Table(
            [[Paragraph(today_str, sty("dt2", fontSize=10, textColor=MUTED)),
              Paragraph(f"Quote #: {quote_number or 'LYN-2026-001'}",
                        sty("qn2", fontName="Helvetica-Bold", fontSize=11,
                            textColor=GOLD, alignment=TA_RIGHT))]],
            colWidths=[W * 0.55, W * 0.45]
        )
        _dt.setStyle(TableStyle([
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        story.append(_dt)
        story.append(Paragraph("BILL TO:", sty("bl2", fontName="Helvetica-Bold",
                                               fontSize=8, textColor=GOLD,
                                               leading=10, spaceBefore=8)))
        story.append(Paragraph("<br/>".join(bill_parts) if bill_parts else "—",
                               sty("bb2", fontSize=10, textColor=black, leading=17)))
        story.append(HRFlowable(width=W, thickness=0.5, color=RULE,
                                spaceBefore=8, spaceAfter=4))
        story.append(Paragraph(f"<b>JOB LOCATION:</b>  {job_location or '—'}",
                               sty("loc2", fontSize=9, textColor=SLATE, spaceAfter=4)))
        story.append(Spacer(1, 10))
    else:
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
            [Paragraph(company_name,
                       sty("co", fontName="Helvetica-Bold", fontSize=20,
                           textColor=GOLD, alignment=TA_CENTER, leading=24))],
            [Paragraph(tagline,
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

    rows = [prow(scope_label,
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
    company_name="LYNSUS CONTRACTING",
    logo_bytes=None,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
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
    if logo_bytes:
        try:
            from PIL import Image as PILImage
            _pil = PILImage.open(io.BytesIO(logo_bytes))
            _lw, _lh = _pil.size
            _max_w, _max_h = 1.5 * inch, 0.8 * inch
            _scale = min(_max_w / _lw, _max_h / _lh)
            _logo_w, _logo_h = _lw * _scale, _lh * _scale
        except Exception:
            _logo_w, _logo_h = 1.2 * inch, 0.65 * inch
        _logo_img = Image(io.BytesIO(logo_bytes), width=_logo_w, height=_logo_h)
        _logo_col_w = _logo_w + 24
        _name_col_w = W - _logo_col_w
        _brand_t = Table([
            [_logo_img, Paragraph(company_name, sty("co", fontName="Helvetica-Bold", fontSize=18,
                                  textColor=GOLD, alignment=TA_CENTER, leading=22))],
            ["",        Paragraph("CONTRACT PROFITABILITY REPORT", sty("sub", fontName="Helvetica-Bold",
                                  fontSize=12, textColor=LITE, alignment=TA_CENTER))],
            ["",        Paragraph("Internal Management Document — Owner Copy",
                                  sty("sub2", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
        ], colWidths=[_logo_col_w, _name_col_w])
        _brand_t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("SPAN",          (0, 0), (0,  -1)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        hdr = Table([[_brand_t]], colWidths=[W])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), DARK),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))
    else:
        hdr = Table([
            [Paragraph(company_name, sty("co", fontName="Helvetica-Bold", fontSize=20,
                       textColor=GOLD, alignment=TA_CENTER, leading=24))],
            [Paragraph("CONTRACT PROFITABILITY REPORT", sty("sub", fontName="Helvetica-Bold",
                       fontSize=12, textColor=LITE, alignment=TA_CENTER))],
            [Paragraph("Internal Management Document — Owner Copy",
                       sty("sub2", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
        ], colWidths=[W])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), DARK),
            ("LEFTPADDING",   (0, 0), (-1, -1), 16),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (0,  0),  20),
            ("TOPPADDING",    (0, 1), (-1, -1), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 20),
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
    company_name="LYNSUS CONTRACTING",
    logo_bytes=None,
):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, Image
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
    if logo_bytes:
        try:
            from PIL import Image as PILImage
            _pil = PILImage.open(io.BytesIO(logo_bytes))
            _lw, _lh = _pil.size
            _max_w, _max_h = 1.5 * inch, 0.8 * inch
            _scale = min(_max_w / _lw, _max_h / _lh)
            _logo_w, _logo_h = _lw * _scale, _lh * _scale
        except Exception:
            _logo_w, _logo_h = 1.2 * inch, 0.65 * inch
        _logo_img = Image(io.BytesIO(logo_bytes), width=_logo_w, height=_logo_h)
        _logo_col_w = _logo_w + 24
        _name_col_w = W - _logo_col_w
        _brand_t = Table([
            [_logo_img, Paragraph(company_name,
                        sty("co", fontName="Helvetica-Bold", fontSize=18,
                            textColor=GOLD, alignment=TA_CENTER, leading=22))],
            ["",        Paragraph("LABOR PLAN SUMMARY",
                        sty("t1", fontName="Helvetica-Bold", fontSize=13,
                            textColor=LITE, alignment=TA_CENTER))],
            ["",        Paragraph("Crew Planner — Internal Management Report",
                        sty("t2", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
            ["",        Paragraph(
                        f"Project: {job_name or '—'}  ·  Quote: {quote_number or '—'}  ·  {today_str}",
                        sty("hd", fontSize=9, textColor=SLATE, alignment=TA_CENTER))],
        ], colWidths=[_logo_col_w, _name_col_w])
        _brand_t.setStyle(TableStyle([
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("SPAN",          (0, 0), (0,  -1)),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        hdr = Table([[_brand_t]], colWidths=[W])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), DARK),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
            ("TOPPADDING",    (0, 0), (-1, -1), 16),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ]))
    else:
        hdr = Table([
            [Paragraph(company_name,
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


st.set_page_config(page_title="LYNSUS SUITE", page_icon="🏗️", layout="wide")

# ── Session state defaults (initialize all critical keys once) ──
_DEFAULTS = {
    "total_bid": 0.0, "materials_cost": 0.0, "labor_cost": 0.0,
    "labor_budget": 0.0, "equipment_cost": 0.0, "subcontractor_cost": 0.0,
    "direct_cost": 0.0, "overhead_cost": 0.0, "profit_amount": 0.0,
    "price_per_sqft": 0.0, "total_sqft": 0.0,
    "concrete_yards": 0.0, "concrete_price": 0.0,
    "ovh_calc_suggested": 0.0, "active_tab": 0, "current_trade": "",
    "generic_materials": [], "generic_trade_last": None,
    "generic_equipment": [{"name": "", "cost": 0.0}],
    "generic_subs": [], "trade_selection": "Concrete / Flatwork",
    # concrete sidebar widget keys
    "c_zone_setup": "Single Thickness (whole job same thickness)",
    "c_sqft": 0.0, "c_thick": 4, "c_waste_pct": 0.0,
    "c_conc_psi": 3000, "c_dw_width": 0.0, "c_sw_width": 0.0,
    "c_form_type": "Sidewalk / Patio",
    "c_use_rebar": False, "c_rebar_type": "#4", "c_rebar_spacing": '12" O.C.', "c_rebar_waste": 0.0,
    "c_use_base": False, "c_base_type": "Crushed Concrete",
    "c_base_sqft": 0.0, "c_base_thick": 6, "c_base_price_ton": 0.0, "c_base_price_truck": 0.0,
    "c_stakes_per_bundle": 25,
    "c_labor_method": "By Square Foot", "c_labor_rate": 0.0, "c_labor_flat": 0.0,
    "c_use_demo": False, "c_demo_rate": 0.0,
    "c_overhead_pct": 0.0, "c_profit_pct": 0.0,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

st.markdown("""
<style>
/* ═══════════════════════════════════════════════════════
   LYNSUS SUITE — CLEAN LIGHT THEME 2026
   UI styling only. No formulas or logic changed.
   ═══════════════════════════════════════════════════════ */

/* ── Global ───────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
    background-color: #f0f4f8 !important;
    color: #1a202c !important;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif !important;
}
[data-testid="stAppViewContainer"] > section {
    background-color: #f0f4f8 !important;
}

/* ── Sidebar ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] h3 {
    color: #1d4ed8 !important;
    font-size: 11px !important;
    font-weight: 700 !important;
    letter-spacing: 2.5px !important;
    text-transform: uppercase !important;
    padding-bottom: 8px !important;
    border-bottom: 2px solid #1d4ed8 !important;
    margin: 20px 0 14px 0 !important;
}

/* ── Header ───────────────────────────────────────────── */
.header {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-bottom: 3px solid #1d4ed8;
    padding: 20px 32px;
    margin-bottom: 24px;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(29,78,216,0.07);
    position: relative;
    overflow: hidden;
}
.header::before {
    content: "";
    position: absolute;
    top: -80px; right: -80px;
    width: 260px; height: 260px;
    background: radial-gradient(circle, rgba(29,78,216,0.05) 0%, transparent 70%);
    pointer-events: none;
}
.header h1 {
    color: #1d4ed8;
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 3px;
    margin: 0;
}
.header p {
    color: #64748b;
    margin: 5px 0 0 0;
    font-size: 12px;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── Section Titles ───────────────────────────────────── */
.section-title {
    display: flex;
    align-items: center;
    background: linear-gradient(90deg, rgba(29,78,216,0.07) 0%, transparent 80%);
    border-left: 3px solid #1d4ed8;
    padding: 8px 16px;
    color: #1d4ed8;
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
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin: 4px 0;
    transition: background 0.15s ease, border-color 0.15s ease;
}
.line-item:hover {
    background: #f8fafc;
    border-color: #1d4ed8;
}
.line-item .name  { color: #1a202c; font-size: 13.5px; }
.line-item .qty   { color: #64748b; font-size: 12px; margin: 0 auto 0 12px; }
.line-item .price { color: #1d4ed8; font-weight: 700; font-size: 14px; }

/* ── Subtotal Rows ────────────────────────────────────── */
.subtotal-row {
    display: flex;
    justify-content: space-between;
    padding: 9px 16px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    margin: 3px 0;
    font-size: 13px;
}

/* ── Result Rows ──────────────────────────────────────── */
.result-row {
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid #e2e8f0;
    font-size: 14px;
}
.result-row:last-child { border-bottom: none; }

/* ── Total Box ────────────────────────────────────────── */
.total-box {
    background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
    border: 2px solid #1d4ed8;
    border-radius: 16px;
    padding: 28px;
    text-align: center;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(29,78,216,0.10);
}
.total-amount {
    color: #1d4ed8;
    font-size: 48px;
    font-weight: 900;
    margin: 8px 0;
    letter-spacing: -1px;
}
.total-sqft { color: #64748b; font-size: 14px; letter-spacing: 1px; }

/* ── Buttons ──────────────────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.3px !important;
    border: none !important;
    border-radius: 8px !important;
    width: 100%;
    box-shadow: 0 2px 12px rgba(29,78,216,0.20) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(29,78,216,0.35) !important;
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
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 16px 18px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="metric-container"]:hover,
[data-testid="stMetric"]:hover {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 20px rgba(29,78,216,0.08) !important;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 800 !important;
    color: #1a202c !important;
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
    background: #ffffff !important;
    border-radius: 12px !important;
    padding: 4px 6px !important;
    border: 1px solid #e2e8f0 !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 8px !important;
    color: #64748b !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    letter-spacing: 0.2px !important;
    padding: 8px 22px !important;
    border: none !important;
    transition: background 0.15s ease, color 0.15s ease !important;
}
[data-testid="stTabs"] [data-baseweb="tab"]:hover {
    background: #f0f4f8 !important;
    color: #1d4ed8 !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(29,78,216,0.12) 0%, rgba(29,78,216,0.06) 100%) !important;
    color: #1d4ed8 !important;
    box-shadow: 0 0 0 1px rgba(29,78,216,0.25) !important;
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
    background: #ffffff !important;
    border: 1px solid #cbd5e0 !important;
    border-radius: 6px !important;
    color: #1a202c !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
input:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 0 3px rgba(29,78,216,0.10) !important;
    outline: none !important;
}

/* ── Selectbox ────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: #ffffff !important;
    border: 1px solid #cbd5e0 !important;
    border-radius: 6px !important;
}

/* ── Caption & Small Text ─────────────────────────────── */
.stCaption, [data-testid="stCaptionContainer"] {
    color: #94a3b8 !important;
    font-size: 11.5px !important;
}

/* ── Dividers ─────────────────────────────────────────── */
hr { border-color: #e2e8f0 !important; margin: 16px 0 !important; }

/* ── Scrollbar ────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #f0f4f8; }
::-webkit-scrollbar-thumb {
    background: #cbd5e0;
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover { background: #1d4ed8; }

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
    background: #ffffff !important;
    border: none !important;
    border-bottom: 2px solid #1d4ed8 !important;
    padding: 10px 4px !important;
    margin-bottom: 8px !important;
    border-radius: 0 !important;
    box-shadow: none !important;
}
.header::before { display: none !important; }
.header h1 {
    color: #1d4ed8 !important;
    font-size: 13px !important;
    font-weight: 700 !important;
    letter-spacing: 3.5px !important;
    margin: 0 !important;
}
.header p { display: none !important; }

/* ── Hero Banner ──────────────────────────────────────── */
.hero-banner {
    width: 100%;
    min-height: 100px;
    border-radius: 24px;
    background-color: #1e3a8a;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    box-shadow: 0 8px 40px rgba(29,78,216,0.20);
    margin-bottom: 28px;
    overflow: hidden;
    position: relative;
}
.hero-banner::after {
    content: "";
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #1d4ed8 0%, rgba(29,78,216,0.25) 55%, transparent 100%);
    pointer-events: none;
}
.hero-overlay {
    min-height: 100px;
    background: linear-gradient(90deg,
        rgba(15,23,42,0.90) 0%,
        rgba(15,23,42,0.60) 50%,
        rgba(15,23,42,0.20) 100%);
    padding: 48px 56px;
    display: flex;
    align-items: center;
    border-radius: 24px;
}
.hero-content { max-width: 580px; }
.hero-badge {
    display: inline-block;
    background: rgba(29,78,216,0.15);
    border: 1px solid rgba(29,78,216,0.40);
    color: #93c5fd;
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
    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
    color: #ffffff !important;
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
    box-shadow: 0 6px 36px rgba(29,78,216,0.40);
    color: #ffffff !important;
    text-decoration: none !important;
}

/* ── Hero gradient fallback (no image) ────────────────── */
.hero-banner.hero-no-image {
    background: linear-gradient(135deg,
        #1e3a8a 0%,
        #1d4ed8 40%,
        #1e3a8a 100%) !important;
}

/* ── Hero responsive ──────────────────────────────────── */
@media (max-width: 768px) {
    .hero-banner, .hero-overlay { min-height: 200px !important; }
    .hero-overlay { padding: 24px 20px !important; }
    .hero-headline { font-size: 22px !important; letter-spacing: -0.5px !important; margin-bottom: 8px !important; }
    .hero-subtitle { font-size: 13px !important; margin-bottom: 16px !important; display: none !important; }
    .hero-badge { display: none !important; }
    .hero-cta { padding: 10px 20px; font-size: 13px; }
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
    color: #1a202c !important;
    background-color: #ffffff !important;
}
section[data-testid="stMain"] input {
    color: #1a202c !important;
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
.stFileUploader label { color: #1a202c !important; }
.stFileUploader div   { color: #1a202c !important; }
.stFileUploader span  { color: #1a202c !important; }
[data-testid="stFileUploader"] { color: #1a202c !important; }
[data-testid="stFileUploadDropzone"] {
    background-color: #eff6ff !important;
    border: 2px dashed #1d4ed8 !important;
    color: #1a202c !important;
}
[data-testid="stFileUploadDropzone"] span { color: #1a202c !important; }

/* ── Input labels everywhere ──────────────────────────────── */
label { color: #1a202c !important; }
.stTextInput label { color: #1a202c !important; }
.stDateInput label { color: #1a202c !important; }
section[data-testid="stMain"] label { color: #1a202c !important; }

/* ── File uploader button ─────────────────────────────────── */
[data-testid="stFileUploaderDropzoneInstructions"] { color: #1a202c !important; }
[data-testid="baseButton-secondary"] {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
    border: none !important;
}
.stFileUploader > div > div {
    background-color: #eff6ff !important;
    border: 2px dashed #1d4ed8 !important;
}
.stFileUploader > div > div > div { color: #1a202c !important; }
.stFileUploader button {
    background-color: #1d4ed8 !important;
    color: #ffffff !important;
    font-weight: bold !important;
}
.stFileUploader * { color: #1a202c !important; }
.stFileUploader button * { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)

# ── Header config (editable per client) ──────────────
if "header_company_name" not in st.session_state:
    st.session_state["header_company_name"] = "LYNSUS"
if "header_sub" not in st.session_state:
    st.session_state["header_sub"] = "Suite"
if "header_bg_image" not in st.session_state:
    st.session_state["header_bg_image"] = None
if "pdf_company_name" not in st.session_state:
    st.session_state["pdf_company_name"] = "LYNSUS CONTRACTING"
if "pdf_tagline" not in st.session_state:
    st.session_state["pdf_tagline"] = "Flatwork Concrete — Driveways · Sidewalks · Patios"
if "pdf_scope_label" not in st.session_state:
    st.session_state["pdf_scope_label"] = "Flatwork Concrete Installation"
if "pdf_logo_bytes" not in st.session_state:
    st.session_state["pdf_logo_bytes"] = None
if "ovh_calc_suggested" not in st.session_state:
    st.session_state["ovh_calc_suggested"] = 0.0

TRADE_MATERIALS = {
    "Concrete / Flatwork":   [],
    "Framing":               ["Lumber 2x4 (LF)", "Lumber 2x6 (LF)", "OSB Sheathing (Sheet)", "LVL Beam (LF)", "Joist Hanger (Unit)", "Structural Screws (Box)", "Hurricane Strap (Unit)", "Blocking (LF)"],
    "Tile / Flooring":       ["Tile (SQFT)", "Mortar (Bag)", "Grout (Bag)", "Backer Board (Sheet)", "Tile Spacers (Unit)", "Transition Strip (LF)", "Waterproof Membrane (SQFT)"],
    "Pool / Piscina":        ["Gunite/Shotcrete (CY)", "Rebar #4 (LF)", "Plaster (Bag)", "Coping Stone (LF)", "PVC Pipe (LF)", "Pool Light (Unit)", "Skimmer (Unit)", "Main Drain (Unit)"],
    "Metal Building":        ["Steel Panel (SQFT)", "Purlin (LF)", "Girt (LF)", "Anchor Bolt (Unit)", "Trim (LF)", "Sealant (Tube)", "Insulation (SQFT)", "Sliding Door (Unit)"],
    "Cleaning Services":     ["Cleaning Solution (Gallon)", "Degreaser (Gallon)", "Pressure Wash (Hour)", "Protective Coating (Gallon)", "PPE / Safety Equipment (Unit)", "Water Supply (Unit)"],
    "Sheetrock / Drywall":   ["Drywall Sheet 4x8 (Sheet)", "Joint Compound (Bucket)", "Mesh Tape (Roll)", "Paper Tape (Roll)", "Corner Bead (LF)", "Drywall Screws (Box)", "Sanding Sponge (Unit)"],
    "Carpentry / Trim":      ["Baseboard (LF)", "Door Casing (LF)", "Crown Molding (LF)", "Chair Rail (LF)", "Finish Nails (Box)", "Wood Glue (Unit)", "Caulk (Tube)", "Wood Filler (Unit)"],
    "Painting / Pintura":    ["Paint (Gallon)", "Primer (Gallon)", "Painter Tape (Roll)", "Roller Cover (Unit)", "Roller Frame (Unit)", "Paint Brush (Unit)", "Drop Cloth (Unit)", "Caulk (Tube)"],
    "Roofing":               ["Shingles (Square)", "Roofing Felt (Roll)", "Roofing Nails (Box)", "Ridge Cap (Bundle)", "Drip Edge (LF)", "Ice & Water Shield (SQFT)", "Roof Deck (Sheet)"],
    "Plumbing":              ["PVC Pipe (LF)", "Copper Pipe (LF)", "Fittings (Unit)", "Ball Valve (Unit)", "Wax Ring (Unit)", "Solder (Roll)", "Flux (Unit)", "Teflon Tape (Roll)"],
    "Electrical":            ["Wire 12/2 (LF)", "Wire 14/2 (LF)", "Outlet (Unit)", "Switch (Unit)", "Breaker (Unit)", "Junction Box (Unit)", "Conduit (LF)", "Wire Nuts (Box)"],
    "HVAC":                  ["Duct (LF)", "Register (Unit)", "Flex Duct (LF)", "Insulation Wrap (LF)", "Refrigerant (Lb)", "Filter (Unit)", "Thermostat (Unit)", "Plenum (Unit)"],
    "Landscaping":           ["Sod (SQFT)", "Mulch (CY)", "Topsoil (CY)", "Plants (Unit)", "Edging (LF)", "Irrigation Pipe (LF)", "Sprinkler Head (Unit)", "Fertilizer (Bag)"],
    "Fencing":               ["Post (Unit)", "Rail (LF)", "Panel/Picket (Unit)", "Concrete (Bag)", "Post Cap (Unit)", "Gate (Unit)", "Hardware/Hinges (Unit)", "Gravel (Bag)"],
    "Demolition":            ["Dumpster Rental (Unit)", "Disposal Fee (Unit)", "PPE (Unit)", "Saw Blade (Unit)", "Sledgehammer (Unit)"],
    "Insulation":            ["Batt Insulation (Roll)", "Spray Foam (Can)", "Rigid Board (Sheet)", "Vapor Barrier (SQFT)", "Staples (Box)", "Tape (Roll)"],
    "Waterproofing":         ["Membrane (SQFT)", "Primer (Gallon)", "Sealant (Tube)", "Drain Mat (SQFT)", "Hydraulic Cement (Bag)", "Crack Filler (Tube)"],
    "Epoxy / Coating":       ["Epoxy Part A (Gallon)", "Epoxy Part B (Gallon)", "Flake/Chip (Lb)", "Top Coat (Gallon)", "Etching Solution (Gallon)", "Roller (Unit)"],
    "Other / Custom":        [],
}
if "generic_materials" not in st.session_state:
    st.session_state["generic_materials"] = []
if "generic_trade_last" not in st.session_state:
    st.session_state["generic_trade_last"] = None
if "generic_equipment" not in st.session_state:
    st.session_state["generic_equipment"] = [{"name": "", "cost": 0.0}]
if "generic_subs" not in st.session_state:
    st.session_state["generic_subs"] = []
if "trade_selection" not in st.session_state:
    st.session_state["trade_selection"] = "Concrete / Flatwork"
if "subcontractor_cost" not in st.session_state:
    st.session_state["subcontractor_cost"] = 0.0

with st.expander("⚙️ Customize Header", expanded=False):
    _col_name, _col_sub = st.columns(2)
    with _col_name:
        _hdr_name_val = st.text_input(
            "Company Name", value=st.session_state["header_company_name"], key="hdr_name_input"
        )
        st.session_state["header_company_name"] = _hdr_name_val
    with _col_sub:
        _hdr_sub_val = st.text_input(
            "Subtitle (under name)", value=st.session_state["header_sub"], key="hdr_sub_input"
        )
        st.session_state["header_sub"] = _hdr_sub_val
    _bg_file = st.file_uploader(
        "Background Image (JPG / PNG)", type=["jpg", "jpeg", "png"], key="hdr_bg_upload"
    )
    if _bg_file is not None:
        _bg_bytes = _bg_file.read()
        _bg_mime  = "image/png" if _bg_file.name.lower().endswith(".png") else "image/jpeg"
        st.session_state["header_bg_image"] = (
            f"data:{_bg_mime};base64,{base64.b64encode(_bg_bytes).decode()}"
        )
    if st.session_state["header_bg_image"] is not None:
        if st.button("Remove Background Image", key="hdr_rm_bg"):
            st.session_state["header_bg_image"] = None
            st.rerun()
    st.markdown("---")
    st.markdown("**📄 PDF / Quote Info**")
    _pdf_col1, _pdf_col2 = st.columns(2)
    with _pdf_col1:
        st.session_state["pdf_company_name"] = st.text_input(
            "Company Name (PDF header)",
            value=st.session_state["pdf_company_name"],
            key="pdf_company_input"
        )
    with _pdf_col2:
        st.session_state["pdf_tagline"] = st.text_input(
            "Tagline (PDF subheader)",
            value=st.session_state["pdf_tagline"],
            key="pdf_tagline_input"
        )
    st.session_state["pdf_scope_label"] = st.text_input(
        "Scope of Work Label (line item name in quote)",
        value=st.session_state["pdf_scope_label"],
        key="pdf_scope_input"
    )
    _logo_file = st.file_uploader(
        "Company Logo (PDF header)", type=["jpg", "jpeg", "png"], key="pdf_logo_upload"
    )
    if _logo_file is not None:
        st.session_state["pdf_logo_bytes"] = _logo_file.read()
    if st.session_state["pdf_logo_bytes"] is not None:
        st.image(st.session_state["pdf_logo_bytes"], width=160)
        if st.button("Remove Logo", key="pdf_rm_logo"):
            st.session_state["pdf_logo_bytes"] = None
            st.rerun()

_hdr_bg_style = (
    f'background-image: url("{st.session_state["header_bg_image"]}"); '
    f'background-size: cover; background-position: center;'
    if st.session_state["header_bg_image"]
    else "background: #1e3a8a;"
)
_hdr_company = st.session_state["header_company_name"] or "LYNSUS"
_hdr_sub     = st.session_state["header_sub"] or "Suite"

st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@700&display=swap" rel="stylesheet">
<style>
.ls-header {{
    border-radius: 14px;
    padding: 18px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
}}
.ls-header-overlay {{
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg,
        rgba(15,23,42,0.88) 0%,
        rgba(15,23,42,0.55) 55%,
        rgba(15,23,42,0.20) 100%);
    border-radius: 14px;
    pointer-events: none;
}}
.ls-header-content {{
    position: relative;
    z-index: 1;
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
}}
.ls-logo-name {{
    font-family: 'Rajdhani', sans-serif;
    font-size: 30px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 6px;
    line-height: 1;
    margin: 0;
}}
.ls-logo-sub {{
    color: #93c5fd;
    font-size: 10px;
    letter-spacing: 3px;
    margin-top: 4px;
    text-transform: uppercase;
}}
.ls-divider {{
    width: 2px; height: 36px;
    background: rgba(255,255,255,0.15);
    border-radius: 2px;
    margin: 0 18px;
}}
.ls-tagline {{
    color: #bfdbfe;
    font-size: 12px;
    line-height: 1.8;
    letter-spacing: 0.5px;
}}
.ls-badge {{
    color: #93c5fd;
    font-size: 11px;
    letter-spacing: 1px;
}}
.ls-features {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 20px;
}}
.ls-feat {{
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 14px 8px;
    text-align: center;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
.ls-feat:hover {{
    border-color: #1d4ed8;
    box-shadow: 0 2px 12px rgba(29,78,216,0.08);
}}
.ls-feat-icon {{
    width: 38px; height: 38px;
    border-radius: 9px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 8px;
    font-size: 19px;
}}
.ls-feat-abbr {{
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 3px;
}}
.ls-feat-name {{
    font-size: 12px;
    font-weight: 600;
    color: #1a202c;
    margin-bottom: 3px;
}}
.ls-feat-desc {{
    font-size: 10px;
    color: #64748b;
    line-height: 1.4;
}}
.ls-tab-badge {{
    display: inline-block;
    font-size: 9px;
    padding: 2px 7px;
    border-radius: 20px;
    margin-top: 5px;
    font-weight: 600;
}}
@media (max-width: 768px) {{
    .ls-features {{ grid-template-columns: repeat(3, 1fr); }}
    .ls-header {{ flex-direction: column; gap: 10px; text-align: center; }}
    .ls-divider {{ display: none; }}
    .ls-logo-name {{ font-size: 22px; }}
}}
/* ── Nav card buttons ── */
div[data-testid="stColumn"] button {{
    border-radius: 12px !important;
    min-height: 66px !important;
    font-size: 12px !important;
    line-height: 1.5 !important;
    white-space: pre-line !important;
    padding: 10px 8px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}}
div[data-testid="stColumn"] button[kind="secondary"] {{
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    color: #1a202c !important;
}}
div[data-testid="stColumn"] button[kind="secondary"]:hover {{
    border-color: #1d4ed8 !important;
    box-shadow: 0 2px 12px rgba(29,78,216,0.08) !important;
}}
</style>

<div class="ls-header" style="{_hdr_bg_style}">
  <div class="ls-header-overlay"></div>
  <div class="ls-header-content">
    <div style="display:flex; align-items:center;">
      <img src="data:image/png;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/4gHYSUNDX1BST0ZJTEUAAQEAAAHIAAAAAAQwAABtbnRyUkdCIFhZWiAH4AABAAEAAAAAAABhY3NwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAA9tYAAQAAAADTLQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAlkZXNjAAAA8AAAACRyWFlaAAABFAAAABRnWFlaAAABKAAAABRiWFlaAAABPAAAABR3dHB0AAABUAAAABRyVFJDAAABZAAAAChnVFJDAAABZAAAAChiVFJDAAABZAAAAChjcHJ0AAABjAAAADxtbHVjAAAAAAAAAAEAAAAMZW5VUwAAAAgAAAAcAHMAUgBHAEJYWVogAAAAAAAAb6IAADj1AAADkFhZWiAAAAAAAABimQAAt4UAABjaWFlaIAAAAAAAACSgAAAPhAAAts9YWVogAAAAAAAA9tYAAQAAAADTLXBhcmEAAAAAAAQAAAACZmYAAPKnAAANWQAAE9AAAApbAAAAAAAAAABtbHVjAAAAAAAAAAEAAAAMZW5VUwAAACAAAAAcAEcAbwBvAGcAbABlACAASQBuAGMALgAgADIAMAAxADb/2wBDAAUDBAQEAwUEBAQFBQUGBwwIBwcHBw8LCwkMEQ8SEhEPERETFhwXExQaFRERGCEYGh0dHx8fExciJCIeJBweHx7/2wBDAQUFBQcGBw4ICA4eFBEUHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh7/wAARCAQ4BDgDASIAAhEBAxEB/8QAHQABAAICAwEBAAAAAAAAAAAAAAgJBgcCBAUDAf/EAEIQAQABAwIDAwQPCAIDAQEAAAABAgMEBQYHESESMUEIIlFhCRMVFhgyMzdWcnaRsbTTI0JSVWJxgZMU0RckJUOh/8QAFAEBAAAAAAAAAAAAAAAAAAAAAP/EABQRAQAAAAAAAAAAAAAAAAAAAAD/2gAMAwEAAhEDEQA/AIZAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAN/cLvJe3DxG2Vhbq29vHbdWJkxNNdq5N6Lli5HxrdcRRPKqP/AOxMTHOJiWgW7/JE4x3OF2+owtWv1e9fWK6bWfTPWMavuoyIj1c+VXLvpme+aaQZv8CXf30s2z99/wDTPgS7++lm2fvv/pp4Wrlu9aou2q6bluumKqK6Z5xVE90xPjDkCBvwJd/fSzbP33/0z4Eu/vpZtn77/wCmnkAgb8CXf30s2z99/wDTPgS7++lm2fvv/pp5AIG/Al399LNs/ff/AEz4Eu/vpZtn77/6aeQCBvwJd/fSzbP33/0z4Eu/vpZtn77/AOmnkAgb8CXf30s2z99/9M+BLv76WbZ++/8App5AIG/Al399LNs/ff8A0z4Eu/vpZtn77/6aeQCBvwJd/fSzbP33/wBM+BLv76WbZ++/+mnkAgb8CXf30s2z99/9N8svyKeIdrEvXbG5NtZF2iiqqi1TXepm5VEdKYmaOUc+7nPRPcBTdqGHlafn5GBnY93Gy8a7Vav2blM01266Z5VUzE90xMTHJ8E0PL24M9uivittvE86mKaNdsW6e+OkU5MR6ulNfq7NXhVKF4AAAAAAAAAAAAAAAAAAAAAAAAAAAAPV2ht7Vt2bm0/bmhYlWVqWoXos2LVPjM98zPhTEc5mfCImfBJH4Eu//pZtn77/AOm3B5EvBX3j7Zje248Psbk1ezHtFq5T52DjT1inl4V19Jq8YjlT0ntc5JAgb8CXf30s2z99/wDTPgS7++lm2fvv/pp5AIG/Al399LNs/ff/AEz4Eu/vpZtn77/6aeQCBvwJd/fSzbP33/0z4Eu/vpZtn77/AOmnkAgb8CXf30s2z99/9M+BLv76WbZ++/8App5AIG/Al399LNs/ff8A0z4Eu/vpZtn77/6aeQCBvwJd/fSzbP33/wBM+BLv76WbZ++/+mnkAgb8CXf30s2z99/9M+BLv76WbZ++/wDpp5AIG/Al399LNs/ff/TPgS7++lm2fvv/AKaeQCBvwJd/fSzbP33/ANN5G8/JJ3PtDa2obl17e218XTtPszevXJm/z5R3U0x2OtUzMREeMzELCVevlscavf5uj3nbdy+3trR70+2XbdXOnNyY5xNfPxop600+E+dV1iaeQRxAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABOTyDeM/uvplHC7cmXz1DCtzVot65V1vWKY5zY5z31UR1p/o5x07HWWinPRNT1DRdXxNX0rLu4mfh3qb+Pftzyqt10zziY/wAwtD8nXinp/Fjh5j63a9qs6rj8rGq4lM/I34j40R39iv41P+Y586ZBskAAAAAAAAAAAAAAAHyzcXGzcO/hZli3kY2RbqtXrVymKqLlFUcqqZie+JiZiYVkeVLwiyeFHEG5j4tu5Xt3Upqv6Vfq5zyp5+dZqn+KiZiPXE0z4zEWeMI43cOdJ4o8Ps3a+pxTbu1x7bg5XZ51YuRTE9i5Hq6zEx40zMesFTw9Xd23tW2pubUNua5i1Yuo6femzftT4THdMT40zHKYnxiYnxeUAAAAAAAAAAAAAAAAAAAAAAAAAkv5EPBX36bkjfe48Ttbd0m9H/FtXKfNzcqnrHTxoo6TPhM8o6x2oal4EcNNV4qcQcTbeB27OLH7bUMuKecY2PEx2qvXVPdTHjMx4c5i0jamgaTtbbmBt7Q8SjE07AsxZx7VPhTHjM+MzPOZmeszMzPeD0wAAAAAAAAAAAAAAAAYBx64m6Vwq4fZe4s7sXs2rnZ03DmeU5N+Y82PT2Y76p8Ij0zESGovLh41e8/b1WwNt5fZ1/VbP/u3rdXnYeLV05c/CuvrEeMU856TNMoBvS3Rruq7m3Dna/reXXmajn3qr2Rer76qp9HoiO6IjpERER0h5oAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADY/k8cUtR4UcQ8bXbHtl7TL/KxqmJTPy1iZ6zEd3bp+NTPpjlz5TLXAC4zQ9V0/XNGw9Y0nKt5eBm2ab+PetzzpuUVRziY/wAS7iDPkHcZ/cXVqOGG48vlpufdmdGvXKuljIqnrZ5z3U1z1j0V9P3+k5gAAAAAAAAAAAAAAAARk8uXgz779tTv/buJ2te0ezP/ADLVunzsvFp6zPLxrt9ZjxmnnHXlTCAS5hXX5aXBn/x5vH3z6Di9jbGtXqqqKKKfNw8medVVr0RTPWqj1dqP3eoR7AAAAAAAAAAAAAAAAAAAAAAdvR9Nz9Y1bE0rS8W7l52ZepsY9i3HOq5XVPKmmPXMy6icvkI8FfcbTbfFDc2Jy1HNtTGjWLlPWxYqjlN+YnuqrjpT6KJ5/v8AQNx+TZwmwOEvD+1pf7K/rWb2b+rZdMfKXeXSime/sURMxHp86rlE1S2gAAAAAAAAAAAAAAAAAOprWp6foukZer6rl2sTAw7NV/Iv3J5U26KY5zVP+IVf+UfxWz+LPEG9rFfttjR8TtWNKxKp+Ss8/jVR3duvlE1f4jnMUw3H5dnGr3d1W5wx21l89LwLvPWL9urpk5FM9LMTHfTbnv8ATXH9HWJ4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOVuuu1cpuW66qK6JiqmqmeUxMd0xKybyQuMlvihsaNP1fIp99Oj0U286JnlVk2+6jIiPX3Vcu6r0RVSrXZTwr3xrPDrfOnbr0O5/7GJX+0szVyoyLU/HtV/01R908pjrEAtvGP8ADvd+jb72bp26tBv+24OdaiumJ+Naq7qrdUeFVM84n+3oZAAAAAAAAAAAAAAAA8HiDtLRt87O1Ha2vY/t2Dn2pt1cvjW6u+m5TPhVTVEVRPph7wCpHivsXWeHO+tQ2prdH7fFr52r0U8qMizPxLtPqqj7p5xPWJYqsp8r3g5RxQ2JOfpOPT76NHoqu4NURynJt99ePM+vvp591UeEVVK2LlFdq5VbuUVUV0TNNVNUcpiY74mAcQAAAAAAAAAAAAAAAAAAZVwp2LrXEffOBtTQrf7fKq53b1VPOjHtR8e7X/TTH3zMRHWYBs/yPOC9XE3eXu1reNVO1dHu01ZXajzcu9302I9Md01+inlHTtRKx6immiimiimKaaY5RERyiI9DH+HOz9F2Fs3T9q6BY9qwsK32Yqq+PdrnrVcrnxqqnnM/36coiIZCAAAAAAAAAAAAAAAAA0J5Y3Ginhps6ND0LJindWsWqqceaZ87Dsd1V+fRV300evnPXszE7Q4s770XhvsXP3XrlyPacans2bMVcq8m9PPsWqfXMx/iImZ6RKrLiJu7Wd97y1HdOv3/AG3Ozrs11RHPsWqe6m3RHhTTHKIj1ekHgV1VV1TVVVNVUzzmZnnMy/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABIHyMeM3/jneXvc13Kmja+tXaabtVdXm4eRPKKb3qpnpTX6uU/u8psXiYmImJ5xKmdPjyFuM3vq27Tw73Fl9rW9Js//AD7tyrzsvFp6dn112+keunlPXs1SCUAAAAAAAAAAAAAAAACDPl48GfcXVq+J+3MTlpufdiNZs26eljIqnlF7lHdTcnpPor+v0nM6Wu6Vp+u6LmaNq2Lby8DNs1WMizcjza6Ko5TAKdBsbyhuF2ocKOImVoN/2y9pl7nf0vLqj5exM9Ime7t0/Fqj0xz7phrkAAAAAAAAAAAAAAAAH0x7N7JyLePj2rl69drii3bt0zVVXVM8oiIjrMzPgsr8kzg5Z4V7FjI1OzRVujVqKbuo3OkzYp76cemfRTz87l31c++Ip5aV8g3gr/yL1rirubE/ZW6pjQse7T8aqOlWTMeiOsUevnV4UymmAAAAAAAAAAAAAAAAA+eVfsYuNdycm9bs2LNE3Lly5VFNNFMRzmqZnpERHXm+iHHl48avard3hVtjL/aVxE67kWqu6metONE+vpNfq5U+NUA0r5WHGO/xV31NrTrtyjbGlVVWtNtdY9unuqyKo9NXLpE91PLpEzVz0wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD09ra7qu2NxYG4NEy68TUcC9Tex7tP7tUemPGJjnExPSYmYnveYAtd4FcStL4p8PcLc2B2LOVy9p1DEirnONkREdqj6s84qpnxpmPHnEZ2q98mLi1l8J+IVrPvV3bmgZ/Zsatj09edvn0u0x410TMzHpiao6c+azvTszE1HT8fUMDItZOJk2qb1i9aq7VFyiqOdNUTHfExMSD7gAAAAAAAAAAAAAAA1p5RvCvA4scPMjRa4tWdXxeeRpWVVHyV6I+LM9/Yrjzav8AE8pmmFXus6bn6Pq2XpOqYtzEzsO9VYyLFyOVVu5TPKqmf7TC41Eby8+DPunp9zintzF55uHbinW7Nunrds0xypyOX8VEcoq/p5T07M8whAAAAAAAAAAAAAAA275LfCDK4sb+osZVFy3tzTZpvarkU847VPPzbNM/xV8pj1RFU+EROvNj7Y1jee69O2zoONOTqGfei1ap8KfGaqp8KaYiapnwiJWmcGuHujcMdg4O1tHpiv2qPbMvJmnlVlX5iO3cq/vy5RHhTER4AyvAxMXT8HHwMHHtY2LjWqbVmzapimi3RTHKmmmI7oiIiOT7gAAAAAAAAAAAAAAADxN97p0bZW0tR3Pr+TGPp+BZm5dq/eqnupopjxqqmYpiPGZgGvPKm4v43CfYNd3DuW7m5NTiqzpVieU9meXnXqo/ho5x/eqaY7ucxWXnZWTnZt/NzL9zIyci5VdvXblU1V3K6p51VVTPWZmZmZllfGPiDrPE3fudurWapom9PYxcaKudGLYiZ7Fun+3PnM9OdUzPiw4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABMbyCuM/tN2jhTuTL/Z3Jqr0K/cq+LV1mrGmfX1qo9fap8aYQ5fXDycjDy7OZiX7ljIsXKblq7bqmmqiumecVRMdYmJiJ5guTGoPJW4vY/Ffh/RczbtujcmmRTY1SzHKO3PLzb9Mfw18p/tVFUd3Lnt8AAAAAAAAAAAAAABwv2rV+zXYv26Ltq5TNFdFdMTTVTMcpiYnviXMBWj5WvB67ws37N/TLFc7Y1eqq9p1ffFirvrx5n008/N599Mx3zFTSq2ri9sLR+JWwtQ2prNMU28int49+KedWNfp59i7T64meseMTMd0qsN97W1jZW7dR2vr2P7RqGn3ptXI/dqjvprpnxpqiYqifGJgHiAAAAAAAAAAP2ImZ5R1l+JSeQxwVndGu0cRtyYnPRNMvf/Ns3KemXk0z8f10W5/xNXKP3aoBu7yLuCscPdp++rcGJ2d0azZiZorp87Cxp5TTa9VdXSqv0cqaf3Z5yGAAAAAAAAAAAAAAAAACZiI5zPKIV2eWhxpniJuz3r7fyu1tfRr0xTXRV5ubkRzpqu+iaaetNHqmqr96OW7vLo40+9nQ6+HG28vs61qdn/6d63V1xMaqPic/Cu5H3Uc5/eplAwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAGacF+Ier8MeIGBunSpquU2p9rzMbtcqcrHqmO3bn7omJ8KopnwWm7N3HpG7trafuXQsqMnTtQsxesXI7+U99NUeFUTziY8JiYU/JKeRBxn95W6Y2PuHL7O3dZvx/x7tyrlTh5U8oirn4UV9KZ8Insz0jtSCwQAAAAAAAAAAAAAAABFf2QvY+3MzYmJvu7l4+Br2Beow7Xa+Nn2q5n9l076qPOrifCIr598cpP6rn4WlaZlanqWVaxcLEtVXr9+7V2aLdFMc6qpn0REKxvKa4uZvFnf1zOt1XbOgYE1WdJxaunK3z63ao/jr5RM+iIpjry5yGqQAAAAAAAAd/b+kalr+uYWiaPiXMzUM69TYx7NuOtddU8oj1f3npHfIM28nvhbqXFjiDjaDje2WNNs8r+qZlMdLFiJ68p7u3V8WmPTPPuiVom3dG0zb2hYWh6NiW8PT8GzTYx7NEdKKKY5R/efTM9ZnnMsH8njhZpvCfh9j6HY9rv6pkcr+qZlMdb9+Y7onv7FPxaY9HOeXOZbHAAAAAAAAAAAAAAAAAa58oXilpvCfh7ka7ke139Tv87Gl4dU9b9+Y6TMd/Yp+NVPo6d8wzjcOsabt/Q83W9Yy7eHp+DZqv5F65PSiimOcz6/7R1mekKu/KF4palxY4g5Gu5HtljTLHOxpeHVPSxYiekzHd26vjVT6endEAwjcOsaluDXc3W9Yy7mZqGdeqv5F6uetddU85n1R6IjpEdIdAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWGeRNxn9/m0vefuDL7e5dFsxFFy5VzqzcWOUU3OfjXT0pq9POmeszPKRioLY26NY2Zu3Ttz6Dkzj6hp96Ltqr92rwqoqjxpqiZpmPGJladwe3/o/EvYOn7r0eqKab9PYyceaudWNfp5du1V/ae6enOJpnxBl4AAAAAAAAAAAANB+WLxqp4abQ9wdCyojdesWpjHmmfOw7M9Kr8+irvij185/dmJDTHl28bPdfULvC/bGXz0/DuR7tZFurpfvUzzixEx+7RPWr01Ry6dnrEpyrqqrrqrrqmqqqeczM85mfS4gAAAAAAAAJ4+QtwW97Wi0cSdyYnZ1nUrPLS7Nynri41UfKequ5H3UfWmI0l5GHBaeIu7ffNr+L2traNeia6K6fNzciOU02fRNMdKq/VMU/vc4sUiIiIiIiIjuiAAAAAAAAAAAAAAAAAAR78s/jTHDvaXvY0DK7O6dZszFFdFXnYWPPOKr3qqnrTR6+dX7vUNI+XRxq982uV8N9tZna0XTb3/ANO9bq83LyaZ+T5+NFuf8TXz/hplFl+zMzPOZ5zL8AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAbm8k7jDe4V79pt6jerq2zq1VNnUrfWfaZ7qL9Memnn15d9Mz3zEctMgLlce9ZyMe3kY92i9Zu0xXbuUVRVTXTMc4mJjpMTHi5og+QXxn/52HRwr3Jl88rHomrQ71yrrctxEzVj8/TTHOqn+nnHTsxEy+AAAAAAAAAB8NQzMXTsDIz87ItY2JjWqrt+9dqimi3RTHOqqZnuiIiZ5gxfjDxA0bhnsPO3VrVUVU2Y7GNjxVyryb88+xap9c8ucz4REz4Ks9/7s1nfG79R3Rr+T7fn592blfL4tFPdTRTHhTTERER6IbA8qPjBlcWd+VXsWu7a23p01WdKx6ucdqn969VH8dfKOnhEUx3xMzqIAAAAAAAABmPB3h9rPE3fuDtXRqZpm9PbysiaedOLYiY7d2r+3PlEeMzEeLFMHFyc7NsYWHYuZGTkXKbVm1bpmqu5XVPKmmmI6zMzMRELM/JX4P43CjYNFvMt27m5NTim9ql+OU9ieXm2KZ/ho5z18apqnu5RAbD2HtXRtk7R07a+gY0Y+n4FqLduP3q576q6p8aqpmapnxmZe4AAAAAAAAAAAAAAAAPjnZWNg4V/NzL9vHxse3VdvXblUU0W6KY51VVTPSIiImZkGK8Y+IOjcMthZ26tZqiqLMe14uNFXKrKv1RPYtU/35c5nwpiZ8FWe+906zvXduo7o1/JnI1DPvTcuT+7RHdTRTHhTTERTEeERDYflT8X8nivv6u5h3LlvbemTVZ0uxPOO3HPzr9UfxV8o6eFMUx385nUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAO1pWoZulani6npuTdxc3Eu03se9bq5VW66Z501RPpiYWfeTVxXwuLPDyzqszas61hdnH1bFp6e13eXSumP4K4iZj0edTznsyq3bB4BcTdT4VcQ8TcWH7Zewa/2GpYkT0yMeZ86PrR8amfTHomYkLVx0Nuazpm4tBwdd0bLt5en51mm/j3qJ6V0VRzj+0+ExPWJ5xLvgAAAAAAITeXfxs/52Ve4V7Yy+eLYrj3cyLdXylyJ5xjxMeFM8pq/q5U9OzMTubyveNFvhfsz3L0bIo99er26qcKInnOLa7qsiY9XWKeffV16xTMK3b1y5eu13r1yq5crqmquuqec1TPWZmfGQcAAAAAAAAAbn8lDg5f4rb6i5qNq5RtjSqqbupXY5x7dPfTj0z6auXWY7qefdM08w3V5BvBX2q3a4q7nxPPriY0LHu090d1WTMevrFHq51eNMpjvni2LGLjWsXGs27NizRFu1bt0xTTRTEcopiI6RER05PoAAAAAAAAAAAAAAAAAhd5eXGr225d4VbYy/MomJ13ItVd9XfTjRPq6TX6+VPhVDdflX8Y7HCnYs29Ou269z6rTVa021PKfaY7qr9Ueinn0ie+rlHKYirlWjlX7+Vk3crJvXL1+9XNy7cuVTVVXVM85qmZ6zMz15g+YAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJU+Qlxn97muU8Ndx5fZ0jU73PS7tyrpjZNU/J+qm5Pd6K/rTKd6mimqqmqKqZmmqJ5xMT1iVj3kc8ZY4l7K9xdbyYq3TotqmjJmqfOy7PdTf8AXPdTX/Vynp2ogG+QAAAGK8V996Lw42Nn7r125+wxqezZs01cq8m9PxLVHrmfuiJmekSyXMycfDxL2Zl37djHsW6rl27cqimm3RTHOapmekRERMzKtHyreMeRxW3zVRp925RtjS6qrWm2Z5x7bPdVfqj+Krl0ie6nlHf2uYa84j7x1rf289Q3Vr9/23Nzbna7NPxLVEdKbdEeFNMcoj755zMyx0AAAAAAAAftFNVdUU00zVVM8oiI5zMg9/h5tHWt9bx07a2gY/t2dnXexTM/Et099VyufCmmOczPq9K03hNsPReG+xcDamh0fscantXr808q8m9Px7tXrmfuiIiOkQ1f5HPBenhps6dc13GindWsWqasiKo87Dsd9NiPRV3VV+vlHXsxM77AAAAAAAAAAAAAAAAAeBxC3douxdnajunX8j2nBwbU11RHxrlXdTbpjxqqnlER6Z8I6verqpopmqqqKaYjnMzPKIhXJ5Y/GiriVvH3B0LJmdq6Pdqpx5pnzcy/HOKr8+mnvpo9XOf3piA1fxZ35rXEjfWfuvXK/wBtk1dmzYirnRjWY+Jap9UR98zMz1mWJgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAyThpvPWeH+9tO3XoV7sZeFc7U0TPmXrc9K7dfppqjnE/fHWIljYC3ThlvTRuIOydO3XoV3t4mbb51W5nz7FyOlduv0VUzzj198dJiWSK3/I64y1cM96+4+tZM07W1m5TRlTVPm4l7upyI9Ed0V/08p69mIWP0VU10xXRVFVNUc4mJ5xMA/QaU8rXjNZ4V7JnE0u/bq3Tq1FVvT7fSZx6O6rIqj0U91PPvq9MRUDTXl38bPbK73Cra+X5lMx7u5NqrvnvjGiY9HSa/8U+FUIbvpkXr2TkXMjIu3L167XNdy5cqmqquqZ5zMzPWZmfF8wAAAAAAAAEsPIT4K+7uq2+J25cTnpeBd5aPYuU9MjIpnrenn300T3emuP6OunPJv4UZ/FniDZ0in22xo+J2b+rZdEfJWufSime7t1zExT/meUxTK0DRdMwNF0jE0jSsS1iYGHZpsY9i3HKm3RTHKKY/xAO2AAAAAAAAAAAAAAAADWflHcVtP4TcPr2sVzavaxl9qxpOJVPyt7l8aY7+xRziqr/Ec4mqAad8uzjV7haTc4Y7ay+WqZ9rnq9+3V1x8eqOlmOXdXcjv9FE/wBcTEFXc1rU9Q1rV8vV9Vy7uXn5l6q/kX7k86rldU85qn/MumAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAnf5CXGf3xaJRw03Hlc9W02zz0q9cq65ONTHyXXvqtx3emj6szMEHf27rGpbe13C1zR8u5iahg3qb+PeonrRXTPOJ9cemJ6THSQWycTt66Lw92TqG69evdjFw6PNt0zHbv3J6UWqI8aqp6errM9ImVWfFDe+t8Q97ahuvXrvaysuvzLdM+ZYtR8S1RHhTTHT19ZnrMyzLyieN+u8YM3S4y8eNN0zT8ejs4VuuZoqyZpj227Pp684pie6n1zVz1MAAAAAAAAA9Pa2harufcWDt/Q8OvM1HPvU2cezR31VT6fRERzmZnpERMz0h5ifvkPcFfeft2nf25MTs7g1azH/Ds3KfOwsWrrHTwrr6TPjFPKOkzVANucBeGWlcKuH2LtzB7F7Mq/bajmRTynJvzHnVeqmPi0x4RHpmZnPwAAAAAAAAAAAAAAAAB5u6Nc0rbO3s7X9bzLeHp2BZqvZF6vuppj8ZnuiI6zMxEdZVc8e+J2qcVuIOVuLN7djCo/Y6bhzPOMaxE9I9Han41U+Mz6IiI275cXGr337hq4f7by+1oGlXv/dvW6vNzMqnpy5+NFuecR4TVznrEUyjEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADOOCPDjV+KW/wDD2xpfatWqv2udl9nnTi48THarn19YiI8apiOneDa/kT8FY35uf35bjxO3trR70e1WrlPOnOyY6xRy8aKOlVXhM9mnrE1crCXk7N25pG0dr6ftvQcWnF07T7MWbFuO/lHfVM+NUzzmZ8ZmZesAAAAAAAAAAAAAAAAAjl5a3Gr3hbW95+3cvsbm1izPbuW6vOwsaecTXz8K6utNPo86rpMRz2vxs4jaPwu2Bm7o1WYuXKP2WFi9rlVlZExPYtx6ukzM+FMTPXuVabz3Jq+7906huXXsqrK1HUL03b1ye7nPdTTHhTEcoiPCIiAeQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADs6Zg5mqaljabp2NdyszKu02bFm1T2q7ldU8qaYjxmZmIWc+THwkw+E3D+3g3abV3X8+Kb+rZNPXnc5dLVM/wUc5iPTM1T058o015B/BX3OwrXFPc2JyzMm3MaHYuU9bVqqOU5Ex6a45xT/TMz17UcpdgAAAAAAAAAAAAAAAAOvqWdh6Zp2TqOoZNrFw8W1Vev3rtXZot0UxzqqmfCIiJl2EJfLx40/wDOy7vCvbOX/wCrj1xOuX7dXylyJ5xjxPopnlNX9URHTszEhpnynuLuXxZ3/czLNVy1t/T5qsaTjVdPM59btUfx18omfREUx4c51OAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADePkicGbnFHevujq9iuNq6Rcprzqp6RlXO+nHpn199XLup9E1Uy1nwx2VrXELe2nbU0Gz28rMucqrkxPYsW4613a58KaY6+vpEdZiFp3DHZWi8Ptk6ftTQbPYxMO3yquVRHbv3J613a58aqp6+rpEdIiAZHZt27NqizZt0W7dFMU0UUxyimI6RER4Q5AAAAAAAAAAAAAAAADHOJe89F4f7K1HdWvXva8PCt84opmO3euT0ot0R41VTyiPvnlETINaeVzxmt8Ldk/8HSb9E7p1eiq3gUdJnGo7qsiqPV3U8++r0xTUrYvXbt+9XevXK7t25VNVdddUzVVVM85mZnvlknFHe+tcQ976huvXbvaycyvzLVMz2Me1HSi1R6KaY6evrM9ZmWMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOdm3cvXqLNm3XcuV1RTRRRHOqqZ6RERHfLgkF5Au3tJ17jx7bquJTkzpOl3dQxKa+tNF+m7aoprmPGYi5VMeiYie+ASm8kTgzb4XbJ90NXsUTurV6KbmdVPWca33048T6u+rl31emKaZbwAAAAAAAAAAAAAAAAAHG7cotW6rt2umiiiJqqqqnlFMR3zM+hW55X3Ga5xP3r7l6PkVe9XR7lVGHETyjKu91WRMevrFPPup69JqmG7fLv41e5eDd4W7Zy+WdlW4nW79urrZs1RzjHiY/erjlNX9MxHXtTyg+AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/wDmMZGhJf2OX58dW+zl/wDMYwLAQAAAAAAAAAAAAAAAGrPKY4tYXCbh/d1GibV7Xc7tWNJxauvaucutyqP4KImJn0zNNPTtc2fbv3DpO09s6huPXcqnF03T7M3r92rwiO6IjxqmeURHjMxHiq2448SdX4p8QMzc2p9q1Yn9lgYna504uPEz2aI9M9ZmqfGqZ7o5RAYdqufm6rqeVqepZN3Kzcu7VeyL1yrnVcrqnnVVM+mZmXWAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABJf2OX58dW+zl/8xjI0JL+xy/Pjq32cv8A5jGBYCAAAAAAAAAAAAAACNPlvcaveXturYu3Mvs7i1azP/Ku26vOwsWrnEzz8LlfWI8YjnPSezINIeW3xq9/G5p2TtzL7W29IvT7fdt1ebm5MdJq5+NFHWKfCZ7VXWOzyjYAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/5jGRoSX9jl+fHVvs5f/MYwLAQAAAAAAAAAAAAAcblU026qo74iZU+7s1/Vt07kz9w65l15eo596b2Rdq8ap8IjwiI5RER0iIiI7lwN/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEl/Y5fnx1b7OX/AMxjAsBAAAAAAAAAAAAABwv/ACFz6s/gpqXK3/kLn1Z/BTUAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAkv7HL8+OrfZy/+YxkaEl/Y5fnx1b7OX/zGMCwEAAAAAAAAAAAAAHC/8hc+rP4Kalyt/wCQufVn8FNQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACS/scvz46t9nL/AOYxkaEkvY7sjHxuN2q3Mm/as0Tt2/EVXK4pjn/yMfp1BYMOn7raV/M8L/fT/wBnutpX8zwv99P/AGDuDp+62lfzPC/30/8AZ7raV/M8L/fT/wBg7g6futpX8zwv99P/AGe62lfzPC/30/8AYO4On7raV/M8L/fT/wBnutpX8zwv99P/AGDuDp+62lfzPC/30/8AZ7raV/M8L/fT/wBg7g6futpX8zwv99P/AGe62lfzPC/30/8AYO4On7raV/M8L/fT/wBnutpX8zwv99P/AGDs3/kLn1Z/BTUuJv6tpftNf/0sL4s//vT6P7qdgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAf/9k=" style="height:48px;width:48px;object-fit:contain;margin-right:14px;border-radius:8px;" alt="logo">
      <div>
        <div class="ls-logo-name">{_hdr_company}</div>
        <div class="ls-logo-sub">{_hdr_sub}</div>
      </div>
      <div class="ls-divider"></div>
      <div class="ls-tagline">
        Estimate &nbsp;·&nbsp; Quote &nbsp;·&nbsp; Prices<br>
        Crew &nbsp;·&nbsp; Contracts
      </div>
    </div>
    <div class="ls-badge">&#9733; AI-Powered Platform</div>
  </div>
</div>

""", unsafe_allow_html=True)

# ── Tab navigation (cards) ──
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = 0

_NAV_ITEMS = [
    ("🧮", "Estimator",    "Estimate · Materials · Labor"),
    ("📄", "Client Quote", "PDF profesional · Firmas"),
    ("💲", "Prices",       "Precios de proveedor"),
    ("👷", "Crew Planner", "Labor · Días · Profit"),
    ("📋", "Contract",     "Analiza contratos del GC"),
]
_nav_cols = st.columns(5)
for _ni, (_icon, _name, _desc) in enumerate(_NAV_ITEMS):
    with _nav_cols[_ni]:
        _is_active = st.session_state["active_tab"] == _ni
        if st.button(
            f"{_icon}  {_name}\n{_desc}",
            key=f"nav_{_ni}",
            use_container_width=True,
            type="primary" if _is_active else "secondary",
        ):
            st.session_state["active_tab"] = _ni
            st.rerun()

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

    # ── Trade Selector ──
    _trade_options = [
        "Concrete / Flatwork", "Framing", "Tile / Flooring", "Pool / Piscina",
        "Metal Building", "Cleaning Services", "Sheetrock / Drywall", "Carpentry / Trim",
        "Painting / Pintura", "Roofing", "Plumbing", "Electrical", "HVAC",
        "Landscaping", "Fencing", "Demolition", "Insulation", "Waterproofing",
        "Epoxy / Coating", "Other / Custom",
    ]
    trade = st.selectbox("🔧 Select Trade", _trade_options, key="trade_selection")

    # Immediately reset materials when trade changes
    if st.session_state.get("current_trade") != trade:
        st.session_state["current_trade"] = trade
        st.session_state["generic_materials"] = [
            {"name": m.split(" (")[0].strip(),
             "unit": m.split("(")[-1].replace(")", "").strip(),
             "qty": 0.0, "price": 0.0}
            for m in TRADE_MATERIALS.get(trade, [])
        ]
        st.session_state["generic_trade_last"] = trade

    if trade == "Concrete / Flatwork":

        # ── 1: Dimensions ──
        st.markdown("### 1 · Project Dimensions")
        job_name   = st.text_input("Job Name", placeholder="e.g. Smith Driveway", key="c_job_name")
        zone_setup = st.selectbox("Concrete Zone Setup", [
            "Single Thickness (whole job same thickness)",
            "Driveway + Apron + Sidewalk (different thicknesses)",
            "Custom (up to 4 zones)",
        ], key="c_zone_setup")

        THICK_OPTIONS = [4, 6, 8, 12]

        if zone_setup == "Single Thickness (whole job same thickness)":
            sqft      = st.number_input("Total Square Footage", min_value=0.0, value=0.0, step=10.0, key="c_sqft")
            thickness = st.selectbox("Concrete Thickness", THICK_OPTIONS, format_func=lambda x: f'{x} inches', key="c_thick")
            zones     = [{"name": "Slab", "sqft": sqft, "thick": thickness}]

        elif zone_setup == "Driveway + Apron + Sidewalk (different thicknesses)":
            c1, c2 = st.columns([2, 1])
            dw_sqft  = c1.number_input("Driveway SQFT",   min_value=0.0, value=0.0, step=10.0, key="z_dw_sqft")
            dw_thick = c2.selectbox("Thickness", THICK_OPTIONS, index=0, format_func=lambda x: f'{x}"', key="z_dw_thick")
            ap_sqft  = c1.number_input("Apron/Turn SQFT", min_value=0.0, value=0.0,  step=10.0, key="z_ap_sqft")
            ap_thick = c2.selectbox("Thickness", THICK_OPTIONS, index=1, format_func=lambda x: f'{x}"', key="z_ap_thick")
            sw_sqft  = c1.number_input("Sidewalk SQFT",   min_value=0.0, value=0.0,  step=10.0, key="z_sw_sqft")
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

        waste_pct  = st.number_input("Concrete Waste %", min_value=0.0, max_value=30.0, value=0.0, step=0.5, key="c_waste_pct")
        conc_price = st.number_input("Concrete ($/CY)",  min_value=0.0,
                                      value=st.session_state["concrete_price"],
                                      step=1.0, format="%.2f", key="conc_price_input")
        conc_psi   = st.selectbox("Concrete PSI", [2500, 3000, 3500, 4000], index=1, format_func=lambda x: f"{x} PSI", key="c_conc_psi")

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
                                      help="Used for center expansion joint rule (>15 ft triggers center joint)", key="c_dw_width")
        sw_width = _wc2.number_input("Sidewalk Width (ft)", min_value=0.0, value=0.0, step=1.0, format="%.0f",
                                      help="Used to calculate required sidewalk expansion joints every 20 ft", key="c_sw_width")

        st.markdown("---")

        # ── 2: Forming ──
        st.markdown("### 2 · Forming Materials")
        form_type = st.selectbox("Form Type", [
            "Sidewalk / Patio",
            "Driveway / Heavy Slab",
            "Mixed (Driveway + Sidewalk)",
            "Manual",
        ], key="c_form_type")

        is_mixed = form_type == "Mixed (Driveway + Sidewalk)"

        if is_mixed:
            sqft_driveway = st.number_input("Driveway SQFT", min_value=0.0, value=0.0, step=10.0, key="c_driveway_sqft")
            sqft_sidewalk = st.number_input("Sidewalk SQFT", min_value=0.0, value=0.0, step=10.0, key="c_sidewalk_sqft")
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
        stakes_per_bundle  = st.number_input("Stakes per bundle", min_value=1, value=25, step=1, key="c_stakes_per_bundle")
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
        use_rebar = st.checkbox("Include Rebar", key="c_use_rebar")
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
            rebar_type      = st.selectbox("Rebar Type", list(REBAR_PRICES.keys()), key="c_rebar_type")
            rebar_spacing   = st.selectbox("Rebar Spacing", list(REBAR_FACTORS.keys()), key="c_rebar_spacing")
            rebar_waste_pct = st.number_input("Rebar Waste %", min_value=0.0, max_value=30.0, value=0.0, step=0.5, key="c_rebar_waste")
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
        use_base = st.checkbox("Include Base Material", key="c_use_base")
        base_type = ""
        base_sqft_used = 0.0
        base_thick_in = 6
        base_waste_pct = 10.0
        base_price = 0.0
        base_tons_raw = base_tons_ord = base_total = 0.0
        base_trucks = 0
        if use_base:
            BASE_TYPES = ["Crushed Concrete", "Flexible Base (Stabilizer)", "Gravel", "Sand"]
            base_type     = st.selectbox("Material Type", BASE_TYPES, key="c_base_type")
            base_sqft_in  = st.number_input("Square Footage (0 = use project sqft)", min_value=0.0, value=0.0, step=10.0, key="c_base_sqft")
            base_sqft_used = base_sqft_in if base_sqft_in > 0 else sqft
            if base_sqft_in == 0:
                st.caption(f"Using project sqft: {sqft:,.0f} sqft")
            base_thick_in  = st.number_input("Base Thickness (inches)", min_value=1, value=6, step=1, key="c_base_thick")
            base_waste_pct  = st.number_input("Waste %", min_value=0.0, max_value=30.0, value=10.0, step=0.5, key="bwp")
            base_tons_raw   = base_sqft_used * base_thick_in * 0.00309
            base_tons_ord   = base_tons_raw * (1 + base_waste_pct / 100)
            base_trucks     = math.ceil(base_tons_ord / 11)
            base_pricing    = st.radio("Pricing Method", ["Price per Ton", "Price per Truck"], horizontal=True, key="bpm")
            if base_pricing == "Price per Ton":
                base_price  = st.number_input("Price ($/ton)", min_value=0.0, value=0.0, step=1.0, format="%.2f", key="c_base_price_ton")
                base_total  = base_tons_ord * base_price
                cost_line   = f"Total cost: **${base_total:,.2f}**"
            else:
                base_price_per_truck = st.number_input("Price ($/truck)", min_value=0.0, value=0.0, step=50.0, format="%.2f", key="c_base_price_truck")
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
        labor_method = st.radio("Labor Method", ["By Square Foot", "Flat Total"], horizontal=True, key="c_labor_method")
        if labor_method == "By Square Foot":
            labor_rate = st.number_input("Labor ($/SQFT)", min_value=0.0, value=0.0, step=0.25, format="%.2f", key="c_labor_rate")
            labor_cost = sqft * labor_rate
            st.info(f"Labor total: **${labor_cost:,.2f}** ({sqft:,.0f} SQFT × ${labor_rate:.2f})")
        else:
            labor_rate = 0.0
            labor_cost = st.number_input("Labor (flat total $)", min_value=0.0, value=0.0, step=50.0, format="%.2f", key="c_labor_flat")

        st.markdown("---")

        # ── 7: Demo ──
        st.markdown("### 7 · Demolition (Optional)")
        use_demo = st.checkbox("Include Demolition", key="c_use_demo")
        demo_cost = 0.0
        if use_demo:
            demo_rate = st.number_input("Demo ($/SQFT)", min_value=0.0, value=0.0, step=0.25, format="%.2f", key="c_demo_rate")
            demo_cost = sqft * demo_rate
            st.info(f"Demo total: **${demo_cost:,.2f}**")

        st.markdown("---")

        # ── 8: Overhead & Profit ──
        st.markdown("### 8 · Overhead & Profit")

        overhead_pct = st.number_input("Overhead %", min_value=0.0, max_value=100.0,
                                       value=float(st.session_state.get("c_overhead_pct", st.session_state.get("ovh_calc_suggested", 0.0))),
                                       step=0.5, key="c_overhead_pct")
        profit_pct   = st.number_input("Profit %", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="c_profit_pct")

        st.markdown("---")
        st.button("🧮 CALCULATE ESTIMATE")

    else:
        # ═══════════════════════════════════════════════════
        # GENERIC ESTIMATOR
        # ═══════════════════════════════════════════════════

        # ── 1: Project Setup ──
        st.markdown("### 1 · Project Setup")
        job_name = st.text_input("Job Name", placeholder="e.g. Smith Residence", key="g_job_name")
        unit_type = st.selectbox("Unit of Measure", [
            "Square Feet (SQFT)", "Linear Feet (LF)", "Units / Each", "Project (lump sum)"
        ], key="g_unit_type")
        _unit_label_map = {
            "Square Feet (SQFT)": "SQFT",
            "Linear Feet (LF)":   "LF",
            "Units / Each":       "Units",
            "Project (lump sum)": "Project",
        }
        unit_label = _unit_label_map.get(unit_type, "unit")
        total_quantity = st.number_input(f"Total Quantity ({unit_label})", min_value=0.0, value=0.0, step=1.0, format="%.1f", key="g_qty")
        sqft = total_quantity

        st.markdown("---")

        # ── 2: Materials ──
        st.markdown("### 2 · Materials")
        _gh1, _gh2, _gh3, _gh4, _gh5 = st.columns([3, 1.2, 1.2, 1.5, 0.5])
        _gh1.markdown("**Material**"); _gh2.markdown("**Unit**"); _gh3.markdown("**Qty**"); _gh4.markdown("**$/Unit**"); _gh5.markdown("")
        _mats_to_delete = []
        for _mi, _mat in enumerate(st.session_state["generic_materials"]):
            _mc1, _mc2, _mc3, _mc4, _mc5 = st.columns([3, 1.2, 1.2, 1.5, 0.5])
            st.session_state["generic_materials"][_mi]["name"]  = _mc1.text_input("", value=_mat["name"],  key=f"gm_n_{_mi}", label_visibility="collapsed", placeholder="Material name")
            st.session_state["generic_materials"][_mi]["unit"]  = _mc2.text_input("", value=_mat["unit"],  key=f"gm_u_{_mi}", label_visibility="collapsed", placeholder="unit")
            st.session_state["generic_materials"][_mi]["qty"]   = _mc3.number_input("", min_value=0.0, value=float(_mat["qty"]),   step=1.0,  key=f"gm_q_{_mi}", label_visibility="collapsed", format="%.1f")
            st.session_state["generic_materials"][_mi]["price"] = _mc4.number_input("", min_value=0.0, value=float(_mat["price"]), step=0.01, key=f"gm_p_{_mi}", label_visibility="collapsed", format="%.2f")
            if _mc5.button("🗑", key=f"gm_d_{_mi}"):
                _mats_to_delete.append(_mi)
        for _mi in reversed(_mats_to_delete):
            st.session_state["generic_materials"].pop(_mi)
            st.rerun()
        if st.button("➕ Add Material", key="gm_add"):
            st.session_state["generic_materials"].append({"name": "", "unit": "unit", "qty": 0.0, "price": 0.0})
            st.rerun()

        st.markdown("---")

        # ── 3: Labor ──
        st.markdown("### 3 · Labor")
        g_labor_method = st.radio("Labor Type", ["Per SQFT / Unit", "Fixed Total (Lump Sum)"], horizontal=True, key="g_labor_method")
        if g_labor_method.startswith("Per"):
            g_labor_rate = st.number_input(f"Labor Rate ($/{unit_label})", min_value=0.0, value=0.0, step=0.25, format="%.2f", key="g_labor_rate")
            labor_cost   = g_labor_rate * total_quantity
            labor_rate   = g_labor_rate
            labor_method = "By Square Foot"
            if labor_cost > 0:
                st.info(f"Labor total: **${labor_cost:,.2f}**")
        else:
            g_labor_rate = 0.0
            labor_cost   = st.number_input("Total Labor Cost ($)", min_value=0.0, value=0.0, step=50.0, format="%.2f", key="g_labor_flat")
            labor_rate   = 0.0
            labor_method = "Flat Total"

        st.markdown("---")

        # ── 4: Equipment ──
        st.markdown("### 4 · Equipment")
        _geq_to_delete = []
        for _ei, _eq in enumerate(st.session_state["generic_equipment"]):
            _ec1, _ec2, _ec3 = st.columns([2, 1, 0.5])
            st.session_state["generic_equipment"][_ei]["name"] = _ec1.text_input("", value=_eq["name"], key=f"ge_n_{_ei}", label_visibility="collapsed", placeholder="Description")
            st.session_state["generic_equipment"][_ei]["cost"] = _ec2.number_input("", min_value=0.0, value=float(_eq["cost"]), step=50.0, key=f"ge_c_{_ei}", label_visibility="collapsed", format="%.0f")
            if _ec3.button("🗑", key=f"ge_d_{_ei}"):
                _geq_to_delete.append(_ei)
        for _ei in reversed(_geq_to_delete):
            st.session_state["generic_equipment"].pop(_ei)
            st.rerun()
        if st.button("➕ Add Equipment", key="ge_add"):
            st.session_state["generic_equipment"].append({"name": "", "cost": 0.0})
            st.rerun()

        st.markdown("---")

        # ── 5: Subcontractors ──
        st.markdown("### 5 · Subcontractors")
        _gsub_to_delete = []
        for _si, _sub in enumerate(st.session_state["generic_subs"]):
            _sc1, _sc2, _sc3, _sc4 = st.columns([2, 2, 1.5, 0.5])
            st.session_state["generic_subs"][_si]["name"]   = _sc1.text_input("", value=_sub["name"],        key=f"gs_n_{_si}", label_visibility="collapsed", placeholder="Sub Name")
            st.session_state["generic_subs"][_si]["desc"]   = _sc2.text_input("", value=_sub.get("desc",""), key=f"gs_d_{_si}", label_visibility="collapsed", placeholder="Description")
            st.session_state["generic_subs"][_si]["amount"] = _sc3.number_input("", min_value=0.0, value=float(_sub["amount"]), step=50.0, key=f"gs_a_{_si}", label_visibility="collapsed", format="%.2f")
            if _sc4.button("🗑", key=f"gs_x_{_si}"):
                _gsub_to_delete.append(_si)
        for _si in reversed(_gsub_to_delete):
            st.session_state["generic_subs"].pop(_si)
            st.rerun()
        if st.button("➕ Add Subcontractor", key="gs_add"):
            st.session_state["generic_subs"].append({"name": "", "desc": "", "amount": 0.0})
            st.rerun()

        st.markdown("---")

        # ── 6: Demolition ──
        st.markdown("### 6 · Demolition (Optional)")
        use_demo = st.checkbox("Include Demolition", key="g_use_demo")
        demo_cost = 0.0
        if use_demo:
            g_demo_method = st.radio("Demo pricing", [f"Per {unit_label}", "Fixed Total"], horizontal=True, key="g_demo_method")
            if g_demo_method.startswith("Per"):
                g_demo_rate = st.number_input(f"Demo ($/{unit_label})", min_value=0.0, value=0.0, step=0.25, format="%.2f", key="g_demo_rate")
                demo_cost   = g_demo_rate * total_quantity
            else:
                demo_cost = st.number_input("Demo flat total ($)", min_value=0.0, value=0.0, step=50.0, format="%.2f", key="g_demo_flat")
            if demo_cost > 0:
                st.info(f"Demo total: **${demo_cost:,.2f}**")

        st.markdown("---")

        # ── 7: Overhead & Profit ──
        st.markdown("### 7 · Overhead & Profit")
        overhead_pct = st.number_input("Overhead %", min_value=0.0, max_value=100.0,
                                       value=float(st.session_state.get("ovh_calc_suggested", 0.0)),
                                       step=0.5, key="g_overhead_pct")
        profit_pct   = st.number_input("Profit %", min_value=0.0, max_value=50.0, value=0.0, step=0.5, key="g_profit_pct")

        st.markdown("---")
        st.button("🧮 CALCULATE ESTIMATE", key="g_calc_btn")

        # Fallbacks for concrete-specific vars used in Tab 2 / PDF generation
        thickness = None
        zones = []
        conc_psi = 3000
        conc_price = 0.0
        use_rebar = False
        rebar_type = ""
        rebar_spacing = ""
        rebar_lf = 0.0
        rebar_lf_base = 0.0
        rebar_lf_waste = 0.0
        rebar_price = 0.0
        rebar_bars = 0
        rebar_waste_pct = 0.0
        use_base = False
        base_total = 0.0
        base_type = ""
        base_thick_in = 0
        base_tons_ord = 0.0
        base_trucks = 0
        base_price = 0.0
        base_sqft_used = 0.0
        base_waste_pct = 0.0
        base_tons_raw = 0.0
        is_mixed = False
        cy_ord = 0
        cy_raw = 0.0
        lumber_lf = 0.0
        lumber_lf_driveway = 0.0
        lumber_lf_sidewalk = 0.0
        lumber_price = 0.0
        lumber_price_driveway = 0.0
        lumber_price_sidewalk = 0.0
        stakes_qty = 0
        ej_lf = 0.0
        ej_price = 0.0
        stake_price = 0.0
        sqft_driveway = 0.0
        sqft_sidewalk = 0.0
        zone_setup = "Single Thickness (whole job same thickness)"


# ══════════════════════════════════════════════
# MAIN — CALCULATIONS
# ══════════════════════════════════════════════
if trade == "Concrete / Flatwork":
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
    _mat_cost_ss = conc_total + lumber_total + stakes_total + ej_total + rebar_total + base_total
    _sub_cost_ss = 0.0
else:
    conc_total      = 0.0
    lumber_total    = lumber_total_dw = lumber_total_sw = 0.0
    stakes_total    = ej_total = rebar_total = 0.0
    equip_items     = [e for e in st.session_state["generic_equipment"] if e["name"] and e["cost"] > 0]
    equip_total     = sum(e["cost"] for e in equip_items)
    _g_mat_cost     = sum(m["qty"] * m["price"] for m in st.session_state["generic_materials"] if m["name"])
    _g_sub_total    = sum(s["amount"] for s in st.session_state["generic_subs"] if s["name"] and s["amount"] > 0)
    direct_cost     = _g_mat_cost + labor_cost + equip_total + _g_sub_total + demo_cost
    _mat_cost_ss    = _g_mat_cost
    _sub_cost_ss    = _g_sub_total

overhead_amt = direct_cost * (overhead_pct / 100)
subtotal     = direct_cost + overhead_amt
profit_amt   = subtotal * (profit_pct / 100)
grand_total  = subtotal + profit_amt
price_per_sf = grand_total / sqft if sqft > 0 else 0

# ── Save values for all tabs (single source of truth) ─────────
if trade == "Concrete / Flatwork":
    st.session_state["total_sqft"] = sqft
else:
    st.session_state["total_sqft"] = sqft if unit_type == "Square Feet (SQFT)" else 0
st.session_state["total_bid"]          = grand_total
st.session_state["materials_cost"]     = _mat_cost_ss
st.session_state["equipment_cost"]     = equip_total
st.session_state["direct_cost"]        = direct_cost
st.session_state["labor_budget"]       = labor_cost
st.session_state["labor_cost"]         = labor_cost
st.session_state["overhead_cost"]      = overhead_amt
st.session_state["profit_amount"]      = profit_amt
st.session_state["price_per_sqft"]     = price_per_sf
st.session_state["concrete_yards"]     = cy_ord
st.session_state["subcontractor_cost"] = _sub_cost_ss

# ─────────────────────── TAB 1: ESTIMATOR ────────────────────────
if st.session_state["active_tab"] == 0:
    if trade == "Concrete / Flatwork":
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
                    pct = fixed_pct if fixed_pct is not None else (amt / grand_total * 100 if grand_total > 0 else 0)
                    st.markdown(f'<div class="result-row"><span style="color:#a0aec0;">{label}</span><span style="color:#e0e0e0;font-weight:600;">${amt:,.2f} <span style="color:#8892a4;font-size:11px;">({pct:.0f}%)</span></span></div>', unsafe_allow_html=True)

            st.markdown("---")

            # ── Overhead Calculator (dentro de col2, anclado al tab) ──
            with st.expander("🧮 Overhead Calculator", expanded=False):
                st.markdown(
                    '<p style="color:#dc2626;font-weight:600;font-size:13px;">'
                    "⚠️ This tool provides an estimate only. Results are not financial or "
                    "accounting advice. Verify all figures with a licensed CPA before use.</p>",
                    unsafe_allow_html=True,
                )
                _oc_left, _oc_right = st.columns(2)
                with _oc_left:
                    st.markdown("**Fixed Overhead** *(same every month)*")
                    _oc_rent   = st.number_input("Office / Warehouse Rent",           min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_rent")
                    _oc_veh    = st.number_input("Vehicle Payments",                   min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_veh")
                    _oc_equip  = st.number_input("Equipment Payments / Leases",        min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_equip")
                    _oc_gl     = st.number_input("General Liability Insurance",        min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_gl")
                    _oc_wc     = st.number_input("Workers Comp Insurance",             min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_wc")
                    _oc_auto   = st.number_input("Commercial Auto Insurance",          min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_auto")
                    _oc_lic    = st.number_input("Business Licenses & Permits (÷12)", min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_lic")
                    _oc_legal  = st.number_input("Accounting / Legal Fees (÷12)",     min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_legal")
                    _oc_admin  = st.number_input("Administrative Salaries",            min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_admin")
                    _oc_phone  = st.number_input("Phone & Internet",                   min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_phone")
                    _oc_soft   = st.number_input("Software & Subscriptions",           min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_soft")
                    _oc_ofixed = st.number_input("Other Fixed",                        min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_ofixed")
                with _oc_right:
                    st.markdown("**Variable Overhead** *(changes with volume)*")
                    _oc_fuel   = st.number_input("Fuel & Transportation",              min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_fuel")
                    _oc_vmaint = st.number_input("Vehicle Maintenance & Repairs",      min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="oc_vmaint")
                    _oc_tools  = st.number_input("Tool Purchases & Repairs",           min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="oc_tools")
                    _oc_ppe    = st.number_input("Safety Equipment & PPE",             min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_ppe")
                    _oc_dump   = st.number_input("Dump Fees & Disposal",               min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="oc_dump")
                    _oc_mktg   = st.number_input("Marketing & Advertising",            min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="oc_mktg")
                    _oc_bank   = st.number_input("Bank Fees & Credit Card Fees",       min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="oc_bank")
                    _oc_misc   = st.number_input("Miscellaneous / Unexpected",         min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="oc_misc")
                    st.markdown("---")
                    st.markdown("**Revenue Base**")
                    _oc_revenue = st.number_input("Average Monthly Revenue ($)",
                                                  min_value=0.0, value=0.0, step=500.0,
                                                  format="%.2f", key="oc_revenue")
                _oc_fixed_total = (_oc_rent + _oc_veh + _oc_equip + _oc_gl + _oc_wc +
                                   _oc_auto + _oc_lic + _oc_legal + _oc_admin +
                                   _oc_phone + _oc_soft + _oc_ofixed)
                _oc_var_total   = (_oc_fuel + _oc_vmaint + _oc_tools + _oc_ppe +
                                   _oc_dump + _oc_mktg + _oc_bank + _oc_misc)
                _oc_total       = _oc_fixed_total + _oc_var_total
                _oc_pct_calc    = (_oc_total / _oc_revenue * 100) if _oc_revenue > 0 else None
                _kpi_css = (
                    "display:inline-block;background:#dbeafe;border:1px solid #93c5fd;"
                    "border-radius:8px;padding:10px 16px;margin:6px 4px;text-align:center;min-width:130px;"
                )
                _kpi_gold = _kpi_css.replace("#dbeafe","#fef3c7").replace("#93c5fd","#fcd34d")
                st.markdown(
                    f'<div style="margin-top:12px;">'
                    f'<div style="{_kpi_css}"><div style="font-size:11px;color:#1e40af;">Fixed Total</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_oc_fixed_total:,.2f}</div></div>'
                    f'<div style="{_kpi_css}"><div style="font-size:11px;color:#1e40af;">Variable Total</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_oc_var_total:,.2f}</div></div>'
                    f'<div style="{_kpi_css}"><div style="font-size:11px;color:#1e40af;">Total Overhead/mo</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_oc_total:,.2f}</div></div>'
                    + (
                        f'<div style="{_kpi_gold}"><div style="font-size:11px;color:#92400e;">Suggested %</div>'
                        f'<div style="font-size:19px;font-weight:700;color:#b45309;">{_oc_pct_calc:.1f}%</div></div>'
                        if _oc_pct_calc is not None
                        else f'<div style="{_kpi_css}"><div style="font-size:11px;color:#1e40af;">Suggested %</div>'
                             f'<div style="font-size:12px;color:#64748b;padding-top:4px;">Enter monthly revenue</div></div>'
                    )
                    + '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("<br>", unsafe_allow_html=True)
                if _oc_pct_calc is not None:
                    if st.button(f"✅ Apply {_oc_pct_calc:.1f}% to Overhead (sidebar)", key="oc_apply_btn"):
                        st.session_state["ovh_calc_suggested"] = round(_oc_pct_calc, 1)
                        st.session_state["c_overhead_pct"] = round(_oc_pct_calc, 1)
                        st.rerun()
                else:
                    st.info("Enter your average monthly revenue to calculate overhead %")

        st.caption("LYNSUS SUITE — All quantities must be verified before ordering.")

    else:
        # ─── GENERIC TRADE DISPLAY ───
        if job_name:
            st.markdown(f"<h3 style='color:#f0a500;margin-bottom:4px;'>{job_name}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='color:#8892a4;margin-bottom:16px;'>Trade: <b>{trade}</b> · Qty: <b>{total_quantity:,.1f} {unit_label}</b></p>", unsafe_allow_html=True)

        _gcol1, _gcol2 = st.columns([3, 2])

        with _gcol1:
            # Materials
            _g_mat_items_disp = [m for m in st.session_state["generic_materials"] if m["name"]]
            if _g_mat_items_disp:
                st.markdown('<div class="section-title">📦 Materials</div>', unsafe_allow_html=True)
                for _m in _g_mat_items_disp:
                    _sub = _m["qty"] * _m["price"]
                    st.markdown(f'<div class="line-item"><span class="name">{_m["name"]}</span><span class="qty">{_m["qty"]:.1f} {_m["unit"]} × ${_m["price"]:.2f}</span><span class="price">${_sub:,.2f}</span></div>', unsafe_allow_html=True)

            # Equipment
            if equip_items:
                st.markdown('<div class="section-title">🚜 Equipment</div>', unsafe_allow_html=True)
                for _eq in equip_items:
                    st.markdown(f'<div class="line-item"><span class="name">{_eq["name"]}</span><span class="qty">flat rate</span><span class="price">${_eq["cost"]:,.2f}</span></div>', unsafe_allow_html=True)

            # Subcontractors
            _g_sub_items_disp = [s for s in st.session_state["generic_subs"] if s["name"] and s["amount"] > 0]
            if _g_sub_items_disp:
                st.markdown('<div class="section-title">🤝 Subcontractors</div>', unsafe_allow_html=True)
                for _sub in _g_sub_items_disp:
                    _desc = f' — {_sub["desc"]}' if _sub.get("desc") else ""
                    st.markdown(f'<div class="line-item"><span class="name">{_sub["name"]}{_desc}</span><span class="qty">subcontract</span><span class="price">${_sub["amount"]:,.2f}</span></div>', unsafe_allow_html=True)

            # Labor
            if labor_cost > 0:
                st.markdown('<div class="section-title">👷 Labor</div>', unsafe_allow_html=True)
                _lqty = f"{total_quantity:,.1f} {unit_label} × ${labor_rate:.2f}/{unit_label}" if labor_rate > 0 else "flat total"
                st.markdown(f'<div class="line-item"><span class="name">Labor</span><span class="qty">{_lqty}</span><span class="price">${labor_cost:,.2f}</span></div>', unsafe_allow_html=True)

            # Demo
            if use_demo and demo_cost > 0:
                st.markdown('<div class="section-title">🔨 Demolition</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="line-item"><span class="name">Demolition</span><span class="qty">flat</span><span class="price">${demo_cost:,.2f}</span></div>', unsafe_allow_html=True)

            # Overhead & Profit
            st.markdown('<div class="section-title">📊 Overhead & Profit</div>', unsafe_allow_html=True)
            for _label, _amt in [
                ("Direct Cost Subtotal", direct_cost),
                (f"Overhead ({overhead_pct:.0f}%)", overhead_amt),
                ("Subtotal", subtotal),
                (f"Profit ({profit_pct:.0f}%)", profit_amt),
            ]:
                st.markdown(f'<div class="subtotal-row"><span style="color:#a0aec0;">{_label}</span><span style="color:#e0e0e0;font-weight:700;">${_amt:,.2f}</span></div>', unsafe_allow_html=True)

        with _gcol2:
            # Grand Total box
            st.markdown(f"""
<div class="total-box">
  <div style="color:#8892a4;font-size:12px;text-transform:uppercase;letter-spacing:2px;">Total Bid Price</div>
  <div class="total-amount">${grand_total:,.2f}</div>
  <div class="total-sqft">${price_per_sf:.2f} per {unit_label}</div>
</div>
""", unsafe_allow_html=True)

            # Cost Breakdown
            st.markdown('<div class="section-title">💰 Cost Breakdown</div>', unsafe_allow_html=True)
            _g_breakdown = [
                ("Materials",      _mat_cost_ss,  None),
                ("Equipment",      equip_total,   None),
                ("Subcontractors", _sub_cost_ss,  None),
                ("Labor",          labor_cost,    None),
                ("Demo",           demo_cost,     None),
                ("Overhead",       overhead_amt,  overhead_pct),
                ("Profit",         profit_amt,    profit_pct),
            ]
            for _lbl, _amt, _fpct in _g_breakdown:
                if _amt > 0:
                    _pct = _fpct if _fpct is not None else (_amt / grand_total * 100 if grand_total > 0 else 0)
                    st.markdown(f'<div class="result-row"><span style="color:#a0aec0;">{_lbl}</span><span style="color:#e0e0e0;font-weight:600;">${_amt:,.2f} <span style="color:#8892a4;font-size:11px;">({_pct:.0f}%)</span></span></div>', unsafe_allow_html=True)

            st.markdown("---")

            # Overhead Calculator (inside _gcol2)
            with st.expander("🧮 Overhead Calculator", expanded=False):
                st.markdown(
                    '<p style="color:#dc2626;font-weight:600;font-size:13px;">'
                    "⚠️ This tool provides an estimate only. Results are not financial or "
                    "accounting advice. Verify all figures with a licensed CPA before use.</p>",
                    unsafe_allow_html=True,
                )
                _goc_l, _goc_r = st.columns(2)
                with _goc_l:
                    st.markdown("**Fixed Overhead** *(same every month)*")
                    _goc_rent  = st.number_input("Office / Warehouse Rent",          min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_rent")
                    _goc_veh   = st.number_input("Vehicle Payments",                  min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_veh")
                    _goc_equip = st.number_input("Equipment Payments / Leases",       min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_equip")
                    _goc_gl    = st.number_input("General Liability Insurance",       min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_gl")
                    _goc_wc    = st.number_input("Workers Comp Insurance",            min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_wc")
                    _goc_auto  = st.number_input("Commercial Auto Insurance",         min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_auto")
                    _goc_lic   = st.number_input("Licenses & Permits (÷12)",         min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_lic")
                    _goc_leg   = st.number_input("Accounting / Legal (÷12)",         min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_leg")
                    _goc_adm   = st.number_input("Administrative Salaries",           min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_adm")
                    _goc_ph    = st.number_input("Phone & Internet",                  min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_ph")
                    _goc_sw    = st.number_input("Software & Subscriptions",          min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_sw")
                    _goc_of    = st.number_input("Other Fixed",                       min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_of")
                with _goc_r:
                    st.markdown("**Variable Overhead** *(changes with volume)*")
                    _goc_fuel  = st.number_input("Fuel & Transportation",             min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_fuel")
                    _goc_vm    = st.number_input("Vehicle Maintenance & Repairs",     min_value=0.0, value=0.0, step=50.0,  format="%.2f", key="goc_vm")
                    _goc_tl    = st.number_input("Tool Purchases & Repairs",          min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="goc_tl")
                    _goc_ppe   = st.number_input("Safety Equipment & PPE",            min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_ppe")
                    _goc_dmp   = st.number_input("Dump Fees & Disposal",              min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="goc_dmp")
                    _goc_mkt   = st.number_input("Marketing & Advertising",           min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="goc_mkt")
                    _goc_bk    = st.number_input("Bank & Credit Card Fees",           min_value=0.0, value=0.0, step=10.0,  format="%.2f", key="goc_bk")
                    _goc_ms    = st.number_input("Miscellaneous / Unexpected",        min_value=0.0, value=0.0, step=25.0,  format="%.2f", key="goc_ms")
                    st.markdown("---")
                    st.markdown("**Revenue Base**")
                    _goc_rev = st.number_input("Average Monthly Revenue ($)", min_value=0.0, value=0.0, step=500.0, format="%.2f", key="goc_rev")
                _goc_fix = (_goc_rent + _goc_veh + _goc_equip + _goc_gl + _goc_wc + _goc_auto +
                            _goc_lic + _goc_leg + _goc_adm + _goc_ph + _goc_sw + _goc_of)
                _goc_var = _goc_fuel + _goc_vm + _goc_tl + _goc_ppe + _goc_dmp + _goc_mkt + _goc_bk + _goc_ms
                _goc_tot = _goc_fix + _goc_var
                _goc_pct = (_goc_tot / _goc_rev * 100) if _goc_rev > 0 else None
                _gkpi = (
                    "display:inline-block;background:#dbeafe;border:1px solid #93c5fd;"
                    "border-radius:8px;padding:10px 16px;margin:6px 4px;text-align:center;min-width:130px;"
                )
                _gkpi_g = _gkpi.replace("#dbeafe","#fef3c7").replace("#93c5fd","#fcd34d")
                st.markdown(
                    f'<div style="margin-top:12px;">'
                    f'<div style="{_gkpi}"><div style="font-size:11px;color:#1e40af;">Fixed Total</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_goc_fix:,.2f}</div></div>'
                    f'<div style="{_gkpi}"><div style="font-size:11px;color:#1e40af;">Variable Total</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_goc_var:,.2f}</div></div>'
                    f'<div style="{_gkpi}"><div style="font-size:11px;color:#1e40af;">Total Overhead/mo</div>'
                    f'<div style="font-size:15px;font-weight:700;color:#1d4ed8;">${_goc_tot:,.2f}</div></div>'
                    + (
                        f'<div style="{_gkpi_g}"><div style="font-size:11px;color:#92400e;">Suggested %</div>'
                        f'<div style="font-size:19px;font-weight:700;color:#b45309;">{_goc_pct:.1f}%</div></div>'
                        if _goc_pct is not None
                        else f'<div style="{_gkpi}"><div style="font-size:11px;color:#1e40af;">Suggested %</div>'
                             f'<div style="font-size:12px;color:#64748b;padding-top:4px;">Enter monthly revenue</div></div>'
                    )
                    + '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown("<br>", unsafe_allow_html=True)
                if _goc_pct is not None:
                    if st.button(f"✅ Apply {_goc_pct:.1f}% to Overhead", key="goc_apply"):
                        st.session_state["ovh_calc_suggested"] = round(_goc_pct, 1)
                        st.session_state["g_overhead_pct"] = round(_goc_pct, 1)
                        st.rerun()
                else:
                    st.info("Enter your average monthly revenue to calculate overhead %")

        st.caption("LYNSUS SUITE — All quantities must be verified before ordering.")


# ─────────────────────── TAB 2: CLIENT QUOTE ─────────────────────
elif st.session_state["active_tab"] == 1:
    # ── Aliases from session_state (single source of truth) ──
    _q_sqft      = st.session_state.get("total_sqft",     0.0)
    _q_total_bid = st.session_state.get("total_bid",      0.0)
    _q_ppsf      = st.session_state.get("price_per_sqft", 0.0)

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

    # ── client-facing price: total bid (equipment already factored in) ──
    scope_subtotal = _q_total_bid
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
        f'{st.session_state.get("pdf_scope_label","Flatwork Concrete Installation")}</div>'
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
        f'letter-spacing:3px;text-transform:uppercase;margin-bottom:4px;">{st.session_state.get("pdf_company_name","LYNSUS CONTRACTING")}</div>'
        f'<div style="text-align:center;color:#8892a4;font-size:12px;margin-bottom:24px;">'
        f'{st.session_state.get("pdf_tagline","Flatwork Concrete — Driveways · Sidewalks · Patios")}</div>'
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
            company_name=st.session_state.get("pdf_company_name", "LYNSUS CONTRACTING"),
            tagline=st.session_state.get("pdf_tagline", "Flatwork Concrete — Driveways · Sidewalks · Patios"),
            scope_label=st.session_state.get("pdf_scope_label", "Flatwork Concrete Installation"),
            logo_bytes=st.session_state.get("pdf_logo_bytes"),
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
elif st.session_state["active_tab"] == 2:
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
elif st.session_state["active_tab"] == 3:
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
                company_name=st.session_state.get("pdf_company_name", "LYNSUS CONTRACTING"),
                logo_bytes=st.session_state.get("pdf_logo_bytes"),
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
elif st.session_state["active_tab"] == 4:

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
    # Sync extracted project info into widget keys before rendering
    for _src, _dst in [
        ("_ca_proj_extracted", "ca_proj_name"),
        ("_ca_gc_extracted",   "ca_gc_name"),
        ("_ca_job_extracted",  "ca_job_num"),
    ]:
        if st.session_state.get(_src):
            st.session_state[_dst] = st.session_state.pop(_src)

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
                        st.session_state["_ca_proj_extracted"] = _proj
                except Exception:
                    pass
                try:
                    _job = _ws.cell_value(5, 9)
                    if _job:
                        st.session_state["_ca_job_extracted"] = str(int(_job)) if isinstance(_job, float) else str(_job).strip()
                except Exception:
                    pass
                try:
                    _gc = str(_ws.cell_value(7, 5)).strip()
                    if _gc and _gc != "0.0":
                        st.session_state["_ca_gc_extracted"] = _gc
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
            _ca_raw   = contract_pdf.read()
            _ca_text  = ""
            _pdf_tables = []

            with _pdfplumber_ca.open(io.BytesIO(_ca_raw)) as _ca_pdf:
                for _ca_page in _ca_pdf.pages:
                    _ca_text += (_ca_page.extract_text() or "") + "\n"
                    _page_tables = _ca_page.extract_tables()
                    if _page_tables:
                        _pdf_tables.extend(_page_tables)

            _is_g703 = "G703" in _ca_text.upper() or "CONTINUATION SHEET" in _ca_text.upper() or "SCHEDULED VALUE" in _ca_text.upper()

            # ── Extract line items from tables ────────────────────
            _pdf_line_items = []
            _pdf_total_from_table = 0.0

            for _tbl in _pdf_tables:
                if not _tbl or len(_tbl) < 3:
                    continue

                # Find the header row — must contain "Description" AND ("Amount" or "Rate")
                _hdr_row_idx = None
                _desc_col_t  = None
                _amt_col     = None
                _qty_col     = None

                for _ri, _row in enumerate(_tbl):
                    if not _row:
                        continue
                    _cells = [str(c).upper().strip() if c else "" for c in _row]
                    _has_desc = any("DESCRIPTION" in c or "WORK" in c for c in _cells)
                    _has_amt  = any("AMOUNT" in c or "PRICE" in c or "VALUE" in c for c in _cells)
                    if _has_desc and _has_amt:
                        _hdr_row_idx = _ri
                        for _ci, _c in enumerate(_cells):
                            if "DESCRIPTION" in _c or "WORK" in _c:
                                _desc_col_t = _ci
                            if "AMOUNT" in _c or "PRICE" in _c or "VALUE" in _c:
                                _amt_col = _ci
                            if "QTY" in _c or "QUANTITY" in _c:
                                _qty_col = _ci
                        break

                # Skip tables without a proper line item header
                if _hdr_row_idx is None or _desc_col_t is None or _amt_col is None:
                    continue

                # Process data rows after the header
                for _row in _tbl[_hdr_row_idx + 1:]:
                    if not _row or len(_row) <= _amt_col:
                        continue

                    _desc_val = str(_row[_desc_col_t] or "").strip()
                    _amt_raw  = str(_row[_amt_col] or "").strip()

                    # Skip empty rows
                    if not _desc_val or not _amt_raw:
                        continue

                    # Skip header-like repeats
                    if any(k in _desc_val.upper() for k in ["DESCRIPTION", "ITEM", "AMOUNT", "RATE", "QTY"]):
                        continue

                    # Parse the amount — extract only digits and decimal point
                    _amt_clean = re.sub(r"[^\d.]", "", _amt_raw.replace(",", ""))
                    try:
                        _amt_float = float(_amt_clean)
                    except (ValueError, TypeError):
                        continue

                    if _amt_float <= 0:
                        continue

                    # Detect total row — "Total" in any cell of this row
                    _row_text = " ".join(str(c or "") for c in _row).upper()
                    _is_total_row = any(k in _row_text for k in ["TOTAL", "GRAND TOTAL", "SUBTOTAL"])

                    if _is_total_row:
                        if _amt_float > _pdf_total_from_table:
                            _pdf_total_from_table = _amt_float
                    else:
                        # Skip rows where qty is 0 (header filler rows)
                        if _qty_col is not None:
                            _qty_raw = str(_row[_qty_col] or "").strip()
                            try:
                                if float(re.sub(r"[^\d.]", "", _qty_raw)) == 0:
                                    continue
                            except (ValueError, TypeError):
                                pass
                        if len(_desc_val) > 1:
                            _pdf_line_items.append({"description": _desc_val, "value": _amt_float})

            if _pdf_line_items:
                _sum_items = sum(i["value"] for i in _pdf_line_items)
                # Use the explicit total row if found, otherwise sum of items
                _pdf_total_from_table = _pdf_total_from_table if _pdf_total_from_table > 0 else _sum_items
                st.session_state["ca_line_items"]  = _pdf_line_items
                st.session_state["ca_total"]       = _pdf_total_from_table
                st.session_state["ca_total_input"] = _pdf_total_from_table

            # ── Extract SQFT ──────────────────────────────────────
            _sqft_found = None
            for _pat in [r"(\d[\d,]+)\s*(?:sq\.?\s*ft|square\s*feet|sqft)", r"(\d[\d,]+)\s*SF\b"]:
                _m = re.search(_pat, _ca_text, re.IGNORECASE)
                if _m:
                    _sqft_found = float(_m.group(1).replace(",", ""))
                    break

            # ── Extract Total from text if no table items ─────────
            _total_found = None
            if not _pdf_line_items:
                for _pat in [
                    r"(?:Total\s+Authorized\s+Amount)[^\d\$]*\$?\s*([\d,]+(?:\.\d{2})?)",
                    r"(?:total|contract\s*(?:amount|price|value)|lump\s*sum|bid\s*amount)[^\d\$]*\$?\s*([\d,]+(?:\.\d{2})?)",
                    r"\$\s*([\d,]+\.\d{2})",
                ]:
                    _m = re.search(_pat, _ca_text, re.IGNORECASE)
                    if _m:
                        _val = float(_m.group(1).replace(",", ""))
                        if _val > 1000:
                            _total_found = _val
                            break

            if _sqft_found:
                st.session_state["ca_sqft"] = _sqft_found
            if _total_found and not _pdf_line_items:
                st.session_state["ca_total"]       = _total_found
                st.session_state["ca_total_input"] = _total_found

            st.session_state["ca_scope_text"] = _ca_text[:800].strip()

            # ── Extract project info ──────────────────────────────
            _po_m = re.search(r"Purchase\s+Order\s+#?([\w.\-]+)", _ca_text, re.IGNORECASE)
            if not _po_m:
                _po_m = re.search(r"P\.?O\.?\s*No\.?\s*[:\-]?\s*([\w.\-]+)", _ca_text, re.IGNORECASE)
            if _po_m:
                st.session_state["_ca_job_extracted"] = _po_m.group(1).strip()

            _gc_m = re.search(r'between\s+(\w[\w\s]{1,30}?)\s*\([\u201c\u201d"\']?Contractor', _ca_text)
            if not _gc_m:
                _gc_m = re.search(r'Ship\s+To\s*\n\s*([A-Z][^\n]{3,40})', _ca_text)
            if _gc_m:
                _gc_val = _gc_m.group(1).strip().strip('"').strip("'")
                if len(_gc_val) > 1:
                    st.session_state["_ca_gc_extracted"] = _gc_val

            _loc_m = re.search(r"Project\s+Location\s*:\s*([^\n]{5,80})", _ca_text, re.IGNORECASE)
            if not _loc_m:
                _loc_m = re.search(r"Job\s*\n\s*([A-Z][^\n]{2,50})", _ca_text)
            if _loc_m and not st.session_state.get("ca_proj_name"):
                st.session_state["_ca_proj_extracted"] = _loc_m.group(1).strip()

            # ── Status message ────────────────────────────────────
            _n_items     = len(st.session_state.get("ca_line_items", []))
            _final_total = st.session_state.get("ca_total", 0.0)
            _format_label = "AIA G703" if _is_g703 else ("Purchase Order" if _n_items > 0 else "Generic Contract")

            if _n_items > 0:
                st.success(f"✅ {_format_label} — {_n_items} line items — Total: **${_final_total:,.2f}**")
            elif _sqft_found or _final_total > 0:
                st.success(f"✅ {_format_label} detected — "
                           f"{"SQFT: " + f"{_sqft_found:,.0f}" if _sqft_found else "SQFT: not found"}  |  "
                           f"{"Total: $" + f"{_final_total:,.2f}" if _final_total else "Total: not found"}")
            else:
                st.warning(f"{_format_label} detected but could not extract numbers. Enter manually below.")

            # ── Show line items from PDF ──────────────────────────
            _loaded_pdf_items = st.session_state.get("ca_line_items", [])
            if _loaded_pdf_items and contract_pdf is not None:
                st.markdown('<div class="section-title">📋 Contract Line Items (from PDF)</div>', unsafe_allow_html=True)
                st.caption("⚠️ Verify every line — confirm nothing is missing before proceeding.")
                for _li in _loaded_pdf_items:
                    st.markdown(
                        f'<div style="display:flex;justify-content:space-between;padding:7px 12px;'
                        f'background:#1c2333;border-radius:6px;margin:2px 0;">'
                        f'<span style="color:#e0e0e0;font-size:13px;">{_li["description"]}</span>'
                        f'<span style="color:#f0a500;font-weight:700;font-size:13px;">${_li["value"]:,.2f}</span>'
                        f'</div>', unsafe_allow_html=True
                    )
                _sum_li = sum(i["value"] for i in _loaded_pdf_items)
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;padding:9px 12px;'
                    f'background:#252d3d;border-radius:6px;margin:4px 0;border-left:3px solid #f0a500;">'
                    f'<span style="color:#f0a500;font-weight:700;">LINE ITEMS TOTAL</span>'
                    f'<span style="color:#f0a500;font-weight:900;font-size:16px;">${_sum_li:,.2f}</span>'
                    f'</div>', unsafe_allow_html=True
                )

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
            _ca_days_req = max(math.ceil(ca_sqft / _ca_prod_rate), 1) if _ca_prod_rate > 0 else 1
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
                company_name   = st.session_state.get("pdf_company_name", "LYNSUS CONTRACTING"),
                logo_bytes     = st.session_state.get("pdf_logo_bytes"),
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
