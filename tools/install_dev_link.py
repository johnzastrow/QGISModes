# -*- coding: utf-8 -*-
"""Install qgismodes into the active QGIS profile via a Windows junction.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\install_dev_link.py').read_text(),
        'install_dev_link.py', 'exec',
    ))

What it does (all idempotent):
  1. Locates the active QGIS profile's `python/plugins/` directory.
  2. Creates a junction `<plugins>/qgismodes` -> `<repo>/src/qgismodes/`
     (Windows junction, NO admin / Developer Mode required).
  3. Refreshes QGIS's plugin index so QGIS Modes appears as "Available".
  4. Persists the enable flag and starts the plugin in-process.
  5. Runs the Phase 1 verification block at the bottom of this file.

If the link already exists, it is left alone (edits in the repo propagate live).
"""

import os
import subprocess

from qgis.core import QgsApplication, QgsSettings
import qgis.utils


# --- Configure ---
REPO_PLUGIN_DIR = r"C:\Users\br8kw\Github\QGISModes\src\qgismodes"
PLUGIN_NAME = "qgismodes"


def _print_header(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


_print_header("Paths")

profile_dir = QgsApplication.qgisSettingsDirPath()
plugins_dir = os.path.normpath(os.path.join(profile_dir, "python", "plugins"))
link_path = os.path.join(plugins_dir, PLUGIN_NAME)

print(f"Profile dir:  {profile_dir}")
print(f"Plugins dir:  {plugins_dir}")
print(f"Repo source:  {REPO_PLUGIN_DIR}")
print(f"Link path:    {link_path}")


_print_header("1. Ensure plugins directory exists")

os.makedirs(plugins_dir, exist_ok=True)
print(f"OK: {plugins_dir}")


_print_header("2. Create junction (if not already present)")

if os.path.exists(link_path):
    if os.path.isdir(link_path):
        print(f"Already exists at {link_path}")
        print("(Leaving in place; edits in the repo propagate through.)")
    else:
        print(f"Path exists but isn't a directory: {link_path}")
else:
    if not os.path.isdir(REPO_PLUGIN_DIR):
        print(f"Source missing: {REPO_PLUGIN_DIR}")
        print("Fix REPO_PLUGIN_DIR at the top of this script and re-run.")
    else:
        # `mklink /J` creates a Windows junction; no admin required.
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", link_path, REPO_PLUGIN_DIR],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print(f"Created junction:\n  {link_path}\n  -> {REPO_PLUGIN_DIR}")
        else:
            print(f"FAILED to create junction (rc={result.returncode}).")
            print(f"  stdout: {result.stdout.strip()}")
            print(f"  stderr: {result.stderr.strip()}")


_print_header("3. Refresh QGIS's plugin index")

qgis.utils.updateAvailablePlugins()
print(f"Available plugins (count): {len(qgis.utils.available_plugins)}")
print(f"qgismodes available?       {PLUGIN_NAME in qgis.utils.available_plugins}")


_print_header("4. Enable + start the plugin")

QgsSettings().setValue(f"PythonPlugins/{PLUGIN_NAME}", True)

if PLUGIN_NAME in qgis.utils.plugins:
    print(f"{PLUGIN_NAME} already loaded; reloading via Plugin Reloader is recommended")
    print("for any code changes you've made since the last load.")
else:
    started = qgis.utils.startPlugin(PLUGIN_NAME)
    print(f"qgis.utils.startPlugin({PLUGIN_NAME!r}) returned: {started}")

print(f"qgismodes loaded?  {PLUGIN_NAME in qgis.utils.plugins}")


_print_header("5. Phase 1 verification")

if PLUGIN_NAME not in qgis.utils.plugins:
    print("Plugin failed to load. Check:")
    print("  - Log Messages -> Python tab (traceback)")
    print("  - Log Messages -> QGIS Modes tab (plugin's own log)")
    print("  - Plugins -> Manage and Install Plugins -> Installed (red-flagged?)")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    modes = qm.registry.available_modes()
    print(f"available_modes(): {len(modes)} mode(s)")
    for mid, meta, is_user in modes:
        print(f"  - id={mid!r}  name={meta.get('name')!r}  user={is_user}")

    default_path = qm.registry.get_path("default")
    print(f"get_path('default'): {default_path}")

    if default_path:
        config, errors = qm.loader.load(default_path)
        print(f"loader.load(...): config_loaded={config is not None}  errors={len(errors)}")
        for err in errors:
            print(f"  - {err.kind}: {err.message}")
        if config:
            print(f"  config.meta.id      = {config['meta'].get('id')!r}")
            print(f"  config.meta.schema  = {config['meta'].get('schema')!r}")
            print(f"  toolbars defined    = {list(config.get('toolbars', {}).keys())}")

    print(f"state_store.enabled(): {qm.state_store.enabled()}")
    print(f"state_store.active_mode_id(): {qm.state_store.active_mode_id()}")

    print()
    print("=" * 60)
    print("PHASE 1 VERIFICATION COMPLETE")
    print("=" * 60)
    print("If all of the above looks right, you're ready for Phase 2.")
