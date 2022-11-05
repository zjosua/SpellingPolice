"""
This is a python port of chromium's convert_dict tool.

Copyright 2006-2008 The Chromium Authors
Copyright 2022 AnkingMed

Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file.
"""
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
    # affix_indices: List[int] Not yet supported
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
        else:
            output[offset_offset : offset_offset + bytes_per_entry] = (
                len(output) - begin_offset
            ).to_bytes(bytes_per_entry, "little")
        serialize_trie(child, output)


def serialize_trie(node: DicNode, output: bytearray) -> None:
    if node.storage in [StorageType.Leaf, StorageType.LeafMore]:
        return serialize_leaf(node, output)
    elif node.storage in [StorageType.List16, StorageType.List8]:
        return serialize_list(node, output)
    elif node.storage in [StorageType.Lookup32, StorageType.Lookup16]:
        return serialize_lookup(node, output)
    else:
        raise Exception("Invalid node.storage")
