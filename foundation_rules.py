"""Foundation / Slab on Grade — Ethoscapes standard calculations."""
import math

# ── Beam defaults ────────────────────────────────────────────────────
BEAM_W_IN      = 10    # beam width (inches)
BEAM_D_IN      = 24    # beam depth (inches)
BEAM_COVER_IN  = 3     # concrete cover (inches)
LONG_COUNT     = 4     # longitudinal bars per beam (2 top + 2 bottom)
LONG_PIECE_FT  = 20    # standard stick length
SPLICE_5_IN    = 31    # lap splice for #5: 50 × 0.625" ≈ 31"

# ── Stirrup defaults ─────────────────────────────────────────────────
STIRRUP_SPACING_IN = 24
STIRRUP_PIECE_FT   = 20

# ── Soil type → max beam spacing (ft) ────────────────────────────────
SOIL_MAX_SPACING = {
    "arena_marga":      20,
    "arcilla_moderada": 16,
    "arcilla_activa":   12,
}

# ── Slab rebar ───────────────────────────────────────────────────────
SLAB_PIECE_FT  = 20
SPLICE_IN      = {"#3": 15, "#4": 20}   # lap splice lengths in inches

# ── Forms ────────────────────────────────────────────────────────────
BOARD_LEN_FT   = 16
BOARD_H_IN     = {"2x12": 11.25, "2x6": 5.5}   # actual dressed height


def _pcs(total_lf: float, stick_lf: float) -> int:
    """Ceiling division → how many sticks cover total_lf."""
    return math.ceil(total_lf / stick_lf) if total_lf > 0 else 0


# ════════════════════════════════════════════════════════════════════
# BEAMS — same detail for perimeter and all interior beams
# ════════════════════════════════════════════════════════════════════

def auto_interior_beams(length_ft: float, width_ft: float,
                        soil_type: str = "arcilla_moderada") -> tuple:
    """
    Returns (n_long, n_trans):
      n_long  = beams parallel to length axis, counted across width  (each spans length_ft)
      n_trans = beams parallel to width axis,  counted along length  (each spans width_ft)
    """
    s = SOIL_MAX_SPACING.get(soil_type, 16)
    n_long  = max(0, math.ceil(width_ft  / s) - 1)
    n_trans = max(0, math.ceil(length_ft / s) - 1)
    return n_long, n_trans


def beam_cy(lf_total: float,
            beam_w: int = BEAM_W_IN,
            beam_d: int = BEAM_D_IN) -> float:
    """Cubic yards of concrete for all beams combined (no waste)."""
    return (beam_w / 12) * (beam_d / 12) * lf_total / 27


def beam_rebar5(perimeter_ft: float,
                int_long: int,
                int_trans: int,
                length_ft: float,
                width_ft: float) -> tuple:
    """
    #5 longitudinal rebar — correct splice per individual beam run.
    int_long  = beams parallel to length axis (each spans length_ft)
    int_trans = beams parallel to width axis  (each spans width_ft)
    Returns (lf_raw, lf_with_splices, piezas_of_20ft)
    """
    # Each run is a separate beam segment
    runs = [perimeter_ft] + [length_ft] * int_long + [width_ft] * int_trans
    lf_raw    = sum(runs) * LONG_COUNT
    n_splices = sum(max(0, math.ceil(r / LONG_PIECE_FT) - 1) for r in runs) * LONG_COUNT
    lf_spliced = lf_raw + n_splices * (SPLICE_5_IN / 12)
    piezas     = _pcs(lf_spliced, LONG_PIECE_FT)
    return round(lf_raw, 1), round(lf_spliced, 1), piezas


def beam_stirrups(lf_total: float,
                  spacing_in: int = STIRRUP_SPACING_IN,
                  cover_in: int = BEAM_COVER_IN,
                  beam_w: int = BEAM_W_IN,
                  beam_d: int = BEAM_D_IN) -> tuple:
    """
    Stirrups for all beams.
    Returns (count, cut_ft_each, total_lf, piezas_of_20ft)
    cut_in = 2*(w-cover) + 2*(d-cover) + 12" hooks = 68" with defaults
    """
    count    = math.ceil(lf_total / (spacing_in / 12)) if lf_total > 0 else 0
    cut_in   = 2 * (beam_w - cover_in) + 2 * (beam_d - cover_in) + 12
    cut_ft   = round(cut_in / 12, 2)
    total_lf = count * cut_ft
    piezas   = _pcs(total_lf, STIRRUP_PIECE_FT)
    return count, cut_ft, round(total_lf, 1), piezas


# ════════════════════════════════════════════════════════════════════
# SLAB
# ════════════════════════════════════════════════════════════════════

def slab_cy(length_ft: float, width_ft: float, thick_in: int) -> float:
    """Cubic yards for the slab portion (no waste)."""
    return (length_ft * width_ft * (thick_in / 12)) / 27


def slab_rebar(length_ft: float,
               width_ft: float,
               spacing_in: int = 16,
               size: str = "#3") -> tuple:
    """
    Bidirectional rebar grid.
    Returns (bars_x, bars_y, lf_raw, lf_with_splices, piezas)
    """
    bars_x = math.ceil(width_ft  * 12 / spacing_in) + 1   # bars running along length
    bars_y = math.ceil(length_ft * 12 / spacing_in) + 1   # bars running along width
    lf_raw = bars_x * length_ft + bars_y * width_ft
    splice_ft  = SPLICE_IN.get(size, 15) / 12
    splices_x  = max(0, math.ceil(length_ft / SLAB_PIECE_FT) - 1) * bars_x
    splices_y  = max(0, math.ceil(width_ft  / SLAB_PIECE_FT) - 1) * bars_y
    lf_spliced = lf_raw + (splices_x + splices_y) * splice_ft
    piezas     = _pcs(lf_spliced, SLAB_PIECE_FT)
    return bars_x, bars_y, round(lf_raw, 1), round(lf_spliced, 1), piezas


# ════════════════════════════════════════════════════════════════════
# CONCRETE TOTAL
# ════════════════════════════════════════════════════════════════════

def concrete_order(cy_slab: float,
                   cy_beams: float,
                   waste_pct: float) -> tuple:
    """
    Total concrete with waste, rounded UP to nearest 0.25 CY.
    Returns (cy_raw, cy_ordered)
    """
    cy_raw     = cy_slab + cy_beams
    cy_wasted  = cy_raw * (1 + waste_pct / 100)
    cy_ordered = math.ceil(cy_wasted * 4) / 4
    return round(cy_raw, 2), round(cy_ordered, 2)


# ════════════════════════════════════════════════════════════════════
# FORMS  (perimeter only — interior beams are trenched)
# ════════════════════════════════════════════════════════════════════

def form_boards(perimeter_ft: float,
                exposed_height_in: float,
                board: str = "2x12") -> tuple:
    """
    Pine form boards (16-ft boards).
    exposed_height_in: visible height above grade (default = slab_thick + 2")
    Returns (hiladas, piezas_of_16ft)
    """
    bh      = BOARD_H_IN.get(board, 11.25)
    hiladas = math.ceil(exposed_height_in / bh)
    piezas  = math.ceil(perimeter_ft / BOARD_LEN_FT) * hiladas if perimeter_ft > 0 else 0
    return hiladas, piezas


def form_stakes(perimeter_ft: float, spacing_ft: float = 4.0) -> tuple:
    """
    2x4 stakes (3 cuts per 16-ft piece).
    Returns (stake_count, piezas_2x4)
    """
    count  = math.ceil(perimeter_ft / spacing_ft) if perimeter_ft > 0 else 0
    piezas = math.ceil(count / 3)
    return count, piezas


# ════════════════════════════════════════════════════════════════════
# MISC
# ════════════════════════════════════════════════════════════════════

def poly_sqft(area: float, overlap: float = 1.10) -> int:
    """Poly 6-mil SQFT with 10% overlap."""
    return math.ceil(area * overlap)


def rebar_chairs(bars_x: int, bars_y: int) -> int:
    """One chair per alternating grid intersection."""
    return math.ceil((bars_x * bars_y) / 2)
