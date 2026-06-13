# LYNSUS FLATWORK ESTIMATOR - CONTEXTO DEL PROYECTO

## ARCHIVO PRINCIPAL: app.py
## COMANDO: python -m streamlit run app.py
## CARPETA: C:\Users\koshl\OneDrive\Desktop\estimator lynsus
## REPO GITHUB: https://github.com/jormanmujica-cmyk/lynsus-Estimator
## APP LIVE: https://lynsus-estimator-ckeyfqcem7zkpnendncopa.streamlit.app

## FLUJO DE DEPLOY:
- Editar app.py en VS Code
- Abrir Git Bash (NO PowerShell — no acepta &&)
- Navegar a carpeta: cd "/c/Users/koshl/OneDrive/Desktop/estimator lynsus"
- git add .
- git commit -m "descripcion"
- git push
- Streamlit Cloud actualiza automaticamente en ~2 minutos

## STACK:
- Python — lenguaje del proyecto
- VS Code — editor de codigo
- Git Bash — terminal para subir cambios (NO usar PowerShell)
- GitHub — almacen del codigo en la nube
- Streamlit — publica la app en internet

## TABS DE LA APP:
1. Estimator
2. Client Quote
3. Update Prices
4. Crew Planner
5. Contract Analyzer

## NAVEGACION (SISTEMA ACTUAL — post Fix 2):
- NO usa st.tabs() — usa sistema if/elif con session_state["active_tab"]
- Nav: 5 botones st.button() en st.columns(5), type="primary" si activo
- Cada boton escribe active_tab y llama st.rerun()
- Contenido: if active_tab==0 / elif ==1 / elif ==2 / elif ==3 / elif ==4
- Keys de nav: nav_0, nav_1, nav_2, nav_3, nav_4
- RAZON: if/elif solo renderiza el tab activo → sin key= los widgets resetean
  al navegar (los inactive tabs desaparecen y el positional ID cambia)

## SESSION STATE — _DEFAULTS (inicio de app, post Fix 3):
Bloque al inicio (antes del CSS), inicializa solo si la key NO existe:
- total_bid, materials_cost, labor_cost, labor_budget, equipment_cost
- subcontractor_cost, direct_cost, overhead_cost, profit_amount
- price_per_sqft, total_sqft, concrete_yards, concrete_price
- ovh_calc_suggested, active_tab (0), current_trade (""), generic_materials ([])
- generic_trade_last (None), generic_equipment ([{"name":"","cost":0.0}])
- generic_subs ([]), trade_selection ("Concrete / Flatwork")
- c_zone_setup, c_sqft, c_thick, c_waste_pct, c_conc_psi
- c_dw_width, c_sw_width, c_form_type, c_use_rebar, c_rebar_type
- c_rebar_spacing, c_rebar_waste, c_use_base, c_base_type, c_base_sqft
- c_base_thick, c_base_price_ton, c_base_price_truck, c_stakes_per_bundle
- c_labor_method, c_labor_rate, c_labor_flat, c_use_demo, c_demo_rate
- c_overhead_pct (0.0), c_profit_pct (0.0)
- c_driveway_sqft (0.0), c_sidewalk_sqft (0.0)  ← agregados Fix 4

## SESSION STATE — KEYS DE WIDGETS (post Fix 3):
REGLA: todos los widgets de sidebar deben tener key= para que session_state
preserve el valor cuando el tab cambia (if/elif descarta los tabs inactivos)
- Overhead Apply button escribe TANTO ovh_calc_suggested COMO c_overhead_pct
  (o g_overhead_pct en generic) — necesario porque key= ignora value= tras 1er render
- Tab 2 lee SOLO de session_state (no de widgets directos)
- Tab 4 lee SOLO de session_state

## TRADE_MATERIALS (post Fix 4 — formato string):
Formato: lista de strings "Nombre (Unidad)"
Parser al resetear: m.split(" (")[0].strip() → name, m.split("(")[-1].replace(")","").strip() → unit
Trades: Concrete/Flatwork=[] (usa su propio estimador), Framing, Tile/Flooring,
Pool/Piscina, Metal Building, Cleaning Services, Sheetrock/Drywall, Carpentry/Trim,
Painting/Pintura, Roofing, Plumbing, Electrical, HVAC, Landscaping, Fencing,
Demolition, Insulation, Waterproofing, Epoxy/Coating, Other/Custom=[]

## RESET DE MATERIALES GENERICOS (post Fix 4):
- Detecta cambio de trade comparando current_trade vs trade recien seleccionado
- Reset ocurre INMEDIATAMENTE despues del selectbox (antes del if/else de trade)
- Nuevo formato: {"name": ..., "unit": ..., "qty": 0.0, "price": 0.0}
- key="trade_selection" en el selectbox para persistir entre tabs

## TAB 1 - ESTIMATOR (MASTER CALCULATION ENGINE):
- Hero section con gradiente azul marino (light theme), altura 100px
- Trade selector en sidebar (key="trade_selection")
- Concrete / Flatwork: estimador dedicado con zonas, PSI, rebar, base, forming, demo
  * Concrete Zones: Single / Driveway+Apron+Sidewalk / Custom
  * PSI: 2500 / 3000 / 3500 / 4000
  * Formula VERIFICADA: CY = (sqft x pulgadas) / 324 + waste%
  * Forming: Sidewalk/Patio (1x4) / Driveway/Heavy (2x4) / Mixed / Manual
  * Mixed mode: inputs c_driveway_sqft y c_sidewalk_sqft (con key=, Fix 4)
  * Rebar: #3/#4/#5, spacing malla dos direcciones, waste %
  * Base Material: tons=(sqft x pulgadas)x0.00309, trucks=ceil(tons/11)
  * Labor: por sqft o total fijo
  * Equipment: lineas multiples
  * Demolition: opcional
  * Overhead % y Profit % (con key= en sidebar)
- Generic Estimator: todos los demas trades
  * Materials tabla editable
  * Labor Type: Employee / Subcontractor (labels correctos post Fix 1)
  * Equipment y Subcontractors separados
  * Overhead Calculator colapsable en col2

## VALORES DEFAULT (todos en 0 al abrir la app):
- Total Square Footage: 0
- Driveway / Apron / Sidewalk SQFT: 0 (keys: c_driveway_sqft, c_sidewalk_sqft)
- Concrete Waste %: 0
- Rebar Waste %: 0
- Labor ($/SQFT): 0
- Demolition ($/SQFT): 0
- Overhead %: 0
- Profit %: 0
- Precios de materiales (concreto, rebar, lumber): valores de Ready Cable — NO en 0

## TEMA VISUAL (LIGHT THEME — aplicado 2026):
- Fondo global: #f0f4f8 (gris claro)
- Sidebar: blanco #ffffff
- Acento principal: azul #1d4ed8 (antes naranja #f59e0b)
- Botones: azul degradado #1d4ed8 → #1e40af
- Total box: fondo azul claro con borde azul
- Inputs: fondo blanco, texto oscuro / Labels: texto oscuro #1a202c
- File uploader: fondo #eff6ff, borde azul punteado
- Hero fallback: azul marino #1e3a8a / Scrollbar: thumb #cbd5e0, hover azul

## SESSION STATE — RESULTADOS (fuente unica de verdad para Tabs 2-5):
- st.session_state["total_sqft"]
- st.session_state["total_bid"]
- st.session_state["materials_cost"]
- st.session_state["equipment_cost"]
- st.session_state["direct_cost"]
- st.session_state["labor_budget"]
- st.session_state["labor_cost"]
- st.session_state["overhead_cost"]
- st.session_state["profit_amount"]
- st.session_state["price_per_sqft"]
- st.session_state["concrete_yards"]
- st.session_state["concrete_price"]
- st.session_state["ovh_calc_suggested"]  ← % sugerido por Overhead Calculator

## TAB 2 - CLIENT QUOTE:
- Lee SOLO de session_state (no de widgets del Tab 1)
- _q_sqft = session_state.get("total_sqft", 0.0)
- _q_total_bid = session_state.get("total_bid", 0.0)
- _q_ppsf = session_state.get("price_per_sqft", 0.0)
- scope_subtotal = _q_total_bid (sin doble resta — Fix 3)
- Info cliente: nombre, apellido, direccion, telefono, email, fecha, quote number
- Scope of Work editable auto-generado
- NO muestra: CY, camiones, barras, overhead, profit
- PROJECT TOTAL + precio por sqft
- Seccion de firmas, Download PDF (reportlab), Print Quote

## TAB 3 - UPDATE PRICES:
- Precio concreto manual → session_state + precios.json
- Upload PDF supplier → extrae precios → tabla confirmacion
- Reset to Ready Cable Defaults
- Precios: #3/#4/#5 Rebar, Lumber 1x4/2x4, Exp Joint, Stakes

## TAB 4 - CREW PLANNER:
- Lee de session_state: total_sqft, total_bid, labor_budget, materials_cost, equipment_cost
- Crew table: nombre, pay type (hourly/daily), rate, horas/dia
- daily_crew_cost = suma crew
- days_required = ceil(sqft / production_rate) — guarded: if _ca_prod_rate > 0 else 1 (Fix 4)
- actual_labor_cost = daily_crew_cost x days_required
- labor_variance = labor_budget - actual_labor_cost
- KPI: Labor Budget / Actual Labor / Variance / Max Days
- Charts Plotly: Donut / Bar / Line / Gauge
- Warning: verde/amarillo/rojo
- PDF Labor Plan descargable

## TAB 5 - CONTRACT ANALYZER:
- Project info fields: Project Name, GC Name, Job Number (auto-filled desde PDF/XLS)
- Upload PDF del GC → extrae SQFT y monto total automaticamente
- Upload G703 XLS → lee todos los line items con descripciones y precios
- Formatos soportados:
  * AIA G703 Excel (.xls/.xlsx) — lee line items por columnas item/description/value
  * Purchase Order PDF con tabla (Proteus format) — detecta header Description+Amount
  * Generic PDF lump sum (MBC format) — extrae total por regex
- Step 2: Contract numbers — SQFT, Total Amount, ppsf calculado automatico
- Step 3: Crew independiente del Tab 4 (st.session_state["ca_crew"])
- Production speed: Slow/Average/Fast/Very Fast/Custom
- Sin SQFT: campo manual "Estimated Days to Complete"
- Calcula: profit/loss, margin %, cost per sqft, labor per sqft, dias
  * _ca_days_req guarded: if _ca_prod_rate > 0 else 1 (Fix 4)
- Verdict Banner: verde si gana / rojo si pierde
- PDF Report descargable

## BUGS RESUELTOS (historial):
- Fix 1: Labor Type labels (Employee/Subcontractor), Cleaning Services separado de Roofing,
  total_sqft solo escribe si unidad es SQFT, reset de materiales inmediato al cambiar trade
- Fix 2: Navegacion reemplazada de st.tabs() a if/elif + st.button() (session_state persiste)
- Fix 3: _DEFAULTS block, key= en todos los widgets sidebar, Apply buttons escriben directo
  a session_state, Tab 2 lee solo de session_state, scope_subtotal sin doble resta
- Fix 4: TRADE_MATERIALS formato string, reset logic parsea strings, keys en Mixed SQFT inputs,
  division-by-zero guards en lineas 2423 y 4105

## OVERHEAD CALCULATOR (Tab 1 → col2, al final del Cost Breakdown):
- UBICACION: dentro de with col2:, DESPUES del Cost Breakdown
- st.expander("🧮 Overhead Calculator", expanded=False) — colapsable
- _oc_left: 12 campos Fixed Overhead / _oc_right: 8 campos Variable + Revenue Base
- Formulas: overhead_pct_calc = (total_overhead / revenue) * 100 (solo si revenue > 0)
- Boton "✅ Apply X.X% to Overhead (sidebar)" → escribe ovh_calc_suggested Y c_overhead_pct → st.rerun()
- Keys: oc_rent, oc_veh, oc_equip, oc_gl, oc_wc, oc_auto, oc_lic, oc_legal,
  oc_admin, oc_phone, oc_soft, oc_ofixed, oc_fuel, oc_vmaint, oc_tools, oc_ppe,
  oc_dump, oc_mktg, oc_bank, oc_misc, oc_revenue, oc_apply_btn

## PRECIOS READY CABLE (12-1-2025):
- Rebar #3=$0.2295/LF / #4=$0.394/LF / #5=$0.6155/LF
- Lumber 1x4x16=$0.252/LF / 2x4x16=$0.328/LF
- Expansion Joint=$0.441/LF / Stakes=$14.17/bundle

## PDF LOGO (sidebar → ⚙️ Customize Header → PDF / Quote Info):
- Upload JPG/PNG → session_state["pdf_logo_bytes"]
- Con logo: letterhead style (logo centrado, linea dorada, sin recuadro oscuro)
- Sin logo: recuadro oscuro original con nombre+tagline
- Aplica a los 3 PDFs: Quote, Labor Plan, Contract Report
- Boton "Remove Logo" en sidebar

## PDF COMPANY NAME / TAGLINE / SCOPE LABEL:
- sidebar → ⚙️ Customize Header → PDF / Quote Info
- Company Name, Tagline, Scope of Work Label — todos personalizables

## REGLAS TECNICAS DE CAMPO:
- Driveway ancho >15ft: expansion joint centro obligatorio
- Sidewalk: expansion joint cada 20ft maximo
- Rebar para MALLA (dos direcciones)
- CY = (sqft x pulgadas) / 324 + waste% — formula VERIFICADA, no cambiar

## PENDIENTE:
- File uploader button completamente visible
- Taxes (revisar con contador)
- Excel export
- Hero image — URL estatica de Streamlit (no carga en cloud, requiere solucion)
