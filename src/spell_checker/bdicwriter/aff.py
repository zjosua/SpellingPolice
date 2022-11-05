"""
This is a python port of chromium's convert_dict tool.

Copyright 2006-2008 The Chromium Authors
Copyright 2022 AnkingMed

Use of this source code is governed by a BSD-style license that can be
found in the LICENSE file.
"""
import re
from typing import List, Dict, Tuple, Iterable


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
            return self.affix_groups_[af_string]
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


def serialize_string_list_null_term(strings: Iterable[str], output: bytearray) -> None:
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
        output.extend(replacement[1].encode("utf-8"))
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
