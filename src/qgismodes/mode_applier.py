# -*- coding: utf-8 -*-
"""ModeApplier — build / tear down a mode's UI in the QGIS main window.

See design-specification.md §3.3.

The applier tracks plugin-created toolbars in ``self._owned_toolbars`` so that
``teardown_owned_toolbars()`` removes exactly what was built — never a borrowed
QGIS QAction (FR-UI-8).

Realises FR-UI-1, FR-UI-5, FR-UI-7, FR-UI-8.
"""

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDockWidget, QToolBar, QWidget


# config string -> Qt enum
_TOOLBAR_AREAS = {
    "top": Qt.ToolBarArea.TopToolBarArea,
    "bottom": Qt.ToolBarArea.BottomToolBarArea,
    "left": Qt.ToolBarArea.LeftToolBarArea,
    "right": Qt.ToolBarArea.RightToolBarArea,
}

_PANEL_AREAS = {
    "top": Qt.DockWidgetArea.TopDockWidgetArea,
    "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
    "left": Qt.DockWidgetArea.LeftDockWidgetArea,
    "right": Qt.DockWidgetArea.RightDockWidgetArea,
}


class ModeApplier:
    """Build a mode's UI; track plugin-owned toolbars; tear them down safely."""

    def __init__(self, mainwindow, token_resolver, logger=None):
        """
        Args:
            mainwindow: The QGIS main window.
            token_resolver: A TokenResolver instance.
            logger: Optional callable ``(message, level)`` for diagnostics.
        """
        self.mainwindow = mainwindow
        self.token_resolver = token_resolver
        self.logger = logger
        self._owned_toolbars: list = []  # plugin-created QToolBar instances

    def log(self, message: str, level: str = "info") -> None:
        if self.logger:
            self.logger(message, level)

    # ------------------------------------------------------------------ apply

    def apply(self, config: dict) -> None:
        """Build toolbars / panels / statusbar from ``config``."""
        # Feed the algorithms groups to TokenResolver so `algorithms:<name>`
        # tokens resolve correctly.
        self.token_resolver.set_algorithms(config.get("algorithms", {}))

        for name, spec in config.get("toolbars", {}).items():
            try:
                self._build_toolbar(name, spec)
            except Exception as e:  # noqa: BLE001
                self.log(f"Failed to build toolbar {name!r}: {e}", "error")

        self._apply_panels(config.get("panels", {}))
        self._apply_statusbar(config.get("statusbar", {}))

    def teardown_owned_toolbars(self) -> None:
        """Remove only plugin-created toolbars (FR-UI-8)."""
        for toolbar in self._owned_toolbars:
            try:
                self.mainwindow.removeToolBar(toolbar)
                toolbar.deleteLater()
            except Exception as e:  # noqa: BLE001
                self.log(f"Failed to remove toolbar: {e}", "warning")
        self._owned_toolbars.clear()

    @property
    def owned_toolbar_names(self) -> list:
        """Names of currently-tracked plugin toolbars (diagnostic)."""
        names = []
        for tb in self._owned_toolbars:
            try:
                names.append(tb.objectName())
            except RuntimeError:  # deleted
                names.append("<deleted>")
        return names

    # ------------------------------------------------------------------ internals

    def _build_toolbar(self, name: str, spec: dict) -> None:
        title = spec.get("title", name)
        area_key = spec.get("area", "top")
        area = _TOOLBAR_AREAS.get(area_key, Qt.ToolBarArea.TopToolBarArea)
        items = spec.get("items", [])

        toolbar = QToolBar(title, self.mainwindow)
        toolbar.setObjectName(name)
        toolbar.setFloatable(False)
        toolbar.setMovable(False)
        toolbar.toggleViewAction().setDisabled(True)
        self.mainwindow.addToolBar(area, toolbar)
        self.token_resolver.add_items(toolbar, items)
        self._owned_toolbars.append(toolbar)
        toolbar.show()
        self.log(f"Built toolbar {name!r} (area={area_key}, items={len(items)})")

    def _apply_panels(self, panels_config: dict) -> None:
        """Hide unlisted panels; (re)position and configure listed ones."""
        # 1. Hide every panel not in the config
        for panel in self.mainwindow.findChildren(QDockWidget):
            name = panel.objectName()
            if name and name not in panels_config and not panel.isHidden():
                panel.hide()

        # 2. Position + show/hide listed panels
        for name, spec in panels_config.items():
            panel = self.mainwindow.findChild(QDockWidget, name)
            if not panel:
                self.log(f"Panel not found: {name!r}", "warning")
                continue
            try:
                state, area_name = spec.split(":", 1)
            except (ValueError, AttributeError):
                self.log(f"Invalid panel spec for {name!r}: {spec!r}", "warning")
                continue
            area = _PANEL_AREAS.get(area_name, Qt.DockWidgetArea.LeftDockWidgetArea)
            self.mainwindow.addDockWidget(area, panel)
            if state == "fixed":
                panel.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
                panel.show()
            elif state == "hidden":
                panel.hide()
            else:
                self.log(f"Invalid panel state for {name!r}: {state!r}", "warning")

    def _apply_statusbar(self, statusbar_config: dict) -> None:
        """Hide listed status-bar widgets (value falsy)."""
        for name, state in statusbar_config.items():
            widget = self.mainwindow.findChild(QWidget, name)
            if not widget:
                self.log(f"Status-bar widget not found: {name!r}", "warning")
                continue
            if not state:
                widget.hide()
