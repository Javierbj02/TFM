package mymod;

import java.util.List;
import java.util.stream.Collectors;

public class IOUtil {
  public static List<String> cleanLines(List<String> lines) {
    return lines.stream()
      .map(String::trim)
      .filter(s -> !s.isEmpty())
      .filter(s -> !s.startsWith("#") && !s.startsWith("//"))
      .collect(Collectors.toList());
  }
}

