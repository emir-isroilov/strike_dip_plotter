"""Main plugin class: adds the toolbar button and menu entry."""

import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .dialog import StrikeDipDialog

MENU_NAME = "&Strike/Dip Plotter"


class StrikeDipPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.action = None

    def initGui(self):
        icon = QIcon(os.path.join(self.plugin_dir, "icon.svg"))
        self.action = QAction(icon, "Strike/Dip Plotter", self.iface.mainWindow())
        self.action.setToolTip("Load strike/dip measurements from CSV")
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu(MENU_NAME, self.action)

    def unload(self):
        if self.action is not None:
            self.iface.removePluginVectorMenu(MENU_NAME, self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action = None

    def run(self):
        dlg = StrikeDipDialog(self.iface, self.plugin_dir, self.iface.mainWindow())
        dlg.exec()
