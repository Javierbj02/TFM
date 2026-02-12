
# Semantic Memory Pipeline

Este módulo implementa el pipeline de construccion de memoria semántica del TFM.  
El flujo se divide en 3 submódulos:

1. Inicialización.
2. Poda causal.
3. Validación.

Como resultado principal del pipeline se obtiene la ontología de trabajo `TMO.owl` (y su versión podada `TMO_pruned.owl` para experimentos comparativos).

## Estructura

```text
Semantic_memory_pipeline/
├─ Inizialization/
├─ Pruning/
├─ Validation/
└─ data/
```

## 1) Inicialización

Objetivo:
- Extraer terminos clave desde la descripción de un escenario de uso.
- Seleccionar ontologías candidatas.
- Realizar el emparejamiento término-clase.

Scripts principales:
- `Inizialization/keyterms_from_text.py`
- `Inizialization/match_key_ontologies.py`

Salida esperada:
- Ontología base de dominio `TMO.owl`.

## 2) Poda causal (Pruning)

Objetivo:
- Refinar la ontología reteniendo estructura y relaciones relevantes para explicación causal.
- Obtener una versión podada para reducir complejidad y ruido semántico.

### Build

Desde `Semantic_memory_pipeline/Pruning`:

```bash
mvn -q package
```

### Comandos principales

```bash
### Find causal properties (*caus*, super/sub classes, inverses, equivalent to)
java -cp .\target\causal-bot-1.0-SNAPSHOT-jar-with-dependencies.jar mymod.FindCausalPropertiesCLI  -i .\ontologies\TMO.owl -o .\config\causal_properties.txt -k caus --no-comments

### Refinement/pruning
java -cp .\target\causal-bot-1.0-SNAPSHOT-jar-with-dependencies.jar mymod.CausalBotCLI -i .\ontologies\TMO.owl -c .\config\key_terms.txt -p .\config\causal_properties.txt -o .\ontologies\TMO_pruned.owl

### Compare ontologies
java -cp .\target\causal-bot-1.0-SNAPSHOT-jar-with-dependencies.jar mymod.OntologyDiffCLI -a .\ontologies\TMO.owl -b .\ontologies\pruned_ont.owl -o .\output\Diff_robot_vs_pruned.txt

### Expand ontology (self-extension) [-o optional]
java -cp .\target\causal-bot-1.0-SNAPSHOT-jar-with-dependencies.jar mymod.AugmentModuleCLI -f .\ontologies\Ont_SOMA_and_OCRA.owl -m .\ontologies\pruned_ont.owl -a http://www.ease-crc.org/ont/SOMA.owl#Collision -p .\config\causal_properties.txt -o .\output\prueba.owl
```

### Ablación: ontologia sin podar vs podada

Se incluye un benchmark comparativo en:
- `Pruning/results_ablation.py`

Este script ejecuta:
- `benchmark_ontology("TMO.owl", "TMO_benchmark.txt")`
- `benchmark_ontology("TMO_pruned.owl", "TMO_pruned_benchmark.txt")`

Y genera:
- `Pruning/TMO_benchmark.txt`
- `Pruning/TMO_pruned_benchmark.txt`

## 3) Validación

Objetivo:
- Instanciar una situación inicial sobre la ontología.
- Verificar consistencia y capacidad de respuesta mediante preguntas de competencia (CQs).

Scripts principales:
- `Validation/instantiation.py`
- `Validation/CQs.py`

### Ejecución sugerida

Desde `Semantic_memory_pipeline/Validation`:

```bash
python instantiation.py data/MLO.owl data/MLO_instantiated.owl
python CQs.py
```

Resultado:
- Se crea una ontología instanciada inicial (`MLO_instantiated.owl`).
- Se evalúa la ontología con consultas SPARQL de competencia.

## Requisitos

- Python 3.9+.
- Java (compatible con Maven).
- Maven.
- Librerias Python usadas por los scripts (por ejemplo, `owlready2`, `spacy`, `sentence-transformers`, `rdflib`, segun submódulo).
