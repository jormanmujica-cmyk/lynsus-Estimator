/**
 * Driveway field formulas — 1:1 port of driveway.py.
 *
 * NO CAMBIAR estos números/fórmulas sin autorización (ver CLAUDE.md raíz).
 * Cada función aquí tiene su contraparte exacta en driveway.py — si cambias
 * algo, cambia los dos lados y revisa frontend/src/lib/calc/driveway.test.ts.
 */

// ── Field-tested constants (driveway.py líneas 14–39) ──────────────────────

export const CONC_DIVISORS = { 4: 81, 6: 54, 8: 40, 12: 27 } as const;
export type ConcreteThickness = keyof typeof CONC_DIVISORS; // 4 | 6 | 8 | 12

export const REBAR_FACTORS = {
  12: 0.11,
  14: 0.094,
  15: 0.088,
  16: 0.0827,
  18: 0.0733,
  24: 0.055,
} as const;
export type RebarSpacing = 12 | 14 | 15 | 16 | 18 | 24;

/** width_ft x truck_length_ft -> divisor. Key format: "WxL". */
export const YARDAGE_TABLE: Record<string, number> = {
  "12x24": 34,
  "12x26": 32,
  "12x28": 30,
  "12x30": 28,
  "10x24": 35,
  "10x26": 33,
  "10x28": 31,
  "10x30": 29,
  "10x25": 34,
  "10x27": 32,
  "10x29": 30,
};

export const DEFAULT_WASTE = {
  concrete: 0.08,
  rebar: 0.1,
  lumber: 0.1,
  stakes: 0.05,
  poly: 0.1,
} as const;

export const DEFAULT_PRICES = {
  concretePerCY: 165.0,
  rebarPerBar: 8.5,
  lumberPerBoard: 7.5,
  stakePerPc: 0.75,
  expansionJointPerLF: 0.65,
  gravelPerCY: 42.0,
  polyPerSqft: 0.08,
};

// ── Inputs / outputs ────────────────────────────────────────────────────────

export interface DrivewayInputs {
  sqft: number;
  widthFt: number;
  perimeterFt: number;
  thickness: ConcreteThickness;
  rebarSpacingIn: RebarSpacing;
  rebarBarLenFt: number; // default 20
  lumberBoardsStacked: number; // default 1
  lumberBoardLenFt: number; // default 16
  stakeSpacingFt: number; // default 4
  expansionJointSpacingFt: number; // default 10
  gravelDepthIn: number; // default 4
  waste?: Partial<Record<keyof typeof DEFAULT_WASTE, number>>;
}

export interface DrivewayTakeoff {
  lengthFt: number;
  concrete: { divisor: number; cyRaw: number; cyOrdered: number };
  rebar: { factor: number; lfRaw: number; lfOrdered: number; barsOrdered: number };
  lumber: { lfRaw: number; lfOrdered: number; boardsOrdered: number };
  stakes: { raw: number; ordered: number };
  expansionJoints: { numJoints: number; lfRaw: number; lfOrdered: number };
  gravel: { divisor: number; cyRaw: number; cyOrdered: number };
  poly: { sqftOrdered: number };
}

/** Field-formula takeoff. Mirrors driveway.py tab 1 ("TAKEOFF") exactly. */
export function calcDrivewayTakeoff(inputs: DrivewayInputs): DrivewayTakeoff {
  const waste = { ...DEFAULT_WASTE, ...inputs.waste };

  const lengthFt = inputs.widthFt > 0 ? inputs.sqft / inputs.widthFt : 0; // driveway.py:139

  // Concrete — driveway.py:150-152
  const concDivisor = CONC_DIVISORS[inputs.thickness];
  const cyRaw = inputs.sqft / concDivisor;
  const cyOrdered = Math.ceil(cyRaw * (1 + waste.concrete));

  // Rebar — driveway.py:170-173
  const rebarFactor = REBAR_FACTORS[inputs.rebarSpacingIn];
  const rebarLfRaw = inputs.sqft * rebarFactor;
  const rebarLfOrdered = rebarLfRaw * (1 + waste.rebar);
  const rebarBarsOrdered = Math.ceil(rebarLfOrdered / inputs.rebarBarLenFt);

  // Lumber / Forms — driveway.py:191-193
  const lumberLfRaw = inputs.perimeterFt * inputs.lumberBoardsStacked;
  const lumberLfOrdered = lumberLfRaw * (1 + waste.lumber);
  const lumberBoardsOrdered = Math.ceil(lumberLfOrdered / inputs.lumberBoardLenFt);

  // Red stakes — driveway.py:208-209
  const stakesRaw = inputs.perimeterFt / inputs.stakeSpacingFt;
  const stakesOrdered = Math.ceil(stakesRaw * (1 + waste.stakes));

  // Expansion joints — driveway.py:224-226 (fixed +5%, not a configurable waste factor)
  const numJoints =
    inputs.expansionJointSpacingFt > 0
      ? Math.floor(lengthFt / inputs.expansionJointSpacingFt)
      : 0;
  const ejLfRaw = numJoints * inputs.widthFt;
  const ejLfOrdered = Math.ceil(ejLfRaw * 1.05);

  // Gravel base — driveway.py:244-246 (divisor = 324 / depth_in, i.e. (27*12)/depth)
  const gravelDivisor = inputs.gravelDepthIn > 0 ? 324 / inputs.gravelDepthIn : 999;
  const gravelCyRaw = inputs.gravelDepthIn > 0 ? inputs.sqft / gravelDivisor : 0;
  const gravelCyOrdered = Math.ceil(gravelCyRaw * 1.1); // fixed +10%

  // Poly — driveway.py:247
  const polySqftOrdered = Math.ceil(inputs.sqft * (1 + waste.poly));

  return {
    lengthFt,
    concrete: { divisor: concDivisor, cyRaw, cyOrdered },
    rebar: { factor: rebarFactor, lfRaw: rebarLfRaw, lfOrdered: rebarLfOrdered, barsOrdered: rebarBarsOrdered },
    lumber: { lfRaw: lumberLfRaw, lfOrdered: lumberLfOrdered, boardsOrdered: lumberBoardsOrdered },
    stakes: { raw: stakesRaw, ordered: stakesOrdered },
    expansionJoints: { numJoints, lfRaw: ejLfRaw, lfOrdered: ejLfOrdered },
    gravel: { divisor: gravelDivisor, cyRaw: gravelCyRaw, cyOrdered: gravelCyOrdered },
    poly: { sqftOrdered: polySqftOrdered },
  };
}
