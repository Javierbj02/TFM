package mymod;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.List;
import java.util.Set;
import java.util.UUID;
import java.util.stream.Collectors;

import org.apache.commons.cli.*;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.model.*;
import uk.ac.manchester.cs.owlapi.modularity.ModuleType;
import uk.ac.manchester.cs.owlapi.modularity.SyntacticLocalityModuleExtractor;

public class AugmentModuleCLI {

  public static void main(String[] args) throws Exception {
    Options opts = new Options();
    opts.addOption("f","full",   true, "full ontology OWL (original) [required]");
    opts.addOption("m","module", true, "current pruned module OWL [required]");
    opts.addOption("a","add",    true, "class IRI to add [required]");
    opts.addOption("p","props",  true, "causal properties file (one IRI per line) [required]");
    opts.addOption("o","output", true, "output ontology OWL (augmented module). If omitted, overwrites --module");
    opts.addOption(null,"help",  false, "show help");

    CommandLineParser parser = new DefaultParser();
    CommandLine cl;
    try {
      cl = parser.parse(opts, args, true);
    } catch (ParseException e) {
      System.err.println("Argument error: " + e.getMessage());
      new HelpFormatter().printHelp("AugmentModuleCLI", opts, true);
      System.exit(2);
      return;
    }
    if (cl.hasOption("help") ||
        !cl.hasOption("full") || !cl.hasOption("module") ||
        !cl.hasOption("add")  || !cl.hasOption("props")) {
      new HelpFormatter().printHelp("AugmentModuleCLI", opts, true);
      System.exit(1);
      return;
    }

    File fullFile = new File(cl.getOptionValue("full"));
    File modFile  = new File(cl.getOptionValue("module"));
    String addIRI = cl.getOptionValue("add");
    File outFile  = cl.hasOption("output") ? new File(cl.getOptionValue("output")) : modFile;

    List<String> propLines = Files.readAllLines(new File(cl.getOptionValue("props")).toPath());

    OWLOntologyManager man = OWLManager.createOWLOntologyManager();
    OWLOntology full = man.loadOntologyFromOntologyDocument(fullFile);
    OWLOntology currentModule = man.loadOntologyFromOntologyDocument(modFile);
    OWLDataFactory df = man.getOWLDataFactory();

    Set<OWLClass> initialClasses = currentModule.classesInSignature().collect(Collectors.toSet());
    initialClasses.add(df.getOWLClass(IRI.create(addIRI)));

    Set<OWLObjectProperty> causalProps =
        CausalSignature.propsFromIRIs(df, IOUtil.cleanLines(propLines));

    Set<OWLEntity> sigma =
        CausalSignature.buildFromInitialClasses(full, initialClasses, causalProps);

    SyntacticLocalityModuleExtractor extr =
        new SyntacticLocalityModuleExtractor(man, full, ModuleType.BOT);
    IRI freshOntologyIRI = IRI.create("urn:augment:" + UUID.randomUUID());
    OWLOntology augmented = extr.extractAsOntology(sigma, freshOntologyIRI);

    File target = outFile.getAbsoluteFile();
    File tmp = new File(target.getParentFile(),
                        target.getName() + ".tmp-" + System.currentTimeMillis());

    man.saveOntology(augmented, IRI.create(tmp.toURI()));

    try {
      Files.move(tmp.toPath(), target.toPath(),
                 StandardCopyOption.REPLACE_EXISTING,
                 StandardCopyOption.ATOMIC_MOVE);
    } catch (Exception e) {

      Files.move(tmp.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
    }

    System.out.println("[Augment] Injected class and saved to " + target.getAbsolutePath() +
                       (target.equals(modFile.getAbsoluteFile()) ? " (in-place)" : ""));
  }
}
