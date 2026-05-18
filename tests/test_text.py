from types import SimpleNamespace

import pytest

from pynvdrs.text import clean_text, correct_spelling, load_symspell


class DummySymSpell:
    def lookup(self, token, verbosity, max_edit_distance):
        if token == "helo":
            return [SimpleNamespace(term="hello")]
        return []


def test_clean_text_handles_abbreviations_and_corrections():
    result = clean_text("t.v. helo", symspell=DummySymSpell())

    assert "television" in result
    assert "hello" in result


def test_correct_spelling_uses_symspell():
    assert correct_spelling("helo", symspell=DummySymSpell()) == "hello"


def test_load_symspell_with_custom_dictionary(tmp_path):
    pytest.importorskip("symspellpy")

    dictionary_path = tmp_path / "dictionary.txt"
    dictionary_path.write_text("hello 10\n", encoding="utf-8")

    symspell = load_symspell(dictionary_path=dictionary_path)

    assert symspell is not None