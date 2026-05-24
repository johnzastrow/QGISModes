# -*- coding: utf-8 -*-
"""Phase 3a verification — inspect ShortcutManager registrations.

Read-only. After Plugin Reloader, this confirms that:
  * a ShortcutManager component is wired on the plugin,
  * one ``qgismodes_toggle`` QAction is registered,
  * one ``qgismodes_switch_<id>`` QAction is registered per installed mode,
  * each registered action is reachable through ``QgsGui.shortcutsManager()``
    so QGIS will show it under *Settings → Keyboard Shortcuts*.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\verify_phase3a.py').read_text(),
        'verify_phase3a.py', 'exec',
    ))
"""

from qgis.gui import QgsGui
from qgis.PyQt.QtWidgets import QAction
import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("QGIS Modes — Phase 3a state inspector")

if PLUGIN_NAME not in qgis.utils.plugins:
    print(f"{PLUGIN_NAME!r} is not loaded. Run install_dev_link.py first.")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    print()
    print("--- ShortcutManager wired? ---")
    sm = getattr(qm, "shortcuts", None)
    print(f"qm.shortcuts: {type(sm).__name__}")

    if sm is None:
        print()
        print("ShortcutManager not wired — Phase 3a not loaded; run Plugin Reloader.")
    else:
        print()
        print("--- Owned actions ---")
        print(f"toggle action object name: "
              f"{sm._toggle_action.objectName() if sm._toggle_action else None}")
        print(f"switch action ids:         {sorted(sm._switch_actions.keys())}")

        print()
        print("--- QGIS Modes shortcuts in QgsGui.shortcutsManager() ---")
        mgr = QgsGui.shortcutsManager()
        # listAll() returns every QObject (QAction/QShortcut) the manager knows.
        try:
            all_items = mgr.listAll()
        except Exception as e:  # noqa: BLE001
            print(f"listAll() failed: {e}")
            all_items = []

        found = []
        for item in all_items:
            try:
                name = item.objectName()
            except RuntimeError:
                continue  # dangling
            if name == "qgismodes_toggle" or name.startswith("qgismodes_switch_"):
                shortcut = ""
                try:
                    if isinstance(item, QAction):
                        shortcut = item.shortcut().toString()
                except Exception:  # noqa: BLE001
                    pass
                found.append((name, item.text() if hasattr(item, "text") else "",
                              shortcut))

        print(f"matching registrations: {len(found)}")
        for name, text, shortcut in sorted(found):
            sc_disp = shortcut if shortcut else "(unbound)"
            print(f"  {name:35s}  {sc_disp:20s}  {text!r}")

        # Sanity-cross-check against the registry
        print()
        print("--- Cross-check against registry ---")
        registry_ids = {mid for mid, _, _ in qm.registry.available_modes()}
        owned_ids = set(sm._switch_actions.keys())
        missing = registry_ids - owned_ids
        extra = owned_ids - registry_ids
        print(f"registry mode ids:  {sorted(registry_ids)}")
        print(f"owned switch ids:   {sorted(owned_ids)}")
        if missing:
            print(f"MISSING (in registry but no shortcut): {sorted(missing)}")
        if extra:
            print(f"EXTRA   (shortcut for unknown mode):   {sorted(extra)}")
        if not missing and not extra:
            print("registry and shortcuts are in sync.")

    print()
    _hdr("How to exercise Phase 3a")
    print("""
1. Open Settings -> Keyboard Shortcuts.
   -> Search 'QGIS Modes'. You should see:
        'QGIS Modes: toggle'
        'QGIS Modes: switch to <name>'   (one per installed mode)

2. Bind a key to one of them (e.g. Ctrl+Alt+Q on the toggle).

3. Close the dialog and press the key.
   -> The bound action should fire (toggle enter/exit, or switch mode).

4. Drop a second .json mode into
   %APPDATA%/QGIS/QGIS4/profiles/<profile>/qgismodes/modes/, then in the
   Python Console:
        qm = qgis.utils.plugins['qgismodes']
        qm.registry.refresh(); qm.shortcuts.refresh()
   -> Re-run this script: the new mode should appear in the shortcut list.
""")
