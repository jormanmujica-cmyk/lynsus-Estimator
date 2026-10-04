import { describe, expect, it } from "vitest";
import { calcDrivewayTakeoff, type DrivewayInputs } from "./driveway";

/**
 * Regression values below were produced by running the exact formulas from
 * driveway.py through Python (not guessed) — see the PR/commit that added
 * this file for the python3 -c snippet used. Do not adjust these numbers to
 * make a refactor pass; if a formula changes on purpose, regenerate them
 * from driveway.py instead.
 */

describe("calcDrivewayTakeoff", () => {
  it("matches driveway.py defaults (sqft=500, width=12, perimeter=90, 4in, 18in O.C.)", () => {
    const inputs: DrivewayInputs = {
      sqft: 500,
      widthFt: 12,
      perimeterFt: 90,
      thickness: 4,
      rebarSpacingIn: 18,
      rebarBarLenFt: 20,
      lumberBoardsStacked: 1,
      lumberBoardLenFt: 16,
      stakeSpacingFt: 4,
      expansionJointSpacingFt: 10,
      gravelDepthIn: 4,
    };

    const r = calcDrivewayTakeoff(inputs);

    expect(r.lengthFt).toBeCloseTo(41.666666666666664, 9);

    expect(r.concrete.divisor).toBe(81);
    expect(r.concrete.cyRaw).toBeCloseTo(6.172839506172839, 9);
    expect(r.concrete.cyOrdered).toBe(7);

    expect(r.rebar.factor).toBe(0.0733);
    expect(r.rebar.lfRaw).toBeCloseTo(36.65, 9);
    expect(r.rebar.lfOrdered).toBeCloseTo(40.315000000000005, 9);
    expect(r.rebar.barsOrdered).toBe(3);

    expect(r.lumber.lfRaw).toBeCloseTo(90.0, 9);
    expect(r.lumber.lfOrdered).toBeCloseTo(99.00000000000001, 9);
    expect(r.lumber.boardsOrdered).toBe(7);

    expect(r.stakes.raw).toBeCloseTo(22.5, 9);
    expect(r.stakes.ordered).toBe(24);

    expect(r.expansionJoints.numJoints).toBe(4);
    expect(r.expansionJoints.lfRaw).toBeCloseTo(48.0, 9);
    expect(r.expansionJoints.lfOrdered).toBe(51);

    expect(r.gravel.divisor).toBeCloseTo(81.0, 9);
    expect(r.gravel.cyRaw).toBeCloseTo(6.172839506172839, 9);
    expect(r.gravel.cyOrdered).toBe(7);

    expect(r.poly.sqftOrdered).toBe(550);
  });

  it("matches driveway.py with a second, non-default input set (sqft=1200, 6in, 12in O.C.)", () => {
    const inputs: DrivewayInputs = {
      sqft: 1200,
      widthFt: 10,
      perimeterFt: 140,
      thickness: 6,
      rebarSpacingIn: 12,
      rebarBarLenFt: 24,
      lumberBoardsStacked: 2,
      lumberBoardLenFt: 12,
      stakeSpacingFt: 5,
      expansionJointSpacingFt: 12,
      gravelDepthIn: 6,
      waste: { concrete: 0.05, rebar: 0.12, lumber: 0.08, stakes: 0.03, poly: 0.15 },
    };

    const r = calcDrivewayTakeoff(inputs);

    expect(r.lengthFt).toBeCloseTo(120.0, 9);

    expect(r.concrete.divisor).toBe(54);
    expect(r.concrete.cyRaw).toBeCloseTo(22.22222222222222, 9);
    expect(r.concrete.cyOrdered).toBe(24);

    expect(r.rebar.factor).toBe(0.11);
    expect(r.rebar.lfRaw).toBeCloseTo(132.0, 9);
    expect(r.rebar.lfOrdered).toBeCloseTo(147.84, 9);
    expect(r.rebar.barsOrdered).toBe(7);

    expect(r.lumber.lfRaw).toBeCloseTo(280.0, 9);
    expect(r.lumber.lfOrdered).toBeCloseTo(302.40000000000003, 9);
    expect(r.lumber.boardsOrdered).toBe(26);

    expect(r.stakes.raw).toBeCloseTo(28.0, 9);
    expect(r.stakes.ordered).toBe(29);

    expect(r.expansionJoints.numJoints).toBe(10);
    expect(r.expansionJoints.lfRaw).toBeCloseTo(100.0, 9);
    expect(r.expansionJoints.lfOrdered).toBe(105);

    expect(r.gravel.divisor).toBeCloseTo(54.0, 9);
    expect(r.gravel.cyRaw).toBeCloseTo(22.22222222222222, 9);
    expect(r.gravel.cyOrdered).toBe(25);

    expect(r.poly.sqftOrdered).toBe(1380);
  });

  it("treats gravel depth 0 as 'no gravel' — matches driveway.py's else-branch guard", () => {
    const r = calcDrivewayTakeoff({
      sqft: 1200,
      widthFt: 10,
      perimeterFt: 140,
      thickness: 6,
      rebarSpacingIn: 12,
      rebarBarLenFt: 24,
      lumberBoardsStacked: 2,
      lumberBoardLenFt: 12,
      stakeSpacingFt: 5,
      expansionJointSpacingFt: 12,
      gravelDepthIn: 0,
    });

    expect(r.gravel.divisor).toBe(999);
    expect(r.gravel.cyRaw).toBe(0);
    expect(r.gravel.cyOrdered).toBe(0);
  });
});
