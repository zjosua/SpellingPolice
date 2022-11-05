"""
This is a python port of chromium's convert_dict tool.

Copyright 2006-2008 The Chromium Authors
Copyright 2022 AnkingMed

Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file.
"""
"""
Useful Links
https://spylls.readthedocs.io/en/latest/hunspell.html#code-walkthrough
https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/hunspell/google/bdict_writer.cc
https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/tools/convert_dict/convert_dict.cc
"""

import hashlib
from typing import List, Optional
from .aff import Aff, serialize_aff
from .dic import DicNode, serialize_trie, compute_trie_storage


VER = 2
DATA_START = 32


def reserve_header(output: bytearray) -> None:
    output.extend(b"\0" * DATA_START)


def write_header(output: bytearray, dic_start: int) -> None:
    output[0:4] = b"BDic"
    output[4:8] = VER.to_bytes(4, byteorder="little")
    output[8:12] = DATA_START.to_bytes(4, byteorder="little")
    output[12:16] = dic_start.to_bytes(4, byteorder="little")
    output[16:DATA_START] = hashlib.md5(output[DATA_START:]).digest()


def aff_bytes(
    output: bytearray, aff_string: Optional[str] = None, chars: str = ""
) -> None:
    """
    - chars: List of valid characters to spellcheck. If unspecified defaults to english characters.
             Ignored if aff_string is set.
    """
    aff = Aff()
    if aff_string is None:
        try_chars = "esianrtolcdugmphbyfvkwzESIANRTOLCDUGMPHBYFVKWZ'"
        for char in chars:
            if char not in try_chars:
                try_chars += char

        # fmt: off
        aff_string = "\n".join((       
            "SET UTF-8",
            f"TRY {try_chars}",
            "ICONV 1",
            "ICONV ’ '"     
        ))
        # fmt: on
    aff.parse(aff_string)
    serialize_aff(aff, output)


def dic_bytes(words: List[str], output: bytearray) -> None:
    trie_root = DicNode()
    words = sorted(words)
    bytewords: List[bytes] = list(map(lambda w: w.encode("utf-8"), words))
    trie_root.build(bytewords, 0, len(bytewords), 0)
    compute_trie_storage(trie_root)
    serialize_trie(trie_root, output)


def create_bdic(words: List[str], aff: Optional[str] = None) -> bytes:
    """
    Create a new bdic file from list of words and aff string.
    Note that most aff commands are not supported.
    """
    possible_chars = set()
    for word in words:
        for c in word:
            possible_chars.add(c)

    output = bytearray()
    reserve_header(output)

    if aff is None:
        aff_bytes(output, chars="".join(possible_chars))
    else:
        aff_bytes(output, aff_string=aff)
    dic_start = len(output)
    dic_bytes(words, output)
    write_header(output, dic_start)
    return bytes(output)
