# Driveway Estimator Pro — Lynsus

## Qué es este proyecto
App web de cotización de driveways de concreto para contratistas. El usuario ingresa los datos del proyecto (SQFT, espesor, rebar, perímetro) y el sistema calcula automáticamente todos los materiales con las fórmulas reales de campo, agrega waste, genera el estimado con precios y produce una cotización lista para el cliente.

**Objetivo final:** convertirlo en un SaaS con login, suscripciones y multi-empresa.

## Stack actual
- **Backend / cálculos (legacy):** Python + Streamlit (`driveway.py`, `app.py`) — funciona, está en producción. No se toca.
- **Next.js (en construcción activa):** Next.js 16 (App Router, TypeScript, Tailwind v4) + Supabase Auth, carpeta `frontend/`. Reemplazó el antiguo esqueleto React + Vite (estaba vacío).
  - **Supabase — qué guarda qué ahora mismo:**
    - **Auth** (login/signup/logout de usuarios): ✅ funcionando, mismo proyecto Supabase que usa Streamlit (`database.py` / `.streamlit/secrets.toml`). Credenciales en `frontend/.env.local` (gitignored).
    - **Datos del takeoff** (lo que el contratista llena en el formulario): ❌ todavía NO va a Supabase. Se autoguarda en `localStorage` del navegador (ver abajo) — persiste en ese navegador/dispositivo, pero no sincroniza entre dispositivos ni queda visible para otro usuario de la empresa. Guardar cotizaciones nombradas en la tabla `quotes` (ya existe, la usa Streamlit) es el siguiente paso pendiente del roadmap.
  - Fase 1 (lista): scaffold Next.js, login/signup/logout con Supabase Auth, `proxy.ts` (Next 16 renombró `middleware.ts` → `proxy.ts`) que protege todas las rutas salvo `/login` y `/auth/*`.
  - Fase 2 (lista para Driveway): fórmulas portadas a TypeScript en `frontend/src/lib/calc/driveway.ts`, con tests de regresión contra el Python real.
  - Fase 3 (lista para Driveway, pendiente para Foundation): formulario completo conectado en `/dashboard/driveway`.
  - Dashboard rediseñado estilo "executive dashboard" oscuro con sidebar + topbar (isotipo "Y" reconstruido como SVG) — ver `frontend/src/components/{sidebar,topbar,logo,welcome-header}.tsx`.

## Fórmulas de campo — NO CAMBIAR sin autorización
Estas fórmulas vienen de práctica real de construcción. Son la base del negocio. `frontend/src/lib/calc/driveway.ts` las porta 1:1 desde `driveway.py` y tiene tests de regresión contra los valores de Python — **no tocar ese archivo** sin regenerar los tests.

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

### Desviaciones autorizadas por el usuario — SOLO en el formulario de Next.js (`driveway-form.tsx`), no en `lib/calc/driveway.ts`
El motor de cálculo (`lib/calc/driveway.ts`) se mantiene 100% fiel a `driveway.py`. El formulario de Next.js calcula algunas cosas distinto, por pedido explícito del usuario (contratista real corrigiendo con su práctica de campo):

- **Estacas rojas**: automáticas, sin inputs propios. `perímetro ÷ 18" O.C.` (no 4 ft como el default viejo de Python). Precio sugerido fijo ($0.75/u), no editable — si hace falta otro precio, se agrega en Extras.
- **Expansion joints**: cuadrícula real de máx. **10×10' o 12×12'** (selector), con juntas en **ambas direcciones** (transversales Y longitudinales si el ancho también excede el máximo) — antes solo se calculaban franjas a lo largo. Fórmula: `ceil(medida / máximo) − 1` juntas interiores por eje (mismo patrón que usa `foundation_rules.py` para beams interiores). Tiene toggle **Automático / Manual** — en manual, el usuario escribe sus propios LF partiendo de la sugerencia calculada.
- **Mano de obra**: ya no son 7 categorías con monto fijo (como Streamlit). Dos modos: **Por día** (trabajadores × tarifa/día × días, cuadrilla completa) o **Por SQFT** (una sola tarifa × sqft).
- **Gravel**: Por CY (como antes) o **Por camión** (CY por camión + precio por camión → calcula camiones necesarios con `ceil`).
- **Overhead + Margen + Extras**: agregado — no existía en Streamlit. Overhead% y Profit% son líneas separadas sobre el mismo subtotal; Extras es una lista libre (descripción + precio) para costos que no entran en ninguna categoría.
- **Poly**: quitado del formulario (se usaba poco) — si un trabajo lo necesita, se agrega como línea en Extras.
- **Alertas rojas**: si algo no cuadra antes de cotizar (precio en $0 con cantidad > 0, margen en 0%, equipo activado sin costo, waste de concreto/rebar en 0%, total en $0 o negativo) se marca en rojo arriba del resumen.

## Materiales que calcula el sistema (Driveway, Next.js)
1. Concreto (CY) — con waste% inline
2. Rebar — tamaño #3/#4/#5, spacing seleccionable — con waste% inline
3. Lumber / Forms — 2x4, 2x6, 2x8 — con waste% inline
4. Estacas rojas — automático (ver arriba)
5. Expansion joints — cuadrícula automática o manual (ver arriba)
6. Gravel base — por CY o por camión
7. Equipment: Pump, Buggy, Maquinaria (opcionales, con costo)
8. Extras — líneas libres

## Personalización por empresa (Streamlit, legacy)
- Nombre de empresa
- Logo (PNG/JPG)
- Se muestran en el header y en la cotización del cliente
- *(Pendiente portar a Next.js — hoy el dashboard usa branding fijo "Lynsus")*

## Estructura de archivos
```
estimator lynsus/
├── driveway.py          # App Streamlit completa (FUNCIONA, legacy)
├── app.py               # Estimador de losas (proyecto anterior)
├── foundation_rules.py  # Fórmulas de Foundation (Python) — aún no portado a TS
├── requirements.txt     # pip install -r requirements.txt
├── RUN_APP.bat          # Doble clic para correr Streamlit
├── CLAUDE.md            # Este archivo
└── frontend/            # Next.js 16 + Supabase Auth
    ├── package.json
    ├── .env.local       # credenciales Supabase (gitignored)
    └── src/
        ├── app/
        │   ├── login/           # login + signup (Supabase Auth)
        │   ├── auth/callback/   # exchange code → sesión
        │   └── dashboard/
        │       ├── layout.tsx       # sidebar + topbar (protegido)
        │       ├── page.tsx         # home: bienvenida + tarjetas de estimadores
        │       └── driveway/
        │           ├── page.tsx
        │           └── driveway-form.tsx   # formulario completo, ~900 líneas
        ├── components/
        │   ├── sidebar.tsx, topbar.tsx      # chrome del dashboard
        │   ├── logo.tsx                     # isotipo "Y" (SVG reconstruido)
        │   └── welcome-header.tsx           # saludo por hora del día (client-only)
        ├── lib/
        │   ├── supabase/    # client.ts, server.ts, proxy.ts
        │   └── calc/        # driveway.ts (fórmulas TS) + driveway.test.ts (regresión vs Python)
        └── proxy.ts         # protección de rutas (ex middleware.ts)
```

## Cómo correr el proyecto

### Streamlit (funciona ahora)
```powershell
streamlit run driveway.py
```

### Next.js frontend (requiere Node.js instalado)
```powershell
cd frontend
npm install
npm run dev
```
Abre `http://localhost:3000` — redirige a `/login` si no hay sesión.

Tests de regresión de fórmulas (compara `lib/calc/*.ts` contra los valores de Python):
```powershell
cd frontend
npm test
```

## Roadmap del proyecto
- [x] Cálculos de campo con fórmulas reales (Streamlit)
- [x] Waste factors por material (Streamlit)
- [x] Personalización de empresa (logo + nombre) (Streamlit)
- [x] Cotización PDF-ready para cliente (Streamlit)
- [x] Export Excel (Streamlit)
- [x] Scaffold Next.js + login/signup/logout (Supabase Auth)
- [x] Dashboard rediseñado (sidebar + topbar, isotipo, bienvenida)
- [x] Portar fórmulas de driveway.py a TypeScript (con tests de regresión)
- [x] Estimador Driveway completo en Next.js (materiales, labor, equipo, overhead, margen, extras, alertas, autosave local)
- [x] Vista de cotización para cliente en Next.js — botón **"👁️ Preview"** debajo del Resumen del takeoff en `/dashboard/driveway` abre un modal con el estimado profesional completo (datos del cliente + alcance editables, documento con tabla/totales/firmas) y ahí mismo "🖨️ Guardar PDF / Imprimir" (`window.print()` + clases `print:*` que ocultan todo menos el documento, en blanco y negro)
- [ ] Portar fórmulas de foundation_rules.py a TypeScript
- [ ] Estimador Foundation en Next.js
- [x] Página de Ajustes (`/dashboard/settings`) — perfil del contratista (nombre/apellido), empresa (nombre + logo), web y redes (Facebook/Instagram/WhatsApp). Se guarda en Supabase, tabla `user_config` (misma que usa Streamlit vía `database.py`, clave `companyProfile` anidada para no chocar con las claves planas de `app.py`). El logo y nombre aparecen en el sidebar y en el header del estimado del cliente — "LYNSUS" ya no está hardcodeado en ningún lado.
- [ ] Guardar cotizaciones en Supabase (tabla `quotes`) — cross-device, multi-empresa, RLS
- [ ] Pagos con Stripe (SaaS)
- [ ] Multi-idioma (EN/ES)

## Reglas importantes
- Los cálculos deben mostrar siempre el valor RAW y el valor ORDENADO (con waste) — esto es crítico para evitar pérdidas
- Nunca cambiar las fórmulas de campo de `lib/calc/driveway.ts` (ni de `driveway.py`) sin confirmación del usuario — las desviaciones de negocio van en el formulario de Next.js, documentadas arriba
- El sistema está orientado a contratistas latinos — lenguaje simple, términos en español cuando sea posible
- Precio sugerido de suscripción: $49–$99/mes por empresa
- El dashboard de Next.js es tema oscuro fijo (no sigue el modo claro/oscuro del sistema) — decisión de diseño deliberada
- **Gotcha de React/Next dev**: cualquier `useEffect(() => { algoAsync().then(setState); }, [])` necesita guard de cancelación (`let ignore = false; ...; return () => { ignore = true; }`) — en dev, Next invoca los efectos 2 veces al montar, y sin el guard la promesa del primer montaje puede resolver tarde y pisar cambios del usuario con datos viejos (pasó de verdad con el perfil de empresa en Ajustes — ver `settings-form.tsx`, `sidebar.tsx`, `driveway-form.tsx`)
