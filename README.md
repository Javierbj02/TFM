# Metodología de validación de grounding basado en ontologías y razonamiento causal para robots sociales

Repositorio principal del TFM organizado en dos módulos:

1. `Semantic_memory_pipeline`: construcción, refinamiento y validación de ontologías/memoria semántica.
2. `Explanations`: ejecución de escenarios y generación de hipotesis explicativas (C0-C3) asistida por LLM.

Este README es una guía general del repositorio. La documentacion detallada de cada módulo se mantiene en sus README específicos.

## Estructura del repositorio

```text
TFM/
├─ Semantic_memory_pipeline/
│  ├─ Inizialization/
│  ├─ Pruning/
│  ├─ Validation/
│  ├─ data/
│  └─README.md 
├─ Explanations/
│  ├─ src/
│  ├─ scripts/
│  ├─ data/
│  ├─results/
│  └─README.md 
└─ README.md
```

## Relación entre modulos

1. En `Semantic_memory_pipeline` se prepara y valida la base ontologica (TMO/MLO).
2. En `Explanations` se definen los escenarios y se generan los experimentos para explicar eventos inesperados.
3. Las salidas de experimentos se guardan como JSONL y metadatos en `Explanations/results/`.

## Requisitos generales

- Python 3.9+ (ambos modulos usan scripts Python).
- Java + Maven (necesario para `Semantic_memory_pipeline/Pruning`).
- Dependencias Python segun cada modulo.
- Variables de entorno para LLM en `Explanations/.env`.

## Arranque rápido

### 1) Módulo de memoria semántica

Desde `Semantic_memory_pipeline`:

- `Inizialization/`: extracción de términos clave y mapeo inicial.
- `Pruning/`: compilación y ejecución de CLIs Java (`mvn package` y herramientas `CausalBotCLI`, `FindCausalPropertiesCLI`, etc.).
- `Validation/`: instanciación y consultas de validación (CQs).

### 2) Módulo de explicaciones

Desde `Explanations`:

1. Configurar entorno Python e instalar dependencias del proyecto.
2. Definir `LOCAL_OPENAI_BASE_URL`, `LOCAL_OPENAI_API_KEY` y `LOCAL_OPENAI_MODEL` en `.env`.
3. Verificar conexión con:
   - `python scripts/smoke_test_llm.py`
4. Ejecutar experimentos:
   - `python scripts/run_c0.py`
   - `python scripts/run_c1.py`
   - `python scripts/run_c2.py`
   - `python scripts/run_c3.py`

## Resultados y artefactos

- Resultados de explicaciones: `Explanations/results/c0|c1|c2|c3/<scenario_id>/`.
- Ontologíaas, diffs y artefactos de pruning: `Semantic_memory_pipeline/Pruning/output/`.
- Ontologías base de trabajo: `Semantic_memory_pipeline/data/` y `Semantic_memory_pipeline/Pruning/ontologies/`.