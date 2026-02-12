package mymod;

import org.apache.commons.cli.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.search.EntitySearcher;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

public class FindCausalPropertiesCLI {

  public static void main(String[] args) throws Exception {
    Options opts = new Options();
    opts.addOption("i","input", true, "input ontology.owl");
    opts.addOption("o","output", true, "output txt (default: causal_properties.txt)");
    opts.addOption("k","keyword", true, "keyword to search (default: cause)");
    opts.addOption(null,"no-iri", false, "disable keyword match in IRI local name");
    opts.addOption(null,"no-comments", false, "disable keyword match in rdfs:comment");
    CommandLine cl = new DefaultParser().parse(opts,args);
    if (!cl.hasOption("input")) {
      new HelpFormatter().printHelp("java mymod.FindCausalPropertiesCLI -i ont.owl [-o out.txt] [-k cause] [--no-iri] [--no-comments]", opts);
      System.exit(1);
    }

    String keyword = cl.getOptionValue("keyword", "cause").toLowerCase(Locale.ROOT);
    boolean matchIRI = !cl.hasOption("no-iri");
    boolean useComments = !cl.hasOption("no-comments");
    String outPath = cl.getOptionValue("output", "causal_properties.txt");

    File in = new File(cl.getOptionValue("input"));
    OWLOntologyManager man = OWLManager.createOWLOntologyManager();
    OWLOntology ont = man.loadOntologyFromOntologyDocument(in);
    Set<OWLOntology> closure = ont.importsClosure().collect(Collectors.toSet());

    Set<OWLObjectProperty> seed = findByKeyword(closure, keyword, matchIRI, useComments);
    Set<OWLObjectProperty> all = closureEquivalentsInversesSubs(closure, seed);

    List<String> iris = all.stream().map(p -> p.getIRI().toString()).distinct().sorted().collect(Collectors.toList());
    try (BufferedWriter bw = new BufferedWriter(new FileWriter(new File(outPath)))) {
      for (String s : iris) {
        bw.write(s);
        bw.newLine();
      }
    }
    System.out.println("Found " + iris.size() + " causal candidate properties.");
    System.out.println("Saved to " + outPath);
  }

  private static Set<OWLObjectProperty> findByKeyword(Set<OWLOntology> onts, String needle, boolean matchIRI, boolean useComments) {
    Set<OWLObjectProperty> result = new HashSet<>();
    for (OWLOntology o : onts) {
      for (OWLObjectProperty p : o.objectPropertiesInSignature().collect(Collectors.toSet())) {
        boolean hit = false;
        Stream<OWLAnnotation> labels = EntitySearcher.getAnnotations(p, o, o.getOWLOntologyManager().getOWLDataFactory().getRDFSLabel());
        if (labels.anyMatch(a -> a.getValue().asLiteral().map(l -> l.getLiteral().toLowerCase(Locale.ROOT).contains(needle)).orElse(false))) hit = true;
        if (!hit && useComments) {
          Stream<OWLAnnotation> comments = EntitySearcher.getAnnotations(p, o, o.getOWLOntologyManager().getOWLDataFactory().getRDFSComment());
          if (comments.anyMatch(a -> a.getValue().asLiteral().map(l -> l.getLiteral().toLowerCase(Locale.ROOT).contains(needle)).orElse(false))) hit = true;
        }
        if (!hit && matchIRI) {
          String local = iriLocalName(p.getIRI()).toLowerCase(Locale.ROOT);
          if (local.contains(needle)) hit = true;
        }
        if (hit) result.add(p);
      }
    }
    return result;
  }

  private static String iriLocalName(IRI iri) {
    String s = iri.toString();
    int hash = s.lastIndexOf('#');
    int slash = s.lastIndexOf('/');
    int idx = Math.max(hash, slash);
    return idx >= 0 && idx + 1 < s.length() ? s.substring(idx + 1) : s;
  }

  private static Set<OWLObjectProperty> closureEquivalentsInversesSubs(Set<OWLOntology> onts, Set<OWLObjectProperty> start) {
    OWLDataFactory df = OWLManager.createOWLOntologyManager().getOWLDataFactory();
    OWLObjectProperty TOP = df.getOWLTopObjectProperty();
    OWLObjectProperty BOT = df.getOWLBottomObjectProperty();
    Set<OWLObjectProperty> seen = new HashSet<>();
    ArrayDeque<OWLObjectProperty> q = new ArrayDeque<>();
    for (OWLObjectProperty s : start) if (!s.equals(TOP) && !s.equals(BOT)) { seen.add(s); q.add(s); }
    while (!q.isEmpty()) {
      OWLObjectProperty cur = q.removeFirst();
      Set<OWLObjectProperty> add = new HashSet<>();
      for (OWLOntology o : onts) {
        for (OWLAxiom ax : o.axioms(AxiomType.EQUIVALENT_OBJECT_PROPERTIES).collect(Collectors.toList())) {
          OWLEquivalentObjectPropertiesAxiom e = (OWLEquivalentObjectPropertiesAxiom) ax;
          Set<OWLObjectProperty> props = e.properties().filter(pe -> !pe.isAnonymous()).map(pe -> pe.asOWLObjectProperty()).collect(Collectors.toSet());
          if (props.contains(cur)) add.addAll(props);
        }
        for (OWLAxiom ax : o.axioms(AxiomType.INVERSE_OBJECT_PROPERTIES).collect(Collectors.toList())) {
          OWLInverseObjectPropertiesAxiom inv = (OWLInverseObjectPropertiesAxiom) ax;
          OWLObjectPropertyExpression a = inv.getFirstProperty();
          OWLObjectPropertyExpression b = inv.getSecondProperty();
          if (!a.isAnonymous() && !b.isAnonymous()) {
            OWLObjectProperty ap = a.asOWLObjectProperty();
            OWLObjectProperty bp = b.asOWLObjectProperty();
            if (ap.equals(cur)) add.add(bp);
            if (bp.equals(cur)) add.add(ap);
          }
        }
        for (OWLAxiom ax : o.axioms(AxiomType.SUB_OBJECT_PROPERTY).collect(Collectors.toList())) {
          OWLSubObjectPropertyOfAxiom sAx = (OWLSubObjectPropertyOfAxiom) ax;
          OWLObjectPropertyExpression sub = sAx.getSubProperty();
          OWLObjectPropertyExpression sup = sAx.getSuperProperty();
          if (!sub.isAnonymous() && !sup.isAnonymous()) {
            OWLObjectProperty subP = sub.asOWLObjectProperty();
            OWLObjectProperty supP = sup.asOWLObjectProperty();
            if (supP.equals(cur)) add.add(subP);
          }
        }
      }
      for (OWLObjectProperty p : add) {
        if (p.equals(TOP) || p.equals(BOT)) continue;
        if (seen.add(p)) q.addLast(p);
      }
    }
    return seen;
  }
}