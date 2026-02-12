

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
    opts.addOption("i","input",true,"input ontology.owl");
    opts.addOption("c","classes",true,"seed classes txt");
    opts.addOption("p","props",true,"causal properties txt");
    opts.addOption("o","output",true,"output ontology");
    CommandLine cl = new DefaultParser().parse(opts,args);

    File in  = new File(cl.getOptionValue("input"));
    File out = new File(cl.getOptionValue("output"));
    List<String> classLines = Files.readAllLines(new File(cl.getOptionValue("classes")).toPath());
    List<String> propLines  = Files.readAllLines(new File(cl.getOptionValue("props")).toPath());

    OWLOntologyManager man = OWLManager.createOWLOntologyManager(); // Manager
    OWLOntology ont       = man.loadOntologyFromOntologyDocument(in); // Carga la ontología completa
    OWLDataFactory df     = man.getOWLDataFactory(); // Para crear clases/propiedades a partir de IRIs

    Set<OWLEntity> sigma = CausalSignature.build( // llamada a la función de CausalSignature, con la ontología inicial, las clases y propiedades
        ont,
        CausalSignature.classesFromIRIs(df, classLines),
        CausalSignature.propsFromIRIs(df, propLines));
    // Esta función incluye las clases y propiedades causales que le pasamos.
    // Para cada propiedad de la lista, busca en la ontología original sus axiomas ObjectPropertyDomain(p D) y ObjectPropertyRange(p R)
    // Añade D y R (clases) si no están. Aquí deberíamos quizás adaptarlo para solo incluir la propiedad si D o R existe.
    
    // Devuelve sigma


    SyntacticLocalityModuleExtractor extr =
        new SyntacticLocalityModuleExtractor(man, ont, ModuleType.BOT);

    IRI outIri = IRI.create(out.toURI());
    OWLOntology module = extr.extractAsOntology(sigma, outIri);
    man.saveOntology(module, outIri);
    System.out.println("Saved causal-BOT module to "+out);
  }
}