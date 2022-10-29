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


def header_bytes() -> bytes:
    return b"\x42\x44\x69\x63\x02\x00\x00\x00\x20\x00\x00\x00\x83\x00\x00\x00"


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


def dic_bytes(words: List[str], output: bytearray) -> bytes:
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
    output.extend(header_bytes())
    md5_start = len(output)
    output.extend(b"\0" * 16)  # md5
    data_start = len(output)
    if aff is None:
        aff_bytes(output, chars="".join(possible_chars))
    else:
        aff_bytes(output, aff_string=aff)
    dic_bytes(words, output)
    output[md5_start:data_start] = hashlib.md5(output[data_start:]).digest()
    return bytes(output)


# For testing purposes
if __name__ == "__main__":
    import sys
    from pathlib import Path

    input_dic = Path(sys.argv[1])
    input_aff = input_dic.parent / (input_dic.stem + ".aff")
    output_bdic = Path(sys.argv[2])
    dic_file = input_dic.read_text()
    lines = dic_file.split("\n")[1:]  # first line contains word count
    words = list(filter(lambda i: i, map(lambda line: line.strip(), lines)))

    aff_string: Optional[str] = None
    if input_aff.exists():
        print("Using input aff")
        aff_string = input_aff.read_text()
    else:
        print("Using default aff")

    b = create_bdic(words, aff=aff_string)
    output_bdic.write_bytes(b)
