# -*- coding: utf-8 -*-

import base64
import os
import re
import urllib.request

from bs4 import BeautifulSoup

from aqt import mw
from aqt.qt import *
from aqt.utils import tooltip

from ..const import DICT_DIR

from .forms import get_dicts

dicts_repo = (
    "https://chromium.googlesource.com/chromium/deps/"
    "hunspell_dictionaries/+/refs/heads/main"
)


class GetDicts(QDialog):
    """Get dictionaries dialog"""

    def __init__(self, parent: QDialog = mw):
        super(GetDicts, self).__init__(parent)
        # load qt-designer form:
        self.f = get_dicts.Ui_Dialog()
        self.f.setupUi(self)
        self.setupUI()

    def setupUI(self):
        self.f.buttonBox.accepted.connect(self.onAccept)
        self.f.buttonBox.rejected.connect(self.onReject)
        self.populateDictList()

    def setupValues(self, values):
        """Set widget values"""
        pass

    def onAccept(self):
        for item in self.f.lwDicts.selectedItems():
            label = item.text()
            if re.search(r" - ", label):
                filename = label.split(" - ")[1]
            else:
                filename = label.split(" - ")[0]
            filename = filename + ".bdic"
            dl_dest = os.path.join(DICT_DIR, filename)
            url = os.path.join(dicts_repo, filename) + "?format=TEXT"
            self.downloadDictionary(url, dl_dest)
            tooltip(f"Downloaded dictionary {filename}")
        self.close()

    def downloadDictionary(self, url, dest):
        """
        Download a decoded dictionary file.

        This code is from qutebrowser's dictcli.py.
        """
        response = urllib.request.urlopen(url)
        decoded = base64.decodebytes(response.read())
        with open(dest, "bw") as dict_file:
            dict_file.write(decoded)

    def onReject(self):
        self.close()

    def populateDictList(self):
        """Add available dicts to the list widget."""
        self.f.lwDicts.clear()
        for d in self.getDicts():
            self.f.lwDicts.addItem(d)

    def getDicts(self):
        """Get a list of dicts available in the chromium repo."""
        dict_list = []
        try:
            with urllib.request.urlopen(dicts_repo) as fp:
                mybytes = fp.read()
                html_doc = mybytes.decode("utf8")
        except urllib.error.URLError:
            showInfo(
                f"Error connecting to {dicts_repo}.<br/><br/>"
                "Are you connected to the internet?",
                type="warning",
                title="Connection Error",
            )
            return dict_list
        soup = BeautifulSoup(html_doc, "html.parser")
        for link in soup.ol.find_all("a"):
            href = link.get("href")
            if not href.endswith(".bdic"):
                continue
            href = os.path.basename(href)
            filename = href.split(".bdic")[0]
            dict_list.append(filename)
            dict_list.sort()
        return dict_list


def invokeGetDicts(parent: QDialog = mw):
    """Invoke options dialog"""
    dialog = GetDicts(parent)
    return dialog.exec()
