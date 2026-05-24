# -*- coding: utf-8 -*-
"""Diagnose missing-toolbar-icon problems for the qgismodes toggle.

Reports:
  * How many `mActionToggleQGISModes` QActions exist (>1 indicates a leftover
    from a previous re-import of the plugin).
  * Each action's parent, icon-null state, and icon file resolution.
  * Whether the icon file exists at the expected path.
  * What's currently in the QGIS file toolbar.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\diagnose_toolbar.py').read_text(),
        'diagnose_toolbar.py', 'exec',
    ))
"""

import os

from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print()
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("Plugin state")
qm = qgis.utils.plugins.get(PLUGIN_NAME)
print(f"plugin loaded:     {qm is not None}")
if qm is None:
    print("Not loaded — run install_dev_link.py.")
else:
    print(f"plugin_dir:        {qm.plugin_dir}")
    expected_icon = os.path.join(qm.plugin_dir, "icons", "qgismodes.svg")
    print(f"expected icon:     {expected_icon}")
    print(f"icon file exists:  {os.path.isfile(expected_icon)}")
    if os.path.isfile(expected_icon):
        size = os.path.getsize(expected_icon)
        print(f"icon file size:    {size} bytes")
        with open(expected_icon, "rb") as f:
            head = f.read(120)
        print(f"icon file head:    {head[:80]!r}")

    _hdr("Toggle QAction(s)")
    mw = qm.mainwindow
    actions = mw.findChildren(QAction, "mActionToggleQGISModes")
    print(f"count: {len(actions)}")
    for i, a in enumerate(actions):
        print()
        print(f"  [{i}] action {a!r}")
        try:
            print(f"      text         = {a.text()!r}")
            print(f"      tooltip      = {a.toolTip()!r}")
            print(f"      enabled      = {a.isEnabled()}")
            print(f"      visible      = {a.isVisible()}")
        except RuntimeError:
            print("      (action is dangling — Qt object deleted)")
            continue
        icon = a.icon()
        print(f"      icon.isNull()  = {icon.isNull()}")
        sizes = icon.availableSizes() if not icon.isNull() else []
        print(f"      icon.sizes     = {sizes}")
        # try to render a pixmap and check its size
        try:
            pm = icon.pixmap(QSize(32, 32))
            print(f"      pixmap 32x32  = {pm.width()}x{pm.height()}  null={pm.isNull()}")
        except Exception as e:  # noqa: BLE001
            print(f"      pixmap render error: {e}")
        # what container is it on?
        try:
            from qgis.PyQt.QtWidgets import QToolBar, QMenu
            containers = []
            for w in a.associatedObjects() if hasattr(a, "associatedObjects") else a.associatedWidgets():
                containers.append(f"{type(w).__name__}({w.objectName() or '<unnamed>'})")
            print(f"      containers   = {containers}")
        except Exception as e:  # noqa: BLE001
            print(f"      container lookup error: {e}")

    _hdr("Direct icon-load test (bypassing the action)")
    if os.path.isfile(expected_icon):
        test_icon = QIcon(expected_icon)
        print(f"QIcon(path).isNull() = {test_icon.isNull()}")
        if not test_icon.isNull():
            pm = test_icon.pixmap(QSize(32, 32))
            print(f"pixmap 32x32 = {pm.width()}x{pm.height()}  null={pm.isNull()}")

    _hdr("File toolbar contents")
    fb = qm.iface.fileToolBar()
    print(f"file toolbar object name: {fb.objectName()}")
    print(f"file toolbar visible:     {fb.isVisible()}")
    print(f"file toolbar action count: {len(fb.actions())}")
    for i, a in enumerate(fb.actions()):
        try:
            on = a.objectName() or "<unnamed>"
            txt = a.text() or "<no text>"
            null = a.icon().isNull()
            print(f"  [{i:>2}] {on:30s}  text={txt!r:25s}  iconNull={null}")
        except RuntimeError:
            print(f"  [{i:>2}] <dangling action>")
