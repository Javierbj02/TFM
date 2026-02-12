package mymod;

import java.util.HashSet;
import java.util.Set;

import org.semanticweb.owlapi.model.*;
import static java.util.stream.Collectors.toSet;

public class CausalSignature { // Clase que construye la firma que se da al extractor

  public static Set<OWLEntity> build(OWLOntology ont, // Método build con la ontología completa, clases y propiedades
                                     Set<OWLClass> seedClasses,
                                     Set<OWLObjectProperty> causalProps) {
    Set<OWLEntity> sigma = new HashSet<>(seedClasses); // Arranca sigma con todas las clases
    sigma.addAll(causalProps); // Y con todas esas propiedades

    causalProps.forEach(p -> { // Para cada propiedad p, busca en la ontología los axiomas y añade D y R
      ont.objectPropertyDomainAxioms(p)
         .forEach(ax -> sigma.addAll(ax.getClassesInSignature()));
      ont.objectPropertyRangeAxioms(p)
         .forEach(ax -> sigma.addAll(ax.getClassesInSignature()));
    });
    return sigma; // Devuelve todas las clases de la lista así como todas las que aparecen explcítamente como dominio o rango de cualquiera de las propiedades causales.
  }

  /** util to create a set of classes from IRIs */


  // Recibe la lista de IRIs y devuelven un Set<OWLClass>
  public static Set<OWLClass> classesFromIRIs(OWLDataFactory df, java.util.Collection<String> iris){
    return iris.stream().map(i->df.getOWLClass(IRI.create(i))).collect(toSet());
  }


  public static Set<OWLObjectProperty> propsFromIRIs(OWLDataFactory df, java.util.Collection<String> iris){
    return iris.stream().map(i->df.getOWLObjectProperty(IRI.create(i))).collect(toSet());
  }
}
