# -*- coding: utf-8 -*-
# Copyright: (C) 2019-2021 Lovac42
# Support: https://github.com/lovac42/SpellingPolice
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


import os
from typing import Optional

from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, showInfo, tooltip

from .const import *
from .bdicwriter import create_bdic
from .anking_menu import get_anking_menu
from .gui import dictionary_dialog


def open_dict_dir() -> None:
    if os.path.exists(DICT_DIR):
        openFolder(DICT_DIR)
    elif ALT_BUILD_VERSION:
        from aqt import moduleDir

        openFolder(moduleDir)

    if ALT_BUILD_VERSION:
        showInfo(ALT_BUILD_INSTRUCTIONS, title="Instructions", textFormat="rich")


class DictionaryManager:
    def __init__(self):
        self.setupMenu()

        self._dicts = [
            i[:-5] for i in os.listdir(DICT_DIR) if RE_DICT_EXT_ENABLED.search(i)
        ]

    def setupMenu(self):
        menu = get_anking_menu()
        a = QAction("Spell Checker Dictionaries", menu)
        menu.addAction(a)
        a.triggered.connect(self.showConfig)

    def showConfig(self):
        profile = mw.web._page.profile()

        profile.setSpellCheckEnabled(False)
        profile.setSpellCheckLanguages({})
        self._dicts = dictionary_dialog.DictionaryDialog(parent=mw).getDictionaries()

        profile.setSpellCheckEnabled(profile.isSpellCheckEnabled())
        profile.setSpellCheckLanguages(self._dicts)
        print(self._dicts)

    def getDictionaries(self):
        return self._dicts


class CustomDicDialog(QDialog):
    saved = False
    parent: QDialog

    def __init__(self, parent: QDialog = mw):
        QDialog.__init__(self, parent)
        self.parent = parent
        Path(CUSTOM_WORDS_TEXT_FILE).touch(exist_ok=True)
        self._setup_dialog()
        self.load_words()

    def _setup_dialog(self) -> None:
        self.setWindowTitle("Custom Dictionary")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(600, 300)

        instruction_text = QLabel("Put one word in each line. Restart Anki afterwards.")
        instruction_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        text_edit = QTextEdit(self)
        text_edit.setAcceptRichText(False)
        text_edit.setMaximumHeight(9999)
        self.text_edit = text_edit

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(open_dict_dir)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply)
        apply_btn.setDefault(True)

        btn_box = QHBoxLayout()
        btn_box.addWidget(browse_btn)
        btn_box.addStretch(0)
        btn_box.addWidget(apply_btn)

        layout = QVBoxLayout()
        layout.addSpacing(3)
        layout.addWidget(instruction_text)
        layout.addWidget(text_edit)
        layout.addLayout(btn_box)

        self.setLayout(layout)

    def load_words(self) -> None:
        text = Path(CUSTOM_WORDS_TEXT_FILE).read_text()
        self.text_edit.setPlainText(text)

    def apply(self) -> None:
        words = self.text_edit.toPlainText().splitlines()
        words = list(sorted(set(words)))
        # Delete dictionary if no words exist
        if len(words) == 0:
            Path(CUSTOM_DICT_FILE).unlink(missing_ok=True)
            Path(CUSTOM_WORDS_TEXT_FILE).write_text("")
            self.saved = True
            self.close()
            return
        # Custom dictionary must have at least 2 words or an error occurs
        if len(words) == 1:
            additional = "a" if "a" not in words else "I"
            words.append(additional)
            tooltip(
                f"Additionally added word '{additional}' because a dictionary must contain at least 2 words.",
                period=6000,
                parent=self.parent,
            )

        aff: Optional[str] = None
        aff_file = Path(CUSTOM_WORDS_AFF_FILE)
        if aff_file.exists():
            aff = aff_file.read_text()
        else:
            invalid_char = filter(lambda word: "/" in word, words)
            if next(invalid_char, None) != None:
                showInfo("One of the words contain invalid character '/'. Aborting.")
                return
        content = create_bdic(words, aff)
        Path(CUSTOM_DICT_FILE).write_bytes(content)
        Path(CUSTOM_WORDS_TEXT_FILE).write_text("\n".join(words))
        self.saved = True
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self.saved:
            resp = QMessageBox.question(
                self,
                "Discard changes?",
                "Closing this window will discard changes. Are you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        event.accept()
