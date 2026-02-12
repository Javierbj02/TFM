import time
import os
from owlready2 import *
import types

def benchmark_ontology(ontology_path, output_file):
    start_total = time.time()
    
    onto = get_ontology(f"file://ontologies/{ontology_path}")
    onto = onto.load()
    load_time = time.time() - start_total

    classes = list(onto.classes())
    object_props = list(onto.object_properties())
    data_props = list(onto.data_properties())
    individuals = list(onto.individuals())
    axioms = len(list(onto.get_triples()))

    ontology_ns = types.SimpleNamespace()
    with onto:
        for cls in classes:
            setattr(ontology_ns, cls.name, cls)

    instances_to_create = []
    created_count = 0
    for cls in classes[:8]:
        if not cls.name.startswith("owl:") and not cls.name.startswith("rdf:") and not cls.name.startswith("rdfs:"):
            instances_to_create.append((cls.name, f"Instance_{created_count}"))
            created_count += 1
            if created_count >= 8:
                break

    start_inst = time.time()
    created_instances = []
    with onto:
        for cls_name, inst_name in instances_to_create:
            cls = getattr(ontology_ns, cls_name, None)
            if cls:
                inst = cls(inst_name)
                created_instances.append(inst)
    inst_time = time.time() - start_inst


    num_instances = len(instances_to_create)
    instances_per_sec = 0
    if inst_time > 0:
        instances_per_sec = num_instances / inst_time

    start_reason = time.time()
    with onto:
        sync_reasoner()
    reason_time = time.time() - start_reason

    total_time = time.time() - start_total

    with open(output_file, 'w') as f:
        f.write(f"Ontology: {ontology_path}\n")
        f.write(f"Reasoner: HermiT\n")
        f.write(f"Total execution time: {total_time:.4f} seconds\n\n")
        
        f.write("ONTOLOGY STATISTICS:\n")
        f.write(f"Classes: {len(classes)}\n")
        f.write(f"Object properties: {len(object_props)}\n")
        f.write(f"Data properties: {len(data_props)}\n")
        f.write(f"Existing individuals: {len(individuals)}\n")
        f.write(f"Estimated axioms: {axioms}\n\n")
        
        f.write("CLASS EXAMPLES (first 5):\n")
        for i, cls in enumerate(classes[:5]):
            f.write(f"{i+1}. {cls.name}\n")
        f.write("\n")
        
        f.write("INSTANCE CREATION BENCHMARK:\n")
        f.write(f"Instances created: {len(instances_to_create)}\n")
        f.write(f"Time: {inst_time:.9f} seconds\n")
        if inst_time > 0:
            f.write(f"Speed: {len(instances_to_create)/inst_time:.2f} instances/second\n")
        f.write("\n")
        
        f.write("REASONER BENCHMARK (HermiT):\n")
        f.write(f"Time: {reason_time:.4f} seconds\n")
        f.write("\n")
        
        f.write("LOAD TIME:\n")
        f.write(f"{load_time:.4f} seconds\n")
        
benchmark_ontology("TMO.owl", "TMO_benchmark.txt")
benchmark_ontology("TMO_pruned.owl", "TMO_pruned_benchmark.txt")