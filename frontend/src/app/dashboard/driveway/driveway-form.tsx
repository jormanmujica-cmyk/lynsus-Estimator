"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  calcDrivewayTakeoff,
  CONC_DIVISORS,
  DEFAULT_PRICES,
  DEFAULT_WASTE,
  REBAR_FACTORS,
  type ConcreteThickness,
  type RebarSpacing,
} from "@/lib/calc/driveway";
import {
  COMPANY_PROFILE_EVENT,
  EMPTY_COMPANY_PROFILE,
  loadCompanyProfile,
  type CompanyProfile,
} from "@/lib/supabase/user-config";

const THICKNESS_OPTIONS = Object.keys(CONC_DIVISORS).map(Number) as ConcreteThickness[];
const SPACING_OPTIONS = Object.keys(REBAR_FACTORS).map(Number) as RebarSpacing[];

const money = (n: number) =>
  n.toLocaleString("en-US", { style: "currency", currency: "USD" });

const plural = (n: number, singular: string, pluralForm: string) => (n === 1 ? singular : pluralForm);

// Estacas: 100% automático a partir del perímetro ya ingresado en
// Dimensiones (lo mismo que usa Lumber & Forms) — sin inputs propios, para
// que el contratista no tenga que pensar en esto. Spacing de campo real:
// máximo 18" O.C. (corregido a pedido del usuario — el default de
// driveway.py era 4 ft, muy abierto).
const STAKE_SPACING_FT = 1.5; // 18"
const STAKE_PRICE = DEFAULT_PRICES.stakePerPc;

type Extra = { id: string; label: string; price: number };

// Catálogo de equipo común con precio sugerido — el contratista elige de la
// lista (precio se autocompleta y queda editable) o usa "Personalizado" para
// algo que no esté aquí. Puede agregar cuantos renglones necesite.
const EQUIPMENT_CATALOG = [
  { type: "pump", label: "Concrete Pump", defaultPrice: 800 },
  { type: "buggy", label: "Power Buggy", defaultPrice: 300 },
  { type: "compactor", label: "Plate Compactor", defaultPrice: 150 },
  { type: "saw", label: "Concrete Saw", defaultPrice: 200 },
  { type: "trowel", label: "Power Trowel", defaultPrice: 250 },
  { type: "laser", label: "Laser Level", defaultPrice: 100 },
  { type: "custom", label: "Personalizado…", defaultPrice: 0 },
] as const;
type EquipmentType = (typeof EQUIPMENT_CATALOG)[number]["type"];
type EquipmentItem = { id: string; type: EquipmentType; customLabel: string; price: number };

// Todos los defaults en un solo lugar: sirve de "fábrica" tanto para el
// primer render como para el botón "Nuevo takeoff" (reset) más abajo.
const DEFAULTS = {
  sqft: 500,
  widthFt: 12,
  perimeterFt: 90,
  thickness: 4 as ConcreteThickness,
  concPrice: DEFAULT_PRICES.concretePerCY,
  rebarSize: "#4",
  rebarSpacingIn: 18 as RebarSpacing,
  rebarBarLenFt: 20,
  rebarPrice: DEFAULT_PRICES.rebarPerBar,
  lumberSize: "2x6",
  lumberBoardLenFt: 16,
  lumberBoardsStacked: 1,
  lumberPrice: DEFAULT_PRICES.lumberPerBoard,
  ejMaxPanelFt: 10 as 10 | 12,
  ejPrice: DEFAULT_PRICES.expansionJointPerLF,
  ejMode: "auto" as "auto" | "manual",
  ejManualLf: 0,
  gravelDepthIn: 4,
  gravelPricingMode: "cy" as "cy" | "truck",
  gravelPrice: DEFAULT_PRICES.gravelPerCY,
  truckCapacityCy: 10,
  truckPrice: 350,
  wasteConc: DEFAULT_WASTE.concrete * 100,
  wasteRebar: DEFAULT_WASTE.rebar * 100,
  wasteLumber: DEFAULT_WASTE.lumber * 100,
  laborMode: "day" as "day" | "sqft",
  laborWorkers: 2,
  laborDailyRate: 150,
  laborDays: 3,
  laborSqftPrice: 4.9,
  equipment: [] as EquipmentItem[],
  overheadPct: 10,
  profitPct: 20,
  extras: [] as Extra[],
  clientName: "",
  clientAddress: "",
  clientPhone: "",
  scopeOfWork:
    "Instalación de driveway de concreto. Incluye excavación, base de gravel, forms, rebar, concreto, acabado, expansion joints y limpieza final.",
};

// Autosave: se guarda en el navegador en cuanto el usuario cambia algo, y se
// recupera solo al volver a entrar — no se reinicia hasta que el contratista
// toque "Nuevo takeoff" a propósito.
const STORAGE_KEY = "lynsus:driveway-takeoff:v1";

export default function DrivewayForm() {
  // ── Dimensiones ──
  const [sqft, setSqft] = useState(DEFAULTS.sqft);
  const [widthFt, setWidthFt] = useState(DEFAULTS.widthFt);
  const [perimeterFt, setPerimeterFt] = useState(DEFAULTS.perimeterFt);

  // ── Concreto ──
  const [thickness, setThickness] = useState<ConcreteThickness>(DEFAULTS.thickness);
  const [concPrice, setConcPrice] = useState(DEFAULTS.concPrice);

  // ── Rebar ──
  const [rebarSize, setRebarSize] = useState(DEFAULTS.rebarSize);
  const [rebarSpacingIn, setRebarSpacingIn] = useState<RebarSpacing>(DEFAULTS.rebarSpacingIn);
  const [rebarBarLenFt, setRebarBarLenFt] = useState(DEFAULTS.rebarBarLenFt);
  const [rebarPrice, setRebarPrice] = useState(DEFAULTS.rebarPrice);

  // ── Lumber / Forms ──
  const [lumberSize, setLumberSize] = useState(DEFAULTS.lumberSize);
  const [lumberBoardLenFt, setLumberBoardLenFt] = useState(DEFAULTS.lumberBoardLenFt);
  const [lumberBoardsStacked, setLumberBoardsStacked] = useState(DEFAULTS.lumberBoardsStacked);
  const [lumberPrice, setLumberPrice] = useState(DEFAULTS.lumberPrice);

  // ── Expansion joints ── cuadros de máximo 10x10 o 12x12 ft, no solo
  // franjas a lo largo — si el ancho también pasa el máximo, hace falta
  // junta longitudinal además de las transversales.
  const [ejMaxPanelFt, setEjMaxPanelFt] = useState<10 | 12>(DEFAULTS.ejMaxPanelFt);
  const [ejPrice, setEjPrice] = useState(DEFAULTS.ejPrice);
  // Auto = usa el cálculo de cuadrícula de abajo. Manual = el contratista
  // pone sus propios LF (ej. layout no rectangular que el cálculo no capta).
  const [ejMode, setEjMode] = useState<"auto" | "manual">(DEFAULTS.ejMode);
  const [ejManualLf, setEjManualLf] = useState(DEFAULTS.ejManualLf);

  // ── Gravel ──
  const [gravelDepthIn, setGravelDepthIn] = useState(DEFAULTS.gravelDepthIn);
  const [gravelPricingMode, setGravelPricingMode] = useState<"cy" | "truck">(DEFAULTS.gravelPricingMode);
  const [gravelPrice, setGravelPrice] = useState(DEFAULTS.gravelPrice);
  const [truckCapacityCy, setTruckCapacityCy] = useState(DEFAULTS.truckCapacityCy);
  const [truckPrice, setTruckPrice] = useState(DEFAULTS.truckPrice);

  // ── Waste factors (%) ──
  const [wasteConc, setWasteConc] = useState(DEFAULTS.wasteConc);
  const [wasteRebar, setWasteRebar] = useState(DEFAULTS.wasteRebar);
  const [wasteLumber, setWasteLumber] = useState(DEFAULTS.wasteLumber);

  // ── Labor ──
  const [laborMode, setLaborMode] = useState<"day" | "sqft">(DEFAULTS.laborMode);
  // Modo "Por día": cuadrilla completa, no por tarea.
  const [laborWorkers, setLaborWorkers] = useState(DEFAULTS.laborWorkers);
  const [laborDailyRate, setLaborDailyRate] = useState(DEFAULTS.laborDailyRate);
  const [laborDays, setLaborDays] = useState(DEFAULTS.laborDays);
  // Modo "Por SQFT": una sola tarifa × SQFT del proyecto.
  const [laborSqftPrice, setLaborSqftPrice] = useState(DEFAULTS.laborSqftPrice);

  // ── Equipment — lista libre tipo "Extras", con catálogo de precios
  // sugeridos. Reemplaza los 3 checkboxes fijos (Pump/Buggy/Otra) de antes.
  const [equipment, setEquipment] = useState<EquipmentItem[]>(DEFAULTS.equipment);
  const addEquipment = () =>
    setEquipment((xs) => [
      ...xs,
      {
        id: (crypto as { randomUUID?: () => string }).randomUUID?.() ?? String(Date.now()),
        type: EQUIPMENT_CATALOG[0].type,
        customLabel: "",
        price: EQUIPMENT_CATALOG[0].defaultPrice,
      },
    ]);
  const updateEquipment = (id: string, patch: Partial<EquipmentItem>) =>
    setEquipment((xs) => xs.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const removeEquipment = (id: string) => setEquipment((xs) => xs.filter((x) => x.id !== id));

  // ── Financial — driveway.py:339-344 ──
  const [overheadPct, setOverheadPct] = useState(DEFAULTS.overheadPct);
  const [profitPct, setProfitPct] = useState(DEFAULTS.profitPct);

  // ── Cliente / cotización formal — driveway.py tab "Quote" ──
  const [clientName, setClientName] = useState(DEFAULTS.clientName);
  const [clientAddress, setClientAddress] = useState(DEFAULTS.clientAddress);
  const [clientPhone, setClientPhone] = useState(DEFAULTS.clientPhone);
  const [scopeOfWork, setScopeOfWork] = useState(DEFAULTS.scopeOfWork);
  // Modal del estimado — estado de sesión nada más, no se autoguarda.
  const [showPreview, setShowPreview] = useState(false);

  // Perfil de la empresa (Ajustes) — para el header del documento del cliente.
  const [companyProfile, setCompanyProfile] = useState<CompanyProfile>(EMPTY_COMPANY_PROFILE);
  useEffect(() => {
    // Guard contra doble-invocación de efectos en dev (ver settings-form.tsx).
    let ignore = false;
    loadCompanyProfile().then((p) => {
      if (!ignore) setCompanyProfile(p);
    });
    const onUpdate = (e: Event) => setCompanyProfile((e as CustomEvent<CompanyProfile>).detail);
    window.addEventListener(COMPANY_PROFILE_EVENT, onUpdate);
    return () => {
      ignore = true;
      window.removeEventListener(COMPANY_PROFILE_EVENT, onUpdate);
    };
  }, []);

  // ── Extras — líneas libres que el contratista agrega a mano ──
  const [extras, setExtras] = useState<Extra[]>(DEFAULTS.extras);
  const addExtra = () =>
    setExtras((xs) => [
      ...xs,
      { id: (crypto as { randomUUID?: () => string }).randomUUID?.() ?? String(Date.now()), label: "", price: 0 },
    ]);
  const updateExtra = (id: string, patch: Partial<{ label: string; price: number }>) =>
    setExtras((xs) => xs.map((x) => (x.id === id ? { ...x, ...patch } : x)));
  const removeExtra = (id: string) => setExtras((xs) => xs.filter((x) => x.id !== id));

  // ── Autosave: cargar lo guardado al entrar ──────────────────────────────
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as Partial<typeof DEFAULTS>;
      if (saved.sqft !== undefined) setSqft(saved.sqft);
      if (saved.widthFt !== undefined) setWidthFt(saved.widthFt);
      if (saved.perimeterFt !== undefined) setPerimeterFt(saved.perimeterFt);
      if (saved.thickness !== undefined) setThickness(saved.thickness);
      if (saved.concPrice !== undefined) setConcPrice(saved.concPrice);
      if (saved.rebarSize !== undefined) setRebarSize(saved.rebarSize);
      if (saved.rebarSpacingIn !== undefined) setRebarSpacingIn(saved.rebarSpacingIn);
      if (saved.rebarBarLenFt !== undefined) setRebarBarLenFt(saved.rebarBarLenFt);
      if (saved.rebarPrice !== undefined) setRebarPrice(saved.rebarPrice);
      if (saved.lumberSize !== undefined) setLumberSize(saved.lumberSize);
      if (saved.lumberBoardLenFt !== undefined) setLumberBoardLenFt(saved.lumberBoardLenFt);
      if (saved.lumberBoardsStacked !== undefined) setLumberBoardsStacked(saved.lumberBoardsStacked);
      if (saved.lumberPrice !== undefined) setLumberPrice(saved.lumberPrice);
      if (saved.ejMaxPanelFt !== undefined) setEjMaxPanelFt(saved.ejMaxPanelFt);
      if (saved.ejPrice !== undefined) setEjPrice(saved.ejPrice);
      if (saved.ejMode !== undefined) setEjMode(saved.ejMode);
      if (saved.ejManualLf !== undefined) setEjManualLf(saved.ejManualLf);
      if (saved.gravelDepthIn !== undefined) setGravelDepthIn(saved.gravelDepthIn);
      if (saved.gravelPricingMode !== undefined) setGravelPricingMode(saved.gravelPricingMode);
      if (saved.gravelPrice !== undefined) setGravelPrice(saved.gravelPrice);
      if (saved.truckCapacityCy !== undefined) setTruckCapacityCy(saved.truckCapacityCy);
      if (saved.truckPrice !== undefined) setTruckPrice(saved.truckPrice);
      if (saved.wasteConc !== undefined) setWasteConc(saved.wasteConc);
      if (saved.wasteRebar !== undefined) setWasteRebar(saved.wasteRebar);
      if (saved.wasteLumber !== undefined) setWasteLumber(saved.wasteLumber);
      if (saved.laborMode !== undefined) setLaborMode(saved.laborMode);
      if (saved.laborWorkers !== undefined) setLaborWorkers(saved.laborWorkers);
      if (saved.laborDailyRate !== undefined) setLaborDailyRate(saved.laborDailyRate);
      if (saved.laborDays !== undefined) setLaborDays(saved.laborDays);
      if (saved.laborSqftPrice !== undefined) setLaborSqftPrice(saved.laborSqftPrice);
      if (saved.equipment !== undefined) setEquipment(saved.equipment);
      if (saved.clientName !== undefined) setClientName(saved.clientName);
      if (saved.clientAddress !== undefined) setClientAddress(saved.clientAddress);
      if (saved.clientPhone !== undefined) setClientPhone(saved.clientPhone);
      if (saved.scopeOfWork !== undefined) setScopeOfWork(saved.scopeOfWork);
      if (saved.overheadPct !== undefined) setOverheadPct(saved.overheadPct);
      if (saved.profitPct !== undefined) setProfitPct(saved.profitPct);
      if (saved.extras !== undefined) setExtras(saved.extras);
    } catch {
      // localStorage no disponible o datos corruptos — se queda con los defaults.
    }
  }, []);

  // ── Autosave: guardar en cada cambio (se salta el primer render para no
  // pisar lo recién cargado arriba con los defaults antes de que apliquen) ──
  const skipFirstSave = useRef(true);
  useEffect(() => {
    if (skipFirstSave.current) {
      skipFirstSave.current = false;
      return;
    }
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          sqft,
          widthFt,
          perimeterFt,
          thickness,
          concPrice,
          rebarSize,
          rebarSpacingIn,
          rebarBarLenFt,
          rebarPrice,
          lumberSize,
          lumberBoardLenFt,
          lumberBoardsStacked,
          lumberPrice,
          ejMaxPanelFt,
          ejPrice,
          ejMode,
          ejManualLf,
          gravelDepthIn,
          gravelPricingMode,
          gravelPrice,
          truckCapacityCy,
          truckPrice,
          wasteConc,
          wasteRebar,
          wasteLumber,
          laborMode,
          laborWorkers,
          laborDailyRate,
          laborDays,
          laborSqftPrice,
          equipment,
          overheadPct,
          profitPct,
          extras,
          clientName,
          clientAddress,
          clientPhone,
          scopeOfWork,
        })
      );
    } catch {
      // localStorage lleno o no disponible — no es crítico, se sigue trabajando en memoria.
    }
  }, [
    sqft,
    widthFt,
    perimeterFt,
    thickness,
    concPrice,
    rebarSize,
    rebarSpacingIn,
    rebarBarLenFt,
    rebarPrice,
    lumberSize,
    lumberBoardLenFt,
    lumberBoardsStacked,
    lumberPrice,
    ejMaxPanelFt,
    ejPrice,
    ejMode,
    ejManualLf,
    gravelDepthIn,
    gravelPricingMode,
    gravelPrice,
    truckCapacityCy,
    truckPrice,
    wasteConc,
    wasteRebar,
    wasteLumber,
    laborMode,
    laborWorkers,
    laborDailyRate,
    laborDays,
    laborSqftPrice,
    equipment,
    overheadPct,
    profitPct,
    extras,
    clientName,
    clientAddress,
    clientPhone,
    scopeOfWork,
  ]);

  const resetAll = () => {
    if (!window.confirm("¿Empezar un takeoff nuevo? Se perderán los valores actuales de este formulario.")) {
      return;
    }
    setSqft(DEFAULTS.sqft);
    setWidthFt(DEFAULTS.widthFt);
    setPerimeterFt(DEFAULTS.perimeterFt);
    setThickness(DEFAULTS.thickness);
    setConcPrice(DEFAULTS.concPrice);
    setRebarSize(DEFAULTS.rebarSize);
    setRebarSpacingIn(DEFAULTS.rebarSpacingIn);
    setRebarBarLenFt(DEFAULTS.rebarBarLenFt);
    setRebarPrice(DEFAULTS.rebarPrice);
    setLumberSize(DEFAULTS.lumberSize);
    setLumberBoardLenFt(DEFAULTS.lumberBoardLenFt);
    setLumberBoardsStacked(DEFAULTS.lumberBoardsStacked);
    setLumberPrice(DEFAULTS.lumberPrice);
    setEjMaxPanelFt(DEFAULTS.ejMaxPanelFt);
    setEjPrice(DEFAULTS.ejPrice);
    setEjMode(DEFAULTS.ejMode);
    setEjManualLf(DEFAULTS.ejManualLf);
    setGravelDepthIn(DEFAULTS.gravelDepthIn);
    setGravelPricingMode(DEFAULTS.gravelPricingMode);
    setGravelPrice(DEFAULTS.gravelPrice);
    setTruckCapacityCy(DEFAULTS.truckCapacityCy);
    setTruckPrice(DEFAULTS.truckPrice);
    setWasteConc(DEFAULTS.wasteConc);
    setWasteRebar(DEFAULTS.wasteRebar);
    setWasteLumber(DEFAULTS.wasteLumber);
    setLaborMode(DEFAULTS.laborMode);
    setLaborWorkers(DEFAULTS.laborWorkers);
    setLaborDailyRate(DEFAULTS.laborDailyRate);
    setLaborDays(DEFAULTS.laborDays);
    setLaborSqftPrice(DEFAULTS.laborSqftPrice);
    setEquipment(DEFAULTS.equipment);
    setOverheadPct(DEFAULTS.overheadPct);
    setProfitPct(DEFAULTS.profitPct);
    setExtras(DEFAULTS.extras);
    setClientName(DEFAULTS.clientName);
    setClientAddress(DEFAULTS.clientAddress);
    setClientPhone(DEFAULTS.clientPhone);
    setScopeOfWork(DEFAULTS.scopeOfWork);
    localStorage.removeItem(STORAGE_KEY);
  };

  const takeoff = useMemo(
    () =>
      calcDrivewayTakeoff({
        sqft,
        widthFt,
        perimeterFt,
        thickness,
        rebarSpacingIn,
        rebarBarLenFt,
        lumberBoardsStacked,
        lumberBoardLenFt,
        stakeSpacingFt: STAKE_SPACING_FT,
        // expansionJointSpacingFt: el motor solo calcula franjas en una
        // dirección (driveway.py original). La cuadrícula real (10x10 /
        // 12x12 en ambas direcciones) se calcula aparte, más abajo.
        expansionJointSpacingFt: ejMaxPanelFt,
        gravelDepthIn,
        // poly y stakes: se omiten — sin tarjetas propias en este formulario,
        // caen al default de la fórmula. Poly se agrega en Extras si hace
        // falta; estacas se calculan 100% automático (ver STAKE_* arriba).
        waste: {
          concrete: wasteConc / 100,
          rebar: wasteRebar / 100,
          lumber: wasteLumber / 100,
        },
      }),
    [
      sqft,
      widthFt,
      perimeterFt,
      thickness,
      rebarSpacingIn,
      rebarBarLenFt,
      lumberBoardsStacked,
      lumberBoardLenFt,
      ejMaxPanelFt,
      gravelDepthIn,
      wasteConc,
      wasteRebar,
      wasteLumber,
    ]
  );

  // Expansion joints como cuadrícula real, no solo franjas a lo largo:
  // "N-1" juntas interiores para partir un tramo en paneles ≤ ejMaxPanelFt
  // (mismo patrón que foundation_rules.py usa para beams interiores).
  // Si el ancho ya cabe en un panel, numLongitudinal da 0 — no agrega
  // juntas de más.
  const ejNumTransverse = Math.max(0, Math.ceil(takeoff.lengthFt / ejMaxPanelFt) - 1); // corren a lo ancho
  const ejNumLongitudinal = Math.max(0, Math.ceil(widthFt / ejMaxPanelFt) - 1); // corren a lo largo
  const ejLfRaw = ejNumTransverse * widthFt + ejNumLongitudinal * takeoff.lengthFt;
  const ejLfAutoOrdered = Math.ceil(ejLfRaw * 1.05);
  const ejLfOrdered = ejMode === "manual" ? ejManualLf : ejLfAutoOrdered;

  const trucksNeeded = Math.ceil(takeoff.gravel.cyOrdered / Math.max(truckCapacityCy, 0.01));
  const gravelTotal =
    gravelPricingMode === "cy" ? takeoff.gravel.cyOrdered * gravelPrice : trucksNeeded * truckPrice;
  const gravelUnitPriceForWarning = gravelPricingMode === "cy" ? gravelPrice : truckPrice;

  const materials = [
    {
      label: `Concreto ${thickness}"`,
      raw: `${takeoff.concrete.cyRaw.toFixed(2)} CY`,
      ordered: takeoff.concrete.cyOrdered,
      unit: "CY",
      total: takeoff.concrete.cyOrdered * concPrice,
      unitPrice: concPrice,
    },
    {
      label: `Rebar ${rebarSize} (${rebarSpacingIn}" O.C.)`,
      raw: `${takeoff.rebar.lfRaw.toFixed(1)} LF`,
      ordered: takeoff.rebar.barsOrdered,
      unit: "varillas",
      total: takeoff.rebar.barsOrdered * rebarPrice,
      unitPrice: rebarPrice,
    },
    {
      label: `Lumber ${lumberSize}`,
      raw: `${takeoff.lumber.lfRaw.toFixed(0)} LF`,
      ordered: takeoff.lumber.boardsOrdered,
      unit: "tablas",
      total: takeoff.lumber.boardsOrdered * lumberPrice,
      unitPrice: lumberPrice,
    },
    {
      label: "Estacas rojas (automático)",
      raw: `${takeoff.stakes.raw.toFixed(1)}`,
      ordered: takeoff.stakes.ordered,
      unit: "pzas",
      total: takeoff.stakes.ordered * STAKE_PRICE,
      unitPrice: STAKE_PRICE,
    },
    {
      label: "Expansion joints",
      raw: `${ejLfRaw.toFixed(0)} LF`,
      ordered: ejLfOrdered,
      unit: "LF",
      total: ejLfOrdered * ejPrice,
      unitPrice: ejPrice,
    },
    {
      label: "Gravel base",
      raw: `${takeoff.gravel.cyRaw.toFixed(2)} CY`,
      ordered: takeoff.gravel.cyOrdered,
      unit: "CY",
      total: gravelTotal,
      unitPrice: gravelUnitPriceForWarning,
    },
  ];

  const totalMaterials = materials.reduce((sum, m) => sum + m.total, 0);
  const totalExtras = extras.reduce((sum, x) => sum + (Number.isFinite(x.price) ? x.price : 0), 0);

  const totalLaborDay = laborWorkers * laborDailyRate * laborDays;
  const totalLaborSqft = laborSqftPrice * sqft;
  const totalLabor = laborMode === "day" ? totalLaborDay : totalLaborSqft;

  const equipmentLabel = (item: EquipmentItem) =>
    item.type === "custom"
      ? item.customLabel || "Equipo personalizado"
      : EQUIPMENT_CATALOG.find((e) => e.type === item.type)?.label ?? item.type;

  const totalEquip = equipment.reduce((sum, x) => sum + (Number.isFinite(x.price) ? x.price : 0), 0);

  const subtotal = totalMaterials + totalLabor + totalEquip + totalExtras;
  const overheadAmt = subtotal * (overheadPct / 100);
  const profitAmt = subtotal * (profitPct / 100);
  const grandTotal = subtotal + overheadAmt + profitAmt;

  // ── Alertas: cosas que no cuadran y pueden hacerte perder dinero ──
  const warnings: string[] = [];

  materials.forEach((m) => {
    if (m.ordered > 0 && m.unitPrice <= 0) {
      warnings.push(`${m.label}: precio en $0 — estás regalando este material.`);
    }
  });

  if (profitPct <= 0) {
    warnings.push("Margen de ganancia en 0% — no queda colchón para errores ni imprevistos.");
  }
  if (totalLabor <= 0) {
    warnings.push("Mano de obra en $0 — revisa trabajadores/tarifa/días o el precio por sqft.");
  }
  equipment.forEach((x) => {
    if (x.price <= 0) warnings.push(`Equipo "${equipmentLabel(x)}": costo en $0.`);
  });
  extras.forEach((x) => {
    if (x.label.trim() && x.price <= 0) {
      warnings.push(`Extra "${x.label}": precio en $0.`);
    }
  });
  if (wasteConc <= 0) warnings.push("Waste de concreto en 0% — cualquier derrame o error te deja corto.");
  if (wasteRebar <= 0) warnings.push("Waste de rebar en 0% — riesgo de quedarte corto en varillas.");
  if (sqft > 0 && grandTotal <= 0) {
    warnings.push("El total calculado es $0 o negativo — revisa los precios ingresados.");
  }

  return (
    <>
      <div className="mb-6 flex items-center justify-between gap-4 print:hidden">
        <p className="text-xs text-white/30">💾 Se guarda solo en este navegador mientras trabajas.</p>
        <button
          type="button"
          onClick={resetAll}
          className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-white/60 transition hover:border-red-500/40 hover:text-red-400"
        >
          🆕 Nuevo takeoff
        </button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px] print:block">
        {/* ── Inputs ── */}
        <div className="columns-1 gap-6 sm:columns-2 print:hidden">
        <FormSection title="📐 Dimensiones del proyecto">
          <Field label="Área total (SQFT)">
            <NumberInput value={sqft} onChange={setSqft} min={1} step={10} />
          </Field>
          <Field label="Ancho del driveway (ft)">
            <NumberInput value={widthFt} onChange={setWidthFt} min={1} step={1} />
          </Field>
          <Field label="Perímetro (LF)">
            <NumberInput value={perimeterFt} onChange={setPerimeterFt} min={1} step={1} />
          </Field>
          <Field label="Largo calculado">
            <div className="mt-1.5 rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white">
              {takeoff.lengthFt.toFixed(1)} ft
            </div>
          </Field>
        </FormSection>

        <FormSection title="🏗️ Concreto — CY = SQFT ÷ divisor">
          <Field label="Espesor (in)">
            <Select
              value={thickness}
              onChange={(v) => setThickness(Number(v) as ConcreteThickness)}
              options={THICKNESS_OPTIONS.map((t) => ({ value: t, label: `${t}"` }))}
            />
          </Field>
          <Field label="Precio ($/CY)">
            <NumberInput value={concPrice} onChange={setConcPrice} min={0} step={1} />
          </Field>
          <Field label="Waste %">
            <NumberInput value={wasteConc} onChange={setWasteConc} min={0} max={20} step={0.5} />
          </Field>
          <Formula>
            SQFT {sqft.toLocaleString()} ÷ {takeoff.concrete.divisor} ={" "}
            <b>{takeoff.concrete.cyRaw.toFixed(2)} CY raw</b>
            <br />
            +{wasteConc.toFixed(0)}% waste → <b className="text-[#f0a500]">{takeoff.concrete.cyOrdered} CY a ordenar</b>
          </Formula>
        </FormSection>

        <FormSection title="🔩 Rebar — LF = SQFT × factor">
          <Field label="Tamaño">
            <Select
              value={rebarSize}
              onChange={setRebarSize}
              options={["#3", "#4", "#5"].map((v) => ({ value: v, label: v }))}
            />
          </Field>
          <Field label="Spacing O.C. (in)">
            <Select
              value={rebarSpacingIn}
              onChange={(v) => setRebarSpacingIn(Number(v) as RebarSpacing)}
              options={SPACING_OPTIONS.map((s) => ({ value: s, label: `${s}"` }))}
            />
          </Field>
          <Field label="Largo de varilla (ft)">
            <NumberInput value={rebarBarLenFt} onChange={setRebarBarLenFt} min={10} max={60} step={2} />
          </Field>
          <Field label="Precio por varilla ($)">
            <NumberInput value={rebarPrice} onChange={setRebarPrice} min={0} step={0.25} />
          </Field>
          <Field label="Waste %">
            <NumberInput value={wasteRebar} onChange={setWasteRebar} min={0} max={20} step={0.5} />
          </Field>
          <Formula>
            SQFT {sqft.toLocaleString()} × {takeoff.rebar.factor} ({rebarSpacingIn}&quot; O.C.) ={" "}
            <b>{takeoff.rebar.lfRaw.toFixed(1)} LF raw</b>
            <br />
            +{wasteRebar.toFixed(0)}% waste = {takeoff.rebar.lfOrdered.toFixed(1)} LF ÷ {rebarBarLenFt} ft ={" "}
            <b className="text-[#f0a500]">{takeoff.rebar.barsOrdered} varillas a ordenar</b>
          </Formula>
        </FormSection>

        <FormSection title="🪵 Lumber, Forms & Expansion Joints">
          <Field label="Tamaño de tabla">
            <Select
              value={lumberSize}
              onChange={setLumberSize}
              options={["2x4", "2x6", "2x8"].map((v) => ({ value: v, label: v }))}
            />
          </Field>
          <Field label="Largo de tabla (ft)">
            <NumberInput value={lumberBoardLenFt} onChange={setLumberBoardLenFt} min={8} step={2} />
          </Field>
          <Field label="Tablas por lado (apiladas)">
            <NumberInput value={lumberBoardsStacked} onChange={setLumberBoardsStacked} min={1} max={4} step={1} />
          </Field>
          <Field label="Precio por tabla ($)">
            <NumberInput value={lumberPrice} onChange={setLumberPrice} min={0} step={0.25} />
          </Field>
          <Field label="Waste %">
            <NumberInput value={wasteLumber} onChange={setWasteLumber} min={0} max={20} step={0.5} />
          </Field>
          <Formula>
            Perímetro {perimeterFt} LF × {lumberBoardsStacked} apiladas = {takeoff.lumber.lfRaw.toFixed(0)} LF raw
            <br />
            +{wasteLumber.toFixed(0)}% waste = {takeoff.lumber.lfOrdered.toFixed(1)} LF ÷ {lumberBoardLenFt} ft ={" "}
            <b className="text-[#f0a500]">{takeoff.lumber.boardsOrdered} tablas a ordenar</b>
          </Formula>

          <div className="col-span-full flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => setEjMode("auto")}
              className={`rounded-lg px-3 py-1.5 transition ${
                ejMode === "auto" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              🧮 EJ automático
            </button>
            <button
              type="button"
              onClick={() => {
                setEjMode("manual");
                setEjManualLf(ejLfAutoOrdered);
              }}
              className={`rounded-lg px-3 py-1.5 transition ${
                ejMode === "manual" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              ✏️ EJ manual
            </button>
          </div>

          <Field label="EJ — Tamaño máx. de cuadro (ft)">
            <Select
              value={ejMaxPanelFt}
              onChange={(v) => setEjMaxPanelFt(Number(v) as 10 | 12)}
              options={[
                { value: 10, label: '10×10"' },
                { value: 12, label: '12×12"' },
              ]}
            />
          </Field>
          <Field label="EJ — Precio ($/LF)">
            <NumberInput value={ejPrice} onChange={setEjPrice} min={0} step={0.05} />
          </Field>
          {ejMode === "manual" && (
            <Field label="EJ — LF personalizados">
              <NumberInput value={ejManualLf} onChange={setEjManualLf} min={0} step={1} />
            </Field>
          )}
          <Formula>
            Expansion Joints — cuadros de máx. {ejMaxPanelFt}×{ejMaxPanelFt} ft:
            <br />
            Transversales: largo {takeoff.lengthFt.toFixed(1)} ft ÷ {ejMaxPanelFt} ft ={" "}
            {ejNumTransverse} {plural(ejNumTransverse, "junta", "juntas")} × {widthFt} ft ancho
            <br />
            Longitudinales: ancho {widthFt} ft ÷ {ejMaxPanelFt} ft = {ejNumLongitudinal}{" "}
            {plural(ejNumLongitudinal, "junta", "juntas")} × {takeoff.lengthFt.toFixed(1)} ft largo
            <br />
            {ejMode === "auto" ? (
              <>
                Total: {ejLfRaw.toFixed(0)} LF → <b className="text-[#f0a500]">{ejLfOrdered} LF (+5%)</b>
              </>
            ) : (
              <>
                Sugerido: {ejLfRaw.toFixed(0)} LF raw → {ejLfAutoOrdered} LF (+5%) — usando tu valor:{" "}
                <b className="text-[#f0a500]">{ejManualLf} LF</b>
              </>
            )}
          </Formula>

          <Formula>
            🔴 Estacas (automático, sin nada que configurar):
            <br />
            Perímetro {perimeterFt} LF ÷ {STAKE_SPACING_FT} ft O.C. = {takeoff.stakes.raw.toFixed(1)} raw
            <br />
            +waste = <b className="text-[#f0a500]">{takeoff.stakes.ordered} estacas a ordenar</b> @{" "}
            {money(STAKE_PRICE)} c/u
          </Formula>
        </FormSection>

        <FormSection title="🛡️ Gravel base">
          <Field label="Profundidad de gravel (in)">
            <NumberInput value={gravelDepthIn} onChange={setGravelDepthIn} min={0} max={12} step={1} />
          </Field>
          <div className="col-span-full flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => setGravelPricingMode("cy")}
              className={`rounded-lg px-3 py-1.5 transition ${
                gravelPricingMode === "cy" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              🪨 Por CY
            </button>
            <button
              type="button"
              onClick={() => setGravelPricingMode("truck")}
              className={`rounded-lg px-3 py-1.5 transition ${
                gravelPricingMode === "truck" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              🚛 Por camión
            </button>
          </div>

          {gravelPricingMode === "cy" ? (
            <>
              <Field label="Precio gravel ($/CY)">
                <NumberInput value={gravelPrice} onChange={setGravelPrice} min={0} step={1} />
              </Field>
              <Formula>
                Gravel: {takeoff.gravel.cyRaw.toFixed(2)} CY raw →{" "}
                <b className="text-[#f0a500]">{takeoff.gravel.cyOrdered} CY (+10%)</b> × {money(gravelPrice)} ={" "}
                <b className="text-[#f0a500]">{money(gravelTotal)}</b>
              </Formula>
            </>
          ) : (
            <>
              <Field label="CY por camión">
                <NumberInput value={truckCapacityCy} onChange={setTruckCapacityCy} min={1} step={1} />
              </Field>
              <Field label="Precio por camión ($)">
                <NumberInput value={truckPrice} onChange={setTruckPrice} min={0} step={10} />
              </Field>
              <Formula>
                Gravel: {takeoff.gravel.cyOrdered} CY ÷ {truckCapacityCy} CY/camión ={" "}
                <b className="text-[#f0a500]">
                  {trucksNeeded} {plural(trucksNeeded, "camión", "camiones")}
                </b>{" "}
                × {money(truckPrice)} ={" "}
                <b className="text-[#f0a500]">{money(gravelTotal)}</b>
              </Formula>
            </>
          )}
        </FormSection>

        <FormSection title="👷 Mano de obra">
          <div className="col-span-full flex items-center gap-2 text-sm">
            <button
              type="button"
              onClick={() => setLaborMode("day")}
              className={`rounded-lg px-3 py-1.5 transition ${
                laborMode === "day" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              📅 Por día
            </button>
            <button
              type="button"
              onClick={() => setLaborMode("sqft")}
              className={`rounded-lg px-3 py-1.5 transition ${
                laborMode === "sqft" ? "bg-[#f0a500] text-black" : "bg-white/5 text-white/60 hover:bg-white/10"
              }`}
            >
              📐 Por SQFT
            </button>
          </div>

          {laborMode === "day" ? (
            <>
              <Field label="Trabajadores">
                <NumberInput value={laborWorkers} onChange={setLaborWorkers} min={1} step={1} />
              </Field>
              <Field label="Tarifa ($/día por trabajador)">
                <NumberInput value={laborDailyRate} onChange={setLaborDailyRate} min={0} step={10} />
              </Field>
              <Field label="Días">
                <NumberInput value={laborDays} onChange={setLaborDays} min={1} step={1} />
              </Field>
              <Formula>
                {laborWorkers} trabajadores × {money(laborDailyRate)}/día × {laborDays} días ={" "}
                <b className="text-[#f0a500]">{money(totalLaborDay)}</b>
              </Formula>
            </>
          ) : (
            <>
              <Field label="Precio por pie cuadrado ($/sqft)">
                <NumberInput value={laborSqftPrice} onChange={setLaborSqftPrice} min={0} step={0.1} />
              </Field>
              <Formula>
                SQFT {sqft.toLocaleString()} × {money(laborSqftPrice)} ={" "}
                <b className="text-[#f0a500]">{money(totalLaborSqft)}</b>
              </Formula>
            </>
          )}
        </FormSection>

        <FormSection title="🚜 Equipo">
          {equipment.length === 0 && (
            <p className="col-span-full text-sm text-white/40">
              Sin equipo agregado. Agrega el que necesites — pump, buggy, compactadora, etc.
            </p>
          )}
          {equipment.map((item) => (
            <div key={item.id} className="col-span-full flex flex-wrap items-end gap-3">
              <label className="block min-w-[150px] flex-1 text-sm">
                <span className="text-white/70">Equipo</span>
                <Select
                  value={item.type}
                  onChange={(v) => {
                    const catalogItem = EQUIPMENT_CATALOG.find((e) => e.type === v);
                    updateEquipment(item.id, {
                      type: v as EquipmentType,
                      price: catalogItem?.defaultPrice ?? item.price,
                    });
                  }}
                  options={EQUIPMENT_CATALOG.map((e) => ({ value: e.type, label: e.label }))}
                />
              </label>
              {item.type === "custom" && (
                <label className="block min-w-[150px] flex-1 text-sm">
                  <span className="text-white/70">Nombre</span>
                  <input
                    type="text"
                    value={item.customLabel}
                    onChange={(e) => updateEquipment(item.id, { customLabel: e.target.value })}
                    placeholder="ej. Generador"
                    className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/30 focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                  />
                </label>
              )}
              <label className="block w-28 shrink-0 text-sm">
                <span className="text-white/70">Precio ($)</span>
                <NumberInput
                  value={item.price}
                  onChange={(v) => updateEquipment(item.id, { price: v })}
                  min={0}
                  step={25}
                />
              </label>
              <button
                type="button"
                onClick={() => removeEquipment(item.id)}
                className="mb-0.5 shrink-0 rounded-lg border border-white/10 px-3 py-2.5 text-sm text-white/50 transition hover:border-red-500/40 hover:text-red-400"
                title="Quitar equipo"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addEquipment}
            className="col-span-full rounded-lg border border-dashed border-white/15 px-3 py-2.5 text-sm text-white/60 transition hover:border-[#f0a500]/50 hover:text-[#f0a500]"
          >
            + Agregar equipo
          </button>
          {equipment.length > 0 && (
            <Formula>
              Total equipo: <b className="text-[#f0a500]">{money(totalEquip)}</b>
            </Formula>
          )}
        </FormSection>

        <FormSection title="📊 Overhead & Margen">
          <Field label="Overhead (%)">
            <NumberInput value={overheadPct} onChange={setOverheadPct} min={0} max={100} step={0.5} />
          </Field>
          <div>
            <span className="text-white/70">Monto</span>
            <div className="mt-1.5 flex h-[42px] items-center text-lg font-semibold text-white">
              {money(overheadAmt)}
            </div>
          </div>
          <Field label="Profit margin (%)">
            <NumberInput value={profitPct} onChange={setProfitPct} min={0} max={100} step={0.5} />
          </Field>
          <div>
            <span className="text-white/70">Monto</span>
            <div className="mt-1.5 flex h-[42px] items-center text-lg font-semibold text-white">
              {money(profitAmt)}
            </div>
          </div>
        </FormSection>

        <FormSection title="➕ Extras">
          {extras.length === 0 && (
            <p className="col-span-full text-sm text-white/40">
              Sin extras todavía. Agrega cualquier costo que no entre en las categorías de arriba.
            </p>
          )}
          {extras.map((x) => (
            <div key={x.id} className="col-span-full flex items-end gap-3">
              <label className="block flex-1 text-sm">
                <span className="text-white/70">Descripción</span>
                <input
                  type="text"
                  value={x.label}
                  onChange={(e) => updateExtra(x.id, { label: e.target.value })}
                  placeholder="ej. Demolición de driveway viejo"
                  className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition placeholder:text-white/30 focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                />
              </label>
              <label className="block w-36 text-sm">
                <span className="text-white/70">Precio ($)</span>
                <NumberInput
                  value={x.price}
                  onChange={(v) => updateExtra(x.id, { price: v })}
                  min={0}
                  step={10}
                />
              </label>
              <button
                type="button"
                onClick={() => removeExtra(x.id)}
                className="mb-0.5 rounded-lg border border-white/10 px-3 py-2.5 text-sm text-white/50 transition hover:border-red-500/40 hover:text-red-400"
                title="Quitar extra"
              >
                ✕
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addExtra}
            className="col-span-full rounded-lg border border-dashed border-white/15 px-3 py-2.5 text-sm text-white/60 transition hover:border-[#f0a500]/50 hover:text-[#f0a500]"
          >
            + Agregar extra
          </button>
          {extras.length > 0 && (
            <Formula>
              Total extras: <b className="text-[#f0a500]">{money(totalExtras)}</b>
            </Formula>
          )}
        </FormSection>
      </div>

      {/* ── Columna derecha: resumen (sticky) + cotización formal (no sticky, debajo) ── */}
      <div className="print:block">
      <div className="lg:sticky lg:top-6 lg:self-start print:hidden">
        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">
            📊 Resumen del takeoff
          </h2>

          {warnings.length > 0 && (
            <div className="mt-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3">
              <p className="flex items-center gap-1.5 text-sm font-semibold text-red-400">
                🚨 Revisa antes de cotizar — {warnings.length}{" "}
                {warnings.length === 1 ? "problema" : "problemas"}
              </p>
              <ul className="mt-2 space-y-1 text-xs text-red-300">
                {warnings.map((w) => (
                  <li key={w}>• {w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-5 overflow-x-auto">
            <table className="w-full text-sm text-white">
              <thead>
                <tr className="border-b border-white/10 text-left text-xs text-white/50">
                  <th className="py-1.5 pr-2 font-medium">Material</th>
                  <th className="py-1.5 pr-2 font-medium">Raw</th>
                  <th className="py-1.5 pr-2 text-right font-medium">A ordenar</th>
                  <th className="py-1.5 text-right font-medium">Total</th>
                </tr>
              </thead>
              <tbody>
                {materials.map((m) => (
                  <tr key={m.label} className="border-b border-white/5">
                    <td className="py-1.5 pr-2">{m.label}</td>
                    <td className="py-1.5 pr-2 text-white/50">{m.raw}</td>
                    <td className="py-1.5 pr-2 text-right font-medium">
                      {m.ordered} {m.unit}
                    </td>
                    <td className="py-1.5 text-right">{money(m.total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 space-y-1.5 border-t border-white/10 pt-4 text-sm">
            <Row label="Materiales" value={money(totalMaterials)} />
            <Row label="Mano de obra" value={money(totalLabor)} />
            <Row label="Equipo" value={money(totalEquip)} />
            {extras.length > 0 && <Row label="Extras" value={money(totalExtras)} />}
            <Row label="Subtotal" value={money(subtotal)} muted />
            <Row label={`Overhead (${overheadPct.toFixed(0)}%)`} value={money(overheadAmt)} />
            <Row label={`Margen (${profitPct.toFixed(0)}%)`} value={money(profitAmt)} />
          </div>

          <div className="mt-3 flex items-baseline justify-between border-t border-white/10 pt-4">
            <span className="text-sm font-medium text-white">TOTAL</span>
            <span className="text-2xl font-bold text-[#f0a500]">{money(grandTotal)}</span>
          </div>
          {sqft > 0 && (
            <p className="mt-1 text-right text-xs text-white/40">{money(grandTotal / sqft)} / sqft</p>
          )}

          <p className="mt-4 rounded-md bg-amber-900/20 px-3 py-2 text-xs text-amber-200">
            ⚠️ Verifica antes de ordenar. Las cantidades de materiales ya incluyen waste.
          </p>
        </div>
      </div>

      {/* ── Botón único: abre el estimado profesional completo en modal ── */}
      <button
        type="button"
        onClick={() => setShowPreview(true)}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-2xl border border-[#f0a500]/30 bg-[#f0a500]/10 py-4 text-sm font-semibold text-[#f0a500] transition hover:bg-[#f0a500]/20 print:hidden"
      >
        👁️ Preview — ver estimado profesional
      </button>
      </div>
      </div>

      {/* ── Modal: estimado profesional completo, editable, con Guardar/Imprimir ── */}
      {showPreview && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/70 p-4 py-10 print:static print:block print:bg-transparent print:p-0">
          <div className="w-full max-w-2xl rounded-2xl border border-white/10 bg-[#111827] p-6 shadow-2xl print:static print:w-full print:max-w-none print:rounded-none print:border-0 print:bg-transparent print:p-0 print:shadow-none">
            <div className="flex items-center justify-between print:hidden">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">
                📄 Estimado profesional
              </h2>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => window.print()}
                  className="rounded-lg bg-[#f0a500] px-3 py-1.5 text-sm font-semibold text-black transition hover:brightness-110"
                >
                  🖨️ Guardar PDF / Imprimir
                </button>
                <button
                  type="button"
                  onClick={() => setShowPreview(false)}
                  className="rounded-lg border border-white/10 px-3 py-1.5 text-sm text-white/60 transition hover:border-white/30 hover:text-white"
                >
                  ✕ Cerrar
                </button>
              </div>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-4 print:hidden">
              <Field label="Nombre del cliente">
                <input
                  type="text"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                />
              </Field>
              <Field label="Teléfono">
                <input
                  type="text"
                  value={clientPhone}
                  onChange={(e) => setClientPhone(e.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                />
              </Field>
              <div className="col-span-full">
                <Field label="Dirección del proyecto">
                  <input
                    type="text"
                    value={clientAddress}
                    onChange={(e) => setClientAddress(e.target.value)}
                    className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                  />
                </Field>
              </div>
              <div className="col-span-full">
                <Field label="Alcance del trabajo">
                  <textarea
                    rows={3}
                    value={scopeOfWork}
                    onChange={(e) => setScopeOfWork(e.target.value)}
                    className="mt-1.5 w-full resize-y rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
                  />
                </Field>
              </div>
            </div>

            {/* El documento en sí — esto es lo único que queda en la hoja al imprimir */}
            <div className="mt-6 rounded-xl border border-white/10 bg-[#0d1117] p-6 text-sm text-white print:border-0 print:bg-white print:text-black">
              <div className="flex items-start justify-between border-b border-white/10 pb-4 print:border-black/20">
                <div>
                  {companyProfile.logoDataUrl && (
                    // Logo del contratista (base64 de Ajustes) — no es un asset
                    // del proyecto, <img> normal en vez de next/image.
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={companyProfile.logoDataUrl}
                      alt={companyProfile.companyName || "Logo"}
                      className="mb-1.5 h-10 object-contain"
                    />
                  )}
                  {companyProfile.companyName ? (
                    <div className="text-lg font-bold text-[#f0a500] print:text-black">
                      {companyProfile.companyName}
                    </div>
                  ) : (
                    <a
                      href="/dashboard/settings"
                      className="text-sm text-white/30 underline-offset-2 hover:text-[#f0a500] hover:underline print:hidden"
                    >
                      Configura el nombre de tu empresa en Ajustes →
                    </a>
                  )}
                  <div className="text-xs text-white/40 print:text-black/60">Estimado de Driveway</div>
                  {(companyProfile.website || companyProfile.whatsapp) && (
                    <div className="mt-1 text-[11px] text-white/40 print:text-black/50">
                      {[companyProfile.website, companyProfile.whatsapp].filter(Boolean).join(" · ")}
                    </div>
                  )}
                </div>
                <div className="text-right text-xs text-white/50 print:text-black/60">
                  {new Date().toLocaleDateString("es-ES", { year: "numeric", month: "long", day: "numeric" })}
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
                <div>
                  <span className="text-white/40 print:text-black/50">Cliente: </span>
                  {clientName || "—"}
                </div>
                <div>
                  <span className="text-white/40 print:text-black/50">Teléfono: </span>
                  {clientPhone || "—"}
                </div>
                <div className="col-span-2">
                  <span className="text-white/40 print:text-black/50">Dirección: </span>
                  {clientAddress || "—"}
                </div>
                <div className="col-span-2">
                  <span className="text-white/40 print:text-black/50">Proyecto: </span>
                  {sqft.toLocaleString()} SQFT · {thickness}&quot; de espesor · {widthFt} ft ancho ×{" "}
                  {takeoff.lengthFt.toFixed(1)} ft largo
                </div>
              </div>

              <div className="mt-4 overflow-x-auto">
                <table className="w-full border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-white/20 text-left print:border-black/30">
                      <th className="py-1.5 font-medium">Concepto</th>
                      <th className="py-1.5 text-right font-medium">Monto</th>
                    </tr>
                  </thead>
                  <tbody>
                    {materials.map((m) => (
                      <tr key={m.label} className="border-b border-white/5 print:border-black/10">
                        <td className="py-1">{m.label}</td>
                        <td className="py-1 text-right">{money(m.total)}</td>
                      </tr>
                    ))}
                    <tr className="border-b border-white/5 print:border-black/10">
                      <td className="py-1">Mano de obra</td>
                      <td className="py-1 text-right">{money(totalLabor)}</td>
                    </tr>
                    {equipment.map((x) => (
                      <tr key={x.id} className="border-b border-white/5 print:border-black/10">
                        <td className="py-1">Equipo — {equipmentLabel(x)}</td>
                        <td className="py-1 text-right">{money(x.price)}</td>
                      </tr>
                    ))}
                    {extras.map((x) => (
                      <tr key={x.id} className="border-b border-white/5 print:border-black/10">
                        <td className="py-1">{x.label || "Extra"}</td>
                        <td className="py-1 text-right">{money(x.price)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Sin Subtotal/Overhead/Margen aquí a propósito — el cliente ve el
                  precio por concepto y el total, no tu desglose de markup interno
                  (eso sigue visible solo en el Resumen del takeoff). */}
              <div className="mt-3 flex items-baseline justify-between border-t border-white/10 pt-3 print:border-black/20">
                <span className="font-semibold">TOTAL</span>
                <span className="text-xl font-bold text-[#f0a500] print:text-black">{money(grandTotal)}</span>
              </div>
              {sqft > 0 && (
                <p className="text-right text-[11px] text-white/40 print:text-black/50">
                  {money(grandTotal / sqft)} / sqft
                </p>
              )}

              <div className="mt-4 whitespace-pre-wrap border-t border-white/10 pt-4 text-xs text-white/60 print:border-black/20 print:text-black/70">
                {scopeOfWork}
              </div>

              <div className="mt-8 grid grid-cols-2 gap-8 text-xs text-white/40 print:text-black/60">
                <div>
                  Firma del cliente: ______________________
                  <br />
                  <br />
                  Fecha: ______________
                </div>
                <div>
                  Firma del contratista: ______________________
                  <br />
                  <br />
                  Fecha: ______________
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── UI helpers ───────────────────────────────────────────────────────────

function FormSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-6 break-inside-avoid rounded-2xl border border-white/10 bg-white/[0.03] p-6 shadow-lg shadow-black/20 backdrop-blur-xl">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-[#f0a500]">
        {title}
      </h2>
      <div className="mt-5 grid grid-cols-2 gap-x-4 gap-y-5">{children}</div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="text-white/70">{label}</span>
      {children}
    </label>
  );
}

function NumberInput({
  value,
  onChange,
  min,
  max,
  step,
}: {
  value: number;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(e) => {
        const v = e.target.valueAsNumber;
        onChange(Number.isFinite(v) ? v : 0);
      }}
      className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
    />
  );
}

function Select<T extends string | number>({
  value,
  onChange,
  options,
}: {
  value: T;
  onChange: (v: string) => void;
  options: { value: T; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/5 px-3.5 py-2.5 text-sm text-white outline-none transition focus:border-[#f0a500]/60 focus:bg-white/[0.07]"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value} className="bg-[#111827] text-white">
          {o.label}
        </option>
      ))}
    </select>
  );
}

function Row({ label, value, muted }: { label: string; value: string; muted?: boolean }) {
  return (
    <div className={`flex items-center justify-between ${muted ? "text-white/40" : "text-white/80"}`}>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <div className="col-span-full rounded-lg border border-[#f0a500]/30 bg-[#f0a500]/[0.07] px-4 py-3 font-mono text-[13px] leading-relaxed text-slate-300">
      {children}
    </div>
  );
}
