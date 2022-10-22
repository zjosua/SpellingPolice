"""
Create a custom dictionary with custom words

The user should be able to edit a .txt file with the words?
as well as an interface 

"""
from typing import List
from .bdicwriter import create_bdic
from .const import CUSTOM_DICT_DIR

import unicodedata
import urllib.parse
from pathlib import Path

CUSTOM_DICT_DIR_PATH = Path(CUSTOM_DICT_DIR)


def add_custom_word(word: str) -> None:
    """
    Add word to custom dictionaries. Overwrite if such dictionary already exists.
    The word must not contain a whitespace.
    """
    word = unicodedata.normalize(word, "NFD")
    if " " in word:
        raise Exception("Whitespace cannot be in the word.")
    file_name = urllib.parse.quote(word, safe="")
    dict_path = CUSTOM_DICT_DIR_PATH / f"{file_name}.bdic"

    bdic_content = create_bdic(word)
    with open(dict_path, "wb") as f:
        f.write(bdic_content)


def custom_words() -> List[str]:
    words = []
    for child in CUSTOM_DICT_DIR_PATH.iterdir():
        if child.is_file() and child.suffix == ".bdic":
            word = urllib.parse.unquote(child.stem)
            words.append(word)
    return words
