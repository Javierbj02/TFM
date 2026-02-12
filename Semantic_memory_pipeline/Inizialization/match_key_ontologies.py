import json
from scenario_builder import ScenarioBuilder
from ontology_utils import load_ontology, initialize_ontology, relate_term_to_ontology, search_lov, search_ols, search_wikidata
from sentence_transformers import SentenceTransformer, util

def main():
    owl_paths = ["data/ocra.owl.xml", "data/SOMA.owl.rdf"]
    
    ontologies = []
    for path in owl_paths:
        initialize_ontology(path)
        ontologies.append(load_ontology(path))

    builder = ScenarioBuilder()
    input_terms = ['achieve', 'collaborate', 'deliver', 'destination', 'follow', 'goal', 'hospital', 'human', 'location', 'medicine', 'nurse', 'place', 'robot', 'supervisor', 'take', 'object']

    model = SentenceTransformer('all-MiniLM-L6-v2')
    for term in input_terms:
            builder.add_term(term)
            
            found_locally = False
            for ontology in ontologies:
                matches = relate_term_to_ontology(term, ontology, False)
                if matches:
                    found_locally = True
                    for match in matches:
                        builder.add_relation(term, match)
            
            if not found_locally:
                suggestionsA = search_lov(term)
                suggestionsB = search_ols(term)
                suggestionsC = search_wikidata(term)            
                
                suggestions = suggestionsA + suggestionsB + suggestionsC
                
                for suggest in suggestions:
                    builder.add_relation(term, suggest)
                
    res = json.loads(json.dumps(builder.export(), indent=2))

    for term in input_terms:
        print(f'\n\n Term: {term} \n\n')
        for relation in res["relations"][term]:
            embeddings_T_L_D = model.encode([term, relation["label"], relation["description"]], convert_to_tensor=True)
            term_label_sim = util.pytorch_cos_sim(embeddings_T_L_D[0], embeddings_T_L_D[1])
            term_desc_sim = util.pytorch_cos_sim(embeddings_T_L_D[0], embeddings_T_L_D[2])
            relation["similarity_embedding"]= max(term_label_sim, term_desc_sim) 
            print(relation)
            print(f'\n')
        print(f'\n\n ----------- \n\n')
            
    print(res)            
    

if __name__ == "__main__":
    main()
