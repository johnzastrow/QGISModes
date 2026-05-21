# Design: Multiple Config "Modes" and a Visual Mode Authoring Tool

This is a **design proposal** — not yet implemented. It answers two questions:

1. Can QGIS Light store several named `config.json` files, each a different
   *mode* of working (Data Editing, Analysis, Raster Processing, Output
   Creation…), and let the user select and apply them dynamically?
2. What would a utility look like that lets **non-developers** author those
   config files interactively?

Short answer to (1): **yes, and it is a modest, well-contained refactor.** The
plugin is already config-driven; today it just happens to load exactly one
config. See [Part A](#part-a-multiple-config-modes).

Short answer to (2): a **"Mode Designer" dialog that runs inside QGIS**, using
drag-and-drop and the real QGIS tool icons, never exposing raw tokens. See
[Part B](#part-b-the-mode-designer).

---

## Part A: Multiple config "modes"

> Terminology note: QGIS already uses the word *profile* for its user-profile
> system. To avoid confusion this design uses **mode** for a QGIS Light config
> file. ("Workspace" or "preset" would work equally well.)

### A.1 Config schema change — add a `meta` block

Today a config file is five sections (`toolbars`, `algorithms`, `panels`,
`providers`, `statusbar`). Add a sixth, `meta`, so a file is self-describing:

```json
{
  "meta": {
    "id": "raster-processing",
    "name": "Raster Processing",
    "description": "DEM analysis, interpolation, and raster statistics.",
    "icon": "icons/mode-raster.svg",
    "version": "1.0",
    "schema": 1
  },
  "toolbars":   { ... },
  "algorithms": { ... },
  "panels":     { ... },
  "statusbar":  { ... }
}
```

- `id` — stable slug, also the file name (`raster-processing.json`).
- `name` — the human label shown in the mode picker (**the "name property"**).
- `description`, `icon` — shown in the picker / manager.
- `schema` — integer config-format version, so the interpreter can migrate or
  reject files written for a future format. This is cheap to add now and
  painful to retrofit later.

`providers` is deliberately **not** in the per-mode list above — see
[A.5](#a5-what-switches-live-and-what-does-not).

### A.2 Where modes live

The current `config.json` lives *inside the plugin folder*, which a plugin
upgrade overwrites. User-authored modes must live outside it.

```
<plugin folder>/modes/            ← bundled, read-only templates (shipped)
    data-editing.json
    analysis.json
    raster-processing.json
    output-creation.json

<QGIS profile>/qgis-light/modes/  ← user modes (editable, survive upgrades)
    raster-processing.json        ← user's edited copy shadows the bundled one
    my-classroom-mode.json        ← brand-new user mode
```

The profile directory is `QgsApplication.qgisSettingsDirPath()`. Resolution
rule: **user folder shadows bundled folder by `id`.** On first run, if the user
folder is empty, copy the bundled modes in as starting points. A "Reset to
default" action just deletes the user copy so the bundled one shows through.

This also makes modes **shareable** — a mode is one JSON file a teacher can
email, drop on a shared drive, or commit to git. A "mode pack" is just a zip.

### A.3 Selecting a mode

Two entry points, both backed by `QgsSettings` key `qgislight/mode` (the active
mode id; `qgislight/enabled` keeps its current meaning):

1. **Split toggle button.** The green QGIS Light button becomes a
   `QToolButton` in `MenuButtonPopup` mode. Clicking the button enables the
   last-used mode; the dropdown lists every installed mode (radio-checked for
   the active one) plus *Manage modes…*.
2. **In-canvas mode switcher.** While in light mode, the simplified toolbar
   carries a small mode dropdown so a student or teacher can move from
   "Data Editing" to "Analysis" **without leaving light mode**. The plugin
   injects this automatically (see the guard-rail note in [B.6](#b6-guard-rails-for-non-developers)).

### A.4 Applying a mode dynamically — the `enable`/`disable` refactor

Today `enable()` does two jobs at once: (a) capture the user's original layout
and hide the standard UI, and (b) build the simplified UI from `self.config`.
Dynamic switching requires **separating those two jobs**, so switching mode
re-runs only (b) and never re-captures the original layout (re-capturing while
already simplified would overwrite the saved original with the *simplified*
state — corrupting the restore data).

Proposed structure:

```python
def enable(self, mode_id=None):
    """Enter simplified mode (first time) and apply a mode."""
    if not self._is_enabled():
        self._capture_original_layout()   # writes qgislight/toolbars + /panels ONCE
        self.mainwindow.menuBar().hide()
        self.mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self._hide_all_toolbars()
        self._apply_providers()           # destructive; first mode only — see A.5
    self.settings.setValue("qgislight/enabled", "true")
    self.apply_mode(mode_id or self._active_mode_id())

def apply_mode(self, mode_id):
    """Swap the simplified UI to a different mode (safe while enabled)."""
    self._remove_simplified_toolbars()    # remove only toolbars THIS plugin made
    self.config = self._load_mode(mode_id)
    self._build_toolbars()
    self._apply_panels()                  # re-hide / re-position per new config
    self._apply_statusbar()
    self.settings.setValue("qgislight/mode", mode_id)

def disable(self):
    """Return to the standard QGIS interface."""
    self._remove_simplified_toolbars()
    self.restoreLayout()                  # uses the captured original layout
    self.mainwindow.menuBar().show()
    self.mainwindow.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
    self.settings.remove("qgislight/enabled")
```

One **important implementation detail**: today `disable()` finds the
plugin-built toolbars by iterating `self.config["toolbars"]` keys. With mode
switching, the *previous* mode's toolbar names differ from the next mode's, so
the plugin must track the toolbars it created in an instance list
(`self._created_toolbars`) and tear those down — not whatever the current
config happens to say.

`_apply_panels()` must also handle the **full** panel set on every switch: hide
panels not listed by the incoming mode, and (re)position the ones that are.
Panels and status-bar widgets can be hidden and re-shown freely at runtime, so
mode switching for them is clean.

### A.5 What switches live, and what does not

| Config section | Live mode switch? | Notes |
| :-- | :-- | :-- |
| `toolbars` | ✅ Yes | Tear down + rebuild. |
| `algorithms` | ✅ Yes | Only referenced by toolbars. |
| `panels` | ✅ Yes | Panels re-show/hide freely. |
| `statusbar` | ✅ Yes | Widgets re-show/hide freely. |
| `providers` | ⚠️ **No** | Removing a data/source provider is destructive; QGIS needs a **restart** to get it back. |

Because of the provider caveat, this design **moves `providers` out of per-mode
files** into a single shared policy applied once when light mode is first
entered. Options, in order of preference:

1. **Shared `providers`** — a top-level `qgis-light/settings.json` (or the
   bundled `config.json`) holds one `providers` allowlist for all modes.
   Simple, predictable.
2. **Union of all modes** — if `providers` stays per-mode, apply the *union*
   across every installed mode at enable time, so switching never needs a
   provider that was removed.
3. **Per-mode with a warning** — keep it per-mode but, on switch, if a mode
   needs a provider that was stripped, show "Restart QGIS to enable X." Worst
   UX; not recommended.

### A.6 Validation and failure handling

- Ship a **JSON Schema** for the config format (`schema: 1`). Validate every
  mode file on load.
- On a malformed or schema-mismatched file: log to the *QGIS Light* log tab,
  show a message-bar warning, and **skip that mode** (don't crash the picker).
- If the *active* mode fails to load, fall back to a known-good bundled mode,
  or to standard QGIS — never leave the user in a half-built interface.
- Every mode must contain an exit path (`mActionDisableQGISLight`) **or** the
  injected mode switcher must always provide one — see [B.6](#b6-guard-rails-for-non-developers).

### A.7 Migrating from today's single config

On upgrade, if the old single `config.json` is the only config and the user
`modes/` folder doesn't exist: create the folder and copy `config.json` in as
`default.json`, synthesizing a `meta` block (`id: "default"`,
`name: "Default"`). Nothing breaks; the user simply now has one mode.

---

## Part B: The Mode Designer

A utility so a teacher or citizen-science coordinator can build a mode **without
touching JSON or knowing object names**.

### B.1 Why it must run *inside* QGIS

The hard part of authoring a mode is knowing what tools exist and what their
tokens are (`mFileToolBar:mActionNewProject`). A standalone web app can't know
that. A dialog **inside the running QGIS** can:

- Enumerate every toolbar, action, panel, and processing algorithm live (the
  plugin already has `getAlgorithms()`, `getProviders()`, etc.).
- Show each tool with its **real icon and real label**.
- Resolve tokens both ways for round-trip editing and live preview.

So the Mode Designer ships as part of the plugin: a `QDialog` opened from
*Manage modes…*.

### B.2 Dialog layout

```
┌─ Mode Designer ────────────────────────────────────────────────┐
│ Mode:  [Raster Processing            ]  Icon:[▣]  [Description] │
├───────────────┬─────────────────────────────────────────────────┤
│ PALETTE       │  LAYOUT CANVAS                                   │
│ [search…]     │   ┌ Top toolbar ──────────────────────────────┐ │
│ ▸ File        │   │ [New][Open][Save] | [▾Add Layer] | [▾Zoom] │ │
│ ▸ Navigation  │   └────────────────────────────────────────────┘ │
│ ▸ Selection   │   ┌ Left toolbar ─┐                              │
│ ▸ Digitizing  │   │ [Edit][Add..] │   [+ Add toolbar]            │
│ ▾ Processing  │   └───────────────┘                              │
│    ▸ Vector   │                                                  │
│    ▾ Raster   │  PANELS                                          │
│       Hillsh… │   Layers      ( ) Hidden (•) Visible  Area[Left] │
│       Slope   │   Browser     (•) Hidden ( ) Visible  Area[Left] │
│ ▸ Plugins     │                                                  │
│ ▸ Panels      │  STATUS BAR / PROVIDERS  [checklists]            │
├───────────────┴─────────────────────────────────────────────────┤
│ [Pick from QGIS]  [Live Preview]  [Validate]   [Save] [Save As]  │
└──────────────────────────────────────────────────────────────────┘
```

- **Palette (left)** — a searchable tree of everything available, grouped by
  source (File, Navigation, Processing › Raster, Plugins, Panels…). Each leaf
  is the real icon + label; the underlying token is hidden metadata.
- **Layout canvas (center)** — the mode being built. Toolbar strips per area
  (top/left/right/bottom). Drag a tool from the palette into a strip; drag
  within a strip to reorder.
- **Panels / status bar / providers** — simple controls (tri-state per panel,
  checklists for the rest).
- **Footer** — Pick from QGIS, Live Preview, Validate, Save / Save As.

### B.3 Direct manipulation, no tokens

Interactions map onto the token grammar behind the scenes:

| User action | Produced config |
| :-- | :-- |
| Drag a tool into a strip | `parent:identifier` token appended to `items` |
| Select 2+ adjacent items → *Group* | wrap them in a JSON array (dropdown) |
| Right-click → *Add separator* | `separator` |
| Right-click → *Add heading…* | `section:Label` |
| Drag in a processing algorithm | algorithm id token (or into an `algorithms` group) |
| Tri-state a panel | `panels` entry `fixed:`/`hidden:` + area |

The Designer is a **bidirectional mapper**:

- **Build the palette (read):** walk QGIS once; for every action record
  `(token, icon, label, source group)`. This index is also what the runtime
  interpreter could share.
- **Save (write):** serialize the canvas back into the token grammar — exactly
  the JSON the existing interpreter already understands. *No interpreter change
  is needed; the Designer just produces valid input.*
- **Open an existing mode (round-trip):** parse the JSON, resolve each token
  back to a live object to recover its icon/label, and render it on the canvas.
  A token that **doesn't resolve** (a tool from an uninstalled plugin) is shown
  as a greyed "Unknown tool" placeholder so it is preserved on save rather than
  silently dropped.

### B.4 "Pick from QGIS" capture mode

The most non-developer-friendly feature. The user clicks **Pick from QGIS**,
the Designer minimizes, and the user simply **clicks the actual button in real
QGIS** that they want. The Designer installs an event filter, highlights the
hovered action, and on click resolves the widget/action under the cursor to a
token and drops it onto the canvas. "Show me the button you want" beats
"find it in a tree."

### B.5 Preview and validation

- **Live Preview** applies the in-progress mode to QGIS temporarily (reusing
  `apply_mode()`), with a *Back to editing* banner. The author sees the real
  result, then returns to the Designer.
- **Validate** runs the JSON Schema check plus semantic checks (see below)
  before save, listing problems inline.

### B.6 Guard rails for non-developers

- **Never display tokens or object names** — only icons and labels.
- **Always provide an exit.** A mode with no `mActionDisableQGISLight` and no
  mode switcher would trap the user. The Designer enforces an exit path, and
  the runtime should *always* inject the mode switcher + exit control into the
  simplified toolbar regardless of the mode file, so a user can never get stuck.
- **Warn on empty toolbars**, on duplicate toolbar ids, on a mode with zero
  toolbars.
- **New mode starts from a copy** of an existing mode, never a blank canvas.
- **Undo/redo** within the Designer.
- **Confirm destructive changes** (deleting a mode, resetting to default).

### B.7 Technology

- PyQt `QDialog`, consistent with the plugin and able to introspect QGIS.
- Palette and toolbar strips: Qt model/view with drag-and-drop; the MIME
  payload carries the token. Strips are `QListView`/`QListWidget` with
  `InternalMove` for reordering.
- Reuses the plugin's existing resolution engine for preview; adds the
  token→metadata index for the reverse direction.
- A bundled JSON Schema drives both validation and (optionally) generic
  property editors.
- *Alternative considered:* a bundled HTML/JS editor. Rejected as the primary
  approach because it cannot introspect the live QGIS for icons, labels, and
  available tools — though it could import a JSON dump the plugin exports.

---

## Phased roadmap

Each phase is independently shippable.

| Phase | Scope | Effort |
| :-- | :-- | :-- |
| **1. Multi-file loading** | `meta` block, `modes/` folders, `qgislight/mode` setting, migration of the current config. Author JSON by hand. | Low |
| **2. Mode picker + manager** | Split toggle button, in-canvas switcher, the `enable`/`apply_mode`/`disable` refactor, a read-only Manage Modes dialog (list / set active / duplicate / import / export / delete). | Medium |
| **3. Visual Mode Designer** | Palette + layout canvas + drag-and-drop, save/round-trip, JSON Schema validation. | High |
| **4. Polish** | "Pick from QGIS" capture, live preview, guard rails, undo/redo. | Medium |

Phase 1 + 2 already deliver the user's core request — several named modes,
selectable and applied dynamically. Phases 3–4 make them authorable by
non-developers.

## Open questions / risks

- **Provider switching** is genuinely limited by QGIS (restart to restore). The
  shared-`providers` decision in [A.5](#a5-what-switches-live-and-what-does-not)
  is the cleanest resolution but should be confirmed with the maintainers.
- **Action reuse across modes** — QGIS Light reattaches the *same* `QAction`
  objects to its toolbars. Tearing down and rebuilding on every mode switch
  must not `deleteLater()` actions it borrowed from QGIS (only ones it created,
  e.g. algorithm wrappers and `section:` separators). The current `disable()`
  already only deletes the *toolbars*, not borrowed actions — that invariant
  must hold for `apply_mode()` too.
- **Performance** — a mode switch rebuilds toolbars; should be sub-second, but
  worth measuring with large `algorithms` groups.
- **Schema evolution** — commit to the `meta.schema` integer from Phase 1 so
  later format changes are migratable.

---

## Design questions

These answer the open design questions raised in `DesignQuestions.md`.

### Q1 — New plugin, or extend the current one?

**Extend the current plugin.** Multiple modes is not a separate concern — it
*is* the existing config-driven mechanism, just loading one config out of
several. A separate plugin would have to duplicate the whole engine
(`enable`/`disable`, token resolution, `addItems`) and then fight the original
for control of the same QGIS main window: two plugins both hiding the menu bar,
both capturing an "original layout", both adding a toggle button, both writing
to `QgsSettings`. Their state would collide.

Reasons to extend:

- The multi-mode refactor ([A.4](#a4-applying-a-mode-dynamically--the-enabledisable-refactor))
  is *internal* — splitting `enable()` into "capture original layout" and
  "apply a config". It is not a rewrite.
- One codebase, one `metadata.txt`, one dependency set, one home for the token
  resolver and the token→metadata index the Designer needs.
- Existing users keep working: the migration in
  [A.7](#a7-migrating-from-todays-single-config) upgrades a single `config.json`
  to a one-mode setup in place.

The only component with a credible case for separation is the **Mode Designer**
itself — a heavyweight authoring UI that a classroom QGIS never needs at
runtime. Even so, prefer keeping it in the same repository and **lazy-loading**
the dialog (import it only when *Manage modes…* is clicked) so it costs nothing
at startup. If footprint ever truly matters, ship it as a *companion* plugin
that declares `plugin_dependencies` on qgis-light and reuses its engine — but
the mode-loading runtime must stay in the core plugin.

### Q2 — How are plugins handled as they inject controls into the UI?

QGIS plugins (Python and C++) add UI through `QgisInterface`: `addToolBar()` /
`addToolBarIcon()`, `addPluginToMenu()` and its vector/raster/database variants,
`addDockWidget()`, or by creating `QToolBar` / `QDockWidget` children of the
main window directly. **Every one of those controls ends up as an ordinary Qt
object in the main-window widget tree** — exactly the tree QGIS Light's token
resolver already walks with `findChild` / `findChildren`.

So QGIS Light needs no special plugin API. A plugin-contributed button is
referenced by the same `parent:identifier` token grammar as a native one —
`config.json` today already carries `mWebToolBar:QuickMapServices` and
`mPluginToolBar:DataPlotly`.

Two consequences shape the design:

- **Timing.** Plugin controls exist only *after* that plugin loads, and load
  order is not guaranteed. This is the whole reason `enable()` is deferred to
  `mainwindow.initializationCompleted`
  ([§2.4 of the customization guide](customizing-qgis-light.md#24-the-deferred-enable-trick))
  — so every plugin's toolbars exist before QGIS Light hides or references them.
- **Inconsistent naming.** Many Python plugins never call `setObjectName()` on
  their actions. That is why `findAction` also matches on `text()` and
  `toolTip()` — QuickMapServices and DataPlotly are matched by visible text,
  not by object name.

Edge case worth noting: a plugin the user **enables *after* QGIS Light is
already in light mode** will have its toolbar appear un-hidden, because
`enable()` has already run. The [A.4](#a4-applying-a-mode-dynamically--the-enabledisable-refactor)
refactor makes this easy to fix — `apply_mode()` can re-run the "hide everything
not in this mode" sweep, or the plugin can watch for newly added toolbars.

### Q3 — Can the Designer handle plugins? Leave them active but hide their UI selectively?

**Yes — and this is already how QGIS Light works.** QGIS Light never disables or
uninstalls a plugin; the plugin stays loaded and its code keeps running. QGIS
Light only hides *toolbars and panels*. Anything not referenced by the active
config is hidden; a plugin tool you *do* want is surfaced with a token. "Active
but UI hidden" is the native model, not a new feature to build.

For the Mode Designer specifically:

- Plugin-contributed actions, toolbars, and docks appear in the palette
  ([B.2](#b2-dialog-layout)) for free, because they sit in the same widget tree
  the palette is built from. They should be grouped under a **"Plugins"** branch
  and labelled by their originating plugin.
- **Selective hiding is the default** — anything not dragged onto the canvas is
  hidden. **Selective showing** is one drag from the palette.
- The palette reflects whatever is installed *on the authoring machine now*. A
  mode that references a plugin tool absent on another machine resolves to the
  greyed "Unknown tool" placeholder
  ([B.3](#b3-direct-manipulation-no-tokens)) — preserved, not lost.
- Therefore a mode should record its plugin dependencies, e.g.
  `meta.requires: ["DataPlotly"]`, so the manager can warn before activating a
  mode whose plugins are missing.

Caveats:

- QGIS Light hides UI; it does **not** stop a plugin's background behaviour or
  its processing providers. That is the intended scope.
- Tools a plugin contributes only to a **menu** (`addPluginToMenu`) are not
  reachable while the menu bar is hidden unless surfaced as a toolbar token; the
  plugin menu's items can still be tokenized via `mPluginMenu:…`.
- A few plugins assume their dock is always visible; hiding it should be tested
  per-plugin (most simply re-show their dock when their action fires).

### Q4 — Can Settings ▸ Interface Customization, or its output, be used here?

**Interface Customization** stores its state in `QGISCUSTOMIZATION3.ini` under
the profile's `QGIS/` folder. It is QGIS's built-in UI-trimming tool: a checkable
tree of nearly every widget, applied **at the next startup** by *hiding*
elements, and exportable to an `.xml` file for sharing between users.

It is the closest built-in to QGIS Light, and the QGIS Light README already
explains why it is not enough: it can only **remove** elements — it cannot
regroup tools into dropdown buttons, build new toolbars, or reorder them. It
also needs a restart and works by widget-path visibility rather than by
rebuilding toolbars.

How it can still help this project:

- **As a precedent.** Its *"Switch to catching widgets in main application"*
  mode — click a real widget to select it — is exactly the interaction proposed
  for the Designer's [B.4 "Pick from QGIS"](#b4-pick-from-qgis-capture-mode)
  feature. The mechanism is proven; reuse the idea.
- **As a name catalogue.** The customization tree is an organized inventory of
  toolbar / panel / widget object names and their hierarchy. It can cross-check
  the Designer's palette — though walking the live widget tree yields the same
  names *plus* icons and labels, so it is a sanity check, not a data source.
- **Not as a format.** Do **not** build on `QGISCUSTOMIZATION3.ini` or emit it.
  Its removal-based, restart-required, path-keyed model cannot express
  dropdowns, regrouping, or runtime switching — the very things QGIS Light
  exists to do. Importing it could at best seed *which top-level toolbars and
  panels to keep*, a lossy one-way hint.

**Interaction risk to document:** if a user runs Interface Customization *and*
QGIS Light, customization hides elements at startup that QGIS Light then tries
to resolve as tokens — producing `Invalid identifier token` failures. The plugin
should detect that customization is enabled and warn, and the docs should
recommend not combining the two.

### Q5 — Why do some buttons stay greyed out?

Almost always because QGIS Light is **faithfully reflecting QGIS's own
context-sensitive state**. QGIS Light reuses the *actual* `QAction` objects; an
action's enabled/disabled state is owned by QGIS core, not by the plugin. Many
actions are deliberately disabled until their precondition is met:

- **Edit actions** (Add Feature, Vertex Tool, Save Edits, Undo/Redo) — disabled
  unless a layer is active *and* in an edit session; Undo/Redo are also disabled
  when there is nothing to undo.
- **Selection-dependent** (Pan/Zoom to Selected, Deselect, table "selected") —
  disabled when nothing is selected.
- **Layer-dependent** (Identify, Open Attribute Table, Field Calculator, Zoom to
  Layer) — disabled with no suitable active layer.
- **History** (Zoom Last / Next) — disabled at the ends of the zoom history.

A freshly opened QGIS with no project or layers therefore shows many greyed
buttons; they enable themselves as the user opens data, selects features, or
starts editing. This is normal QGIS behaviour, not a bug.

A **second, QGIS Light-specific** cause: an action can stay disabled because
QGIS Light hid the panel, or removed the provider or feature, that the action
depends on. If a button is greyed and *should* be usable, check whether the
active mode dropped a dependency it needs.

Design implications:

- For non-technical users a permanently-greyed button is confusing. The
  Designer's **Live Preview** ([B.5](#b5-preview-and-validation)) surfaces this;
  the Designer could optionally flag tools that are context-sensitive.
- The runtime could attach explanatory tooltips ("Select a layer to enable…")
  for the common cases — a small expansion item, not a blocker.

---

## References

- Current architecture — [`customizing-qgis-light.md`](customizing-qgis-light.md)
- Plugin source — `src/qgis-light/qgis_light.py`, `src/qgis-light/config.json`
- [Working with user profiles (QGIS docs)](https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_configuration.html#working-with-user-profiles)
- [QgisInterface class (PyQGIS docs)](https://qgis.org/pyqgis/master/gui/QgisInterface.html)
