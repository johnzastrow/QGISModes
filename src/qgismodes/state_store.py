# -*- coding: utf-8 -*-
"""StateStore — all persistent state I/O via QgsSettings.

See design-specification.md §3.6. Centralises QgsSettings access so other
components don't speak the key strings directly.

Realises FR-PS-1, FR-PS-2, FR-LC-2 / FR-LC-4 / FR-LC-5, FR-SW-3.
"""

from qgis.core import QgsSettings


class StateStore:
    """All persistent state under the `qgismodes/` QgsSettings namespace."""

    PREFIX = "qgismodes"

    def __init__(self, settings: QgsSettings = None):
        self._settings = settings or QgsSettings()

    def _key(self, *parts) -> str:
        return "/".join((self.PREFIX,) + parts)

    # ------------------------------------------------------------ enabled flag

    def enabled(self) -> bool:
        return self._settings.value(self._key("enabled")) == "true"

    def set_enabled(self, value: bool) -> None:
        if value:
            self._settings.setValue(self._key("enabled"), "true")
        else:
            self._settings.remove(self._key("enabled"))
        self._settings.sync()

    # ------------------------------------------------------------ active mode

    def active_mode_id(self):
        return self._settings.value(self._key("mode"))

    def set_active_mode_id(self, mode_id: str) -> None:
        self._settings.setValue(self._key("mode"), mode_id)
        self._settings.sync()

    # ------------------------------------------------- captured original layout

    def save_original_layout(self, toolbars: list, panels: list) -> None:
        """Persist the captured original toolbar + panel state."""
        self._settings.setValue(self._key("original_layout", "toolbars"), toolbars)
        self._settings.setValue(self._key("original_layout", "panels"), panels)
        self._settings.sync()

    def original_layout(self) -> tuple:
        """Return (toolbars, panels) as previously captured; ([], []) if none."""
        toolbars = self._settings.value(self._key("original_layout", "toolbars"), [])
        panels = self._settings.value(self._key("original_layout", "panels"), [])
        return (toolbars or [], panels or [])

    def clear_original_layout(self) -> None:
        self._settings.remove(self._key("original_layout", "toolbars"))
        self._settings.remove(self._key("original_layout", "panels"))
        self._settings.sync()

    # ----------------------------------------------------- export dir memory

    def last_export_dir(self):
        return self._settings.value(self._key("import_export", "last_export_dir"))

    def set_last_export_dir(self, path: str) -> None:
        self._settings.setValue(self._key("import_export", "last_export_dir"), path)
        self._settings.sync()
