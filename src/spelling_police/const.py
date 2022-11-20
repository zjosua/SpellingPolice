# -*- coding: utf-8 -*-
# Copyright: (C) 2019-2021 Lovac42
# Support: https://github.com/lovac42/SpellingPolice
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


import re, os
from aqt import mw
from pathlib import Path


ADDON_PATH = os.path.dirname(__file__)

ADDON_NAME = "SpellingPolice"

TARGET_STABLE_VERSION = 23

RE_DICT_EXT_ENABLED = re.compile(r'\.bdic$', re.I)

RE_DICT_EXT_DISABLED = re.compile(r'\.bdic\.disabled$', re.I)

DICT_DIR = os.environ["QTWEBENGINE_DICTIONARIES_PATH"]

try:
    Path(DICT_DIR).mkdir(parents=True, exist_ok=True)
except:
    print(f"Can't create dictionary folder ({DICT_DIR}), check permissions.")
