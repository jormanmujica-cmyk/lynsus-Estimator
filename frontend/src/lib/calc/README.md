# Fórmulas de campo (Fase 2)

Esta carpeta va a contener el puerto a TypeScript de las fórmulas en
[`driveway.py`](../../../../../driveway.py) y [`foundation_rules.py`](../../../../../foundation_rules.py).

**Regla de oro:** no se cambia ningún número ni fórmula sin autorización
explícita (ver `CLAUDE.md` en la raíz del repo). El puerto debe ser 1:1,
verificado con tests que comparen contra los valores que hoy produce el
Streamlit (`driveway.py`, `app.py`, `foundation_rules.py`).

Estado:

- [x] `driveway.ts` — concreto, rebar, lumber/forms, stakes, expansion joints, gravel, poly. `calcDrivewayTakeoff()` es la función principal.
- [x] `driveway.test.ts` — 3 casos de regresión (defaults, un set no-default, y el edge case gravel_depth=0), con valores generados corriendo las fórmulas reales en Python (no adivinados). Correr con `npm test`.
- [ ] `foundation.ts` — beams, slab, stirrups, forms (estándar Ethoscapes) — pendiente, mismo patrón: puerto 1:1 + tests contra `foundation_rules.py`.

Nota: `calcDrivewayTakeoff()` todavía no está conectado a ninguna UI — eso es la fase 3 (armar el formulario en `/dashboard`). Precios (`DEFAULT_PRICES`) y waste (`DEFAULT_WASTE`) también viven en `driveway.ts`.
