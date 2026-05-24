# QGIS Modes — Software Requirements Specification (SRS)

| | |
| :-- | :-- |
| **Document** | Software Requirements Specification |
| **Project** | QGIS Modes |
| **Version** | 1.0 — baseline |
| **Date** | 2026-05-23 |
| **Status** | Baselined (tag `spec-v1.0`). SRS frozen; changes require a change-note round. |
| **Baseline target** | Release 1.0 (MVP — Phases 1 & 2) |
| **Related** | [`vision-and-scope.md`](vision-and-scope.md), [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md), [`customizing-qgis-light.md`](customizing-qgis-light.md) |


## 1. Introduction

### 1.1 Purpose

This SRS specifies the requirements for **Release 1.0 (MVP)** of QGIS Modes — a
working multi-mode QGIS plugin, without the visual authoring tool. It also
records post-MVP requirements at lower priority so the design can accommodate
them. It is the contract against which the design ([Stage 4](design-multi-mode-and-authoring.md))
and verification are traced.

### 1.2 Scope of the product

QGIS Modes is a QGIS plugin that provides multiple simplified QGIS interfaces
("modes"), selectable and switchable at runtime. It hides and regroups existing
QGIS UI elements; it adds no GIS functionality. See
[`vision-and-scope.md`](vision-and-scope.md) for the full scope rationale.

### 1.3 Definitions

| Term | Meaning |
| :-- | :-- |
| **Mode** | One simplified interface, defined by one **mode file**. |
| **Mode file** | A JSON file describing a mode: a `meta` block plus interface sections. |
| **Simplified mode** | The state in which a mode is applied and the standard QGIS UI is hidden. |
| **Standard interface** | QGIS's normal, full interface. |
| **Token** | A string in a mode file naming an existing QGIS/plugin UI element. |
| **Token resolution** | Turning tokens into live Qt objects — the core mechanism inherited from QGIS Light. |
| **Original layout** | The toolbar/panel arrangement captured before simplified mode is first entered. |
| **Provider policy** | The allow-list of QGIS data-source / data-item providers. |
| **The Designer** | The future visual mode-authoring tool (post-MVP). |

### 1.4 Requirement conventions

- **Identifiers.** `FR-<area>-<n>` for functional, `NFR-<area>-<n>` for
  non-functional, `UC-<n>` for use cases, `IF-<n>` for interfaces. IDs are
  stable and never reused.
- **Priority (MoSCoW).** **M** = Must (MVP-blocking) · **S** = Should (MVP if
  feasible) · **C** = Could (post-MVP) · **W** = Won't (this release).
- **"shall"** denotes a binding requirement.
- **DECISION** callouts mark open choices from
  [`vision-and-scope.md`](vision-and-scope.md) §11; each states a recommended
  default used by this draft.

### 1.5 References

QGIS plugin development and publishing
([docs.qgis.org PyQGIS cookbook](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/plugins/plugins.html),
[plugins.qgis.org/docs/publish](https://plugins.qgis.org/docs/publish),
[plugin security scanning](https://plugins.qgis.org/docs/security-scanning),
[QGIS Human Interface Guidelines](https://docs.qgis.org/latest/en/docs/developers_guide/hig.html))
inform the packaging, quality, and usability requirements in §5.


## 2. Overall description

### 2.1 Product perspective

QGIS Modes is a Python plugin loaded into the QGIS process. It is **derived from
QGIS Light** and reuses its config-driven, token-resolution architecture
(documented in [`customizing-qgis-light.md`](customizing-qgis-light.md)),
generalising one config into many switchable modes. It is a self-contained
plugin with no server component.

### 2.2 Product functions (summary)

1. Load and validate mode files.
2. **Import and export mode files** (single or multiple) between users, from QGIS Light configs, and across QGIS user profiles. See FR-MS-7a/7b/8/9/10.
3. Enter and exit simplified mode.
4. Capture and restore the original layout.
5. Select and switch modes at runtime.
6. Build the interface from a mode via token resolution.
7. Keep the user safe (always exit, always switch, fail soft).
8. Persist state across sessions.

### 2.3 User classes

Per [`vision-and-scope.md`](vision-and-scope.md) §7: **P1** end user, **P2**
educator, **P3** mode author, **P4** maintainer, **P5** GIS analyst (power
user). P1, P2, and P5 are the primary runtime users for the MVP; P3 and P5
author modes by editing JSON in the MVP.



### 2.4 Operating environment

- QGIS **3.44+ and 4.x**; Qt 5 (QGIS 3.44 LTR) and Qt 6 (QGIS 4); PyQt5 / PyQt6.
- Windows, Linux, macOS.
- Runtime plugin dependencies: **QuickMapServices**, **DataPlotly**.

> **D1 resolved.** Minimum QGIS = **3.44** (the latest QGIS 3 LTR) — see §10.
> 3.44 supports every API this plugin relies on, including `plugin_dependencies`
> (needs ≥ 3.8) and `mainwindow.initializationCompleted`. The dual Qt 5 / Qt 6
> obligation (NFR-CMP-2) is preserved.

### 2.5 Design and implementation constraints

| ID | Constraint |
| :-- | :-- |
| CON-1 | Plain QGIS Python plugin — no build/compile step. |
| CON-2 | Single codebase for Qt 5 and Qt 6 (fully-scoped enum names; the `associatedObjects()` / `toEnum()` shims). |
| CON-3 | Licensed GPL-3.0-or-later; a `LICENSE` file ships in the package. |
| CON-4 | The deployable unit is the `src/qgismodes/` folder; its name is ASCII and does not start with a digit. |
| CON-5 | The package contains no binaries, no generated files, no `__pycache__`/`.git`. |
| CON-6 | Mode files are data — parsed as JSON only; never `eval`/`exec`-ed. |
| CON-7 | Built only on the public QGIS/PyQt API; no private QGIS internals beyond documented widget discovery. |

### 2.6 Assumptions and dependencies

| ID | Assumption / dependency |
| :-- | :-- |
| ASM-1 | QGIS calls `classFactory` → `initGui` / `unload` and emits `initializationCompleted` as documented. |
| ASM-2 | The QGIS Light token-resolution logic ports without redesign. |
| ASM-3 | `QgsSettings` and `QgsApplication.qgisSettingsDirPath()` behave as documented under Qt 5 and Qt 6. |
| ASM-4 | QuickMapServices and DataPlotly are installed when a mode references them; absence degrades gracefully (FR-UI-6). |
| ASM-5 | Users have write access to their QGIS profile directory. |


## 3. Functional requirements

Priorities: **M**ust · **S**hould · **C**ould · **W**on't (this release).

### 3.1 Mode files and schema (FR-MF)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-MF-1 | M | Each mode shall be defined by a single JSON mode file. | A well-formed mode file produces exactly one selectable mode. |
| FR-MF-2 | M | A mode file shall contain a `meta` block with at least `id`, `name`, and integer `schema`. | A file missing any of the three is rejected (FR-MF-5). |
| FR-MF-3 | M | A mode file shall support the sections `toolbars`, `algorithms`, `panels`, and `statusbar`. Per-mode menu-bar rebuild is deferred to v1.1+ (FR-UI-9); provider policy is global, not per-mode (FR-MF-7); the exit control and mode switcher are runtime-injected (FR-GR-3); the term "panels" covers what is sometimes called "docks" — they are the same Qt object. | Each present section is applied per §3.4–§3.5; no other top-level section (e.g. `menus`, `docks`, `browser`) is recognised by the v1.0 schema. |
| FR-MF-4 | M | The system shall validate every mode file against the published JSON Schema on load. | A file violating the schema is detected before it is applied. |
| FR-MF-5 | M | An invalid or unparseable mode file shall be skipped with a logged diagnostic; it shall not abort plugin load or startup. | With one corrupt file present, all valid modes still load; a warning names the bad file. |
| FR-MF-6 | M | The mode-file format shall carry an integer `schema` version. | A file whose `schema` exceeds the supported version is skipped with an explanatory diagnostic. |
| FR-MF-7 | M | Provider policy shall be defined once and shared by all modes — never stored per mode file. | The schema has no per-mode `providers` section; switching modes does not change provider policy. |
| FR-MF-8 | C | A mode file may declare `meta.requires` (names of QGIS plugins it depends on). | When present, the value is readable by the mode manager for dependency warnings. |

### 3.2 Mode storage and discovery (FR-MS)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-MS-1 | M | The system shall load **bundled** modes from the plugin's `modes/` directory. | Bundled modes appear in the mode list. |
| FR-MS-2 | M | The system shall load **user** modes from `<QGIS profile>/qgismodes/modes/`. | A user-placed mode file appears in the mode list after reload. |
| FR-MS-3 | M | A user mode shall override (shadow) a bundled mode having the same `meta.id`. | With both present, the user version is the one offered. |
| FR-MS-4 | M | User modes shall be unaffected by plugin upgrade/reinstall. | After reinstalling the plugin, user modes still exist and load. |
| FR-MS-5 | S | On first run with an empty user modes directory, the system shall seed it by copying the bundled modes. | First launch creates editable copies; **DECISION D5**. |
| FR-MS-6 | C | The system shall import an existing QGIS Light `config.json` as a `default` mode. | Legacy migration; **DECISION D3**. |
| FR-MS-7a | M | The system shall provide an **Import mode** command that accepts one or more mode files — or every valid `.json` file in a chosen directory — validates each against the schema, and installs valid modes into the user modes directory under the filename `<meta.id>.json`. | A user can import a single file, multiple selected files, or all valid `.json` in a chosen folder; invalid files are skipped with a logged diagnostic; the stored filename always equals `<meta.id>.json`. |
| FR-MS-7b | M | The system shall provide an **Export mode** command that writes one or more selected modes as separate JSON files (one mode per file, named `<meta.id>.json`) to a user-chosen location. | With N modes selected, N files are written; the export dialog defaults to the most recently used location in the session. |
| FR-MS-8 | C | The system shall gracefully adapt earlier mode-file schema versions to the current schema on load and import. | Trivially satisfied while only schema v1 exists; revisit when schema v2 lands. |
| FR-MS-9 | M | On import, if a mode with the same `meta.id` already exists, the system shall present the user a choice of **Overwrite**, **Keep both** (rename the incoming mode), or **Cancel** — per conflict. | Each collision triggers a dialog; the user's choice for one mode does not affect other modes in the same import batch. |
| FR-MS-10 | M | Before installing an imported mode, the system shall display a preview listing any QGIS plugins it requires (per `meta.requires`) and request user confirmation. | A preview dialog appears before write; the user may confirm or cancel; a mode without `meta.requires` shows no plugin list but the confirmation step still runs. |

### 3.3 Lifecycle — enter / exit simplified mode (FR-LC)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-LC-1 | M | The system shall provide a user command to **enter** simplified mode. | Invoking it applies the active mode and hides the standard UI. |
| FR-LC-2 | M | On the **first** entry, the system shall capture the original toolbar and panel layout. | The captured layout is persisted and is sufficient to fully reconstruct the pre-simplification UI. |
| FR-LC-3 | M | The system shall provide a user command to **exit** to the standard interface. | Invoking it removes mode UI and restores the standard UI. |
| FR-LC-4 | M | On exit, the system shall restore the captured original layout exactly. | Toolbars/panels return to their prior visibility, position, and dock state. |
| FR-LC-5 | M | Simplified state (on/off and active mode) shall persist across QGIS restarts. | Restarting QGIS while simplified resumes the same mode. |
| FR-LC-6 | M | When simplified mode is active at startup, building the interface shall be deferred until QGIS initialisation completes. | Tokens referencing other plugins' toolbars resolve correctly at startup. |
| FR-LC-7 | M | A mode switch shall **not** re-capture or overwrite the stored original layout. | After A→B→exit, the UI matches the state captured before A. |
| FR-LC-8 | M | On plugin `unload()`, the system shall remove all UI it added and, if simplified mode is active, restore the standard interface. | After disabling the plugin, no QGIS Modes UI remains and the standard UI is intact. |
| FR-LC-9 | M | In simplified mode, the main window's context-menu policy shall be set to `NoContextMenu` so users cannot re-expose hidden UI via right-click; on exit, the previous policy shall be restored. | Right-click in QGIS chrome shows no context menu while a mode is active; normal right-click behaviour returns after exit. A per-mode opt-in (`meta.allow_context_menu`) is a v1.1+ option. |

### 3.4 Mode selection and switching (FR-SW)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-SW-1 | M | The system shall let the user select which mode to apply, listing modes by `meta.name`. | The picker shows every installed mode's human name. |
| FR-SW-2 | M | The system shall let the user switch to a different mode **while remaining in simplified mode**, without restarting QGIS. | Switching A→B replaces the interface in place; QGIS is not restarted. |
| FR-SW-3 | M | The system shall persist the active mode `id` and reapply it on next startup. | Selected mode survives a restart. |
| FR-SW-4 | M | The active mode shall be indicated in the mode picker. | The current mode is visibly marked. |
| FR-SW-5 | M | When ≥ 2 modes are installed, a mode switcher shall be reachable from within the simplified interface. | A user in simplified mode can switch modes without exiting first. |
| FR-SW-6 | S | A mode switch shall complete without flicker of the standard (un-simplified) interface. | The menu bar / standard toolbars do not momentarily reappear during a switch. |
| FR-SW-7 | M | The system shall register each installed mode (and the global enter/exit action) with QGIS's keyboard-shortcut manager so users can bind keys in **Settings → Keyboard Shortcuts**. **No default bindings shall be set** (to avoid conflicts with users' existing shortcuts). | Each mode appears in *Settings → Keyboard Shortcuts* as a bindable action; once bound, the key immediately switches modes without using the mouse. |

### 3.5 Interface construction — token resolution (FR-UI)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-UI-1 | M | The system shall create the toolbars defined in the active mode's `toolbars` section, in the specified areas. | Each declared toolbar appears in its `area` with its items. |
| FR-UI-2 | M | The system shall resolve `parent:identifier` tokens to existing QGIS or plugin UI elements (matched by object name, text, or tooltip). | A valid token yields the corresponding live action/widget. |
| FR-UI-3 | M | The system shall render a nested array of tokens as a single dropdown button, the first item shown by default. | A grouped array produces one drop-down tool button. |
| FR-UI-4 | M | The system shall support `separator`, `section:Label`, wildcard (`*`) expansion, processing-algorithm id tokens, and `algorithms:<group>` tokens. | Each token form behaves as documented in [`customizing-qgis-light.md`](customizing-qgis-light.md) §2.5. |
| FR-UI-5 | M | The system shall apply the `panels` section (visibility, dock area, fixed/hidden state) and the `statusbar` section. | Listed panels/status-bar widgets reach their declared state; unlisted panels are hidden. |
| FR-UI-6 | M | A token that fails to resolve shall be skipped with a logged diagnostic; interface construction shall continue. | A mode with one bad token still builds; the bad token is named in the log. |
| FR-UI-7 | M | On entering simplified mode, the system shall hide the menu bar and all standard toolbars and panels not required by the active mode. | Only the active mode's toolbars/panels are visible. |
| FR-UI-8 | M | `apply_mode()` shall tear down only the toolbars QGIS Modes created, never `QAction`s borrowed from QGIS. | After repeated switching, borrowed QGIS actions remain valid and functional. |
| FR-UI-9 | W | A mode file may declare a `menus` section that the system rebuilds as a simplified menu bar from tokens (same mechanism as toolbars). | **Deferred to v1.1** (the power-user release). v1.0 hides the menu bar entirely (FR-UI-7); menu actions remain reachable through toolbar tokens such as `mProjectMenu:mActionShowLayoutManager`. |
| FR-UI-10 | C | The system may provide a **quick-run** command-search box that finds and runs any QGIS action by name, regardless of the active mode (P5's "escape hatch"). | **v1.1+ target.** Search returns matching actions across all toolbars/menus; invoking a result runs it as if the user had clicked the original. |

### 3.6 Safety and guard rails (FR-GR)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-GR-1 | M | The simplified interface shall **always** present a visible control to exit to the standard interface. | Every mode, including a minimal or malformed-but-loadable one, shows an exit control. |
| FR-GR-2 | M | When ≥ 2 modes are installed, the simplified interface shall always present a mode switcher (see FR-SW-5). | The switcher is present regardless of mode-file content. |
| FR-GR-3 | M | The exit control and mode switcher shall be **injected by the runtime**, independent of mode-file content. | Removing all items from a mode file does not remove the exit/switcher. |
| FR-GR-4 | M | If the active mode fails to load or apply, the system shall fall back to a known-good mode, or to the standard interface, and inform the user. | A corrupt active mode never leaves the user with a broken or empty interface. |
| FR-GR-5 | M | All foreseeable errors (file I/O, parse, token, Qt) shall be caught, logged to the "QGIS Modes" log tab, and — when user-relevant — surfaced via the message bar. | No QGIS Modes operation produces an unhandled exception dialog or crash. |

### 3.7 Persistence and configuration (FR-PS)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-PS-1 | M | All persisted state shall be stored in `QgsSettings` under the `qgismodes/` namespace. | Keys observed: `qgismodes/enabled`, `qgismodes/mode`, and the captured layout. |
| FR-PS-2 | M | The system shall not write outside its `qgismodes/` settings namespace and its own modes directories. | No settings/files are created elsewhere. |

### 3.8 Provider policy (FR-PP)

| ID | Pri | Requirement | Acceptance criteria |
| :-- | :-- | :-- | :-- |
| FR-PP-1 | C | The system shall apply a single shared provider policy when simplified mode is first entered. | **Deferred to v1.1+ per D2.** P5 (power user) needs an unrestricted Browser; provider removal is destructive (needs a QGIS restart to undo) and cannot vary per mode. To be revisited as a per-installation toggle. |
| FR-PP-2 | C | A mode switch shall not change provider policy. | Conditional on FR-PP-1. |
| FR-PP-3 | C | The system shall warn the user that restoring removed providers requires a QGIS restart. | Conditional on FR-PP-1. |

### 3.9 Visual Mode Designer (FR-DS) — post-MVP

| ID | Pri | Requirement |
| :-- | :-- | :-- |
| FR-DS-1 | C | The system shall provide a visual dialog to create and edit mode files without editing JSON. |
| FR-DS-2 | C | The Designer shall present available tools/panels/algorithms by real icon and label, never raw tokens. |
| FR-DS-3 | C | The Designer shall build interfaces by drag-and-drop and round-trip existing mode files. |
| FR-DS-4 | W | "Pick from QGIS" capture, live preview, and undo/redo. |

> FR-DS-* are recorded so the MVP design does not foreclose them; they are **not**
> in Release 1.0. Their full design is in
> [`design-multi-mode-and-authoring.md`](design-multi-mode-and-authoring.md)
> Part B.

### 3.10 Capture features (FR-CP) — post-MVP

| ID | Pri | Requirement |
| :-- | :-- | :-- |
| FR-CP-1 | W | The system may provide a command to **capture the current QGIS profile's UI** as a starter mode that the author can then refine. |
| FR-CP-2 | W | The system may provide a command to **capture the UI of another QGIS profile** on the same machine as a starter mode. |

> FR-CP-* are tracked for post-MVP; they share mechanism with the future Visual
> Mode Designer's "Pick from QGIS" capture mode. They are the formal answer to
> the L5(a) reading of "from User Profiles" in §2.2 item 2.

## 4. Use cases

Each use case is a scenario the design must satisfy. **Pass criteria** are
concrete, testable checks — the UC passes when all bullets verify true. The
UCs collectively form the §8 manual verification checklist.

### UC-1 — First-time use

*Actor:* P1 / P2.
*Preconditions:* plugin installed, never enabled.
*Trigger:* user invokes *Enter QGIS Modes*.
*Main flow:*
1. The system captures the original toolbar and panel layout.
2. The menu bar and standard toolbars/panels are hidden; context-menu policy is set to `NoContextMenu`.
3. The default mode is applied.
4. The simplified interface appears with an exit control and (if ≥ 2 modes installed) a mode switcher.

*Postconditions:* simplified mode active; default mode is the active mode.

*Pass criteria:*
- ✓ Simplified interface matches the default mode's `toolbars` / `panels` / `statusbar`.
- ✓ Original layout persisted to `QgsSettings` under `qgismodes/`.
- ✓ Exit control visible and functional.
- ✓ Right-click in QGIS chrome shows no context menu.

*Covers:* FR-LC-1, FR-LC-2, FR-LC-9, FR-UI-1, FR-UI-7, FR-GR-1, FR-MS-1.

### UC-2 — Switch modes mid-session

*Actor:* P2 / P5.
*Preconditions:* simplified mode active; ≥ 2 modes installed; current mode = "Analysis".
*Trigger:* user picks a different mode from the mode switcher (or its keyboard shortcut — see UC-12).
*Main flow:*
1. The system tears down the current mode's plugin-created toolbars.
2. The new mode is loaded and validated.
3. The new mode's `toolbars` / `panels` / `statusbar` are applied.
4. `qgismodes/mode` is updated to the new id.

*Alternate flows:* new mode fails to load → UC-5 fallback.

*Postconditions:* new mode active; captured original layout untouched; provider policy unchanged; QGIS not restarted.

*Pass criteria:*
- ✓ The previous mode's plugin-created toolbars are removed.
- ✓ The new mode's interface is in place.
- ✓ `qgismodes/mode` reflects the new mode id.
- ✓ The captured original layout in `QgsSettings` is unchanged.
- ✓ Switch latency < 1 s (NFR-PRF-1).

*Covers:* FR-SW-1, FR-SW-2, FR-SW-3, FR-SW-5, FR-UI-8, FR-LC-7, FR-PP-2.

### UC-3 — Exit to standard QGIS

*Actor:* P1 / P2 / P5.
*Preconditions:* simplified mode active.
*Trigger:* user invokes the runtime-injected exit control.
*Main flow:*
1. The system tears down all plugin-created toolbars.
2. The standard menu bar, toolbars, and panels are restored from the captured layout.
3. The context-menu policy is restored.
4. `qgismodes/enabled` is cleared.

*Postconditions:* the standard QGIS interface is exactly as before simplification.

*Pass criteria:*
- ✓ Every toolbar/panel visible before simplification is visible again, in the same area.
- ✓ The menu bar is visible.
- ✓ Right-click works again in QGIS chrome.
- ✓ No QGIS Modes-created widgets remain in the main window.

*Covers:* FR-LC-3, FR-LC-4, FR-LC-9, FR-GR-1.

### UC-4 — Author a mode by editing JSON

*Actor:* P3 (also P5, for their own modes).
*Preconditions:* plugin installed.
*Trigger:* author wants to create or change a mode.
*Main flow:*
1. Author copies an existing `.json` from `<plugin>/modes/` or `<profile>/qgismodes/modes/`.
2. Author edits `meta.id`, `meta.name`, and the body.
3. Author reloads the plugin (Plugin Reloader) or restarts QGIS.
4. The new/changed mode appears in the picker.

*Alternate flows:* file fails schema validation → mode skipped, diagnostic logged (UC-5 partial).

*Postconditions:* the new/changed mode is selectable and usable.

*Pass criteria:*
- ✓ A schema-valid file becomes a selectable mode.
- ✓ A schema-invalid file is skipped with a diagnostic in the *QGIS Modes* log tab.
- ✓ Other modes still load correctly when one mode is broken.

*Covers:* FR-MS-2, FR-MF-1, FR-MF-2, FR-MF-3, FR-MF-4, FR-MF-5, FR-MF-6, FR-SW-1.

### UC-5 — Recover from a broken mode

*Actor:* P2 / P5.
*Preconditions:* the active mode file is malformed (bad JSON, schema violation, or `meta.schema` > supported).
*Trigger:* QGIS starts (UC-6) or the user picks the broken mode.
*Main flow:*
1. Validation fails for the file.
2. The system logs the failure to the *QGIS Modes* tab and pushes a message-bar warning naming the bad file.
3. The system falls back to a known-good mode (e.g. `default`) or to the standard interface.

*Postconditions:* the user has a usable interface; they are not trapped.

*Pass criteria:*
- ✓ The broken file does not raise an unhandled exception.
- ✓ A diagnostic naming the bad file appears in the log.
- ✓ A user-readable warning appears in the message bar.
- ✓ A usable interface (good mode or standard QGIS) is shown.

*Covers:* FR-MF-5, FR-MF-6, FR-GR-4, FR-GR-5.

### UC-6 — Restart while simplified

*Actor:* P1 / P2 / P5.
*Preconditions:* simplified mode active when QGIS is closed.
*Trigger:* QGIS is reopened.
*Main flow:*
1. The plugin sees `qgismodes/enabled` is true.
2. The plugin defers building until `mainwindow.initializationCompleted`.
3. The plugin reapplies the persisted mode id.

*Postconditions:* the same mode is active after restart; tokens from late-loading plugins resolve.

*Pass criteria:*
- ✓ The active mode after restart equals the active mode before close.
- ✓ Tokens referencing QuickMapServices and DataPlotly resolve successfully.
- ✓ Startup adds < 200 ms when QGIS Modes is *not* active (NFR-PRF-2).

*Covers:* FR-LC-5, FR-LC-6, FR-SW-3.

### UC-7 — Author exports a mode and shares it

*Actor:* P3 (sender).
*Preconditions:* P3 has authored one or more modes.
*Trigger:* P3 invokes *Export mode…*.
*Main flow:*
1. P3 selects one or more modes.
2. The export dialog opens at the most-recently-used location in the session.
3. P3 chooses a folder and confirms.
4. The system writes one `<meta.id>.json` per selected mode.
5. P3 attaches the file(s) to email, drops on a shared drive, etc.

*Postconditions:* schema-valid `.json` file(s) exist at the chosen location.

*Pass criteria:*
- ✓ With N modes selected, N files are written, each named `<meta.id>.json`.
- ✓ Re-importing an exported file (UC-8) reproduces the mode exactly.
- ✓ Subsequent export reopens at the last-used location.

*Covers:* FR-MS-7b.

### UC-8 — Receiver imports a single mode

*Actor:* P2 / P5 (receiver).
*Preconditions:* receiver has a `.json` mode file from a sender.
*Trigger:* receiver invokes *Import mode…*.
*Main flow:*
1. File picker opens; receiver selects the `.json`.
2. The system validates the file against `mode.schema.json`.
3. If `meta.requires` is present, the plugin-requires preview is shown for confirmation.
4. If a mode with the same `meta.id` already exists, the conflict dialog (UC-10) is shown.
5. The mode file is copied to the user modes dir as `<meta.id>.json`.
6. The new mode appears in the picker (after reload, if required).

*Alternate flows:*
- File is malformed → skipped with diagnostic; receiver is informed.
- Preview cancelled → import aborted; nothing written.

*Postconditions:* the new mode is selectable and usable.

*Pass criteria:*
- ✓ A schema-valid file becomes a selectable mode.
- ✓ A schema-invalid file is skipped with a diagnostic; no exception.
- ✓ Preview confirmation step happens when `meta.requires` is present.
- ✓ Stored filename is `<meta.id>.json` regardless of the incoming filename.

*Covers:* FR-MS-7a, FR-MS-9, FR-MS-10.

### UC-9 — Receiver imports many modes from a folder

*Actor:* P2 / P5.
*Preconditions:* receiver has a folder containing several mode `.json` files.
*Trigger:* receiver invokes *Import mode… → from folder* (or multi-select in the picker).
*Main flow:*
1. Receiver picks a directory.
2. The system enumerates all `.json` files and validates each.
3. For each valid file: plugin-requires preview, conflict resolution, install (UC-8 sub-flow).
4. For each invalid file: skipped with diagnostic.
5. A summary is shown (e.g. *"N modes imported, M skipped"*).

*Postconditions:* every valid mode is installed; receiver knows what was skipped and why.

*Pass criteria:*
- ✓ Every valid mode in the folder is imported.
- ✓ Every invalid file is named in the log with the reason.
- ✓ Conflict choices for one mode do not affect others.
- ✓ Summary counts match (`imported + skipped = total found`).

*Covers:* FR-MS-7a, FR-MS-9, FR-MS-10.

### UC-10 — Resolve a mode-id conflict on import

*Actor:* P2 / P5.
*Preconditions:* during UC-8 or UC-9, an incoming mode's `meta.id` matches an existing user mode.
*Trigger:* the conflict dialog appears for that mode.
*Main flow:* user chooses one of:
- **Overwrite** — existing user mode is replaced; bundled mode (if any) is shadowed unchanged.
- **Keep both** — incoming mode is renamed (e.g. `<id>-1`, `<id>-2`); existing mode is untouched.
- **Cancel** — nothing is written for this mode.

*Postconditions:* the chosen outcome is applied for the conflicting mode; other modes in the batch are unaffected.

*Pass criteria:*
- ✓ Each choice produces the documented outcome.
- ✓ A choice for one mode is honoured even when other choices in the same batch differ.
- ✓ *Cancel* leaves the user modes dir unchanged for that mode.

*Covers:* FR-MS-9.

### UC-11 — Educator distributes modes to a class

*Actor:* P2 (educator); P1 (students).
*Preconditions:* P2 has prepared one or more modes for the activity.
*Trigger:* P2 needs every student's QGIS to have the same modes.
*Main flow* — any combination of three supported mechanics:
- **(A) Email.** P2 exports (UC-7) and emails `.json` files; students import (UC-8 / UC-9).
- **(B) Shared drive.** P2 places `.json` files on a shared network/cloud folder; students *Import from folder* pointing at it (UC-9).
- **(C) Pre-install.** P2 (or IT) copies `.json` files directly into each laptop's `<profile>/qgismodes/modes/` before class. Students do nothing.

*Postconditions:* every student's QGIS has the prepared modes available.

*Pass criteria:*
- ✓ All three mechanics produce identical mode files on the receiving machine (same `meta.id`, same body).
- ✓ Mechanic (C) requires no student action — modes appear on next QGIS start (UC-1 / UC-6).

*Covers:* FR-MS-2, FR-MS-7a, FR-MS-7b.

### UC-12 — Power user's day with keyboard shortcuts

*Actor:* P5.
*Preconditions:* simplified mode active; multiple task-focused modes installed; P5 has bound keyboard shortcuts in *Settings → Keyboard Shortcuts*.
*Trigger:* P5 presses a bound shortcut to switch mode (or, v1.1+, to invoke quick-run).
*Main flow:*
1. P5 works in mode A; the shortcut switches to mode B (UC-2 mechanics).
2. P5 needs a tool not in mode B. One of:
   - **(a)** Switch to mode C that has it (UC-2).
   - **(b)** One-click exit → use tool in standard QGIS → re-enter (UC-3 + UC-1, mode id preserved by `qgismodes/mode`).
   - **(c)** (v1.1+) Invoke quick-run (FR-UI-10) to run the action without switching.
   - **(d)** Decide the current mode is too narrow and edit/author a richer one (UC-4).
3. P5 continues across the day; ends in whichever mode they last used.

*Postconditions:* P5 accomplished a multi-task day without restarting QGIS or losing focus.

*Pass criteria:*
- ✓ Each bound shortcut switches modes without using the mouse.
- ✓ Switch latency < 1 s (NFR-PRF-1).
- ✓ The exit → re-enter sequence preserves the previously active mode id.
- ✓ No mode-switch attempt triggers an unhandled exception.

*Covers:* FR-SW-1, FR-SW-2, FR-SW-7, FR-LC-1, FR-LC-3, FR-LC-5; *post-MVP:* FR-UI-10.

### UC-13 — Backup and restore user modes

*Actor:* P3 / P5 (user keeping their own modes safe).
*Preconditions:* user has authored or accumulated user modes they want to preserve.
*Trigger:* user wants a backup (machine migration, OS reinstall, risky change).
*Main flow:*
1. User invokes *Export* and selects all their user modes.
2. The system writes one `<meta.id>.json` per mode to a chosen location (UC-7).
3. Later (perhaps on another machine), user invokes *Import from folder* pointing at the backup (UC-9).

*Postconditions:* the user's modes are reproducible on any machine.

*Pass criteria:*
- ✓ Exporting all user modes and re-importing on a clean install yields an identical set of selectable modes.
- ✓ `meta.id`, `meta.name`, and body match before and after the round trip.

*Covers:* FR-MS-7a, FR-MS-7b.


## 5. Non-functional requirements

### 5.1 Compatibility (NFR-CMP)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-CMP-1 | M | One codebase shall run on QGIS **3.44+** and QGIS 4.x. | Verified on a QGIS 3.44 install and a QGIS 4.x install. |
| NFR-CMP-2 | M | The code shall run under both Qt 5 / PyQt5 and Qt 6 / PyQt6 (fully-scoped enums; the documented shims). | No Qt-version errors on either. |
| NFR-CMP-3 | M | The plugin shall function on Windows, Linux, and macOS. | Core flows verified per platform (at least Windows; others by review/spot-check). |
| NFR-CMP-4 | M | `metadata.txt` shall set `qgisMaximumVersion=4.99` to remain on the "QGIS 4 Ready" list. | Field present and correct. |

### 5.2 Performance (NFR-PRF)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-PRF-1 | M | A mode switch shall complete in **< 1 s** on a typical project and machine. | Measured switch time < 1 s. |
| NFR-PRF-2 | S | The plugin shall add **< 200 ms** to QGIS startup when simplified mode is off. | Measured startup delta within budget. |

### 5.3 Usability (NFR-USA)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-USA-1 | M | A first-time non-technical user shall be able to enter a mode, switch modes, and exit, **with no training and no dead-ends**. | Confirmed in informal usability testing (Goal G3). |
| NFR-USA-2 | M | The user shall **never** be left unable to return to the standard interface through the UI. | No reachable state lacks an exit (see FR-GR-1/3). |
| NFR-USA-3 | S | The interface shall follow the QGIS Human Interface Guidelines where applicable (minimalism, grouping, novice-first). | Reviewed against the HIG. |
| NFR-USA-4 | S | Diagnostics shall be discoverable in the Log Messages panel under a "QGIS Modes" tab; user-facing notices use the message bar. | Both channels present and used. |

### 5.4 Reliability (NFR-REL)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-REL-1 | M | The plugin shall not crash QGIS under any specified operation or input. | Survives the §4 use cases plus malformed inputs without crashing. |
| NFR-REL-2 | M | Exiting simplified mode or unloading the plugin shall restore the standard interface to its pre-simplification state 100% of the time. | No residual/missing toolbars or panels after exit/unload. |
| NFR-REL-3 | M | `unload()` shall remove every menu item, toolbar item, and widget the plugin added, and disconnect every signal it connected. | Verified by inspection and by enable→disable cycling. |
| NFR-REL-4 | S | Repeated enter/exit and mode-switch cycles shall not leak widgets or degrade behaviour. | 20 cycles leave behaviour and the standard UI intact. |

### 5.5 Maintainability (NFR-MNT)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-MNT-1 | M | Customising an interface shall require **only** editing a mode file — no code change. | A new mode is created without touching Python. |
| NFR-MNT-2 | M | Code shall follow PEP 8 and pass Flake8 with no errors. | Flake8 reports zero errors. |
| NFR-MNT-3 | S | Public modules, classes, and methods shall carry docstrings. | Spot-check: all public APIs documented. |
| NFR-MNT-4 | S | The mode-file format shall be defined by a versioned, published JSON Schema. | `schema/mode.schema.json` exists and matches FR-MF. |

### 5.6 Security (NFR-SEC)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-SEC-1 | M | The package shall pass the plugins.qgis.org security scan (Bandit, detect-secrets) with **no CRITICAL findings**. | Local Bandit + detect-secrets run is clean. |
| NFR-SEC-2 | M | Mode files shall be treated as data: parsed as JSON only, never `eval`/`exec`-ed (CON-6). | No dynamic-execution calls on file content. |
| NFR-SEC-3 | M | The plugin shall contain no hardcoded secrets/credentials and make no undisclosed network calls. | detect-secrets clean; no network code in 1.0. |

### 5.7 Licensing and packaging (NFR-PKG)

| ID | Pri | Requirement | Acceptance |
| :-- | :-- | :-- | :-- |
| NFR-PKG-1 | M | The plugin shall be licensed GPL-3.0-or-later, with a `LICENSE` file in the package and SPDX/GPL notices in source headers; QGIS Light attribution preserved. | License file and headers present and correct. |
| NFR-PKG-2 | M | `metadata.txt` shall contain all repository-required fields (`name`, `qgisMinimumVersion`, `description`, `about`, `version`, `author`, `email`, `repository`) and the recommended `tags`, `changelog`, `category`, `tracker`, `homepage`; `about` shall disclose the QuickMapServices/DataPlotly dependencies. | Metadata validated against the publish checklist. |
| NFR-PKG-3 | M | The published package shall contain no binaries, no generated files, and no `__pycache__`/`.git` (CON-5). | Package inspected before upload. |
| NFR-PKG-4 | M | The 1.0 release shall set `experimental=False`. | Field is `False` for the public release. |
| NFR-PKG-5 | M | `metadata.txt` `homepage`, `repository`, and `tracker` URLs shall be live and point to the QGIS Modes repository. | All three URLs resolve. |
| NFR-PKG-6 | M | `plugin_dependencies` shall list QuickMapServices and DataPlotly so QGIS prompts the user to install them. | Field present; install prompt observed. |


## 6. External interface requirements

| ID | Interface | Requirement |
| :-- | :-- | :-- |
| IF-1 | **QGIS plugin API** | `__init__.py` exposes `classFactory(iface)`; the plugin class implements `initGui()` and `unload()` (FR-LC-8, NFR-REL-3). |
| IF-2 | **QgsSettings** | State under `qgismodes/`: `enabled`, `mode`, captured layout (FR-PS-1). |
| IF-3 | **File system** | Reads bundled modes from `<plugin>/modes/`; reads/writes user modes under `<QGIS profile>/qgismodes/modes/` (FR-MS-1/2). |
| IF-4 | **Mode file format** | JSON conforming to `schema/mode.schema.json` (FR-MF-4). |
| IF-5 | **QGIS UI surface** | Discovers and reuses existing QGIS/plugin `QAction`/`QToolBar`/`QDockWidget`/`QWidget` objects via token resolution (FR-UI-2). |
| IF-6 | **User commands** | A toolbar/menu entry point to enter simplified mode; an in-canvas exit control and mode switcher (FR-LC-1/3, FR-SW-5). |


## 7. Out of scope for Release 1.0

The visual Mode Designer (FR-DS-*), the capture features (FR-CP-*), and the
menu-bar rebuild (FR-UI-9, planned for v1.1); internationalisation; managing PIP
dependencies; an automated test suite (a manual verification checklist is used
instead — see §8). Permanent exclusions are in
[`vision-and-scope.md`](vision-and-scope.md) §8.3.


## 8. Verification approach and Definition of Done

There is no automated test framework in 1.0; verification is by a **manual
verification checklist** executed before release, structured around the §4 use
cases and the acceptance criteria in §3 and §5.

**Release 1.0 is Done when:**

1. Every **M** requirement passes its acceptance criteria.
2. All thirteen use cases (UC-1…UC-13) pass on QGIS 3.44+ and QGIS 4.x.
3. Flake8, Bandit, and detect-secrets are clean (NFR-MNT-2, NFR-SEC-1).
4. The package meets all NFR-PKG requirements.
5. Goals G1–G5 ([`vision-and-scope.md`](vision-and-scope.md) §5) are met.
6. The traceability matrix (Stage 4) shows every **M** requirement covered by a
   design element.


## 9. Traceability

| Direction | Status |
| :-- | :-- |
| Vision goals → requirements | G1→§5.7; G2→FR-SW; G3→NFR-USA; G4→NFR-REL/FR-GR/FR-LC; G5→FR-MF/NFR-MNT. |
| Requirements → design | **Pending Stage 4** — a requirement-to-design matrix will be added to `design-specification.md`. |
| Requirements → verification | §8 manual checklist, keyed by requirement ID. |


## 10. Open decisions (consolidated)

All five decisions are **resolved**. This section records final values for
audit; they are realised in the requirements above and mirrored in
[`vision-and-scope.md`](vision-and-scope.md) §11.

| # | Decision | Resolution |
| :-- | :-- | :-- |
| D1 | Minimum QGIS version | **3.44+** (and QGIS 4.x) — NFR-CMP-1, §2.4. Latest 3.x LTR; supports every API the plugin relies on. |
| D2 | Provider trimming in MVP | **Deferred** — FR-PP-* moved to *Could*; revisit alongside v1.1 power-user work. P5 needs an unrestricted Browser. |
| D3 | Legacy QGIS Light `config.json` migration | **Could** — FR-MS-6. Broader import/export need realised as FR-MS-7a / 7b / 8 / 9 / 10. |
| D4 | Bundled example modes in 1.0 | **Three** — `default`, `raster-analysis`, `vector-editing`. |
| D5 | Seed user modes dir on first run | **Yes** (*Should*) — FR-MS-5. |

> All D1–D5 resolved across the agenda-closure commits. On final sign-off this
> SRS becomes **baseline v1.0** and Stage 4 (design specification) begins.
