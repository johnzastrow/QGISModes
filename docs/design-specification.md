# QGIS Modes — Design Specification

| | |
| :-- | :-- |
| **Document** | Design Specification |
| **Project** | QGIS Modes |
| **Version** | 1.0 — baseline |
| **Date** | 2026-05-23 |
| **Status** | Baselined (tag `spec-v1.0`). Design frozen; changes require a change-note round. |
| **Baseline target** | Release 1.0 (MVP — Phases 1 & 2) |
| **Implements** | [`requirements.md`](requirements.md) v0.2 (baselined SRS) |
| **Companions** | [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md) (architectural narrative); [`customizing-qgis-light.md`](customizing-qgis-light.md) (inherited token-resolution mechanism) |

> This is **Stage 4** of the formal process. It complements
> `design-multi-mode-and-authoring.md` (which holds the architectural rationale)
> by specifying components, data models, sequence flows, and interface
> contracts. §10 is the **requirement-to-design traceability matrix**:
> every MVP-blocking requirement maps to the component(s) that implement it.

---

## 1. Introduction

### 1.1 Purpose

Specify the design that implements the baselined SRS for **Release 1.0 (MVP)**.
Post-MVP requirements (Designer, capture, menu rebuild, quick-run, provider
trimming) are referenced as stubs (§8) — designed only enough that the MVP
architecture doesn't foreclose them.

### 1.2 Document conventions

- **Component names** in `PascalCase`.
- Each major design element ends with a `*Realises:*` line listing the FR-IDs
  it covers; these feed §10.
- "MVP" = Release 1.0 (Phases 1 & 2). "Post-MVP" = v1.1+.
- File paths use Unix-style separators; the implementation uses `os.path.join`.

### 1.3 References

- SRS: [`requirements.md`](requirements.md)
- Architectural narrative: [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md)
- Inherited token-resolution mechanism: [`customizing-qgis-light.md`](customizing-qgis-light.md) §2.5–§2.6
- Mode-file schema: `src/qgismodes/schema/mode.schema.json`

---

## 2. System overview

QGIS Modes is a single QGIS Python plugin. `QGISModesPlugin` is QGIS's entry
point; it assembles **nine components**, each with one responsibility.

### 2.1 Component map

```
                       QGISModesPlugin   (entry point — §3.10)
                        ───────┬───────
                               │ assembles & wires:
       ┌───────────┬───────────┼───────────┬─────────────────┐
       │           │           │           │                 │
LifecycleCtrl  ImportExport  Shortcut    UIWidgets       (lifecycle of
   (§3.5)      Service (§3.7) Manager     (§3.9)         these is the
                              (§3.8)                     plugin itself)
       │           │
       │           └── uses ──► ModeRegistry (§3.1) ──► ModeLoader (§3.2)
       │                        └── lists modes ─┘
       │
       ├── uses ──► ModeApplier (§3.3) ──► TokenResolver (§3.4)
       │            └─ builds/tears down per-mode UI
       │
       └── uses ──► StateStore (§3.6) ──► QgsSettings under "qgismodes/"
```

### 2.2 Components at a glance

| Component | One-line responsibility |
|:--|:--|
| `ModeRegistry` | Discover installed modes; maintain in-memory list; user overrides bundled. |
| `ModeLoader` | Parse a mode file from disk and validate against the JSON Schema. |
| `ModeApplier` | Build a mode's UI in the QGIS main window; track plugin-owned toolbars; tear them down on switch. |
| `TokenResolver` | Resolve string tokens to live Qt objects (ported from QGIS Light). |
| `LifecycleController` | Orchestrate `enable` / `apply_mode` / `switch_mode` / `disable`; capture original layout once; restore on exit. |
| `StateStore` | All persistent state via `QgsSettings` under `qgismodes/`. |
| `ImportExportService` | Import (single / multiple / folder) and Export mode files; route conflicts and previews to UIWidgets. |
| `ShortcutManager` | Register one QAction per mode with QGIS shortcut manager; users bind keys in *Settings → Keyboard Shortcuts*. |
| `UIWidgets` | Build user-facing widgets and dialogs (see §7). |

Components communicate by direct method calls. The only Qt signals consumed are
`QAction.triggered` (UIWidgets → LifecycleController / ImportExportService) and
`mainwindow.initializationCompleted` (deferral on startup).

---

## 3. Component architecture

### 3.1 `ModeRegistry`

**Responsibility.** Discover, cache, and serve metadata for every installed mode.

**State.** An in-memory ordered dict keyed by `meta.id`, value
`(meta, source_path, is_user_mode)`. Rebuilt on `refresh()`.

**Discovery algorithm.**
1. List `<plugin>/modes/*.json` (bundled).
2. List `<profile>/qgismodes/modes/*.json` (user). Create the dir if absent.
3. For each, call `ModeLoader.load()`.
4. Valid entries are added; **user entries shadow bundled entries** with the
   same `meta.id` (FR-MS-3).
5. Invalid files are skipped; the loader's diagnostics are forwarded to the
   QGIS Modes log tab (FR-MF-5, FR-GR-5).
6. **First-run seeding (FR-MS-5):** if the user dir is empty when first
   created, copy every bundled mode into it.

**Public API.**
```
available_modes() -> list[(id: str, meta: dict, is_user_mode: bool)]
get_metadata(id) -> dict | None
get_path(id) -> str | None
refresh() -> int                # returns count of valid modes loaded
is_user_mode(id) -> bool
```

*Realises:* FR-MS-1, FR-MS-2, FR-MS-3, FR-MS-4, FR-MS-5.

### 3.2 `ModeLoader`

**Responsibility.** Parse a single mode file from disk and validate it against
`mode.schema.json`.

**Public API.**
```
load(path) -> tuple[config_dict | None, list[Error]]
validate(config_dict) -> list[Error]      # used standalone for import-time validation
```

**Behaviour.**
- Catches `json.JSONDecodeError` → returns `(None, [ParseError(msg)])`.
- Validates against the schema using the `jsonschema` library if available;
  otherwise falls back to a minimal hand-rolled validator covering
  `meta.{id, name, schema}` and top-level section types (FR-MF-2, FR-MF-4).
- Checks `meta.schema` ≤ `SUPPORTED_SCHEMA` (module constant, currently `1`).
  Higher → returns `[VersionError(...)]` (FR-MF-6, FR-MS-8).
- Returns the config dict unchanged on success.

*Realises:* FR-MF-1, FR-MF-2, FR-MF-4, FR-MF-5, FR-MF-6, FR-MS-8 (forward-compat
diagnostic).

### 3.3 `ModeApplier`

**Responsibility.** Take a validated mode config and apply it to the QGIS main
window. Track plugin-owned toolbars so `apply_mode()` can tear down exactly
what *this plugin* created — never QGIS's own toolbars or borrowed `QAction`s
(FR-UI-8).

**State.** `self._owned_toolbars: list[QToolBar]` — toolbars this plugin
created. Cleared by `teardown_owned_toolbars()`.

**Public API.**
```
apply(config_dict) -> None
teardown_owned_toolbars() -> None
```

**`apply()` algorithm.**
1. For each `(name, spec)` in `config["toolbars"]`:
   - Create a `QToolBar(spec["title"], mainwindow)` with `objectName=name`,
     `setFloatable(False)`, `setMovable(False)`,
     `toggleViewAction().setDisabled(True)`.
   - `mainwindow.addToolBar(area_enum(spec["area"]), toolbar)`.
   - `TokenResolver.add_items(toolbar, spec["items"])`.
   - Append to `self._owned_toolbars`.
   - `toolbar.show()`.
2. Apply `config["panels"]` per the rules in `customizing-qgis-light.md` §3.3
   (hide unlisted, position listed per `<state>:<area>`).
3. Apply `config["statusbar"]`: hide each listed widget whose value is `false`.
4. Delegate to `UIWidgets` to inject the `ExitControl` and (if ≥ 2 modes)
   `InlineModeSwitcher` into the active mode's main toolbar.

**`teardown_owned_toolbars()` algorithm.**
1. For each `toolbar in self._owned_toolbars`:
   - `mainwindow.removeToolBar(toolbar)`.
   - `toolbar.deleteLater()` — **only the toolbar widget**, never any borrowed
     `QAction` (FR-UI-8).
2. Clear the list.

*Realises:* FR-UI-1, FR-UI-5, FR-UI-7, FR-UI-8.

### 3.4 `TokenResolver`

**Responsibility.** Resolve a token string to one or more live Qt objects;
recursively place items into a parent widget (toolbar or menu).

**Behaviour.** Ported from QGIS Light (see `customizing-qgis-light.md`
§2.5–§2.6). Honours all existing token forms:
- `parent:identifier` (with optional `*` wildcard)
- `parent:` (empty identifier → all actions of parent)
- `separator`, `section:Label`
- `algorithms:<group>`
- Processing-algorithm ids (e.g. `native:buffer`)
- `mActionDisableQGISModes` — synthetic exit action (renamed from QGIS Light's
  `mActionDisableQGISLight`).
- Nested JSON arrays → grouped dropdown buttons (first item shown by default;
  last-used promoted).

**Public API.**
```
get_items(token, parent_for_actions) -> list[QObject]
add_items(parent_widget, items_list) -> None
find_action(widget, identifier) -> QAction | None       # internal helper
```

**Token-failure policy.** A token that fails to resolve is **skipped** with a
warning naming the token (FR-UI-6, FR-GR-5). Interface construction continues.

*Realises:* FR-UI-2, FR-UI-3, FR-UI-4, FR-UI-6.

### 3.5 `LifecycleController`

**Responsibility.** Orchestrate the enter/apply/exit lifecycle. The crucial
split: **capture-original-layout runs once, applying-a-mode runs on every
switch** (see `design-multi-mode-and-authoring.md` §A.4).

**State machine.**

```
   ┌──────────────────────────────────────────┐
   │                                           │
   ▼               enable(id)                  │
Disabled  ───────────────────────────►  Enabled(id)
   ▲                                           │  switch_mode(other_id)
   │              disable()                    │  ─────────────────────► Enabled(other_id)
   └──────────────────────────────────────────┘
```

**Public API.**
```
enable(mode_id: str = None) -> None
apply_mode(mode_id: str) -> None
switch_mode(mode_id: str) -> None
disable() -> None
is_enabled() -> bool
active_mode_id() -> str | None
```

**`enable(mode_id)` algorithm.**
1. If `is_enabled()`: degrade to `switch_mode(mode_id or active_mode_id())`.
2. Capture the original layout via `StateStore.save_original_layout(...)`
   (FR-LC-2). **Runs once.**
3. Save current context-menu policy; set
   `mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)`
   (FR-LC-9).
4. Hide the menu bar.
5. Hide every standard `QToolBar` direct-child of main window (FR-UI-7).
6. Hide every `QDockWidget` not listed in the target mode's config
   (final positioning done in `apply_mode`).
7. `apply_mode(mode_id or default_mode_id())`.
8. `StateStore.set_enabled(True)`.

**`apply_mode(mode_id)` algorithm** — safe whether transitioning from
`Disabled→Enabled` (first time, called by `enable`) **or** from
`Enabled(A)→Enabled(B)` (a switch). **Does not touch the captured original
layout** (FR-LC-7).
1. `path = ModeRegistry.get_path(mode_id)`; `config, errors = ModeLoader.load(path)`.
2. If errors: log; fall back to last-known-good mode (preferably the previous
   mode, else `default`); push a message-bar warning (FR-GR-4). Recurse with
   the fallback id, OR `disable()` if no good mode exists.
3. `ModeApplier.teardown_owned_toolbars()`.
4. `ModeApplier.apply(config)`.
5. `StateStore.set_active_mode_id(mode_id)`.

**`switch_mode(mode_id)` algorithm.**
- `assert is_enabled()`; calls `apply_mode(mode_id)`. Distinct method for
  semantic clarity (used by UI + shortcut handlers).

**`disable()` algorithm.**
1. `ModeApplier.teardown_owned_toolbars()`.
2. Restore the captured original layout via StateStore (FR-LC-4).
3. Show the menu bar; restore previous context-menu policy.
4. `StateStore.set_enabled(False)`. **Leave `qgismodes/mode` set** — re-entry
   picks the same mode.

**Startup path** — called from `QGISModesPlugin.initGui()`:
- If `StateStore.enabled()`: connect `mainwindow.initializationCompleted` →
  `enable(active_mode_id())` (FR-LC-6).
- Else: do nothing.

*Realises:* FR-LC-1, FR-LC-2, FR-LC-3, FR-LC-4, FR-LC-5, FR-LC-6, FR-LC-7,
FR-LC-8, FR-LC-9, FR-SW-2, FR-SW-3, FR-GR-3, FR-GR-4.

### 3.6 `StateStore`

**Responsibility.** All persistent-state I/O. Centralises QgsSettings access
so other components don't speak the key strings directly.

**Settings keys** (all under `qgismodes/`):

| Key | Type | Purpose |
|:--|:--|:--|
| `qgismodes/enabled` | string ("true" / absent) | Whether simplified mode is active |
| `qgismodes/mode` | string | Active mode id (preserved across `disable()`) |
| `qgismodes/original_layout/toolbars` | list[dict] | Captured original toolbar state |
| `qgismodes/original_layout/panels` | list[dict] | Captured original panel state |
| `qgismodes/import_export/last_export_dir` | string | Most-recent export directory (per-session UX) |

**Captured-layout shapes** (see also §4.3):

`toolbars` entry: `{"name": str, "area": int, "hidden": bool}`
`panels` entry: `{"name": str, "area": int, "features": int, "hidden": bool, "floating": bool}`

Qt enum values stored as ints for forward compatibility. The Qt5 / Qt6 shim
`toEnum()` (carried over from QGIS Light) converts on read.

**Public API.**
```
enabled() -> bool
set_enabled(value: bool) -> None
active_mode_id() -> str | None
set_active_mode_id(id: str) -> None
save_original_layout(toolbars, panels) -> None
original_layout() -> tuple[list[dict], list[dict]]
last_export_dir() -> str | None
set_last_export_dir(path: str) -> None
```

*Realises:* FR-PS-1, FR-PS-2, FR-LC-2, FR-LC-4, FR-LC-5, FR-SW-3.

### 3.7 `ImportExportService`

**Responsibility.** Handle Import and Export commands end-to-end; coordinate
with UIWidgets for the conflict and preview dialogs.

**Public API.**
```
import_files(paths: list[str]) -> ImportSummary
import_directory(path: str) -> ImportSummary
export_modes(ids: list[str], dest_dir: str) -> ExportSummary
```

Where:
- `ImportSummary = (imported: list[id], skipped: list[(path, reason)])`
- `ExportSummary = (written: list[path], errors: list[(id, reason)])`

**Import algorithm** (per file in the batch):
1. `config, errors = ModeLoader.load(path)`. If errors → record in `skipped`, continue.
2. If `config["meta"].get("requires")` is non-empty:
   show `UIWidgets.RequiresPreviewDialog`. On *Cancel* → record in `skipped` and continue.
3. If a user mode with the same `meta.id` already exists:
   show `UIWidgets.ConflictDialog` *(Overwrite / Keep both / Cancel,
   plus "Apply to all remaining" checkbox once ≥ 2 conflicts remain in the
   batch)*. The chosen action:
   - **Overwrite** → write to `<user>/qgismodes/modes/<id>.json`.
   - **Keep both** → write to `<user>/qgismodes/modes/<id>-N.json` (N = lowest
     free integer); rewrite `config["meta"]["id"]` to match the new stem so the
     in-file id matches the filename.
   - **Cancel** → record in `skipped`, continue.
4. Write the file to user modes dir (always named `<meta.id>.json`).
5. After the entire batch:
   - `ModeRegistry.refresh()`
   - `ShortcutManager.refresh()`
   - Push `ImportSummary` to the message bar
     (e.g. *"3 imported, 1 skipped"*).

**Export algorithm** (per id):
1. `path = ModeRegistry.get_path(id)`; load the file's content.
2. Write to `<dest_dir>/<meta.id>.json`. **Preserve exact file content** — do
   not re-serialise stylistically (round-trip fidelity for shared modes).
3. `StateStore.set_last_export_dir(dest_dir)` after the first file.

*Realises:* FR-MS-7a, FR-MS-7b, FR-MS-9, FR-MS-10.

### 3.8 `ShortcutManager`

**Responsibility.** Register one QAction per installed mode (plus one for the
global toggle) with QGIS's keyboard-shortcut system, so users can bind keys in
*Settings → Keyboard Shortcuts*.

**Behaviour.**
- On startup and after every `ModeRegistry.refresh()`, sync registered actions:
  - For each installed mode, ensure a QAction named `qgismodes_switch_<id>`
    exists with text `"QGIS Modes: switch to <name>"` and is registered via
    `QgsGui.shortcutsManager().registerAction(action, "")`. **Empty default
    shortcut** (FR-SW-7) — users bind keys themselves.
  - Triggering a switch action calls
    `LifecycleController.switch_mode(id)` (or `enable(id)` if not enabled).
  - For removed modes, unregister + delete the action.
- One additional QAction `qgismodes_toggle` exists for enter/exit (the
  ToggleSplitButton's default action; just ensure it's also registered with the
  shortcut manager).

**Public API.**
```
refresh() -> None          # called by plugin and by ImportExportService
unregister_all() -> None   # called from QGISModesPlugin.unload()
```

*Realises:* FR-SW-7.

### 3.9 `UIWidgets`

**Responsibility.** Build user-facing widgets and dialogs. See §7 for the full
UI design with mockups.

**Components produced** (see §7 for details):
- `ToggleSplitButton` — entry/exit toggle in the QGIS file toolbar; dropdown
  with modes + *Import…* / *Export…*.
- `InlineModeSwitcher` — small dropdown injected into the active mode's main
  toolbar while simplified (FR-GR-2).
- `ImportExportMenu` — top-level QGIS Modes menu in the QGIS menu bar
  (per **D**ecision 2 in agenda ④: import/export commands live in **both**
  the menu and the toggle dropdown).
- `ConflictDialog` — modal Overwrite / Keep both / Cancel + Apply-to-all.
- `RequiresPreviewDialog` — modal listing `meta.requires` + install status.
- `ExitControl` — runtime-injected button calling
  `LifecycleController.disable()` (FR-GR-1).

*Realises:* FR-SW-1, FR-SW-4, FR-SW-5, FR-SW-6, FR-GR-1, FR-GR-2, FR-GR-3.

### 3.10 `QGISModesPlugin` (entry point)

**Responsibility.** QGIS-side entry/exit; assemble components; connect signals.

**Lifecycle methods.**
- `__init__(iface)` — instantiate components, wire dependencies, build the
  ModeRegistry (one initial `refresh()`).
- `initGui()` — create the `ToggleSplitButton` (file toolbar) and the
  `ImportExportMenu` (menu bar); `ShortcutManager.refresh()`; if
  `StateStore.enabled()` is true, connect `mainwindow.initializationCompleted`
  to `LifecycleController.enable(StateStore.active_mode_id())`.
- `unload()` — `LifecycleController.disable()` if currently enabled;
  `ShortcutManager.unregister_all()`; remove the toggle button and the menu.

*Realises:* FR-LC-8; supports NFR-REL-3 (clean unload).

---

## 4. Data models

### 4.1 Mode file

Formally defined by `src/qgismodes/schema/mode.schema.json` (JSON Schema
draft-07). Top level: `meta` + four section sub-objects.

Sections recognised by v1.0 (FR-MF-3): `toolbars`, `algorithms`, `panels`,
`statusbar`. Provider policy is **global, not per-mode** (FR-MF-7) — the
schema has no per-mode `providers` section.

`meta` block (required: `id`, `name`, `schema`):

| Field | Type | Required | Notes |
|:--|:--|:--|:--|
| `id` | string (`^[a-z0-9-]+$`) | ✓ | Stable slug; also the filename `<id>.json` |
| `name` | string | ✓ | Human label in mode picker |
| `description` | string | | |
| `icon` | string | | Qt resource path or file path |
| `version` | string | | Mode-author's version of the mode (free-form) |
| `author` | string | | Optional, useful for shared modes (added in agenda ③) |
| `schema` | integer ≥ 1 | ✓ | Config-format version (currently `1`) |
| `requires` | list[string] | | QGIS plugins this mode references (preview on import, FR-MS-10) |

Token vocabulary inside `toolbars` and `algorithms` is detailed in
`customizing-qgis-light.md` §2.5.

### 4.2 Persistent state (QgsSettings)

See §3.6 StateStore for the key table and shapes.

### 4.3 Captured layout snapshot

```python
CapturedLayout = {
    "toolbars": [
        {"name": str, "area": int, "hidden": bool},
        ...
    ],
    "panels": [
        {"name": str, "area": int, "features": int, "hidden": bool, "floating": bool},
        ...
    ],
}
```

Stored as two separate QgsSettings entries
(`qgismodes/original_layout/toolbars`, `qgismodes/original_layout/panels`),
since QgsSettings cannot natively serialise a deeply nested dict.

`area` and `features` are integer values of the corresponding Qt enums;
`toEnum()` shim converts them back on read.

---

## 5. Sequence flows

Tight ladder format. Each step lists *Component.method* and key effects.

### 5.1 UC-1 — First-time enter

```
1. User clicks ToggleSplitButton
2. QGISModesPlugin → LifecycleController.enable(default_id)
3. LifecycleController:
     a. !is_enabled():
        StateStore.save_original_layout(snapshot of toolbars + panels)
     b. save prev contextMenuPolicy
        mainwindow.setContextMenuPolicy(NoContextMenu)
        mainwindow.menuBar().hide()
     c. hide all standard toolbars; hide all docks not in target mode
     d. apply_mode(default_id)
4. apply_mode:
     a. ModeLoader.load(default_path) → config
     b. ModeApplier.teardown_owned_toolbars()  (no-op first time)
     c. ModeApplier.apply(config)              (TokenResolver does the work)
     d. UIWidgets.inject(ExitControl, InlineModeSwitcher) into top toolbar
     e. StateStore.set_active_mode_id(default_id)
5. StateStore.set_enabled(True)
```

*Realises:* FR-LC-1, FR-LC-2, FR-LC-9, FR-UI-1, FR-UI-7, FR-GR-1, FR-MS-1.

### 5.2 UC-2 — Switch modes mid-session

```
1. User picks mode B from InlineModeSwitcher
2. → LifecycleController.switch_mode("B")
3. switch_mode → apply_mode("B"):
     a. ModeLoader.load(path_for("B")) → config
        (failure → fall back to previous mode; UC-5 path)
     b. ModeApplier.teardown_owned_toolbars()
     c. ModeApplier.apply(config)
        — does NOT touch standard QGIS toolbars/panels
        — does NOT touch captured original layout
     d. StateStore.set_active_mode_id("B")
```

*Realises:* FR-SW-1, FR-SW-2, FR-SW-3, FR-SW-5, FR-UI-8, FR-LC-7, FR-PP-2.

### 5.3 UC-3 — Exit

```
1. User clicks ExitControl
2. → LifecycleController.disable():
     a. ModeApplier.teardown_owned_toolbars()
     b. Restore captured original layout:
        for each saved toolbar: addToolBar(area, toolbar); show/hide as captured
        for each saved panel:   addDockWidget(area, panel); set features; show/hide
     c. mainwindow.menuBar().show()
        mainwindow.setContextMenuPolicy(prev policy)
     d. StateStore.set_enabled(False)
        # qgismodes/mode is left in place so re-entry picks the same mode
```

*Realises:* FR-LC-3, FR-LC-4, FR-LC-9, FR-GR-1.

### 5.4 UC-6 — Restart while simplified

```
1. QGIS startup → classFactory → QGISModesPlugin.__init__()
   → ModeRegistry.refresh()  (load all mode files)
2. QGIS calls QGISModesPlugin.initGui():
     a. Build ToggleSplitButton + ImportExportMenu
     b. ShortcutManager.refresh()    (register per-mode actions)
     c. StateStore.enabled() == True:
        connect mainwindow.initializationCompleted
        → LifecycleController.enable(StateStore.active_mode_id())
3. Other plugins load (QuickMapServices, DataPlotly, …) → main window
   emits initializationCompleted
4. enable(...) runs (as in UC-1; save_original_layout would re-run but
   the !is_enabled() guard is true on first call so it does run; subsequent
   re-entries during the same QGIS session preserve the original layout)
```

*Realises:* FR-LC-5, FR-LC-6, FR-SW-3.

### 5.5 UC-8 — Import a single mode (with conflict + requires preview)

```
1. User → ImportExportMenu → "Import mode…"
2. File picker → user selects path
3. → ImportExportService.import_files([path]):
     a. ModeLoader.load(path) → (config, errors)
        if errors: skipped += [(path, errors)]; continue
     b. config.meta.requires non-empty?
        UIWidgets.RequiresPreviewDialog(requires, install_status)
        if Cancel: skipped += [(path, "user cancelled at preview")]; continue
     c. user-mode with same meta.id exists?
        UIWidgets.ConflictDialog(id)
          → Overwrite: target = <user>/qgismodes/modes/<id>.json
          → Keep both: target = <user>/qgismodes/modes/<id>-N.json
                       (N = smallest free); rewrite config.meta.id
          → Cancel:    skipped += ...; continue
     d. write file to target (preserves original content for Overwrite/no-rename;
        re-serialises only when id is rewritten)
     e. imported += [id]
4. After batch:
     a. ModeRegistry.refresh()
     b. ShortcutManager.refresh()
     c. Push ImportSummary to message bar
```

*Realises:* FR-MS-7a, FR-MS-9, FR-MS-10.

---

## 6. Interface contracts

### 6.1 External (QGIS-facing)

| Interface | Implementation |
|:--|:--|
| `classFactory(iface)` | `src/qgismodes/__init__.py` |
| `QGISModesPlugin.initGui()` | §3.10 |
| `QGISModesPlugin.unload()` | §3.10 |
| Signal `mainwindow.initializationCompleted` | Connected in `initGui` when `StateStore.enabled()` is true (§3.5 startup path) |
| `QgsGui.shortcutsManager()` | Used by `ShortcutManager` (§3.8) |

### 6.2 File system

| Path | Purpose | R/W |
|:--|:--|:--|
| `<plugin>/modes/*.json` | Bundled modes | R |
| `<profile>/qgismodes/modes/*.json` | User modes | R + W |
| `<plugin>/schema/mode.schema.json` | Validation schema | R |

### 6.3 Settings keys

See §3.6 table.

### 6.4 Internal (between components)

Each component's public API is listed in §3. Components communicate by direct
method calls (no signal/slot pubsub in MVP). The only Qt signals consumed are
`QAction.triggered` (UIWidgets → LifecycleController / ImportExportService) and
`mainwindow.initializationCompleted` (deferral).

---

## 7. UI design

### 7.1 `ToggleSplitButton` (file toolbar)

A `QToolButton` in `MenuButtonPopup` mode. Always present in the QGIS file
toolbar (added by `initGui`).

```
┌────────────────────┐
│ [QGIS Modes  ▾]    │  ← clicking the button toggles enter/exit
└────────────────────┘     clicking ▾ opens the dropdown:
                            ┌───────────────────────┐
                            │ ○ default              │  ← list of modes;
                            │ ● raster-analysis      │     dot indicates active
                            │ ○ vector-editing       │
                            │ ──────────────────────│
                            │ Import mode…           │
                            │ Import folder…         │
                            │ Export modes…          │
                            └───────────────────────┘
```

- Body click while *standard* UI shown → `LifecycleController.enable(active_or_default_id())`.
- Body click while *simplified* UI shown → `LifecycleController.disable()`.
- Dropdown mode item → `LifecycleController.switch_mode(id)` (or `enable(id)` if not enabled).
- Dropdown Import/Export → `ImportExportService` flow.

### 7.2 `ImportExportMenu` (QGIS menu bar)

When standard UI is shown, a top-level *"QGIS Modes"* menu appears:

```
QGIS Modes
├── Enter simplified mode
├── ──────────────────────
├── Import mode…
├── Import folder…
├── Export modes…
└── ──────────────────────
└── Manage modes…           (placeholder; reserved for v1.1)
```

When the simplified UI is shown the menu bar is hidden (FR-UI-7); the
`InlineModeSwitcher` and `ExitControl` take over.

*Per Decision 2 in agenda ④: Import/Export commands live in BOTH the menu and
the toggle dropdown. We may remove from the dropdown in a later release if
discoverability surveys prefer the menu.*

### 7.3 `InlineModeSwitcher` (in simplified toolbar)

A small `QComboBox` widget injected into the active mode's main toolbar (or
the first eligible toolbar). Lists every installed mode by `meta.name`;
current mode is the selected item.

```
[mode-icon  ▾ raster-analysis        ]
```

Selection change → `LifecycleController.switch_mode(id)`.

Always present when ≥ 2 modes are installed (FR-GR-2).

### 7.4 `ExitControl`

A `QAction` with the QGIS Modes icon, injected into the active mode's main
toolbar. Object name `mActionDisableQGISModes`. Triggers
`LifecycleController.disable()`.

Always injected, regardless of mode-file content (FR-GR-3).

### 7.5 `ConflictDialog`

```
┌──────────────────────────────────────────────┐
│ Mode already exists                          │
├──────────────────────────────────────────────┤
│ A mode with id "raster-analysis" is already  │
│ installed in your user modes folder.         │
│                                              │
│ ☐ Apply to all remaining conflicts (3 left)  │
│                                              │
│           [Overwrite] [Keep both] [Cancel]   │
└──────────────────────────────────────────────┘
```

- *Apply to all remaining* is offered only when ≥ 2 conflicts remain in the
  batch. Ticking it pins the chosen action for the rest of the batch (no
  further prompts).
- Uses `QDialogButtonBox` for OS-appropriate button order (NFR-USA-3).

### 7.6 `RequiresPreviewDialog`

```
┌────────────────────────────────────────────────┐
│ This mode requires:                            │
├────────────────────────────────────────────────┤
│  ✓ QuickMapServices  (installed)               │
│  ✗ DataPlotly        (not installed)           │
│                                                │
│ Tools referenced by this mode that depend on   │
│ missing plugins will not appear until those    │
│ plugins are installed.                         │
│                                                │
│                          [Cancel]  [Import]    │
└────────────────────────────────────────────────┘
```

Importing proceeds regardless (NFR-SEC-2 — mode files are data only); the
dialog is informational so the user can decline before installing.

### 7.7 Keyboard shortcuts

No default bindings (FR-SW-7). Actions appear in
*Settings → Keyboard Shortcuts* with these names:

- *"QGIS Modes: toggle"* — the global enter/exit.
- *"QGIS Modes: switch to <mode-name>"* — one per installed mode.

`ShortcutManager.refresh()` keeps the registered set in sync as modes are
imported / exported / removed.

### 7.8 Context-menu policy

In `LifecycleController.enable()` step (b):
```python
self._prev_ctxmenu_policy = mainwindow.contextMenuPolicy()
mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
```
Restored in `disable()`:
```python
mainwindow.setContextMenuPolicy(self._prev_ctxmenu_policy)
```

*Realises:* FR-LC-9.

---

## 8. Post-MVP design stubs

Each item is referenced here so the MVP design doesn't foreclose it.

| ID | Architectural reference | One-line plan |
|:--|:--|:--|
| **FR-UI-9** (menu rebuild) | A.3 / B.6 | New `MenuBarBuilder` component, parallel to `ModeApplier`, consuming a new `menus` mode-file section. Schema bump to v2. |
| **FR-UI-10** (quick-run) | new | New `QuickRunSearch` widget: fuzzy match across all `QAction`s reachable from the main window; invoke on click. |
| **FR-CP-1** (capture current profile) | B.4 | New `UICapture` component implementing the "Pick from QGIS" mechanism scoped to the current profile. |
| **FR-CP-2** (capture another profile) | B.4 | Extension of `UICapture` to enumerate sibling directories under `QgsApplication.qgisSettingsDirPath()/..`. |
| **FR-DS-*** (Visual Mode Designer) | Part B | Heavyweight `QDialog` per the existing design — palette + canvas + drag-drop + round-trip. |
| **FR-PP-*** (provider trimming) | A.5 | New `ProviderTrimmer` component running once at first `enable()`. Per D2 deferred to v1.1+ as a per-installation toggle. |

None of these require changing the MVP component boundaries — each is an
addition.

---

## 9. How the design satisfies non-functional requirements

| NFR | Design choice |
|:--|:--|
| **NFR-CMP-1** (QGIS 3.44+ / 4.x) | Plain QGIS Python plugin; `metadata.txt qgisMinimumVersion=3.44`. |
| **NFR-CMP-2** (Qt5 + Qt6) | Fully-scoped enum names throughout; `associatedObjects()` and `toEnum()` shims carried over from QGIS Light. |
| **NFR-CMP-3** (cross-platform) | No platform-specific code; file paths via `os.path.join` and `QgsApplication.qgisSettingsDirPath()`. |
| **NFR-CMP-4** (`qgisMaximumVersion=4.99`) | Set in `metadata.txt`. |
| **NFR-PRF-1** (switch < 1 s) | `apply_mode()` only rebuilds plugin-owned toolbars (O(N_toolbars in mode)); panel positioning is O(N_panels). No I/O on the hot path other than reading the mode file (small). |
| **NFR-PRF-2** (< 200 ms startup) | `__init__` performs only a modes-dir scan (small); `initGui` adds a button and a menu. Heavy work (token resolution, toolbar build) runs only on `enable()`. |
| **NFR-USA-1 / 2** (no dead-ends) | `ExitControl` always injected (FR-GR-1, §7.4); `InlineModeSwitcher` always present when ≥ 2 modes (FR-GR-2, §7.3); both runtime-injected and independent of mode-file content (FR-GR-3). |
| **NFR-USA-3** (HIG) | `QDialogButtonBox` in dialogs; group boxes; minimal text; mode picker uses real icons + labels. |
| **NFR-USA-4** (diagnostics in Log Messages tab) | All components route via `plugin.log()` to the "QGIS Modes" tab; user-facing notices via `plugin.message()`. |
| **NFR-REL-1** (never crash QGIS) | Every component public method catches and logs; ModeLoader returns errors as data, not exceptions. |
| **NFR-REL-2** (full restore on exit) | Captured layout fully roundtrips toolbar `(name, area, hidden)` and panel `(name, area, features, hidden, floating)`. |
| **NFR-REL-3** (clean unload) | `QGISModesPlugin.unload()` → `disable()` → restored standard UI → `ShortcutManager.unregister_all()` → remove toggle and menu. |
| **NFR-REL-4** (no leaks under cycling) | `_owned_toolbars` cleared each switch; `deleteLater()` on plugin-created widgets only; no borrowed `QAction`s touched. |
| **NFR-MNT-1** (no code change to customise) | Mode files are JSON; schema is the only authoring surface. |
| **NFR-MNT-2** (PEP 8 / Flake8 clean) | Implementation concern; structure (small components, single responsibility) keeps modules tractable. |
| **NFR-MNT-3** (docstrings on public API) | Every component public method here has a counterpart docstring expectation. |
| **NFR-MNT-4** (versioned schema) | `meta.schema` integer; `SUPPORTED_SCHEMA` constant in `ModeLoader`. |
| **NFR-SEC-1** (Bandit / detect-secrets clean) | Implementation concern; no `eval`/`exec`/`subprocess`/network in this design. |
| **NFR-SEC-2** (mode files are data) | `ModeLoader` uses `json.loads()` only. |
| **NFR-SEC-3** (no hardcoded secrets, no undisclosed network) | Design has no network I/O. |
| **NFR-PKG-1..6** | Implementation concern (`metadata.txt`, `LICENSE`, no binaries, etc.); design imposes no obstacle. |

---

## 10. Traceability matrix

Every **Must (M)** requirement → component(s) that implement it.

| Requirement | Implemented by |
|:--|:--|
| FR-MF-1 (one JSON per mode) | ModeLoader §3.2 |
| FR-MF-2 (`meta` block) | ModeLoader §3.2 + schema §4.1 |
| FR-MF-3 (sections) | ModeApplier §3.3 + schema §4.1 |
| FR-MF-4 (schema validation) | ModeLoader §3.2 |
| FR-MF-5 (invalid file skipped) | ModeLoader §3.2 + ModeRegistry §3.1 |
| FR-MF-6 (schema version) | ModeLoader §3.2 |
| FR-MF-7 (provider policy not per-mode) | Schema §4.1 (no `providers` section) |
| FR-MS-1 (bundled modes) | ModeRegistry §3.1 |
| FR-MS-2 (user modes) | ModeRegistry §3.1 |
| FR-MS-3 (user shadows bundled) | ModeRegistry §3.1 |
| FR-MS-4 (user modes survive upgrade) | ModeRegistry §3.1 (user dir outside plugin) |
| FR-MS-7a (Import command) | ImportExportService §3.7 + UIWidgets ImportExportMenu §7.2 + ToggleSplitButton §7.1 |
| FR-MS-7b (Export command) | ImportExportService §3.7 |
| FR-MS-9 (conflict dialog) | ImportExportService §3.7 + UIWidgets ConflictDialog §7.5 |
| FR-MS-10 (requires preview) | ImportExportService §3.7 + UIWidgets RequiresPreviewDialog §7.6 |
| FR-LC-1 (enter command) | LifecycleController.enable §3.5; UIWidgets ToggleSplitButton §7.1 |
| FR-LC-2 (capture original layout) | LifecycleController.enable step (a); StateStore §3.6 |
| FR-LC-3 (exit command) | LifecycleController.disable §3.5; UIWidgets ExitControl §7.4 |
| FR-LC-4 (restore original layout) | LifecycleController.disable step (b); StateStore §3.6 |
| FR-LC-5 (state persists) | StateStore §3.6 (enabled + mode keys) |
| FR-LC-6 (deferred startup build) | QGISModesPlugin.initGui §3.10 + LifecycleController startup path §3.5 |
| FR-LC-7 (switch does not re-capture) | LifecycleController.apply_mode §3.5 (does NOT call `save_original_layout`) |
| FR-LC-8 (unload removes UI) | QGISModesPlugin.unload §3.10 |
| FR-LC-9 (context menu policy) | LifecycleController.enable / disable §3.5 + §7.8 |
| FR-SW-1 (mode picker) | UIWidgets InlineModeSwitcher §7.3 + ToggleSplitButton §7.1 + ImportExportMenu §7.2 |
| FR-SW-2 (switch without restart) | LifecycleController.switch_mode §3.5 |
| FR-SW-3 (active mode persists) | StateStore §3.6 |
| FR-SW-4 (active mode indicated) | UIWidgets InlineModeSwitcher §7.3 (checked indicator) |
| FR-SW-5 (switcher reachable from simplified) | UIWidgets InlineModeSwitcher §7.3 |
| FR-SW-7 (keyboard shortcuts) | ShortcutManager §3.8 |
| FR-UI-1 (build toolbars) | ModeApplier §3.3 |
| FR-UI-2 (resolve `parent:identifier`) | TokenResolver §3.4 |
| FR-UI-3 (dropdown groups) | TokenResolver §3.4 |
| FR-UI-4 (separator / section / wildcard / algorithm tokens) | TokenResolver §3.4 |
| FR-UI-5 (apply panels + statusbar) | ModeApplier §3.3 |
| FR-UI-6 (skip unresolved token) | TokenResolver §3.4 |
| FR-UI-7 (hide standard UI on enter) | LifecycleController.enable §3.5 |
| FR-UI-8 (teardown only owned toolbars) | ModeApplier §3.3 |
| FR-GR-1 (always-visible exit) | UIWidgets ExitControl §7.4 |
| FR-GR-2 (mode switcher when ≥ 2 modes) | UIWidgets InlineModeSwitcher §7.3 |
| FR-GR-3 (exit/switcher runtime-injected) | UIWidgets §3.9 — both are added by the plugin, independent of mode content |
| FR-GR-4 (fallback on broken mode) | LifecycleController.apply_mode fallback path §3.5 |
| FR-GR-5 (errors caught, logged, surfaced) | All component public methods catch + log via `plugin.log()` / `plugin.message()` |
| FR-PS-1 (state under `qgismodes/`) | StateStore §3.6 |
| FR-PS-2 (no writes outside namespace) | StateStore §3.6 (sole settings writer); ImportExportService §3.7 (sole modes-dir writer) |

**Coverage check:** every M requirement in the SRS appears at least once above.
Should (S) and Could (C) requirements are covered by the same components — not
enumerated to keep this matrix focused on the MVP gate.

---

## 11. Open implementation questions

Surfaced here so they are not lost; **not blockers for the design**:

- **`jsonschema` library availability.** Verify on QGIS 3.44 LTR's bundled
  Python. If not present, the hand-rolled fallback validator covers the must-have
  checks but loses schema-level richness; consider bundling the lib or
  documenting the install requirement.
- **Late-arriving plugin toolbars.** A plugin enabled *while* QGIS Modes is in
  simplified mode adds a toolbar that QGIS Modes didn't hide. Options:
  install an event filter, watch `QObject.childEvent`, or document the
  limitation. Decision deferred to implementation; document the caveat.
- **Multi-process safety.** Two QGIS instances on the same profile share
  `QgsSettings`. Writes are not transactional; race conditions are possible.
  *Document as a caveat; do not engineer around for v1.0.*
- **i18n.** All strings hard-coded for v1.0; Qt translation infrastructure
  deferred.
- **Qt enum value storage.** Qt6 preserves enums, Qt5 stores integers. Design
  writes ints for forward compatibility; `toEnum()` shim handles read-back.
- **Conflict-dialog "Keep both" id rewrite.** If `meta.id` is rewritten on
  import (Keep both), this is the only case where the on-disk file differs
  from the sender's bytes. The export round-trip in UC-13 will preserve the
  renamed id, not the original.

---

## 12. References

- Requirements baseline: [`requirements.md`](requirements.md) v0.2
- Architectural narrative: [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md)
- Inherited token-resolution mechanism: [`customizing-qgis-light.md`](customizing-qgis-light.md) §2.5–§2.6
- Mode-file schema: `src/qgismodes/schema/mode.schema.json`
- QGIS plugin API: [QgisInterface](https://qgis.org/pyqgis/master/gui/QgisInterface.html)
- QGIS Human Interface Guidelines: [docs.qgis.org HIG](https://docs.qgis.org/latest/en/docs/developers_guide/hig.html)
