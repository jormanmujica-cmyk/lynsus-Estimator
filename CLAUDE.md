# Driveway Estimator Pro — Lynsus

## Qué es este proyecto
App web de cotización de driveways de concreto para contratistas. El usuario ingresa los datos del proyecto (SQFT, espesor, rebar, perímetro) y el sistema calcula automáticamente todos los materiales con las fórmulas reales de campo, agrega waste, genera el estimado con precios y produce una cotización lista para el cliente.

**Objetivo final:** convertirlo en un SaaS con login, suscripciones y multi-empresa.

## Stack actual
- **Backend / cálculos:** Python + Streamlit (`driveway.py`) — funciona, está en producción
- **Frontend nuevo:** React + Vite (carpeta `frontend/`) — en construcción

## Fórmulas de campo — NO CAMBIAR sin autorización
Estas fórmulas vienen de práctica real de construcción. Son la base del negocio.

### Concreto (CY = SQFT ÷ divisor)
| Espesor | Divisor |
|---------|---------|
| 4"      | 81      |
| 6"      | 54      |
| 8"      | 40      |
| 12"     | 27      |

### Rebar (LF = SQFT × factor, grid bidireccional)
| Spacing O.C. | Factor |
|-------------|--------|
| 12"         | 0.1100 |
| 14"         | 0.0940 |
| 15"         | 0.0880 |
| 16"         | 0.0827 |
| 18"         | 0.0733 |
| 24"         | 0.0550 |

### Tabla de yardage por dimensión de driveway
- 12x24 → ÷34 | 12x26 → ÷32 | 12x28 → ÷30 | 12x30 → ÷28
- 10x24 → ÷35 | 10x26 → ÷33 | 10x28 → ÷31 | 10x30 → ÷29

## Materiales que calcula el sistema
1. Concreto (CY)
2. Rebar — tamaño #3/#4/#5, spacing seleccionable
3. Lumber / Forms — 2x4, 2x6, 2x8
4. Stakes rojas
5. Expansion joints
6. Gravel base
7. Poly / Plastic
8. Equipment: Pump, Buggy, Maquinaria (opcionales)

## Waste factors (configurables por el usuario)
- Concreto: 8% default
- Rebar: 10% default
- Lumber: 10% default
- Stakes: 5% default
- Poly: 10% default

## Personalización por empresa
- Nombre de empresa
- Logo (PNG/JPG)
- Se muestran en el header y en la cotización del cliente

## Estructura de archivos
```
estimator lynsus/
├── driveway.py          # App Streamlit completa (FUNCIONA)
├── app.py               # Estimador de losas (proyecto anterior)
├── requirements.txt     # pip install -r requirements.txt
├── RUN_APP.bat          # Doble clic para correr Streamlit
├── CLAUDE.md            # Este archivo
└── frontend/            # React + Vite (en construcción)
    ├── package.json
    ├── vite.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── index.css
        ├── App.jsx
        ├── components/
        ├── pages/
        └── utils/
```

## Cómo correr el proyecto

### Streamlit (funciona ahora)
```powershell
streamlit run driveway.py
```

### React frontend (requiere Node.js instalado)
```powershell
cd frontend
npm install
npm run dev
```

## Roadmap del proyecto
- [x] Cálculos de campo con fórmulas reales
- [x] Waste factors por material
- [x] Personalización de empresa (logo + nombre)
- [x] Cotización PDF-ready para cliente
- [x] Export Excel
- [ ] Frontend React completo
- [ ] Login por usuario
- [ ] Guardar proyectos en base de datos
- [ ] Pagos con Stripe (SaaS)
- [ ] Multi-idioma (EN/ES)

## Reglas importantes
- Los cálculos deben mostrar siempre el valor RAW y el valor ORDENADO (con waste) — esto es crítico para evitar pérdidas
- Nunca cambiar las fórmulas de campo sin confirmación del usuario
- El sistema está orientado a contratistas latinos — lenguaje simple, términos en español cuando sea posible
- Precio sugerido de suscripción: $49–$99/mes por empresa
