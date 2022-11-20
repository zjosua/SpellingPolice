# -*- coding: utf-8 -*-

import os

from aqt.qt import *

from ..const import DICT_DIR, RE_DICT_EXT_DISABLED, RE_DICT_EXT_ENABLED

from .forms import dictionary_dialog


class DictionaryDialog(QDialog):
    def __init__(self, parent):
        super(DictionaryDialog, self).__init__(parent=parent)
        self.form = dictionary_dialog.Ui_DictionaryDialog()
        self.form.setupUi(self)
        self._connect_signals()
        self._update()

    def _connect_signals(self):
        from ..dict import CustomDicDialog, open_dict_dir

        self.form.list.itemDoubleClicked.connect(self._toggle)
        self.form.bws_btn.clicked.connect(open_dict_dir)
        self.form.custom_words_btn.clicked.connect(
            lambda _: CustomDicDialog(parent=self).exec()
        )
        self.form.en_btn.clicked.connect(self._enable)
        self.form.dis_btn.clicked.connect(self._disable)

    def getDictionaries(self):
        self.exec()
        return self._dict

    def _update(self):
        self._dict = []
        self.form.list.clear()

        try:
            DICT_FILES = os.listdir(DICT_DIR)
        except FileNotFoundError:
            showInfo("Missing or no read/write permission to dictionary folder.")
            return

        for d in DICT_FILES:
            if RE_DICT_EXT_ENABLED.search(d):
                item = QListWidgetItem(d)
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.form.list.addItem(item)
                self._dict.append(d[:-5])

        for d in DICT_FILES:
            if RE_DICT_EXT_DISABLED.search(d):
                item = QListWidgetItem(d)
                item.setData(Qt.ItemDataRole.UserRole, d)
                self.form.list.addItem(item)

    def _enable(self):
        sel = [
            i
            for i in range(self.form.list.count())
            if self.form.list.item(i).isSelected()
        ]
        if sel:
            for i in sel:
                fn = self.form.list.item(i).text()
                if RE_DICT_EXT_DISABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f[:-9])
        self._update()

    def _disable(self):
        sel = [
            i
            for i in range(self.form.list.count())
            if self.form.list.item(i).isSelected()
        ]
        if sel:
            for i in sel:
                fn = self.form.list.item(i).text()
                if RE_DICT_EXT_ENABLED.search(fn):
                    f = os.path.join(DICT_DIR, fn)
                    os.rename(f, f + ".disabled")
        self._update()

    def _toggle(self):
        fn = self.form.list.currentItem().text()
        if RE_DICT_EXT_ENABLED.search(fn):
            self._disable()
        else:
            self._enable()
