# LYNSUS FLATWORK ESTIMATOR - CONTEXTO DEL PROYECTO

## ARCHIVO PRINCIPAL: app.py
## COMANDO: python -m streamlit run app.py
## CARPETA: C:\Users\koshl\OneDrive\Desktop\estimator lynsus
## REPO GITHUB: https://github.com/jormanmujica-cmyk/lynsus-Estimator
## APP LIVE: https://lynsus-estimator-ckeyfqcem7zkpnendncopa.streamlit.app

## FLUJO DE DEPLOY:
- Editar app.py en VS Code
- Desde terminal de VS Code (NO descargar archivos):
  git add . → git commit -m "descripcion" → git push
- Streamlit Cloud actualiza automaticamente en ~2 minutos

## TABS DE LA APP:
1. Estimator
2. Client Quote
3. Update Prices
4. Crew Planner
5. Contract Analyzer

## TAB 1 - ESTIMATOR (MASTER CALCULATION ENGINE):
- Hero section con gradiente oscuro + imagen PNG (static/hero_background.png)
- Concrete Zones: Single / Driveway+Apron+Sidewalk / Custom
- PSI selector: 2500 / 3000 / 3500 / 4000
- Formula VERIFICADA: CY = (sqft x pulgadas) / 324 + waste%
- Driveway Width y Sidewalk Width inputs
- Forming: Sidewalk/Patio (1x4) / Driveway/Heavy (2x4) / Mixed / Manual
- Rebar: #3/#4/#5, spacing malla dos direcciones, waste %
- Base Material: tons=(sqft x pulgadas)x0.00309, trucks=ceil(tons/11)
- Labor: por sqft o total fijo
- Equipment: lineas multiples
- Demolition: opcional
- Overhead % y Profit %

## SESSION STATE (fuente unica de verdad):
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

## TAB 2 - CLIENT QUOTE:
- Lee SOLO de session_state
- Info cliente: nombre, apellido, direccion, telefono, email, fecha, quote number
- Scope of Work editable auto-generado
- NO muestra: CY, camiones, barras, overhead, profit
- PROJECT TOTAL + precio por sqft
- Seccion de firmas
- Boton Download PDF (reportlab) — VERIFICADO FUNCIONA
- Boton Print Quote
- BUG RESUELTO: sqft viene de session_state["total_sqft"]

## TAB 3 - UPDATE PRICES:
- Precio concreto manual → session_state + precios.json
- Upload PDF supplier → extrae precios → tabla confirmacion
- Reset to Ready Cable Defaults
- Precios mostrados: #3/#4/#5 Rebar, Lumber 1x4/2x4, Exp Joint, Stakes
- BUG RESUELTO: precio actualizado se refleja en Tab 1 via session_state

## TAB 4 - CREW PLANNER:
- Lee de session_state: total_sqft, total_bid, labor_budget, materials_cost, equipment_cost
- Crew table: nombre, pay type (hourly/daily), rate, horas/dia
- daily_crew_cost = suma crew
- days_required = ceil(sqft / production_rate)
- actual_labor_cost = daily_crew_cost x days_required
- labor_variance = labor_budget - actual_labor_cost
- max_days_budget = floor(labor_budget / daily_crew_cost)
- KPI: Labor Budget / Actual Labor / Variance / Max Days
- Charts Plotly: Donut / Bar / Line / Gauge
- Warning: verde/amarillo/rojo
- PDF Labor Plan descargable
- Profit Protection Summary
- Management Decision Box

## TAB 5 - CONTRACT ANALYZER:
- Project info fields: Project Name, GC Name, Job Number (auto-filled desde PDF/XLS)
- Upload PDF del GC → extrae SQFT y monto total automaticamente
- Upload G703 XLS → lee todos los line items con descripciones y precios
- Formatos soportados:
  * AIA G703 Excel (.xls/.xlsx) — lee line items por columnas item/description/value
  * Purchase Order PDF con tabla (Proteus format) — detecta header Description+Amount
  * Generic PDF lump sum (MBC format) — extrae total por regex
- Auto-extraccion de project info:
  * G703: Owner Project No (row4), Job Number (row5), Contractor (row7)
  * PDF PO: PO number, GC name (between X "Contractor"), Project Location
  * Keys intermedios (_ca_proj_extracted, _ca_gc_extracted, _ca_job_extracted)
    para evitar conflicto de session_state con widgets
- Step 2: Contract numbers — SQFT, Total Amount, ppsf calculado automatico
- Step 3: Crew independiente del Tab 4 (st.session_state["ca_crew"])
- Production speed: Slow/Average/Fast/Very Fast/Custom
- Sin SQFT: campo manual "Estimated Days to Complete"
- Campos de costo: Your Materials Cost ($), Equipment, Overhead %, Other
- Calcula: profit/loss, margin %, cost per sqft, labor per sqft, dias
- Verdict Banner: verde si gana / rojo si pierde
- Recommendation box: Accept o No Accept
- Grafica de rentabilidad por dia
- PDF Report descargable con:
  * Project info, G703/PO line items, cost analysis, crew, notas, recomendacion

## TABLE PARSER LOGIC (PDF line items):
- Busca tabla con header que contenga "Description" AND "Amount"
- Detecta columnas: desc_col, amt_col, qty_col
- Filtra filas con qty=0 (filler rows)
- Separa total rows de line item rows por keyword "TOTAL"
- Total: usa row de total si existe, sino suma de items

## CSS FIXES APLICADOS:
- Input text: color #1a1a2e en fondo blanco
- Labels: color #ffffff
- Placeholders: color #888888
- File uploader: estilos aplicados
- Sidebar inputs: texto visible

## REGLAS TECNICAS DE CAMPO:
- Driveway ancho >15ft: expansion joint centro obligatorio
- Sidewalk: expansion joint cada 20ft maximo
- Rebar para MALLA (dos direcciones)

## PRECIOS READY CABLE (12-1-2025):
- Rebar #3=$0.2295/LF / #4=$0.394/LF / #5=$0.6155/LF
- Lumber 1x4x16=$0.252/LF / 2x4x16=$0.328/LF
- Expansion Joint=$0.441/LF / Stakes=$14.17/bundle

## PENDIENTE:
- File uploader button completamente visible
- Taxes (revisar con contador)
- Excel export
- Hero image — URL estatica de Streamlit (no carga en cloud, requiere solucion)
