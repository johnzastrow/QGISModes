# -*- coding: utf-8 -*-
"""Phase 3b verification — inspect UIWidgets installations.

Read-only. After Plugin Reloader, confirms that:
  * a UIWidgets component is wired on the plugin,
  * the ToggleSplitButton (QToolButton, objectName 'qgismodes_toggle_button')
    is on the QGIS file toolbar and uses qgismodes_toggle as its default
    action,
  * the dropdown lists one menu item per installed mode + Import/Export
    stubs,
  * a "QGIS Modes" top-level menu exists in the menu bar,
  * when simplified mode is active, the ExitControl
    (objectName 'mActionDisableQGISModes') is present on the primary
    toolbar; the InlineModeSwitcher appears only when ≥ 2 modes are
    installed.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\verify_phase3b.py').read_text(),
        'verify_phase3b.py', 'exec',
    ))
"""

from qgis.PyQt.QtWidgets import (
    QAction,
    QComboBox,
    QToolButton,
)
import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("QGIS Modes — Phase 3b state inspector")

if PLUGIN_NAME not in qgis.utils.plugins:
    print(f"{PLUGIN_NAME!r} is not loaded. Run install_dev_link.py first.")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    print()
    print("--- UIWidgets wired? ---")
    uw = getattr(qm, "uiwidgets", None)
    print(f"qm.uiwidgets: {type(uw).__name__}")
    print(f"lifecycle.uiwidgets is qm.uiwidgets: "
          f"{getattr(qm.lifecycle, 'uiwidgets', None) is uw}")

    if uw is None:
        print()
        print("UIWidgets not wired — Phase 3b not loaded; run Plugin Reloader.")
    else:
        mw = qm.mainwindow

        print()
        print("--- ToggleSplitButton on file toolbar ---")
        button = mw.findChild(QToolButton, "qgismodes_toggle_button")
        print(f"button found: {button is not None}")
        if button:
            default = button.defaultAction()
            print(f"default action: {default.objectName() if default else None!r}")
            print(f"popup mode:     {button.popupMode()!r}")
            print(f"icon null:      "
                  f"{button.icon().isNull() if button.icon() else 'no icon'}")
            menu = button.menu()
            if menu is not None:
                print(f"dropdown menu actions ({len(menu.actions())}):")
                for a in menu.actions():
                    label = a.text() if not a.isSeparator() else "<sep>"
                    mid = a.data() if not a.isSeparator() else None
                    check = "[x]" if a.isCheckable() and a.isChecked() else (
                        "[ ]" if a.isCheckable() else "   ")
                    extra = f"  data={mid!r}" if mid else ""
                    print(f"  {check} {label}{extra}")

        print()
        print("--- QGIS Modes menubar menu ---")
        menubar = mw.menuBar()
        found_menu = None
        for action in menubar.actions():
            sub = action.menu()
            if sub is not None and sub.objectName() == "qgismodes_main_menu":
                found_menu = sub
                break
        print(f"menubar menu found: {found_menu is not None}")
        if found_menu:
            print(f"entries ({len(found_menu.actions())}):")
            for a in found_menu.actions():
                label = a.text() if not a.isSeparator() else "<sep>"
                enabled = "" if a.isEnabled() else "  (disabled)"
                print(f"  - {label}{enabled}")

        print()
        print("--- Lifecycle state + injected widgets ---")
        applied = qm.lifecycle.is_currently_applied()
        print(f"is_currently_applied: {applied}")
        if applied:
            primary = qm.applier.primary_toolbar()
            print(f"primary toolbar: "
                  f"{primary.objectName() if primary else None}")
            if primary:
                names = [a.objectName() or a.text() for a in primary.actions()]
                print(f"primary toolbar entries ({len(names)}):")
                for n in names:
                    print(f"  - {n}")
                exit_act = primary.findChild(QAction, "mActionDisableQGISModes")
                print(f"ExitControl present: {exit_act is not None}")
                combo = primary.findChild(QComboBox, "qgismodes_inline_switcher")
                print(f"InlineModeSwitcher present: {combo is not None}")
                if combo:
                    print(f"  current index: {combo.currentIndex()}")
                    print(f"  current text:  {combo.currentText()!r}")
        else:
            print("(enter simplified mode then re-run to inspect injected UI)")

    print()
    _hdr("How to exercise Phase 3b")
    print("""
1. Look at the file toolbar — the bare 'QGIS Modes' action is replaced by
   a split button. The body has the QGIS Modes icon (clicks the toggle);
   the dropdown arrow lists installed modes + Import/Export stubs.

2. Look at the QGIS main menu bar — there should be a 'QGIS Modes' top-level
   menu with: Enter simplified mode | Import mode… | Import folder… |
   Export modes… | Manage modes… (disabled).

3. Click 'Import mode…' (either in dropdown or menu) — the message bar should
   say "Import mode — not yet implemented (Phase 3c)." That stub is the
   right hook for Phase 3c to repoint at ImportExportService.

4. Click the toggle to enter simplified mode. Re-run this script.
   -> primary toolbar should now have an ExitControl
      (objectName 'mActionDisableQGISModes') at its tail.
   -> InlineModeSwitcher (QComboBox) shows up ONLY when ≥ 2 modes are
      installed. With just 'default' you should see "InlineModeSwitcher
      present: False" — that's correct.

5. Click the exit (the QGIS Modes icon at the end of the toolbar) — returns
   to standard UI.

6. Drop a second mode .json into
   %APPDATA%/QGIS/QGIS4/profiles/<profile>/qgismodes/modes/, then:
        qm = qgis.utils.plugins['qgismodes']
        qm.registry.refresh()
        qm.shortcuts.refresh()
        qm.uiwidgets.refresh_mode_lists()
   Re-enter simplified mode — the InlineModeSwitcher should now appear and
   the dropdown should list both modes.
""")
