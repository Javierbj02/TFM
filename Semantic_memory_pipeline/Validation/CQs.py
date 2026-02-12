from owlready2 import *
from rdflib import Graph

onto = get_ontology("file://data/MLO_instantiated.owl").load()
g = default_world.as_rdflib_graph()

g.bind("dul", "http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#")
g.bind("ocra", "http://www.iri.upc.edu/groups/perception/OCRA/ont/ocra.owl#")
g.bind("soma", "http://www.ease-crc.org/ont/SOMA.owl#")

def run_sparql(name, sparql):
    print(name)
    results = list(g.query(sparql))
    if not results:
        print("(no hay resultados)")
    else:
        for row in results:
            print(tuple(row))

cq1 = """
PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
SELECT ?goal WHERE {
  ?goal a dul:Goal .
}
"""
print("\n")
print("-" * 40)
run_sparql("CQ1 - What is the goal of the operation?", cq1)

cq2 = """
PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
SELECT ?plan WHERE {
  ?goal a dul:Goal .
  ?plan a dul:Plan ;
        dul:hasComponent ?goal .
}
"""
print("\n")
print("-" * 40)
run_sparql("CQ2 - What is the plan to achieve the goal", cq2)


cq3 = """
PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
SELECT ?agent ?loc WHERE {
  ?agent a dul:Agent ;
         dul:hasLocation ?loc .
}
"""
print("\n")
print("-" * 40)
run_sparql("CQ3 - Which agents are present, and where are they located", cq3)

cq4 = """
PREFIX ocra: <http://www.iri.upc.edu/groups/perception/OCRA/ont/ocra.owl#>
PREFIX dul:  <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
SELECT ?collab ?agent WHERE {
  ?collab a ocra:Collaboration ;
          dul:hasParticipant ?agent .
  ?agent a dul:Agent .
}
"""
print("\n")
print("-" * 40)
run_sparql("CQ4 - What collaboration is taking place, and who is collaborating?", cq4)

cq5 = """
PREFIX dul: <http://www.ontologydesignpatterns.org/ont/dul/DUL.owl#>
SELECT ?object ?loc WHERE {
  ?object a dul:PhysicalObject ;
          dul:hasLocation ?loc .
}
"""
print("\n")
print("-" * 40)
run_sparql("CQ5 - What physical objects are present, and where are they located?", cq5)
