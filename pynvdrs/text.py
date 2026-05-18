import re
from importlib import resources
from typing import Optional

try:
    from symspellpy import SymSpell, Verbosity
except Exception:  # pragma: no cover
    SymSpell = None
    Verbosity = None


_ABBREVIATIONS = {
    "t\.v\.": "television",
    "t\.v": "television",
    "h\.i\.v\.": "hiv",
    "h\.i\.v": "hiv",
    "i\.v\.": "iv",
    "i\.v": "iv",
    "i/v": "iv",
    "n/v": "nausea and vomiting",
    "d/v": "domestic violence",
    "dv": "domestic violence",
    "g\.o\.v\.": "gov",
    "m\.v\.": "moving vehicle",
    "m\.v": "moving vehicle",
    "mv": "moving vehicle",
    "r\.v\.": "rv",
    "r\.v": "rv",
    "r/v": "rv",
    "v": "Victim",
    "vs": "victims",
    "v's": "victims",
    "rp": "reporting party",
    "nok": "next of kin",
    "yo": "year old",
    "y/o": "year old",
    "w/an": "with an",
    "w/a": "with a",
    "d/t": "due to",
    "b/c": "because",
    "le": "law enforcement",
    "c/me": "coroner/medical examiner",
    "gsw": "gunshot wound",
    "hx": "history",
    "rx": "prescription",
    "b/f": "boyfriend",
    "g/f": "girlfriend",
    "bf": "boyfriend",
    "gf": "girlfriend",
    "er": "emergency room",
    "mg/l": "mg per liter",
    "w/v": "weight per volume",
    "w/m/": "white male ",
    "w/f/": "white female ",
    "b/m/": "black male ",
    "b/f/": "black female ",
    "h/m/": "hispanic male ",
    "h/f/": "hispanic female ",
    "a/m/": "asian male ",
    "a/m/": "asian female ",
    "wm": "white male",
    "w/m": "white male",
    "w/f": "white female",
    "bm": "black male",
    "b/m": "black male",
    "b/f": "black female",
    "h/m": "hispanic male",
    "h/f": "hispanic female",
    "a/m": "asian male",
    "a/f": "asian female",
    "w/": "with",
    "f/": "from",
}


def load_symspell(max_dictionary_edit_distance: int = 1, prefix_length: int = 7) -> Optional[object]:
    """Lazily load SymSpell dictionary from `symspellpy` package resources.

    Returns a SymSpell instance or None if `symspellpy` not installed.
    """
    if SymSpell is None:
        return None

    sym = SymSpell(max_dictionary_edit_distance=max_dictionary_edit_distance, prefix_length=prefix_length)
    dict_path = resources.files("symspellpy").joinpath("frequency_dictionary_en_82_765.txt")
    sym.load_dictionary(str(dict_path), term_index=0, count_index=1)
    return sym


def replace_abnormal_characters(text: str) -> str:
    text = re.sub(
        "â\x80\x9d|â\x80\x9c|â\x80\x99|‚Äú|‚Äù|‚Äô|aÌ\x82Â\x80Â|â\x80\x98|`", "'", text
    )
    text = re.sub("a√å¬Ç1√¢¬Å¬Ñ", "-", text)
    text = re.sub("Ì\x81|aÌ\x83Â\x89|Ã\x89|ã\x89|ã¨|Ã¨|eâ´|eÂ´|é", "e", text)
    text = re.sub("ã§|Ã§", "c", text)
    text = re.sub("ã¤|Ã¤|ã¡|Ã¡", "a", text)
    text = re.sub("ã¶|Ã¶", "o", text)
    text = re.sub("ã¯|Ã¯|ã®|Ã®", "i", text)
    text = re.sub("aÌ\x82(.)â\x81\x84(.)", "\\1/\\2", text)
    text = re.sub("â½|Â½", "1/2", text)
    text = re.sub("â¼|Â¼", "1/4", text)
    text = re.sub("â¾|Â¾", "3/4", text)
    text = re.sub("ã\x9f|Ã\x9f", "1", text)
    text = re.sub("â\xad|Â\xad|ã\x97|Ã\x97", "-", text)
    text = re.sub("^aÌ\x82Â\x80Â¢|^â\x80¢|\x01\x0b|\x7f|\x03", "", text)
    text = re.sub("aÌ\x82Â\x80Â¢|â\x80¢", ",", text)
    text = re.sub("aÌ\x82Â\x80Â¦|â\x80\x94", "... ", text)
    text = re.sub("\t|\n", " ", text)
    text = re.sub("`", "'", text)
    text = re.sub("â°|Â°", " degrees ", text)

    text = re.sub(
        'â\x80\x94|â\xa0|Â\xa0|â\x80¢|â\x80¦|â\x98|â\x80|â·|Â·|"â¦|â¦|â¬|Â¬|¢',
        " ",
        text,
    )
    text = re.sub("^\\\\|\\\\$", "", text)
    text = re.sub("\b\\\\| \\\\,", " ", text)
    text = re.sub("\\\\\b|\\\\ ", " ", text)
    text = re.sub("\\\\", " / ", text)
    return text


def replace_abbreviations(text: str) -> str:
    for a, f in _ABBREVIATIONS.items():
        text = re.sub("\\b" + a + "\\b", f, text, flags=re.IGNORECASE)
    return text


def correct_spelling(text: str, symspell=None) -> str:
    """Fast spell correction via SymSpell when available; falls back to no-op."""
    if symspell is None:
        return text

    tokens = text.split()
    corrected = []
    for token in tokens:
        if not token.isalpha() or len(token) < 4:
            corrected.append(token)
            continue

        suggestions = symspell.lookup(token.lower(), verbosity=Verbosity.CLOSEST, max_edit_distance=1)
        if not suggestions:
            corrected.append(token)
            continue

        suggestion = suggestions[0].term
        if token.isupper():
            corrected.append(suggestion.upper())
        elif token.istitle():
            corrected.append(suggestion.title())
        else:
            corrected.append(suggestion)

    return " ".join(corrected)


def clean_nvdrs_text(text: str, symspell=None) -> str:
    text = str(text)
    text = replace_abnormal_characters(text)
    text = re.sub(r"[^a-zA-Z0-9 ,./<>?;:\\"'~!@#$%&^*()\[\]{}_+=\-]", " ", text)
    text = replace_abbreviations(text)
    text = correct_spelling(text, symspell=symspell)
    text = re.sub("([a-zA-Z]{2,})\.([a-zA-Z]{1,})", "\\1. \\2", text)
    text = " ".join([w for w in text.split(" ") if w != "" and w != " "])
    text = re.sub(" +", " ", text)
    return text.strip()

