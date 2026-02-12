import spacy
from spacy.lang.en.stop_words import STOP_WORDS

nlp = spacy.load("en_core_web_sm")

def extract_key_terms(text):
    doc = nlp(text)

    key_terms = set()
    for token in doc:
        if token.pos_ in {"NOUN", "VERB"} and not token.is_stop and token.is_alpha:
            key_terms.add(token.lemma_.lower())
    return sorted(key_terms)

input_text = """
a robot and a human supervisor, typically a nurse, collaborate to achieve a common goal—delivering medicine to a specific location in a hospital. The nurse initially places the medicine in the robot, and the robot then follows the human so that the medicine can be taken to any destination
"""

terms = extract_key_terms(input_text)
print("Key terms:", terms)
