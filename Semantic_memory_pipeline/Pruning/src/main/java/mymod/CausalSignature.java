package mymod;

import java.util.HashSet;
import java.util.Set;

import org.semanticweb.owlapi.model.*;

import static java.util.stream.Collectors.toSet;

public class CausalSignature {


  public static Set<OWLEntity> build(OWLOntology ont, Set<OWLClass> seed, Set<OWLObjectProperty> props) {
    return buildFromInitialClasses(ont, seed, props);
  }

  public static Set<OWLEntity> buildFromInitialClasses(OWLOntology ont, Set<OWLClass> initial, Set<OWLObjectProperty> props) {
    Set<OWLClass> classesUp = upwardClosure(ont, initial);
    Set<OWLEntity> sigma = new HashSet<>(classesUp);

    boolean changed = true;
    while (changed) {
      changed = false;

      for (OWLObjectProperty p : props) {
        Set<OWLClass> dom = ont.objectPropertyDomainAxioms(p)
            .flatMap(ax -> ax.getDomain().classesInSignature()).collect(toSet());
        Set<OWLClass> ran = ont.objectPropertyRangeAxioms(p)
            .flatMap(ax -> ax.getRange().classesInSignature()).collect(toSet());

        boolean touches = intersects(dom, classesUp) || intersects(ran, classesUp);
        if (touches) {
          if (!sigma.contains(p)) {
            sigma.add(p);
            changed = true;
          }
          Set<OWLClass> newlySeen = new HashSet<>();
          for (OWLClass c : union(dom, ran)) {
            if (!classesUp.contains(c)) newlySeen.add(c);
          }
          if (!newlySeen.isEmpty()) {
            Set<OWLClass> deltaClosure = upwardClosure(ont, newlySeen);
            if (!classesUp.containsAll(deltaClosure)) changed = true;
            classesUp.addAll(deltaClosure);
            sigma.addAll(deltaClosure);
          }
        }
      }
    }
    return sigma;
  }


  static Set<OWLClass> upwardClosure(OWLOntology ont, Set<OWLClass> start) {
    Set<OWLClass> closure = new HashSet<>(start);
    boolean changed = true;
    while (changed) {
      changed = false;
      Set<OWLClass> toAdd = new HashSet<>();
      for (OWLClass c : new HashSet<>(closure)) {
        ont.subClassAxiomsForSubClass(c).forEach(ax ->
            ax.getSuperClass().classesInSignature().forEach(toAdd::add)
        );

        ont.equivalentClassesAxioms(c).forEach(ax ->
            ax.classExpressions()
              .filter(ce -> !ce.isOWLClass() || !ce.asOWLClass().equals(c))
              .forEach(ce -> ce.classesInSignature().forEach(toAdd::add))
        );
      }
      if (closure.addAll(toAdd)) changed = true;
    }
    return closure;
  }

  private static boolean intersects(Set<?> a, Set<?> b) {
    for (Object x : a) if (b.contains(x)) return true;
    return false;
  }
  private static <T> Set<T> union(Set<T> a, Set<T> b) {
    Set<T> u = new HashSet<>(a); u.addAll(b); return u;
  }

  public static Set<OWLClass> classesFromIRIs(OWLDataFactory df, java.util.Collection<String> iris){
    return iris.stream().map(i -> df.getOWLClass(IRI.create(i))).collect(toSet());
  }
  public static Set<OWLObjectProperty> propsFromIRIs(OWLDataFactory df, java.util.Collection<String> iris){
    return iris.stream().map(i -> df.getOWLObjectProperty(IRI.create(i))).collect(toSet());
  }
}
