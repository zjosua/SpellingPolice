# -*- coding: utf-8 -*-

import base64
import os
import re
import urllib.request
from typing import List, Dict

from bs4 import BeautifulSoup
from typing import Any, Optional

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, tooltip

from .const import DICT_DIR

dicts_repo = (
    "https://chromium.googlesource.com/chromium/deps/"
    "hunspell_dictionaries/+/refs/heads/main"
)


class GetDicts(QDialog):
    """Get dictionaries dialog"""

    def __init__(self, parent: Optional[QWidget] = mw) -> None:
        super(GetDicts, self).__init__(parent)
        self.setupUI()

    def setupUI(self) -> None:
        self.setObjectName("Dialog")
        self.resize(400, 300)
        self.setWindowTitle("Select dictionary")
        self.verticalLayout_2 = QVBoxLayout(self)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.lwDicts = QListWidget(self)
        self.lwDicts.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.lwDicts.setObjectName("lwDicts")
        self.verticalLayout_2.addWidget(self.lwDicts)
        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_2.addWidget(self.buttonBox)
        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.onReject)
        self.populateDictList()

    def setupValues(self, values: Dict[str, Any]) -> None:
        """Set widget values"""
        pass

    def onAccept(self) -> None:
        for item in self.lwDicts.selectedItems():
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

    def downloadDictionary(self, url: str, dest: str) -> None:
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

    def populateDictList(self) -> None:
        """Add available dicts to the list widget."""
        self.lwDicts.clear()
        for d in self.getDicts():
            self.lwDicts.addItem(d)

    def getDicts(self) -> List[str]:
        """Get a list of dicts available in the chromium repo."""
        dict_list: List[str] = []
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


def invokeGetDicts(parent: Optional[QWidget] = mw) -> None:
    """Invoke options dialog"""
    dialog = GetDicts(parent)
    dialog.exec()
