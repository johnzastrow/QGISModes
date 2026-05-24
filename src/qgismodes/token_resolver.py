# -*- coding: utf-8 -*-
"""TokenResolver — resolve mode-file tokens to live Qt objects.

See design-specification.md §3.4. Token vocabulary is documented in
docs/customizing-qgis-light.md §2.5.

Ported from QGIS Light's `getItems` / `addItems` / `findAction`. The synthetic
exit token is renamed `mActionDisableQGISLight` → `mActionDisableQGISModes`.

Realises FR-UI-2, FR-UI-3, FR-UI-4, FR-UI-6.
"""

import os

from qgis.core import QgsApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QMenu,
    QToolButton,
    QWidget,
    QWidgetAction,
)

from processing import execAlgorithmDialog


class TokenResolver:
    """Resolve mode-file tokens; place items recursively into a parent widget.

    The active mode's `algorithms` groups must be supplied via `set_algorithms()`
    before `add_items()` builds a toolbar that references them; ModeApplier
    will do this on each `apply()`.

    The synthetic `mActionDisableQGISModes` token is created with an optional
    `disable_callback` wired by the plugin (`LifecycleController.disable`).
    """

    DISABLE_TOKEN = "mActionDisableQGISModes"

    def __init__(self, mainwindow, plugin_dir: str, logger=None, disable_callback=None):
        self.mainwindow = mainwindow
        self.plugin_dir = plugin_dir
        self.logger = logger
        self.disable_callback = disable_callback
        # active mode's algorithms-groups dict; set by ModeApplier per apply()
        self._algorithms: dict = {}

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    def set_algorithms(self, algorithms: dict) -> None:
        self._algorithms = algorithms or {}

    # ----------------------------------------------------- action discovery

    def find_action(self, widget: QWidget, identifier: str):
        """Find an action by objectName, text, or tooltip (recursive)."""
        for action in widget.actions():
            if isinstance(action, QWidgetAction):
                action = self.find_action(action.defaultWidget(), identifier)
            elif identifier in (action.objectName(), action.text(), action.toolTip()):
                pass
            elif action.menu():
                action = self.find_action(action.menu(), identifier)
            else:
                continue
            if action:
                return action
        return None

    # ----------------------------------------------------- token resolution

    def get_items(self, token: str) -> list:
        """Resolve one token to a list of live Qt objects."""
        # processing-algorithm id (e.g. "native:buffer")
        algorithm = QgsApplication.processingRegistry().algorithmById(token)
        if algorithm:
            action = QAction(self.mainwindow)
            action.setIcon(algorithm.icon())
            action.setText(algorithm.displayName())
            action.triggered.connect(
                lambda checked=False, t=token: execAlgorithmDialog(t)
            )
            return [action]

        # synthetic disable token (mode-file optional; UIWidgets also injects)
        if token == self.DISABLE_TOKEN:
            action = QAction(self.mainwindow)
            action.setObjectName(self.DISABLE_TOKEN)
            action.setIcon(QIcon(os.path.join(self.plugin_dir, "icons", "qgismodes.svg")))
            action.setText("Disable QGIS Modes")
            if self.disable_callback:
                action.triggered.connect(
                    lambda checked=False: self.disable_callback()
                )
            return [action]

        # parent:identifier (optionally with trailing '*' wildcard)
        if ":" not in token:
            self.log(f"Invalid token (missing ':'): {token}", "warning")
            return []

        parent_name, name = token.split(":", 1)

        if parent_name == "section":
            action = QAction(self.mainwindow)
            action.setText(name)
            action.setSeparator(True)
            return [action]

        if parent_name == "algorithms":
            group = self._algorithms.get(name)
            if not group:
                self.log(f"Unknown algorithms group: {name}", "warning")
                return []
            menu = QMenu(self.mainwindow)
            self.add_items(menu, group.get("items", []))
            toolbutton = QToolButton(self.mainwindow)
            toolbutton.setIcon(QIcon(group.get("icon", "")))
            toolbutton.setMenu(menu)
            toolbutton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
            return [toolbutton]

        parent = self.mainwindow.findChild(QWidget, parent_name)
        if not parent:
            self.log(f"Invalid parent object name: {parent_name}", "warning")
            return []

        wildcard = name.endswith("*")
        if wildcard:
            name = name[:-1]

        if not name:
            return list(parent.actions())

        action = self.find_action(parent, name)
        if not action:
            self.log(f"Invalid identifier token: {token}", "warning")
            return []

        if not wildcard:
            return [action]

        # wildcard: return the associated dropdown menu / its actions
        for widget in self._associated_objects(action):
            if isinstance(widget, QToolButton):
                return [widget.menu()] if widget.menu() else list(widget.actions())
        for widget in self._associated_objects(action):
            if isinstance(widget, QMenu):
                return [widget]
        return [action]

    # ----------------------------------------------------- item placement

    def add_items(self, parent: QWidget, items: list) -> None:
        """Recursively place items into `parent` (a toolbar or menu)."""
        for item in items:
            if item == "separator":
                parent.addSeparator()
            elif isinstance(item, str):
                self.add_items(parent, self.get_items(item))
            elif isinstance(item, list):
                # nested array → grouped dropdown button
                menu = QMenu()
                self.add_items(menu, item)
                self.add_items(parent, [menu])
            elif isinstance(item, QAction):
                parent.addAction(item)
            elif isinstance(item, QMenu) and item.actions():
                if isinstance(parent, QMenu):
                    group = None
                    for action in item.actions():
                        parent.addAction(action)
                        if action.actionGroup():
                            if not group:
                                group = action.actionGroup()
                            else:
                                action.setActionGroup(group)
                else:
                    toolbutton = QToolButton(self.mainwindow)
                    toolbutton.setMenu(item)
                    toolbutton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
                    toolbutton.setDefaultAction(item.actions()[0])
                    item.triggered.connect(toolbutton.setDefaultAction)
                    parent.addWidget(toolbutton)
            elif isinstance(item, QWidget):
                parent.addWidget(item)
            else:
                self.log(f"Invalid item: {item}", "warning")

    # ----------------------------------------------------- Qt5/Qt6 shim

    @staticmethod
    def _associated_objects(action):
        """`QAction.associatedWidgets()` was renamed to `associatedObjects()` in Qt6."""
        if hasattr(action, "associatedObjects"):
            return action.associatedObjects()
        return action.associatedWidgets()
