# -*- coding: utf-8 -*-
"""Stand-alone Phase 1 verification — runs the checks without doing the install.

Use after `install_dev_link.py`, or any time you've reloaded the plugin.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\verify_phase1.py').read_text(),
        'verify_phase1.py', 'exec',
    ))
"""

import qgis.utils

PLUGIN_NAME = "qgismodes"


print("=" * 60)
print("QGIS Modes — Phase 1 verification")
print("=" * 60)

if PLUGIN_NAME not in qgis.utils.plugins:
    print(f"{PLUGIN_NAME!r} is not loaded.")
    print(f"Available plugins includes {PLUGIN_NAME!r}? "
          f"{PLUGIN_NAME in qgis.utils.available_plugins}")
    print("If False -> run install_dev_link.py first.")
    print("If True  -> enable via Plugins -> Manage and Install Plugins -> Installed,")
    print("           or check Log Messages -> Python for a load-time traceback.")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    print()
    print("--- ModeRegistry ---")
    modes = qm.registry.available_modes()
    print(f"available_modes() -> {len(modes)} mode(s)")
    for mid, meta, is_user in modes:
        print(f"  id={mid!r}  name={meta.get('name')!r}  user={is_user}")

    print()
    print("--- ModeLoader (default mode) ---")
    default_path = qm.registry.get_path("default")
    print(f"get_path('default') -> {default_path}")
    if default_path:
        config, errors = qm.loader.load(default_path)
        print(f"loader.load(...) -> config_loaded={config is not None}, "
              f"errors={len(errors)}")
        for err in errors:
            print(f"  {err.kind}: {err.message}")
        if config:
            meta = config.get("meta", {})
            print(f"  meta.id     = {meta.get('id')!r}")
            print(f"  meta.name   = {meta.get('name')!r}")
            print(f"  meta.schema = {meta.get('schema')!r}")
            print(f"  toolbars    = {list(config.get('toolbars', {}).keys())}")
            print(f"  algorithms  = {list(config.get('algorithms', {}).keys())}")
            print(f"  panels      = {list(config.get('panels', {}).keys())}")

    print()
    print("--- StateStore ---")
    print(f"enabled()        -> {qm.state_store.enabled()}")
    print(f"active_mode_id() -> {qm.state_store.active_mode_id()}")

    print()
    print("--- TokenResolver (smoke check) ---")
    # Try resolving a couple of harmless tokens. These should succeed if
    # standard QGIS toolbars are present.
    for token in ("mFileToolBar:mActionNewProject", "separator", "section:Test"):
        items = qm.token_resolver.get_items(token)
        print(f"get_items({token!r}) -> {len(items)} object(s)")

    print()
    print("=" * 60)
    print("PHASE 1 VERIFICATION COMPLETE")
    print("=" * 60)
