package mymod;

import org.semanticweb.owlapi.model.parameters.Imports;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Set;
import java.util.TreeSet;

import org.apache.commons.cli.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import org.semanticweb.owlapi.util.SimpleIRIShortFormProvider;

public class OntologyDiffCLI {

  public static void main(String[] args) throws Exception {
    Options opts = new Options();
    opts.addOption("a","ontoA", true, "first ontology file (A)");
    opts.addOption("b","ontoB", true, "second ontology file (B)");
    opts.addOption(null,"include-imports", false, "include imports in the signature comparison");
    opts.addOption(null,"short", false, "print short forms instead of full IRIs");
    opts.addOption("o","output", true, "output report file (.txt). If omitted, a name is generated");

    CommandLine cl = new DefaultParser().parse(opts, args);
    if (!cl.hasOption("ontoA") || !cl.hasOption("ontoB")) {
      new HelpFormatter().printHelp("OntologyDiffCLI -a A.owl -b B.owl [--include-imports] [--short] [-o report.txt]", opts);
      System.exit(1);
    }

    boolean includeImports = cl.hasOption("include-imports");
    boolean shortForms     = cl.hasOption("short");

    File fA = new File(cl.getOptionValue("ontoA"));
    File fB = new File(cl.getOptionValue("ontoB"));

    File outFile;
    if (cl.hasOption("output")) {
      outFile = new File(cl.getOptionValue("output"));
    } else {
      String baseA = stripExt(fA.getName());
      String baseB = stripExt(fB.getName());
      String autoName = baseA + "__vs__" + baseB + "__diff.txt";
      outFile = new File(autoName).getAbsoluteFile();
    }

    OWLOntologyManager man = OWLManager.createOWLOntologyManager();
    OWLOntology A = man.loadOntologyFromOntologyDocument(fA);
    OWLOntology B = man.loadOntologyFromOntologyDocument(fB);

    Imports imports = includeImports ? Imports.INCLUDED : Imports.EXCLUDED;
    SimpleIRIShortFormProvider shortener = new SimpleIRIShortFormProvider();

    Set<String> classesA = new TreeSet<>();
    for (OWLClass c : A.getClassesInSignature(imports)) {
      classesA.add(shortForms ? shortener.getShortForm(c.getIRI()) : c.getIRI().toString());
    }
    Set<String> classesB = new TreeSet<>();
    for (OWLClass c : B.getClassesInSignature(imports)) {
      classesB.add(shortForms ? shortener.getShortForm(c.getIRI()) : c.getIRI().toString());
    }

    Set<String> objPropsA = new TreeSet<>();
    for (OWLObjectProperty p : A.getObjectPropertiesInSignature(imports)) {
      objPropsA.add(shortForms ? shortener.getShortForm(p.getIRI()) : p.getIRI().toString());
    }
    Set<String> objPropsB = new TreeSet<>();
    for (OWLObjectProperty p : B.getObjectPropertiesInSignature(imports)) {
      objPropsB.add(shortForms ? shortener.getShortForm(p.getIRI()) : p.getIRI().toString());
    }

    Set<String> classesAminusB = new TreeSet<>(classesA); classesAminusB.removeAll(classesB);
    Set<String> classesBminusA = new TreeSet<>(classesB); classesBminusA.removeAll(classesA);

    Set<String> objPropsAminusB = new TreeSet<>(objPropsA); objPropsAminusB.removeAll(objPropsB);
    Set<String> objPropsBminusA = new TreeSet<>(objPropsB); objPropsBminusA.removeAll(objPropsA);

    StringBuilder sb = new StringBuilder();
    sb.append("=== Ontology Diff Report ===\n");
    sb.append("A: ").append(fA.getAbsolutePath()).append("\n");
    sb.append("B: ").append(fB.getAbsolutePath()).append("\n");
    sb.append("Imports: ").append(includeImports ? "INCLUDED" : "EXCLUDED").append("\n");
    sb.append("Format: ").append(shortForms ? "short forms" : "full IRIs").append("\n");
    sb.append("\n");

    appendSection(sb, "Classes in A \\ B (" + classesAminusB.size() + ")", classesAminusB);
    appendSection(sb, "Classes in B \\ A (" + classesBminusA.size() + ")", classesBminusA);

    appendSection(sb, "ObjectProperties in A \\ B (" + objPropsAminusB.size() + ")", objPropsAminusB);
    appendSection(sb, "ObjectProperties in B \\ A (" + objPropsBminusA.size() + ")", objPropsBminusA);

    String report = sb.toString();

    System.out.print(report);

    ensureParentDirs(outFile);
    Files.write(outFile.toPath(), report.getBytes(StandardCharsets.UTF_8));
    System.out.println("Report saved to: " + outFile.getAbsolutePath());
  }

  private static void appendSection(StringBuilder sb, String title, Set<String> items) {
    sb.append("[").append(title).append("]\n");
    if (items.isEmpty()) {
      sb.append("  (none)\n\n");
    } else {
      for (String s : items) sb.append("  ").append(s).append("\n");
      sb.append("\n");
    }
  }

  private static String stripExt(String name) {
    int i = name.lastIndexOf('.');
    return (i > 0) ? name.substring(0, i) : name;
  }

  private static void ensureParentDirs(File f) throws IOException {
    File parent = f.getAbsoluteFile().getParentFile();
    if (parent != null && !parent.exists() && !parent.mkdirs()) {
      throw new IOException("Could not create directories for " + parent);
    }
  }
}