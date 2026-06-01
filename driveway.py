import streamlit as st
import math
import io
import base64
import pandas as pd
import datetime

st.set_page_config(page_title="Driveway Estimator Pro", page_icon="🏗️", layout="wide")

# ══════════════════════════════════════════════
# FIELD-TESTED CONSTANTS
# ══════════════════════════════════════════════

# Concrete divisors: CY = SQFT / divisor  (already accounts for 27 cf/CY conversion)
CONC_DIVISORS = {
    4:  81,
    6:  54,
    8:  40,
    12: 27,
}

# Rebar factors: LF = SQFT × factor  (bidirectional grid)
REBAR_FACTORS = {
    12: 0.1100,
    14: 0.0940,
    15: 0.0880,
    16: 0.0827,
    18: 0.0733,
    24: 0.0550,
}

# Concrete yardage by driveway dimension (width × truck-length segments)
# Format: (width_ft, truck_length_ft): divisor
# These are field-tested divisors that include slab + footing volume
YARDAGE_TABLE = {
    (12, 24): 34, (12, 26): 32, (12, 28): 30, (12, 30): 28,
    (10, 24): 35, (10, 26): 33, (10, 28): 31, (10, 30): 29,
    (10, 25): 34, (10, 27): 32, (10, 29): 30,
}

# ══════════════════════════════════════════════
# SESSION STATE
# ══════════════════════════════════════════════
for k, v in {"company_name": "My Company", "logo_b64": None}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════
st.markdown("""
<style>
body { background-color: #0e1117; color: #e0e0e0; }
.header-bar {
    background: #1c2333; border-left: 5px solid #f0a500;
    padding: 18px 24px; border-radius: 6px; margin-bottom: 24px;
    display: flex; align-items: center; gap: 20px;
}
.company-name { font-size: 26px; font-weight: 800; color: #f0a500;
    letter-spacing: 2px; text-transform: uppercase; }
.section {
    background: #1c2333; border-left: 4px solid #f0a500;
    padding: 8px 16px; margin: 16px 0 8px 0;
    font-size: 12px; color: #f0a500;
    text-transform: uppercase; letter-spacing: 2px;
}
.formula-box {
    background: #0e1117; border: 1px solid #f0a500;
    border-radius: 6px; padding: 12px 16px; margin: 4px 0;
    font-family: monospace; font-size: 13px; color: #e0e0e0;
}
.warn-box {
    background: #2d1a00; border: 1px solid #f0a500;
    border-radius: 6px; padding: 10px 14px; color: #f0a500;
    font-size: 13px; margin: 8px 0;
}
.stButton > button { background: #f0a500; color: #000; font-weight: 700; border: none; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Company Setup")
    company = st.text_input("Company Name", value=st.session_state.company_name)
    st.session_state.company_name = company

    logo_file = st.file_uploader("Upload Logo (PNG/JPG)", type=["png","jpg","jpeg"])
    if logo_file:
        b64 = base64.b64encode(logo_file.read()).decode()
        ext = logo_file.name.split(".")[-1]
        st.session_state.logo_b64 = f"data:image/{ext};base64,{b64}"
        st.success("Logo uploaded ✓")
    if st.session_state.logo_b64:
        st.image(st.session_state.logo_b64, width=120)

    st.markdown("---")
    st.markdown("## 🗑️ Waste Factors")
    st.caption("Added on top of field formulas to prevent shortages")
    waste_conc   = st.number_input("Concrete %",       0.0, 20.0, 8.0,  0.5) / 100
    waste_rebar  = st.number_input("Rebar %",          0.0, 20.0, 10.0, 0.5) / 100
    waste_lumber = st.number_input("Lumber / Forms %", 0.0, 20.0, 10.0, 0.5) / 100
    waste_stakes = st.number_input("Stakes %",         0.0, 20.0, 5.0,  0.5) / 100
    waste_poly   = st.number_input("Poly / Plastic %", 0.0, 20.0, 10.0, 0.5) / 100

    st.markdown("---")
    st.caption("Driveway Estimator Pro v2.0")

# ══════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════
logo_html = f'<img src="{st.session_state.logo_b64}" style="height:60px;border-radius:4px;">' if st.session_state.logo_b64 else ""
st.markdown(f"""
<div class="header-bar">
    {logo_html}
    <div>
        <div class="company-name">{st.session_state.company_name}</div>
        <div style="color:#8892a4;font-size:13px;">Driveway Estimator Pro — Field-Formula Engine</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["📐 TAKEOFF", "💰 PRICES & ESTIMATE", "📄 QUOTE", "📊 FORMULA REFERENCE"])


# ─────────────────────── TAB 1: TAKEOFF ───────────────────────
with tab1:

    # ── Project Dimensions ──
    st.markdown('<div class="section">📐 Project Dimensions</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)
    sqft      = d1.number_input("Total Area (SQFT)", value=500.0, min_value=1.0, step=10.0)
    width_ft  = d2.number_input("Driveway Width (ft)", value=12.0, min_value=1.0, step=1.0)
    perimeter = d3.number_input("Perimeter (LF)", value=90.0, min_value=1.0, step=1.0)
    length_ft = sqft / width_ft if width_ft > 0 else 0
    d4.metric("Calculated Length", f"{length_ft:.1f} ft")

    # ── CONCRETE ──
    st.markdown('<div class="section">🏗️ Concrete — Field Formula: CY = SQFT ÷ Divisor</div>', unsafe_allow_html=True)

    thick_options = [4, 6, 8, 12]
    c1, c2, c3 = st.columns(3)
    thickness = c1.selectbox("Slab Thickness (inches)", thick_options, index=0)
    conc_price= c2.number_input("Concrete ($/CY)", value=165.0, min_value=0.0, step=1.0, format="%.2f")

    divisor      = CONC_DIVISORS[thickness]
    cy_raw       = sqft / divisor
    cy_w         = math.ceil(cy_raw * (1 + waste_conc))

    c3.markdown(f"""
<div class="formula-box">
SQFT {sqft:,.0f} ÷ {divisor} = <strong>{cy_raw:.2f} CY raw</strong><br>
+{waste_conc*100:.0f}% waste → <strong style="color:#f0a500;">{cy_w} CY to order</strong>
</div>
""", unsafe_allow_html=True)

    # ── REBAR ──
    st.markdown('<div class="section">🔩 Rebar — Field Formula: LF = SQFT × Factor</div>', unsafe_allow_html=True)

    r1, r2, r3, r4 = st.columns(4)
    rebar_size   = r1.selectbox("Rebar Size", ["#3", "#4", "#5"], index=1)
    spacing_in   = r2.selectbox("Spacing O.C. (inches)", list(REBAR_FACTORS.keys()), index=4, format_func=lambda x: f'{x}"')
    bar_len_ft   = r3.number_input("Bar Length (ft)", value=20.0, min_value=10.0, max_value=60.0, step=2.0)
    rebar_price  = r4.number_input("Price per Bar ($)", value=8.50, min_value=0.0, step=0.25, format="%.2f")

    factor       = REBAR_FACTORS[spacing_in]
    rebar_lf_raw = sqft * factor
    rebar_lf_w   = rebar_lf_raw * (1 + waste_rebar)
    rebar_bars   = math.ceil(rebar_lf_w / bar_len_ft)

    st.markdown(f"""
<div class="formula-box">
SQFT {sqft:,.0f} × {factor} ({spacing_in}" O.C.) = <strong>{rebar_lf_raw:,.1f} LF raw</strong>
+{waste_rebar*100:.0f}% waste = {rebar_lf_w:,.1f} LF
÷ {bar_len_ft:.0f} ft bars = <strong style="color:#f0a500;">{rebar_bars} bars to order</strong>
</div>
""", unsafe_allow_html=True)

    # ── LUMBER / FORMS ──
    st.markdown('<div class="section">🪵 Lumber & Forms</div>', unsafe_allow_html=True)
    l1, l2, l3, l4 = st.columns(4)
    lumber_size   = l1.selectbox("Board Size", ["2x4","2x6","2x8"], index=1)
    board_len_ft  = l2.number_input("Board Length (ft)", value=16.0, min_value=8.0, step=2.0)
    boards_stacked= l3.number_input("Boards per side (stacked)", value=1, min_value=1, max_value=4, step=1)
    lumber_price  = l4.number_input("Price per Board ($)", value=7.50, min_value=0.0, step=0.25, format="%.2f")

    lumber_lf_raw = perimeter * boards_stacked
    lumber_lf_w   = lumber_lf_raw * (1 + waste_lumber)
    lumber_boards = math.ceil(lumber_lf_w / board_len_ft)

    st.markdown(f"""
<div class="formula-box">
Perimeter {perimeter:.0f} LF × {boards_stacked} stacked = {lumber_lf_raw:.0f} LF raw
+{waste_lumber*100:.0f}% waste = {lumber_lf_w:.1f} LF ÷ {board_len_ft:.0f} ft = <strong style="color:#f0a500;">{lumber_boards} boards to order</strong>
</div>
""", unsafe_allow_html=True)

    # ── STAKES ──
    st.markdown('<div class="section">🔴 Red Stakes</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    stake_spacing = s1.number_input("Stake Spacing (ft)", value=4.0, min_value=1.0, max_value=8.0, step=0.5)
    stake_price   = s2.number_input("Price per Stake ($)", value=0.75, min_value=0.0, step=0.05, format="%.2f")

    stakes_raw = perimeter / stake_spacing
    stakes_w   = math.ceil(stakes_raw * (1 + waste_stakes))
    s3.markdown(f"""
<div class="formula-box">
{perimeter:.0f} LF ÷ {stake_spacing} ft = {stakes_raw:.1f} raw
+{waste_stakes*100:.0f}% = <strong style="color:#f0a500;">{stakes_w} stakes</strong>
</div>
""", unsafe_allow_html=True)
    s4.metric("Stakes to order", f"{stakes_w} pcs")

    # ── EXPANSION JOINTS ──
    st.markdown('<div class="section">📏 Expansion Joints</div>', unsafe_allow_html=True)
    ej1, ej2, ej3, ej4 = st.columns(4)
    ej_spacing = ej1.number_input("EJ Spacing (ft)", value=10.0, min_value=4.0, max_value=20.0, step=1.0)
    ej_price   = ej2.number_input("EJ Price ($/LF)", value=0.65, min_value=0.0, step=0.05, format="%.2f")

    num_ej    = math.floor(length_ft / ej_spacing) if ej_spacing > 0 else 0
    ej_lf_raw = num_ej * width_ft
    ej_lf_w   = math.ceil(ej_lf_raw * 1.05)

    ej3.markdown(f"""
<div class="formula-box">
Length {length_ft:.1f} ft ÷ {ej_spacing:.0f} ft = {num_ej} joints<br>
× {width_ft:.0f} ft wide = {ej_lf_raw:.0f} LF → <strong style="color:#f0a500;">{ej_lf_w} LF (+5%)</strong>
</div>
""", unsafe_allow_html=True)
    ej4.metric("EJ to order", f"{ej_lf_w} LF")

    # ── GRAVEL & POLY ──
    st.markdown('<div class="section">🛡️ Gravel Base & Poly</div>', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns(4)
    gravel_depth = g1.number_input("Gravel Depth (in)", value=4.0, min_value=0.0, max_value=12.0, step=1.0)
    gravel_price = g2.number_input("Gravel ($/CY)", value=42.0, min_value=0.0, step=1.0, format="%.2f")
    poly_price   = g3.number_input("Poly ($/SQFT)", value=0.08, min_value=0.0, step=0.01, format="%.3f")

    # Gravel uses same divisor logic: depth in inches
    gravel_divisor = 324 / gravel_depth if gravel_depth > 0 else 999  # (27*12)/depth
    gravel_cy_raw  = sqft / gravel_divisor if gravel_depth > 0 else 0
    gravel_cy_w    = math.ceil(gravel_cy_raw * 1.10)
    poly_sqft_w    = math.ceil(sqft * (1 + waste_poly))

    g4.markdown(f"""
<div class="formula-box">
Gravel: {gravel_cy_raw:.2f} CY raw → <strong style="color:#f0a500;">{gravel_cy_w} CY (+10%)</strong><br>
Poly: {sqft:.0f} sqft → <strong style="color:#f0a500;">{poly_sqft_w} sqft (+{waste_poly*100:.0f}%)</strong>
</div>
""", unsafe_allow_html=True)

    # ── TAKEOFF SUMMARY ──
    st.markdown("---")
    st.markdown('<div class="section">📊 Complete Takeoff Summary</div>', unsafe_allow_html=True)
    m1,m2,m3,m4,m5,m6,m7 = st.columns(7)
    m1.metric("Concrete",         f"{cy_w} CY",          delta=f"raw {cy_raw:.1f}")
    m2.metric(f"Rebar {rebar_size}", f"{rebar_bars} bars", delta=f"{rebar_lf_w:.0f} LF")
    m3.metric(f"Lumber {lumber_size}",f"{lumber_boards} pcs", delta=f"{lumber_lf_w:.0f} LF")
    m4.metric("Red Stakes",       f"{stakes_w} pcs")
    m5.metric("Expansion Joints", f"{ej_lf_w} LF",        delta=f"{num_ej} joints")
    m6.metric("Gravel Base",      f"{gravel_cy_w} CY")
    m7.metric("Poly",             f"{poly_sqft_w} sqft")

    st.markdown(f"""
<div class="warn-box">
⚠️ <strong>Verify before ordering.</strong> These quantities include waste factors.
Concrete: {cy_raw:.2f} raw → {cy_w} CY ordered (+{waste_conc*100:.0f}%).
Rebar: {rebar_lf_raw:.0f} raw LF → {rebar_bars} bars (+{waste_rebar*100:.0f}%).
</div>
""", unsafe_allow_html=True)


# ─────────────────────── TAB 2: PRICES ───────────────────────
with tab2:
    st.markdown('<div class="section">💰 Materials Cost</div>', unsafe_allow_html=True)

    mat_rows = [
        {"Material": f"Concrete {thickness}\"",    "Qty": cy_w,          "Unit": "CY",   "Unit $": conc_price,   "Total": cy_w          * conc_price},
        {"Material": f"Rebar {rebar_size} ({spacing_in}\" O.C.)", "Qty": rebar_bars, "Unit": "bars", "Unit $": rebar_price,  "Total": rebar_bars    * rebar_price},
        {"Material": f"Lumber {lumber_size}",      "Qty": lumber_boards, "Unit": "pcs",  "Unit $": lumber_price, "Total": lumber_boards * lumber_price},
        {"Material": "Red Stakes",                 "Qty": stakes_w,      "Unit": "pcs",  "Unit $": stake_price,  "Total": stakes_w      * stake_price},
        {"Material": "Expansion Joints",           "Qty": ej_lf_w,       "Unit": "LF",   "Unit $": ej_price,     "Total": ej_lf_w       * ej_price},
        {"Material": "Gravel Base",                "Qty": gravel_cy_w,   "Unit": "CY",   "Unit $": gravel_price, "Total": gravel_cy_w   * gravel_price},
        {"Material": "Poly / Plastic",             "Qty": poly_sqft_w,   "Unit": "SQFT", "Unit $": poly_price,   "Total": poly_sqft_w   * poly_price},
    ]
    mat_df    = pd.DataFrame(mat_rows)
    total_mat = mat_df["Total"].sum()

    display_mat = mat_df.copy()
    display_mat["Unit $"] = display_mat["Unit $"].map("${:,.2f}".format)
    display_mat["Total"]  = display_mat["Total"].map("${:,.2f}".format)
    st.dataframe(display_mat, use_container_width=True, hide_index=True)
    st.metric("🧱 TOTAL MATERIALS", f"${total_mat:,.2f}")

    # ── LABOR ──
    st.markdown('<div class="section">👷 Labor</div>', unsafe_allow_html=True)
    labor_mode    = st.radio("Labor input mode", ["💰 Lump Sum", "📐 Per SQFT"], horizontal=True)
    use_sqft_mode = "SQFT" in labor_mode
    if use_sqft_mode:
        st.info(f"Project area: **{sqft:,.0f} SQFT**")

    def lab(label, default_ls, default_sqft, col):
        if use_sqft_mode:
            rate  = col.number_input(f"{label} ($/sqft)", value=default_sqft, min_value=0.0, step=0.01, format="%.3f")
            total = rate * sqft
            col.caption(f"= ${total:,.2f}")
            return total
        return col.number_input(f"{label} ($)", value=default_ls, min_value=0.0, step=25.0, format="%.2f")

    la, lb, lc, ld = st.columns(4)
    l_grading = lab("Grading / Excavation", 400.0,  0.80, la)
    l_forms   = lab("Set Forms",            600.0,  1.20, lb)
    l_rebar_i = lab("Rebar Install",        350.0,  0.70, lc)
    l_finish  = lab("Finish / Trowel",      500.0,  1.00, ld)

    le, lf_col, lg, lh = st.columns(4)
    l_strip   = lab("Strip Forms",          250.0,  0.50, le)
    l_cure    = lab("Cure / Seal",          200.0,  0.40, lf_col)
    l_cleanup = lab("Cleanup",              150.0,  0.30, lg)

    total_lab = l_grading + l_forms + l_rebar_i + l_finish + l_strip + l_cure + l_cleanup

    # ── EQUIPMENT ──
    st.markdown('<div class="section">🚜 Equipment</div>', unsafe_allow_html=True)
    eq1, eq2, eq3 = st.columns(3)
    use_pump  = eq1.checkbox("Concrete Pump")
    use_buggy = eq2.checkbox("Buggy / Power Buggy")
    use_mach  = eq3.checkbox("Other Machinery")
    pump_cost  = eq1.number_input("Pump ($)",     value=800.0, min_value=0.0, step=50.0, format="%.2f") if use_pump  else 0.0
    buggy_cost = eq2.number_input("Buggy ($)",    value=300.0, min_value=0.0, step=25.0, format="%.2f") if use_buggy else 0.0
    mach_cost  = eq3.number_input("Machinery ($)",value=0.0,   min_value=0.0, step=50.0, format="%.2f") if use_mach  else 0.0
    total_equip = pump_cost + buggy_cost + mach_cost

    # ── FINANCIAL SUMMARY ──
    st.markdown('<div class="section">📊 Financial Summary</div>', unsafe_allow_html=True)
    profit_pct = st.number_input("Profit Margin (%)", 0.0, 100.0, 20.0, 0.5)

    subtotal   = total_mat + total_lab + total_equip
    profit_amt = subtotal * (profit_pct / 100)
    grand      = subtotal + profit_amt

    s1,s2,s3,s4,s5 = st.columns(5)
    s1.metric("Materials",              f"${total_mat:,.2f}")
    s2.metric("Labor",                  f"${total_lab:,.2f}")
    s3.metric("Equipment",              f"${total_equip:,.2f}")
    s4.metric(f"Profit ({profit_pct:.0f}%)", f"${profit_amt:,.2f}")
    s5.metric("🔥 GRAND TOTAL",         f"${grand:,.2f}")

    if sqft > 0:
        st.markdown("---")
        p1,p2,p3 = st.columns(3)
        p1.metric("$/SQFT Materials", f"${total_mat/sqft:,.2f}")
        p2.metric("$/SQFT Labor",     f"${total_lab/sqft:,.2f}")
        p3.metric("$/SQFT Total",     f"${grand/sqft:,.2f}")


# ─────────────────────── TAB 3: QUOTE ───────────────────────
with tab3:
    st.markdown('<div class="section">📄 Client Quote</div>', unsafe_allow_html=True)

    client_name    = st.text_input("Client Name", "")
    client_address = st.text_input("Project Address", "")
    client_phone   = st.text_input("Client Phone", "")
    quote_notes    = st.text_area(
        "Scope of Work",
        f"Concrete driveway installation — {sqft:,.0f} SQFT, {thickness}\" thick. "
        "Includes: excavation, gravel base, poly, forms, rebar, concrete, finishing, expansion joints and cleanup.",
        height=80,
    )
    today = datetime.date.today().strftime("%B %d, %Y")

    logo_q = f'<img src="{st.session_state.logo_b64}" style="height:70px;margin-bottom:8px;">' if st.session_state.logo_b64 else ""

    rows_html = "".join(
        f'<tr style="border-bottom:1px solid #2d3748;">'
        f'<td style="padding:8px;">{r["Material"]}</td>'
        f'<td style="text-align:center;padding:8px;">{r["Qty"]}</td>'
        f'<td style="text-align:center;padding:8px;">{r["Unit"]}</td>'
        f'<td style="text-align:right;padding:8px;">${r["Total"]:,.2f}</td>'
        f'</tr>'
        for r in mat_rows
    )
    equip_row = f'<tr><td style="padding:8px;">Equipment</td><td></td><td></td><td style="text-align:right;padding:8px;">${total_equip:,.2f}</td></tr>' if total_equip > 0 else ""

    st.markdown(f"""
<div style="background:#1c2333;border:1px solid #2d3748;border-radius:10px;padding:32px;max-width:780px;margin:0 auto;">
{logo_q}
<h2 style="color:#f0a500;margin:0 0 4px 0;">{st.session_state.company_name}</h2>
<p style="color:#8892a4;margin:0 0 20px 0;">Date: {today}</p>

<table style="width:100%;margin-bottom:12px;">
<tr><td><strong>Client:</strong> {client_name or "—"}</td><td><strong>Phone:</strong> {client_phone or "—"}</td></tr>
<tr><td colspan="2"><strong>Location:</strong> {client_address or "—"}</td></tr>
<tr><td colspan="2"><strong>Project:</strong> {sqft:,.0f} SQFT · {thickness}" thick · {width_ft:.0f} ft wide · {length_ft:.1f} ft long</td></tr>
</table>

<hr style="border-color:#2d3748;">

<table style="width:100%;border-collapse:collapse;margin:12px 0;">
<tr style="background:#0e1117;color:#f0a500;">
  <th style="text-align:left;padding:8px;">Item</th>
  <th style="text-align:center;padding:8px;">Qty</th>
  <th style="text-align:center;padding:8px;">Unit</th>
  <th style="text-align:right;padding:8px;">Amount</th>
</tr>
{rows_html}
<tr><td style="padding:8px;">Labor</td><td></td><td></td><td style="text-align:right;padding:8px;">${total_lab:,.2f}</td></tr>
{equip_row}
</table>

<hr style="border-color:#2d3748;">

<div style="text-align:right;margin-top:8px;">
  <p style="margin:4px 0;color:#8892a4;">Subtotal: ${subtotal:,.2f}</p>
  <p style="margin:4px 0;color:#8892a4;">Overhead/Profit ({profit_pct:.0f}%): ${profit_amt:,.2f}</p>
  <p style="font-size:26px;color:#f0a500;font-weight:900;margin:12px 0 4px 0;">TOTAL: ${grand:,.2f}</p>
  <p style="color:#8892a4;font-size:13px;">${grand/sqft:,.2f} per SQFT</p>
</div>

<hr style="border-color:#2d3748;">
<p style="color:#8892a4;font-size:13px;white-space:pre-wrap;">{quote_notes}</p>

<div style="margin-top:28px;display:flex;justify-content:space-between;">
  <div style="color:#8892a4;font-size:13px;">
    Client Signature: _______________________<br><br>Date: _______________
  </div>
  <div style="color:#8892a4;font-size:13px;">
    Contractor Signature: _______________________<br><br>Date: _______________
  </div>
</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("📥 GENERATE EXCEL REPORT"):
        buf = io.BytesIO()
        summary_rows = [
            {"Category": "Materials",                  "Amount": round(total_mat, 2)},
            {"Category": "Labor",                      "Amount": round(total_lab, 2)},
            {"Category": "Equipment",                  "Amount": round(total_equip, 2)},
            {"Category": "Subtotal",                   "Amount": round(subtotal, 2)},
            {"Category": f"Profit {profit_pct:.1f}%",  "Amount": round(profit_amt, 2)},
            {"Category": "GRAND TOTAL",                "Amount": round(grand, 2)},
            {"Category": "$/SQFT Total",               "Amount": round(grand/sqft, 2)},
        ]
        takeoff_rows = [
            {"Item": "Area (SQFT)",                   "Raw",    "Ordered"},
        ]
        takeoff_rows = [
            {"Item": "Area (SQFT)",                "Raw": sqft,           "Ordered": sqft},
            {"Item": f"Concrete {thickness}\" (CY)",  "Raw": round(cy_raw,2),"Ordered": cy_w},
            {"Item": f"Rebar {rebar_size} (bars)",    "Raw": round(rebar_lf_raw,1), "Ordered": rebar_bars},
            {"Item": f"Lumber {lumber_size} (boards)","Raw": round(lumber_lf_raw,1),"Ordered": lumber_boards},
            {"Item": "Red Stakes (pcs)",           "Raw": round(stakes_raw,1),  "Ordered": stakes_w},
            {"Item": "Expansion Joints (LF)",      "Raw": ej_lf_raw,      "Ordered": ej_lf_w},
            {"Item": "Gravel Base (CY)",           "Raw": round(gravel_cy_raw,2),"Ordered": gravel_cy_w},
            {"Item": "Poly (SQFT)",                "Raw": sqft,           "Ordered": poly_sqft_w},
        ]
        equip_rows = [
            {"Equipment": "Concrete Pump",    "Cost": pump_cost},
            {"Equipment": "Buggy",            "Cost": buggy_cost},
            {"Equipment": "Other Machinery",  "Cost": mach_cost},
        ]
        proj = client_name.replace(" ","_") if client_name else "Quote"
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            pd.DataFrame(summary_rows).to_excel(w,  sheet_name="Summary",   index=False)
            mat_df.to_excel(w,                       sheet_name="Materials", index=False)
            pd.DataFrame(takeoff_rows).to_excel(w,   sheet_name="Takeoff",  index=False)
            pd.DataFrame(equip_rows).to_excel(w,     sheet_name="Equipment",index=False)

        st.download_button(
            "⬇️ Download Excel",
            data=buf.getvalue(),
            file_name=f"{st.session_state.company_name.replace(' ','_')}_{proj}_{today.replace(' ','_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


# ─────────────────────── TAB 4: FORMULA REFERENCE ───────────────────────
with tab4:
    st.markdown('<div class="section">📊 Field Formula Reference</div>', unsafe_allow_html=True)

    st.markdown("### 🏗️ Concrete — CY = SQFT ÷ Divisor")
    conc_ref = pd.DataFrame([
        {"Thickness": '4"',  "Divisor": 81, "Example (500 sqft)": f"{500/81:.1f} CY"},
        {"Thickness": '6"',  "Divisor": 54, "Example (500 sqft)": f"{500/54:.1f} CY"},
        {"Thickness": '8"',  "Divisor": 40, "Example (500 sqft)": f"{500/40:.1f} CY"},
        {"Thickness": '12"', "Divisor": 27, "Example (500 sqft)": f"{500/27:.1f} CY"},
    ])
    st.dataframe(conc_ref, use_container_width=True, hide_index=True)

    st.markdown("### 🔩 Rebar — LF = SQFT × Factor")
    rebar_ref = pd.DataFrame([
        {"Spacing O.C.": f'{s}"', "Factor": f, "Bars from 500 sqft (20ft bars)": math.ceil(500*f/20)}
        for s, f in REBAR_FACTORS.items()
    ])
    st.dataframe(rebar_ref, use_container_width=True, hide_index=True)

    st.markdown("### 🚛 Concrete Yardage by Driveway Dimension")
    yard_ref = pd.DataFrame([
        {
            "Width (ft)": w,
            "Truck Length (ft)": tl,
            "Divisor": d,
            "Example": f"{w*tl:.0f} sqft ÷ {d} = {(w*tl)/d:.1f} CY"
        }
        for (w, tl), d in sorted(YARDAGE_TABLE.items())
    ])
    st.dataframe(yard_ref, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🔢 Quick Lookup — Your Current Job")
    st.markdown(f"""
<div class="formula-box">
Job: <strong>{sqft:,.0f} SQFT</strong> · {thickness}" thick · {width_ft:.0f} ft wide · {length_ft:.1f} ft long<br><br>
Concrete:  {sqft:,.0f} ÷ {divisor} = <strong>{cy_raw:.2f} CY raw → {cy_w} CY ordered</strong><br>
Rebar {spacing_in}" O.C.: {sqft:,.0f} × {factor} = <strong>{rebar_lf_raw:.1f} LF raw → {rebar_bars} bars</strong><br>
Lumber: {perimeter:.0f} LF perimeter → <strong>{lumber_boards} boards</strong><br>
Stakes @ {stake_spacing:.0f} ft: <strong>{stakes_w} pcs</strong><br>
Expansion Joints @ {ej_spacing:.0f} ft: <strong>{ej_lf_w} LF ({num_ej} joints)</strong>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.caption("Driveway Estimator Pro v2.0 · Field formulas from industry practice · Verify all quantities before ordering · Not a substitute for professional engineering review.")
