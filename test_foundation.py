"""Quick validation — Ethoscapes Foundation standard."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import math
import foundation_rules as fn

def test_interior_beams_25x40_arcilla():
    """25×40 + arcilla_moderada (16 ft) -> 1 long + 2 trans"""
    n_long, n_trans = fn.auto_interior_beams(length_ft=40, width_ft=25, soil_type="arcilla_moderada")
    assert n_long  == 1, f"Expected 1 longitudinal, got {n_long}"
    assert n_trans == 2, f"Expected 2 transversal, got {n_trans}"
    print(f"  OK 25×40 arcilla_moderada -> {n_long} longitudinal + {n_trans} transversal")

def test_stirrup_cut_68in():
    """Stirrup cut with default 10×24 beam, cover=3\" -> 68\" = 5.67 ft"""
    _, cut_ft, _, _ = fn.beam_stirrups(lf_total=100)
    expected = (2*(10-3) + 2*(24-3) + 12) / 12   # = 68/12 ≈ 5.6667
    assert abs(cut_ft - expected) < 0.01, f"Expected {expected:.4f} ft, got {cut_ft}"
    print(f"  OK Stirrup cut = {cut_ft:.4f} ft  ({cut_ft*12:.1f}\")")

def test_form_boards_exposed_height():
    """form_boards with exposed_height=6\" and 2x12 board (11.25\" actual) -> 1 hilada"""
    hiladas, pcs = fn.form_boards(perimeter_ft=130, exposed_height_in=6, board="2x12")
    assert hiladas == 1, f"Expected 1 hilada, got {hiladas}"
    print(f"  OK form_boards 6\" exposed / 2x12 -> {hiladas} hilada(s), {pcs} pcs")

def test_beam_rebar5_convention():
    """Longitudinal beams span length_ft, transversal span width_ft"""
    lf_raw, _, _ = fn.beam_rebar5(
        perimeter_ft=0, int_long=1, int_trans=2,
        length_ft=40, width_ft=25
    )
    # 1 long beam × 40 ft × 4 bars + 2 trans beams × 25 ft × 4 bars = 360 LF raw (no splices)
    expected = (1*40 + 2*25) * 4
    assert lf_raw == expected, f"Expected {expected} LF raw, got {lf_raw}"
    print(f"  OK beam_rebar5 convention: {lf_raw:.1f} LF raw (expected {expected})")

if __name__ == "__main__":
    print("Foundation rules — validation tests")
    test_interior_beams_25x40_arcilla()
    test_stirrup_cut_68in()
    test_form_boards_exposed_height()
    test_beam_rebar5_convention()
    print("\nAll tests passed OK")
