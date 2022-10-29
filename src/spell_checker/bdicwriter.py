"""
Create a new bdic file from list of words

You can create a bdic file from hunspell .dic and .aff with 
qwebengine_convert_dict tool that comes with qt

Useful Links
https://spylls.readthedocs.io/en/latest/hunspell.html#code-walkthrough
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict.h
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict_writer.cc
https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/tools/convert_dict/convert_dict.cc
"""
import hashlib
from typing import List, Dict, Optional, Tuple
import re


class StorageType:
    Undefined = 0
    Leaf = 1
    LeafMore = 2
    List16 = 3
    List8 = 4
    Lookup32 = 5
    Lookup16 = 6


class BDictConst:
    LEAF_NODE_TYPE_MASK = 0x80
    LEAF_NODE_TYPE_VALUE = 0
    LEAF_NODE_ADDITIONAL_MASK = 0xC0
    LEAF_NODE_ADDITIONAL_VALUE = 0x40
    LEAF_NODE_FOLLOWING_MASK = 0xA0
    LEAF_NODE_FOLLOWING_VALUE = 0x20
    LEAF_NODE_FIRST_BYTE_AFFIX_MASK = 0x1F
    LEAF_NODE_MAX_FIRST_AFFIX_ID = 0x1FFE
    FIRST_AFFIX_IS_UNUSED = 0x1FFF
    MAX_AFFIXES_PER_WORD = 32
    LEAF_NODE_FOLLOWING_LIST_TERMINATOR = 0xFFFF
    LOOKUP_NODE_TYPE_MASK = 0xFC
    LOOKUP_NODE_TYPE_VALUE = 0xC0
    LOOKUP_NODE_0TH_MASK = 0xFD
    LOOKUP_NODE_0TH_VALUE = 0xC1
    LOOKUP_NODE_32BIT_MASK = 0xFE
    LOOKUP_NODE_32BIT_VALUE = 0xC2
    LIST_NODE_TYPE_MASK = 0xE0
    LIST_NODE_TYPE_VALUE = 0xE0
    LIST_NODE_16BIT_MASK = 0xF0
    LIST_NODE_16BIT_VALUE = 0xF0
    LIST_NODE_COUNT_MASK = 0xF


class DicNode:
    addition: bytes  # always 1 byte
    children: List["DicNode"]
    leaf_addition: bytes
    # affix_indices: List[int]
    storage: int  # StorageType

    def __init__(self):
        self.addition = b"\0"
        self.children = []
        self.leaf_addition = b""

    # BuildTrie()
    def build(self, words: List[bytes], begin: int, end: int, depth: int) -> int:
        begin_str = words[begin]
        if len(begin_str) < depth:
            self.addition = b"\0"
            # self.affix_indices = words[begin].affix_indices
            return begin + 1

        match_count: int
        if depth == 0 and begin == 0:
            match_count = end - begin
            self.addition = b"\0"
        else:
            match_count = 0
            self.addition = begin_str[depth - 1 : depth]
            while (
                begin + match_count < end
                and words[begin + match_count][depth - 1 : depth] == self.addition
            ):
                match_count += 1
        if match_count == 1:
            # self.affix_indices = words[begin].affix_indices
            self.leaf_addition = begin_str[depth:]
            return begin + 1
        i = begin
        while i < begin + match_count:
            cur = DicNode()
            i = cur.build(words, i, begin + match_count, depth + 1)
            self.children.append(cur)
        return begin + match_count


def compute_trie_storage(node: DicNode) -> int:
    if len(node.children) == 0:
        supplimentary_size = 0  # affix size...
        if len(node.leaf_addition) == 0:
            node.storage = StorageType.Leaf
            return 2 + supplimentary_size
        node.storage = StorageType.LeafMore
        return 3 + len(node.leaf_addition) + supplimentary_size

    child_size = 0
    for child in node.children:
        child_size += compute_trie_storage(child)
    kListHeaderSize = 1
    kListThreshold = 16
    if len(node.children) < kListThreshold and child_size <= 0xFF:
        node.storage = StorageType.List8
        return kListHeaderSize + len(node.children) * 2 + child_size
    if len(node.children) < kListThreshold and child_size <= 0xFFFF:
        node.storage = StorageType.List16
        return kListHeaderSize + len(node.children) * 3 + child_size

    kTableHeaderSize = 2
    strategy = compute_lookup_strategy_details(node.children)
    zeroth_item_size = 2 if strategy.has_0th_item else 0
    if (
        child_size + kTableHeaderSize + zeroth_item_size + strategy.list_size * 2
        < 0xFFFF
    ):
        node.storage = StorageType.Lookup16
        return kTableHeaderSize + zeroth_item_size + strategy.list_size * 2 + child_size
    node.storage = StorageType.Lookup32
    zeroth_item_size = 4 if strategy.has_0th_item else 0
    return kTableHeaderSize + zeroth_item_size + strategy.list_size * 4 + child_size


class LookupStrategy:
    has_0th_item: bool
    first_item: int
    list_size: int

    def __init__(self):
        self.has_0th_item = False
        self.first_item = 0
        self.list_size = 0


def compute_lookup_strategy_details(children: List[DicNode]) -> LookupStrategy:
    strategy = LookupStrategy()
    if len(children) == 0:
        return strategy
    first_offset = 0
    if children[0].addition == b"\0":
        strategy.has_0th_item = True
        first_offset += 1
    if len(children) == first_offset:
        return strategy
    strategy.first_item = ord(children[first_offset].addition)
    last_item = ord(children[-1].addition)
    strategy.list_size = last_item - strategy.first_item + 1
    return strategy


def serialize_leaf(node: DicNode, output: bytearray) -> None:
    first_affix = 0  # node.affix_indices[0] or 0
    id_byte = (first_affix >> 8) & BDictConst.LEAF_NODE_FIRST_BYTE_AFFIX_MASK
    if node.storage == StorageType.LeafMore:
        id_byte |= BDictConst.LEAF_NODE_ADDITIONAL_VALUE
    # if node.affix_indices.size() > 1 : id_byte |= ...
    output.extend(id_byte.to_bytes(1, "little"))
    output.extend((first_affix & 0xFF).to_bytes(1, "little"))
    if node.storage == StorageType.LeafMore:
        for i in range(len(node.leaf_addition)):
            output.extend(node.leaf_addition[i : i + 1])
        output.extend(b"\0")  # c string
    # handle affixes...


def serialize_list(node: DicNode, output: bytearray) -> None:
    is_8_bit = node.storage == StorageType.List8
    id_byte = BDictConst.LIST_NODE_TYPE_VALUE
    if not is_8_bit:
        id_byte |= BDictConst.LIST_NODE_16BIT_VALUE
    id_byte |= len(node.children)
    output.append(id_byte)

    bytes_per_entry = 2 if is_8_bit else 3
    table_begin = len(output)
    output.extend(b"\0" * len(node.children) * bytes_per_entry)
    children_begin = len(output)
    for i, child in enumerate(node.children):
        idx = table_begin + i * bytes_per_entry
        output[idx : idx + 1] = child.addition
        offset = len(output) - children_begin
        if is_8_bit:
            output[idx + 1] = offset & 0xFF
        else:
            output[idx + 1 : idx + 3] = offset.to_bytes(2, "little")
        serialize_trie(child, output)


"""
[begin_offset]
id_byte (1)
strategy.first_table_item (1)
strategy.table_item_count (1)
[zeroth_item_offset]
0th_entry? (bytes_per_entry if 0th_entry else 0)
[table_begin]
for each table item:
    child.entry (bytes_per_entry)
for each table item:
    [offset]
    serialize_trie
"""


def serialize_lookup(node: DicNode, output: bytearray) -> None:
    id_byte = BDictConst.LOOKUP_NODE_TYPE_VALUE
    strategy = compute_lookup_strategy_details(node.children)
    is_32_bit = node.storage == StorageType.Lookup32
    if is_32_bit:
        id_byte |= BDictConst.LOOKUP_NODE_32BIT_VALUE
    if strategy.has_0th_item:
        id_byte |= BDictConst.LOOKUP_NODE_0TH_VALUE
    begin_offset = len(output)
    output.append(id_byte)
    output.append(strategy.first_item)
    output.append(strategy.list_size)

    bytes_per_entry = 4 if is_32_bit else 2
    zeroth_item_offset = len(output)
    if strategy.has_0th_item:
        output.extend(b"\0" * bytes_per_entry)
    table_begin = len(output)
    output.extend(b"\0" * (strategy.list_size * bytes_per_entry))
    for i, child in enumerate(node.children):
        offset = len(output)
        offset_offset: int
        if i == 0 and strategy.has_0th_item:
            offset_offset = zeroth_item_offset
        else:
            table_index: int = ord(child.addition) - strategy.first_item
            offset_offset = table_begin + table_index * bytes_per_entry

        if is_32_bit:
            output[offset_offset : offset_offset + bytes_per_entry] = len(
                output
            ).to_bytes(bytes_per_entry, "little")
            # Have to store absolute byte position.
            # Which is not possible with this architecture...
            pass
        else:
            output[offset_offset : offset_offset + bytes_per_entry] = (
                len(output) - begin_offset
            ).to_bytes(bytes_per_entry, "little")
        serialize_trie(child, output)
    return output


def serialize_trie(node: DicNode, output: bytearray) -> None:
    if node.storage in [StorageType.Leaf, StorageType.LeafMore]:
        return serialize_leaf(node, output)
    elif node.storage in [StorageType.List16, StorageType.List8]:
        return serialize_list(node, output)
    elif node.storage in [StorageType.Lookup32, StorageType.Lookup16]:
        return serialize_lookup(node, output)
    else:
        raise Exception("Invalid node.storage")


class Aff:
    intro_comment_: str
    encoding_: str
    affix_groups_: Dict[str, int]
    has_indexed_affixes_: bool
    affix_rules_: List[str]
    replacements_: List[Tuple[str, str]]
    other_commands_: List[str]

    def __init__(self):
        self.intro_comment_ = ""
        self.encoding_ = ""
        self.affix_groups_ = {}
        self.has_indexed_affixes_ = False
        self.affix_rules_ = []
        self.replacements_ = []
        self.other_commands_ = []

    @staticmethod
    def strip_comments(line: str) -> str:
        return line.split("#")[0].strip()

    @staticmethod
    def collapse_duplicate_spaces(line: str) -> str:
        multi = re.compile(" +")
        return re.sub(multi, " ", line)

    def get_af_index_for_af_string(self, af_string: str) -> int:
        if af_string in self.affix_groups_:
            return self.affix_groups_[af_string][1]
        return self.add_affix_group(af_string)

    def parse(self, aff_str: str) -> None:
        lines = aff_str.split("\n")
        got_command = False
        got_first_af = False
        got_first_rep = False
        self.has_indexed_affixes_ = False
        for line in lines:
            if not got_command and len(line) > 0 and line[0] == "#":
                self.intro_comment_ += line
                self.intro_comment_ += "\n"
                continue
            line = Aff.strip_comments(line)
            if line == "":
                continue
            got_command = True
            if line.startswith("SET "):
                self.encoding_ = line[4:].strip()
            elif line.startswith("AF "):
                self.has_indexed_affixes_ = True
                if got_first_af:
                    self.add_affix_group(line[3:])
                else:
                    got_first_af = True
            elif line.startswith("SFX ") or line.startswith("PFX "):
                self.add_affix(line)
            elif line.startswith("REP "):
                if got_first_rep:
                    self.add_replacement(line[4:])
                else:
                    got_first_rep = True
            elif line.startswith("TRY ") or line.startswith("MAP "):
                self.handle_encoded_command(line)
            elif line.startswith("IGNORE "):
                raise Exception("IGNORE command not supported")
            elif line.startswith("COMPLEXPREFIXES"):
                raise Exception("COMPLEXPREFIXES command not supported")
            else:
                self.handle_raw_command(line)

    def add_affix_group(self, rule: str) -> int:
        rule = rule.strip()
        affix_id = len(self.affix_groups_) + 1
        self.affix_groups_[rule] = affix_id
        return affix_id

    def add_affix(self, rule: str) -> None:
        rule = rule.strip()
        rule = Aff.collapse_duplicate_spaces(rule)
        found_spaces = 0
        token = ""
        for i in range(len(rule)):
            if rule[i] == " ":
                found_spaces += 1
                if found_spaces == 3:
                    part_start = i
                    if token[0] != "Y" and token[0] != "N":
                        part_start = i - len(token)
                    part = rule[part_start:]
                    if part.find("-") != -1:
                        tokens = list(map(lambda i: i.strip(), part.split(" ")))
                        if len(tokens) >= 5:
                            # cstr has ending null char
                            part = "{}\0 {}\0/{}\0 {}\0".format(
                                tokens[0], tokens[1], tokens[4], tokens[2]
                            )
                    slash_index = part.find("/")
                    if slash_index != -1 and not self.has_indexed_affixes_:
                        before_flags = part[0 : slash_index + 1]
                        after_slash = list(
                            map(lambda i: i.strip(), part[slash_index + 1 :].split(" "))
                        )
                        if len(after_slash) == 0:
                            raise Exception(
                                f"Found 0 terms after slash in affix rule '{part}' but need at least 2."
                            )
                        if len(after_slash) == 1:
                            print(
                                f"Warning: Found 1 term after slash in affix rule '{part}', but expected at least 2. Adding '.'."
                            )
                            after_slash.append(".")
                        part = "{}\0{} {}\0".format(
                            before_flags,
                            self.get_af_index_for_af_string(after_slash[0]),
                            after_slash[1],
                        )
                    rule = rule[0:part_start] + part
                    break
                token = ""
            else:
                token += rule[i]
        self.affix_rules_.append(rule)

    def add_replacement(self, rule: str) -> None:
        rule = rule.strip()
        rule = Aff.collapse_duplicate_spaces(rule)
        split = rule.split(" ", maxsplit=1)
        split[0].replace("_", " ")
        split[1].replace("_", " ")
        self.replacements_.append((split[0], split[1]))

    def handle_raw_command(self, line: str) -> None:
        self.other_commands_.append(line)

    def handle_encoded_command(self, line: str) -> None:
        self.other_commands_.append(line)


def serialize_string_list_null_term(strings: List[str], output: bytearray) -> None:
    for string in strings:
        if string == "":
            output.extend(b" ")
        else:
            output.extend(string.encode("utf-8"))
        output.append(0)
    output.append(0)


def serialize_replacements(
    replacements: List[Tuple[str, str]], output: bytearray
) -> None:
    for replacement in replacements:
        output.extend(replacement[0].encode("utf-8"))
        output.append(0)
        output.extend(replacements[1].encode("utf-8"))
        output.append(0)
    output.append(0)


def serialize_aff(aff: Aff, output: bytearray) -> None:
    header_offset = len(output)
    AFF_HEADER_SIZE = 16
    output.extend(b"\0" * AFF_HEADER_SIZE)
    output.extend(b"\n")
    output.extend(aff.intro_comment_.encode("utf-8"))  # comment_ = aff.comments()
    output.extend(b"\n")
    affix_group_offset = len(output)
    output.extend(f"AF {len(aff.affix_groups_)}".encode("utf-8"))
    output.append(0)
    serialize_string_list_null_term(aff.affix_groups_, output)
    affix_rule_offset = len(output)
    serialize_string_list_null_term(aff.affix_rules_, output)
    rep_offset = len(output)
    serialize_replacements(aff.replacements_, output)
    other_offset = len(output)
    serialize_string_list_null_term(aff.other_commands_, output)
    output[header_offset : header_offset + 4] = affix_group_offset.to_bytes(4, "little")
    output[header_offset + 4 : header_offset + 8] = affix_rule_offset.to_bytes(
        4, "little"
    )
    output[header_offset + 8 : header_offset + 12] = rep_offset.to_bytes(4, "little")
    output[header_offset + 12 : header_offset + 16] = other_offset.to_bytes(4, "little")


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
    aff.parse(aff_string)
    # fmt: on
    serialize_aff(aff, output)


def header_bytes() -> bytes:
    return b"\x42\x44\x69\x63\x02\x00\x00\x00\x20\x00\x00\x00\x83\x00\x00\x00"


def dic_bytes(words: List[str], output: bytearray) -> bytes:
    trie_root = DicNode()
    words = sorted(words)
    bytewords: List[bytes] = list(map(lambda w: w.encode("utf-8"), words))
    trie_root.build(bytewords, 0, len(bytewords), 0)
    compute_trie_storage(trie_root)
    serialize_trie(trie_root, output)


def create_bdic(words: List[str], aff: Optional[str] = None) -> bytes:
    """Create a .bdic file content containing a single word (and a placeholder word 'a' or 'I')"""
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
