# -*- coding: utf-8 -*-
# Copyright: (C) 2019-2021 Lovac42
# Support: https://github.com/lovac42/SpellingPolice
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html


import os

from aqt import mw
from aqt.qt import *
from aqt.utils import openFolder, showInfo

from .const import *
from .custom import add_custom_word, custom_dict_files, custom_words, remove_custom_word


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
        for d in custom_dict_files():
            self._dicts.append(str(d)[:-5])

    def setupMenu(self):
        a = QAction("Dictionary Configuration", mw)
        a.triggered.connect(self.showConfig)
        mw.form.menuTools.addAction(a)

    def showConfig(self):
        profile = mw.web._page.profile()

        profile.setSpellCheckEnabled(False)
        profile.setSpellCheckLanguages({})
        self._dicts = DictionaryDialog().getDictionaries()

        profile.setSpellCheckEnabled(profile.isSpellCheckEnabled())
        profile.setSpellCheckLanguages(self._dicts)
        print(self._dicts)

    def getDictionaries(self):
        return self._dicts


class DictionaryDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self._setupDialog()
        self._update()
        self.exec()

    def getDictionaries(self):
        return self._dict

    def _setupDialog(self):
        self.setWindowTitle("Dictionaries")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(250, 250)

        layout = QVBoxLayout()
        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.itemDoubleClicked.connect(self._toggle)

        bws_btn = QPushButton("Browse")
        bws_btn.clicked.connect(open_dict_dir)
        custom_words_btn = QPushButton("Custom Words")
        custom_words_btn.clicked.connect(lambda _: CustomWordsDialog().exec())
        en_btn = QPushButton("Enable")
        en_btn.clicked.connect(self._enable)
        dis_btn = QPushButton("Disable")
        dis_btn.clicked.connect(self._disable)

        control_box = QHBoxLayout()
        control_box.addWidget(bws_btn)
        control_box.addWidget(custom_words_btn)
        control_box.addWidget(en_btn)
        control_box.addWidget(dis_btn)

        layout.addWidget(self.list)
        layout.addLayout(control_box)
        self.setLayout(layout)

    def _update(self):
        self._dict = []
        self.list.clear()

        try:
            DICT_FILES = os.listdir(DICT_DIR)
            CUSTOM_DICT_FILES = custom_dict_files()
        except FileNotFoundError:
            showInfo("Missing or no read/write permission to dictionary folder.")
            return

        for d in DICT_FILES:
            if RE_DICT_EXT_ENABLED.search(d):
                item = QListWidgetItem(d)
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.list.addItem(item)
                self._dict.append(d[:-5])

        for d in DICT_FILES:
            if RE_DICT_EXT_DISABLED.search(d):
                item = QListWidgetItem(d)
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.list.addItem(item)

        for d in CUSTOM_DICT_FILES:
            self._dict.append(str(d)[:-5])

    def _enable(self):
        sel = [i for i in range(self.list.count()) if self.list.item(i).isSelected()]
        if sel:
            for i in sel:
                fn = self.list.item(i).text()
                if RE_DICT_EXT_DISABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f[:-9])
        self._update()

    def _disable(self):
        sel = [i for i in range(self.list.count()) if self.list.item(i).isSelected()]
        if sel:
            for i in sel:
                fn = self.list.item(i).text()
                if RE_DICT_EXT_ENABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f + ".disabled")
        self._update()

    def _toggle(self):
        fn = self.list.currentItem().text()
        if RE_DICT_EXT_ENABLED.search(fn):
            self._disable()
        else:
            self._enable()


class CustomWordsDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.words = set(custom_words())
        self.restore()
        self._setup_dialog()

    def _setup_dialog(self) -> None:
        self.setWindowTitle("Custom Words")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.resize(600, 300)

        word_count_text = QLabel(
            f"<center>You currently have <b>{len(self.words)}</b> custom words.</center>"
        )
        instruction_text = QLabel(
            "<h4>How to add or delete custom words in the dictionary.</h4>"
            "1. Click Browse.<br/>"
            "2. Open 'custom_words.txt'.<br/>"
            "3. Put in or remove words. The words may be separated by whitespace or new line.<br/>"
            "4. Click Apply to save the text file content into dictionary files.<br/>"
            "5. If you make a mistake, you can click 'Restore' to restore the text file from the dictionary files. All changes will be lost."
        )
        word_count_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        instruction_text.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction
        )
        word_count_text.setTextFormat(Qt.TextFormat.RichText)
        instruction_text.setTextFormat(Qt.TextFormat.RichText)
        instruction_text.setWordWrap(True)
        instruction_text.setMinimumWidth(400)
        instruction_text.setMinimumHeight(200)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(open_dict_dir)
        restore_btn = QPushButton("Restore")
        restore_btn.clicked.connect(self.restore)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply)
        apply_btn.setDefault(True)

        btn_box = QHBoxLayout()
        btn_box.addWidget(browse_btn)
        btn_box.addStretch(0)
        btn_box.addWidget(restore_btn)
        btn_box.addWidget(apply_btn)

        layout = QVBoxLayout()
        layout.addSpacing(5)
        layout.addWidget(word_count_text)
        layout.addSpacing(5)
        layout.addWidget(instruction_text)
        layout.addStretch(0)
        layout.addLayout(btn_box)

        self.setLayout(layout)

    def restore(self) -> None:
        with open(CUSTOM_WORDS_TEXT_FILE, "w") as f:
            f.writelines(sorted(self.words))

    def apply(self) -> None:
        new_words = set()
        with open(CUSTOM_WORDS_TEXT_FILE, "r") as f:
            for line in f.readlines():
                new_words.update(line.split(" "))

        new_words = [word for word in new_words if word not in self.words]
        delete_words = [word for word in self.words if word not in new_words]
        for word in delete_words:
            remove_custom_word(word)
        for word in new_words:
            add_custom_word(word)

        self.close()
