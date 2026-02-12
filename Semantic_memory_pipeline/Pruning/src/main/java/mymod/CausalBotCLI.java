package mymod;

import java.io.File;
import java.nio.file.Files;
import java.util.List;
import java.util.Set;
import org.apache.commons.cli.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import uk.ac.manchester.cs.owlapi.modularity.*;

public class CausalBotCLI {

  public static void main(String[] args) throws Exception {
    Options opts = new Options();
    opts.addOption("i","input", true, "input ontology.owl");
    opts.addOption("c","classes", true, "seed classes txt (one IRI per line)");
    opts.addOption("p","props", true, "causal properties txt (one IRI per line)");
    opts.addOption("o","output", true, "output ontology");
    CommandLine cl = new DefaultParser().parse(opts,args);

    File in = new File(cl.getOptionValue("input"));
    File out = new File(cl.getOptionValue("output"));
    List<String> classLines = Files.readAllLines(new File(cl.getOptionValue("classes")).toPath());
    List<String> propLines = Files.readAllLines(new File(cl.getOptionValue("props")).toPath());

    OWLOntologyManager man = OWLManager.createOWLOntologyManager();
    OWLOntology ont = man.loadOntologyFromOntologyDocument(in);
    OWLDataFactory df = man.getOWLDataFactory();

    Set<OWLEntity> sigma = CausalSignature.build(ont, CausalSignature.classesFromIRIs(df, classLines), CausalSignature.propsFromIRIs(df, propLines));

    SyntacticLocalityModuleExtractor extr = new SyntacticLocalityModuleExtractor(man, ont, ModuleType.BOT);

    IRI outIri = IRI.create(out.toURI());
    OWLOntology module = extr.extractAsOntology(sigma, outIri);
    man.saveOntology(module, outIri);
    System.out.println("Causal pruning - Saved module to " + out);
  }
}