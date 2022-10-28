"""
Create a new bdic file from list of words

Note that it doesn't work with large number of words! 
Cutoff is at about 7000 words, but it varies. So it is recommended you feed < 5000 words

You can create a bdic file from hunspell .dic and .aff with 
qwebengine_convert_dict tool that comes with qt

Useful Links
https://spylls.readthedocs.io/en/latest/hunspell.html#code-walkthrough
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict.h
https://chromium.googlesource.com/chromium/deps/hunspell/+/61b053c9d102442e72af854d9f0a28ce60d539f5/google/bdict_writer.cc
https://chromium.googlesource.com/chromium/src/+/refs/heads/main/chrome/tools/convert_dict/convert_dict.cc
"""
import hashlib
from typing import List


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


def serialize_leaf(node: DicNode) -> bytes:
    output = b""
    first_affix = 0  # node.affix_indices[0] or 0
    id_byte = (first_affix >> 8) & BDictConst.LEAF_NODE_FIRST_BYTE_AFFIX_MASK
    if node.storage == StorageType.LeafMore:
        id_byte |= BDictConst.LEAF_NODE_ADDITIONAL_VALUE
    # if node.affix_indices.size() > 1 : id_byte |= ...
    output += id_byte.to_bytes(1, "little")
    output += (first_affix & 0xFF).to_bytes(1, "little")
    if node.storage == StorageType.LeafMore:
        for i in range(len(node.leaf_addition)):
            output += node.leaf_addition[i : i + 1]
        output += b"\0"  # c string
    # handle affixes...
    return output


def serialize_list(node: DicNode) -> bytes:
    output = b""
    is_8_bit = node.storage == StorageType.List8
    id_byte = BDictConst.LIST_NODE_TYPE_VALUE
    if not is_8_bit:
        id_byte |= BDictConst.LIST_NODE_16BIT_VALUE
    id_byte |= len(node.children)
    output += id_byte.to_bytes(1, "little")

    bytes_per_entry = 2 if is_8_bit else 3
    child_outputs: List[bytes] = []
    child_outputs_offset = 0
    # instead of reserving space and putting it in-place,
    # serialize children, then append in order.
    for child in node.children:
        child_outputs.append(serialize_trie(child))

    for i, child in enumerate(node.children):
        assert len(child.addition) == 1
        output += child.addition  # 1 byte
        if is_8_bit:
            output += (child_outputs_offset & 0xFF).to_bytes(
                bytes_per_entry - 1, "little"
            )
        else:
            output += child_outputs_offset.to_bytes(bytes_per_entry - 1, "little")
        child_outputs_offset += len(child_outputs[i])

    for child_output in child_outputs:
        output += child_output

    return output


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


def serialize_lookup(node: DicNode) -> bytes:
    output = b""

    id_byte = BDictConst.LOOKUP_NODE_TYPE_VALUE
    strategy = compute_lookup_strategy_details(node.children)
    is_32_bit = node.storage == StorageType.Lookup32
    if is_32_bit:
        # calculating absolute offset is currently not possible
        raise Exception("Lookup32 is not supported! (Too many words)")
    if is_32_bit:
        id_byte |= BDictConst.LOOKUP_NODE_32BIT_VALUE
    if strategy.has_0th_item:
        id_byte |= BDictConst.LOOKUP_NODE_0TH_VALUE
    begin_offset = len(output)
    output += id_byte.to_bytes(1, "little")
    output += strategy.first_item.to_bytes(1, "little")
    output += strategy.list_size.to_bytes(1, "little")

    bytes_per_entry = 4 if is_32_bit else 2
    zeroth_item_offset = len(output)
    if strategy.has_0th_item:
        output += b"\0" * bytes_per_entry
    table_begin = len(output)
    output += b"\0" * (strategy.list_size * bytes_per_entry)
    for i, child in enumerate(node.children):
        offset = len(output)
        offset_offset: int
        if i == 0 and strategy.has_0th_item:
            offset_offset = zeroth_item_offset
        else:
            table_index: int = ord(child.addition) - strategy.first_item
            offset_offset = table_begin + table_index * bytes_per_entry

        if is_32_bit:
            # Have to store absolute byte position.
            # Which is not possible with this architecture...
            pass
        else:
            output = (
                output[0:offset_offset]
                + (len(output) - begin_offset).to_bytes(bytes_per_entry, "little")
                + output[offset_offset + bytes_per_entry :]
            )
        output += serialize_trie(child)
    return output


def serialize_trie(node: DicNode) -> bytes:
    if node.storage in [StorageType.Leaf, StorageType.LeafMore]:
        return serialize_leaf(node)
    elif node.storage in [StorageType.List16, StorageType.List8]:
        return serialize_list(node)
    elif node.storage in [StorageType.Lookup32, StorageType.Lookup16]:
        return serialize_lookup(node)
    else:
        raise Exception("Invalid node.storage")


def aff_bytes() -> bytes:
    """
    SET UTF-8
    TRY esianrtolcdugmphbyfvkwzESIANRTOLCDUGMPHBYFVKWZ'
    ICONV 1
    ICONV ’ '
    """
    return b"\x32\x00\x00\x00\x38\x00\x00\x00\x39\x00\x00\x00\x3A\x00\x00\x00\x0A\x0A\x41\x46\x20\x30\x00\x00\x00\x00\x54\x52\x59\x20\x65\x73\x69\x61\x6E\x72\x74\x6F\x6C\x63\x64\x75\x67\x6D\x70\x68\x62\x79\x66\x76\x6B\x77\x7A\x45\x53\x49\x41\x4E\x52\x54\x4F\x4C\x43\x44\x55\x47\x4D\x50\x48\x42\x59\x46\x56\x4B\x57\x5A\x27\x00\x49\x43\x4F\x4E\x56\x20\x31\x00\x49\x43\x4F\x4E\x56\x20\xE2\x80\x99\x20\x27\x00\x00"


def header_bytes() -> bytes:
    return b"\x42\x44\x69\x63\x02\x00\x00\x00\x20\x00\x00\x00\x83\x00\x00\x00"


# May raise an exception if too many words.
# TODO: make multiple dictionary files for such cases
def dic_bytes(words: List[str]) -> bytes:
    trie_root = DicNode()
    words = sorted(words)
    bytewords: List[bytes] = list(map(lambda w: w.encode("utf-8"), words))
    trie_root.build(bytewords, 0, len(bytewords), 0)
    compute_trie_storage(trie_root)
    return serialize_trie(trie_root)


def create_bdic(words: List[str]) -> bytes:
    """Create a .bdic file content containing a single word (and a placeholder word 'a' or 'I')"""
    header = header_bytes()
    aff = aff_bytes()
    dic = dic_bytes(words)
    md5 = hashlib.md5(aff + dic).digest()
    return header + md5 + aff + dic


# For testing purposes
if __name__ == "__main__":
    import sys
    from pathlib import Path

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    dic_file = input_path.read_text()
    lines = dic_file.split("\n")[1:]  # first line contains word count
    mwords = map(lambda line: line.strip(), lines)
    fwords = filter(lambda i: i, mwords)
    words = list(fwords)

    b = create_bdic(words)
    output_path.write_bytes(b)
