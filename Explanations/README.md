# Explanations

Este módulo implementa los experimentos de generación de explicaciones causales sobre escenarios definidos de forma hardcodeada.

El objetivo es detectar cambios no explicados en la ejecución de un escenario (especialmente retracts), validar causalmente esos cambios y, cuando sea necesario, generar hipótesis con LLM.

## Estructura del módulo

```text
Explanations/
├─ data/
├─ results/
├─ scripts/
└─ src/
   ├─ scenarios/
   ├─ validator/
   ├─ hypotheses/
   ├─ experiments/
   ├─ llm/
   └─ utils/
```

## Componentes principales

### 1) Escenarios (hardcodeados)

Se definen como secuencias de `Step` en `src/scenarios/`, usando:
- `types`: instanciación de entidades/eventos.
- `asserts`: hechos añadidos.
- `retracts`: hechos retirados.
- `updates`: reemplazos de hechos.
- `deletes`: eliminación de instancias.

Escenarios actuales:
- `src/scenarios/nominal.py`
- `src/scenarios/medicine_lost.py`

### 2) Validador causal

Implementado en:
- `src/validator/causal_validator.py`
- `src/validator/runtime.py`

Función general:
- Ejecuta el escenario paso a paso sobre la ontología.
- Detecta cambios de alto nivel (MVP: retracts).
- Intenta encontrar un evento causalmente explicativo usando criterios tipo `When/Where/Who/How`.
- Si no hay explicación causal, activa el callback para generar hipótesis.

### 3) Experimentos y generación de hipótesis

Runner principal:
- `src/experiments/runner.py`

Configuraciones experimentales:
- `C0`: baseline de hipótesis.
- `C1`: restricciones por vocabulario ontológico.
- `C2`: añade recuperación de contexto.
- `C3`: extiende catálogo de tipos de evento (usando ontología extra, `TMO.owl`).

Generadores por configuración:
- `src/hypotheses/c0.py`
- `src/hypotheses/c1.py`
- `src/hypotheses/c2.py`
- `src/hypotheses/c3.py`

Cliente LLM:
- `src/llm/client.py`

## Ejecución

Desde `Explanations/`:

```bash
python -m pip install -e .
python scripts/smoke_test_llm.py
python scripts/run_c0.py
python scripts/run_c1.py
python scripts/run_c2.py
python scripts/run_c3.py
```

## Variables de entorno

En `Explanations/.env`:

- `LOCAL_OPENAI_BASE_URL`
- `LOCAL_OPENAI_API_KEY`
- `LOCAL_OPENAI_MODEL`

El módulo usa una API compatible con OpenAI (en este caso, servidor local).

## Resultados

Las ejecuciones guardan resultados en `results/` por configuración y escenario:

- `results/c0/<scenario_id>/...jsonl`
- `results/c1/<scenario_id>/...jsonl`
- `results/c2/<scenario_id>/...jsonl`
- `results/c3/<scenario_id>/...jsonl`

Cada ejecución incluye:
- archivo `.jsonl` con muestras por ejecución,
- archivo `_meta.json` con configuración del experimento (modelo, temperatura, parámetros, etc.).
