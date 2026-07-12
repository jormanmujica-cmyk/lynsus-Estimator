"""Quick validation — Ethoscapes Foundation standard."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import math
import foundation_rules as fn

# ── Existing tests ────────────────────────────────────────────────────

def test_stirrup_cut_68in():
    """Stirrup cut with default 10x24 beam, cover=3in -> 68in = 5.67 ft"""
    _, cut_ft, _, _ = fn.beam_stirrups(lf_total=100)
    expected = (2*(10-3) + 2*(24-3) + 12) / 12
    assert abs(cut_ft - expected) < 0.01, f"Expected {expected:.4f} ft, got {cut_ft}"
    print(f"  OK Stirrup cut = {cut_ft:.4f} ft  ({cut_ft*12:.1f}in)")

def test_form_boards_exposed_height():
    """form_boards with exposed_height=6in and 2x12 board (11.25in actual) -> 1 hilada"""
    hiladas, pcs = fn.form_boards(perimeter_ft=130, exposed_height_in=6, board="2x12")
    assert hiladas == 1, f"Expected 1 hilada, got {hiladas}"
    print(f"  OK form_boards 6in exposed / 2x12 -> {hiladas} hilada(s), {pcs} pcs")

def test_beam_rebar5_convention():
    """Longitudinal beams span length_ft, transversal span width_ft"""
    lf_raw, _, _ = fn.beam_rebar5(
        perimeter_ft=0, int_long=1, int_trans=2,
        length_ft=40, width_ft=25
    )
    expected = (1*40 + 2*25) * 4   # 4 bars/beam (ESTANDAR default)
    assert lf_raw == expected, f"Expected {expected} LF raw, got {lf_raw}"
    print(f"  OK beam_rebar5 convention: {lf_raw:.1f} LF raw (expected {expected})")

# ── Profile tests ─────────────────────────────────────────────────────

def test_25x20_arena():
    """25x20 arena_marga (area=500 <= 600) -> LIGERO, 0 interior beams"""
    n_long, n_trans = fn.auto_interior_beams(length_ft=25, width_ft=20, soil_type="arena_marga")
    assert (n_long, n_trans) == (0, 0), f"Expected (0,0), got ({n_long},{n_trans})"
    profile = fn.beam_profile_auto(500, "arena_marga", n_long, n_trans)
    assert profile == "ligero", f"Expected ligero, got {profile}"
    print(f"  OK 25x20 arena_marga -> LIGERO, {n_long}L + {n_trans}T interior beams")

def test_25x20_moderada():
    """25x20 arcilla_moderada (area=500 <= 600) -> ESTANDAR, 0 interior beams"""
    n_long, n_trans = fn.auto_interior_beams(length_ft=25, width_ft=20, soil_type="arcilla_moderada")
    assert (n_long, n_trans) == (0, 0), f"Expected (0,0), got ({n_long},{n_trans})"
    profile = fn.beam_profile_auto(500, "arcilla_moderada", n_long, n_trans)
    assert profile == "estandar", f"Expected estandar, got {profile}"
    print(f"  OK 25x20 arcilla_moderada -> ESTANDAR, {n_long}L + {n_trans}T interior beams")

def test_25x20_activa():
    """25x20 arcilla_activa (area=500, no exception) -> ESTANDAR + interior beams"""
    n_long, n_trans = fn.auto_interior_beams(length_ft=25, width_ft=20, soil_type="arcilla_activa")
    # spacing=12: n_long=ceil(20/12)-1=1, n_trans=ceil(25/12)-1=2
    assert n_long == 1, f"Expected n_long=1, got {n_long}"
    assert n_trans == 2, f"Expected n_trans=2, got {n_trans}"
    profile = fn.beam_profile_auto(500, "arcilla_activa", n_long, n_trans)
    assert profile == "estandar", f"Expected estandar, got {profile}"
    print(f"  OK 25x20 arcilla_activa -> ESTANDAR, {n_long}L + {n_trans}T interior beams")

def test_25x40_any_soil():
    """25x40 (area=1000 > 600) -> ESTANDAR for all soil types"""
    for soil in ["arena_marga", "arcilla_moderada", "arcilla_activa"]:
        n_long, n_trans = fn.auto_interior_beams(length_ft=40, width_ft=25, soil_type=soil)
        profile = fn.beam_profile_auto(1000, soil, n_long, n_trans)
        assert profile == "estandar", f"Expected estandar for {soil}, got {profile}"
    print(f"  OK 25x40 all soils -> ESTANDAR")

def test_25x40_arcilla_moderada_beams():
    """Original test: 25x40 arcilla_moderada -> 1 long + 2 trans (area=1000 > 600)"""
    n_long, n_trans = fn.auto_interior_beams(length_ft=40, width_ft=25, soil_type="arcilla_moderada")
    assert n_long  == 1, f"Expected 1 longitudinal, got {n_long}"
    assert n_trans == 2, f"Expected 2 transversal, got {n_trans}"
    print(f"  OK 25x40 arcilla_moderada -> {n_long}L + {n_trans}T")

def test_ligero_long_count():
    """LIGERO uses 2 bars, ESTANDAR uses 4 bars"""
    lf_ligero,   _, _ = fn.beam_rebar5(130, 0, 0, 40, 25, long_count=2)
    lf_estandar, _, _ = fn.beam_rebar5(130, 0, 0, 40, 25, long_count=4)
    assert lf_estandar == lf_ligero * 2, f"ESTANDAR should be 2x LIGERO LF raw"
    print(f"  OK LIGERO={lf_ligero:.0f} LF, ESTANDAR={lf_estandar:.0f} LF (2x ratio confirmed)")

if __name__ == "__main__":
    print("Foundation rules — validation tests")
    test_stirrup_cut_68in()
    test_form_boards_exposed_height()
    test_beam_rebar5_convention()
    test_25x20_arena()
    test_25x20_moderada()
    test_25x20_activa()
    test_25x40_any_soil()
    test_25x40_arcilla_moderada_beams()
    test_ligero_long_count()
    print("\nAll tests passed OK")
