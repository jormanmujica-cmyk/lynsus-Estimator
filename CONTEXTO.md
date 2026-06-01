# LYNSUS FLATWORK ESTIMATOR - CONTEXTO DEL PROYECTO

## ARCHIVO PRINCIPAL: app.py
## COMANDO: python -m streamlit run app.py
## CARPETA: C:\Users\koshl\OneDrive\Desktop\estimator lynsus

## TABS DE LA APP:
1. Estimator
2. Client Quote
3. Update Prices
4. Crew Planner

## TAB 1 - ESTIMATOR (MASTER CALCULATION ENGINE):
- Hero section con gradiente oscuro + imagen PNG (static/hero_background.png)
  URL: http://localhost:8501/app/static/hero_background.png
- Concrete Zones: Single / Driveway+Apron+Sidewalk / Custom
- PSI selector: 3000 / 3500 / 4000 / Custom
- Formula VERIFICADA: CY = (sqft x pulgadas) / 324 + waste%
- Driveway Width y Sidewalk Width inputs
- Forming: 1x4x16 / 2x4x16 / Mixed / Manual
- Rebar: #3/#4/#5, spacing malla dos direcciones
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
- Boton Download PDF (reportlab)
- Boton Print Quote
- BUG PENDIENTE: verificar sqft viene de session_state["total_sqft"]

## TAB 3 - UPDATE PRICES:
- Precio concreto manual → session_state + precios.json
- Upload PDF supplier → extrae precios → tabla confirmacion
- Reset to Ready Cable Defaults
- Precios mostrados: #3/#4/#5 Rebar, Lumber 1x4/2x4, Exp Joint, Stakes
- BUG PENDIENTE: verificar precio actualizado se refleja en Tab 1

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

## CSS FIXES APLICADOS:
- Input text: color #1a1a2e en fondo blanco
- Labels: color #ffffff
- Placeholders: color #888888
- File uploader: estilos aplicados (parcialmente visible)
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
- Corregir bug sqft Client Quote
- Corregir bug precio concreto Tab 3 a Tab 1
- File uploader button completamente visible
- PDF download verificar funciona
- Taxes (revisar con contador)
- Excel export
- Hero image carga pero con URL estatica de Streamlit