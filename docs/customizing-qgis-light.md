# Customizing QGIS Light — How It Works and How to Extend It

This document explains the internal workings of the **QGIS Light** plugin, what
you can change without writing any code, how to do it, and what would require
Python changes. If you only want to add or remove buttons, jump straight to
[Section 4 — Customization recipes](#4-customization-recipes).

---

## 1. What QGIS Light is

QGIS Light is a **QGIS plugin** that replaces QGIS's full interface with a
stripped-down one — fewer toolbars, fewer panels, fewer processing algorithms —
aimed at non-technical users (secondary education, citizen science).

It does **not** add GIS functionality. It *hides and regroups* UI elements that
QGIS (and other plugins) already provide. Everything QGIS Light shows is an
existing QGIS tool surfaced through a simpler layout.

Key consequence for customization: **you are not building new tools, you are
choosing which existing QGIS tools to expose and how to arrange them.**

---

## 2. How the plugin works

### 2.1 Two-file design: interpreter + spec

The whole plugin is essentially two files:

| File | Role |
| :-- | :-- |
| `src/qgis-light/qgis_light.py` | The **interpreter** — class `QGISLightPlugin`. ~600 lines of Python. You rarely need to touch it. |
| `src/qgis-light/config.json` | The **specification** — a declarative description of the simplified interface. **This is what you edit to customize the plugin.** |

The Python code reads `config.json` once at startup and builds the interface
from it. Changing the simplified interface almost always means editing
`config.json`, not the Python.

### 2.2 Plugin lifecycle

QGIS drives the plugin through a fixed lifecycle:

1. **`classFactory(iface)`** in `__init__.py` — QGIS calls this when the plugin
   loads. It returns a `QGISLightPlugin` instance.
2. **`__init__()`** — stores the QGIS interface handle, finds the plugin
   directory, and **loads `config.json` into `self.config`**. (This is why a
   `config.json` edit only takes effect after a plugin reload — see
   [4.1](#41-the-editreloadtest-cycle).)
3. **`initGui()`** — adds the green QGIS Light toggle button to the file toolbar
   and a "Toggle QGIS Light" item to the View menu. If simplified mode was
   already on (see persistence below), it schedules `enable()` to run later.
4. **`enable()` / `disable()`** — switch simplified mode on and off. These are
   the heart of the plugin.
5. **`unload()`** — QGIS calls this on teardown; it restores the standard
   interface and removes the toggle button.

### 2.3 Enable / disable — a toggle, not an install

QGIS Light **does not install or uninstall** the simplified interface.
Simplification is a *state* you toggle. That state is persisted in
`QgsSettings` (QGIS's settings store) under the `qgislight/` namespace:

| Setting key | Meaning |
| :-- | :-- |
| `qgislight/enabled` | `"true"` when simplified mode is active. |
| `qgislight/toolbars` | The **original** toolbar layout, captured before simplification, so it can be restored. |
| `qgislight/panels` | The **original** panel layout, captured the same way. |

When you click the green button, `enable(store=True)` runs:

- Captures the current toolbar and panel layout into `QgsSettings`.
- Hides the menu bar and disables the right-click context menu.
- Hides every existing toolbar.
- Builds the toolbars defined in `config.json`.
- Hides panels not listed in `config.json`; positions the listed ones.
- Removes data-source / data-item providers not on the allowlist.
- Hides the status-bar widgets listed in `config.json`.

Clicking the colored QGIS logo (the synthetic *Disable QGIS Light* action) runs
`disable(store=True)`, which removes the simplified toolbars and calls
`restoreLayout()` to put the captured original layout back.

> Because the original layout is *captured* rather than assumed, QGIS Light can
> coexist with whatever toolbar arrangement the user already had.

### 2.4 The deferred-enable trick

If `qgislight/enabled` is already `"true"` when QGIS starts, `initGui()` does
**not** call `enable()` immediately. Instead it connects `enable()` to the
`mainwindow.initializationCompleted` signal.

Why: other plugins (QuickMapServices, DataPlotly, …) create their own toolbars
and actions during startup. QGIS Light must wait until *all* of them exist
before it can hide or reference them. If it ran too early, tokens like
`mWebToolBar:QuickMapServices` would resolve to nothing.

### 2.5 Token resolution — the core mechanism

`config.json` never holds actual buttons. It holds **string tokens** that name
existing QGIS UI elements. Two methods turn tokens into a live interface:

- **`getItems(token)`** — resolves one token to one or more live Qt objects.
- **`addItems(parent, items)`** — recursively places resolved objects into a
  toolbar or menu.

The token vocabulary:

| Token form | Resolves to | Example |
| :-- | :-- | :-- |
| `parent:identifier` | A single action found inside a named widget. The widget is matched by object name; the action inside it is matched by **object name, visible text, or tooltip**, searched recursively through submenus. | `mFileToolBar:mActionNewProject` |
| `parent:identifier*` | The whole **dropdown menu** belonging to that action (the trailing `*` is a wildcard). | `mDigitizeToolBar:mActionDigitizeShape*` |
| `parent:` | **Every** action of the named widget (empty identifier). | `mMapNavToolBar:` |
| `separator` | A plain divider. | `separator` |
| `section:Label` | A divider with a heading caption. Empty label (`section:`) = plain divider inside a dropdown. | `section:Interpolation` |
| `algorithms:<group>` | A dropdown tool button built from an `algorithms` group defined elsewhere in `config.json`. | `algorithms:vector` |
| A processing algorithm id | A button that opens that algorithm's dialog. | `native:buffer` |
| `mActionDisableQGISLight` | The synthetic "exit simplified mode" button. | `mActionDisableQGISLight` |
| A JSON **array** of tokens | All the tokens grouped into **one dropdown button**; the first becomes the default, and the last one used becomes the new default. | `["mMapNavToolBar:mActionZoomIn", "mMapNavToolBar:mActionZoomOut"]` |

The important idea: a token like `mFileToolBar:mActionNewProject` reuses the
*actual* QGIS "New Project" `QAction` object. QGIS Light adds that same object
to its own toolbar. There is no copy — clicking it triggers the genuine QGIS
behavior. That is why QGIS Light can expose any QGIS tool without
re-implementing it.

### 2.6 How `addItems` builds dropdowns

When `addItems` meets a JSON array, it creates a `QMenu`, fills it, then wraps it
in a `QToolButton` with `MenuButtonPopup` mode — a button with a small arrow.
The first entry is shown by default; selecting another entry promotes it to the
visible default. This is how grouped tools (zoom in / out / full extent / …)
collapse into a single space-saving button.

---

## 3. `config.json` reference

`config.json` has five top-level sections.

### 3.1 `toolbars`

Defines the simplified toolbars to create. Each entry is keyed by a **unique
object name** (must not collide with QGIS or other plugins) and contains:

```json
"mMainToolBar": {
  "title": "Main Toolbar",
  "area": "top",
  "items": [ ... ]
}
```

- `title` — the human-readable toolbar name.
- `area` — `top`, `bottom`, `left`, or `right`.
- `items` — an ordered list of [tokens](#25-token-resolution--the-core-mechanism).

The stock config defines two toolbars: `mMainToolBar` (top) and
`mEditingToolBar` (left). You can add more.

### 3.2 `algorithms`

Named groups of processing algorithms, rendered as dropdown buttons and
referenced from toolbars with `algorithms:<name>`:

```json
"vector": {
  "icon": ":/images/themes/default/mIconVector.svg",
  "items": [ "native:buffer", "native:clip", "section:Boundary", ... ]
}
```

- `icon` — a Qt resource path (`:/...`) or a file path for the button icon.
- `items` — processing algorithm ids and `section:` headings.

The stock config groups algorithms into `raster` and `vector`.

### 3.3 `panels`

Controls which dock panels survive simplification:

```json
"panels": {
  "Layers": "fixed:left",
  "ResultsViewer": "hidden:right"
}
```

Each value is `<state>:<area>`:

- `fixed` — panel is visible and **undockable** (cannot be moved or floated).
- `hidden` — panel starts hidden but is **pre-positioned** to the given area,
  so when a tool later needs it, it reappears docked where you expect.
- `area` — `top`, `bottom`, `left`, `right`.

**Any panel not listed here is simply hidden.** The practical difference between
"not listed" and `hidden:<area>` is that a listed panel gets a defined docking
area for when it pops back up.

### 3.4 `providers`

Allowlists of data-access components:

```json
"providers": {
  "data_sources": ["delimitedtext", "gdal", "ogr", "wms", ...],
  "data_items": ["files", "GPKG", "WMS", ...]
}
```

- `data_sources` — providers shown in the Data Source Manager dialog.
- `data_items` — providers shown in the Browser tree.

Providers **not** on a list are removed from the registry. ⚠️ Re-enabling a
removed provider requires a **QGIS restart** — QGIS Light cannot add it back
live.

### 3.5 `statusbar`

Status-bar widgets to hide, keyed by object name with value `false`:

```json
"statusbar": {
  "LocatorWidget": false,
  "mRotationLabel": false
}
```

Only `false` does anything (it hides the widget). Remove a line to keep the
widget visible.

---

## 4. Customization recipes

### 4.1 The edit–reload–test cycle

1. The live `config.json` is the one inside the plugin folder of your QGIS
   profile, typically:
   - Windows: `%APPDATA%\QGIS\QGIS3\profiles\<profile>\python\plugins\qgis-light\config.json`
     (QGIS 4 uses a `QGIS4` folder). If you symlinked `src/qgis-light/` there,
     editing the repo file edits the live one.
2. `config.json` is read **once**, in the plugin constructor. After editing it:
   - Reload the plugin with the **Plugin Reloader** plugin, *or* restart QGIS.
   - Then toggle QGIS Light **off and on** so the toolbars rebuild.
3. Watch **Log Messages → "QGIS Light" tab** for warnings like
   `Invalid identifier token ...` or `Invalid parent object name ...` — those
   tell you a token didn't resolve.
4. `config.json` must stay valid JSON — a trailing comma or missing bracket
   stops the plugin from loading at all.

> 💡 **Tip:** Test on a throwaway QGIS *user profile* first. If a config change
> breaks the interface, switch back to the default profile to recover.

> ⚠️ **Upgrades overwrite `config.json`.** It lives inside the plugin folder, so
> reinstalling or updating QGIS Light replaces your customized file. Keep a copy
> of your edits.

### 4.2 Discovering object names (the most important skill)

Every token depends on knowing the **object name** of a toolbar, action, panel,
algorithm, or status-bar widget. The reliable way to discover them is the QGIS
**Python Console** (`Plugins → Python Console`).

**List all toolbars:**

```python
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QToolBar, QDockWidget
mw = iface.mainWindow()
for tb in sorted(mw.findChildren(QToolBar), key=lambda t: t.objectName()):
    print(tb.objectName(), "—", tb.windowTitle())
```

**List the actions inside one toolbar (or any menu):**

```python
tb = mw.findChild(QToolBar, "mFileToolBar")
for a in tb.actions():
    print(repr(a.objectName()), "|", repr(a.text()))
```

The first column is what you put after the colon in a token. (Text or tooltip
also work, but object names are the most stable across QGIS versions.)

**List all panels:**

```python
for d in mw.findChildren(QDockWidget):
    print(d.objectName(), "—", d.windowTitle())
```

**List every processing algorithm id:**

```python
from qgis.core import QgsApplication
for p in QgsApplication.processingRegistry().providers():
    for alg in p.algorithms():
        print(alg.id(), "|", alg.displayName())
```

The plugin also ships helper methods (`getAlgorithms`, `getProviders`,
`getDataSourceProviders`, `getDataItemProviders`) you can call from the console
on the loaded plugin instance:

```python
from qgis.utils import plugins
ql = plugins['qgis-light']
ql.getAlgorithms()            # [{'id', 'group', 'name'}, ...]
ql.getDataSourceProviders()   # provider names for the providers allowlist
```

(Run `Processing → Toolbox` once first so the algorithm registry is populated.)

### 4.3 Remove a control

Delete its token line from the relevant `items` array. To drop the field
calculator from the main toolbar, remove:

```json
"mAttributesToolBar:mActionOpenFieldCalc",
```

### 4.4 Add a single control

Find the action's parent widget and object name with the console snippets
above, then add the `parent:action` token where you want it. To add the
"Show Bookmarks" button next to Identify:

```json
"mAttributesToolBar:mActionIdentify",
"mAttributesToolBar:mActionShowBookmarks",
```

### 4.5 Group controls into a dropdown

Wrap several tokens in a JSON array. They collapse into one dropdown button:

```json
[
  "mAttributesToolBar:mActionMeasure",
  "mAttributesToolBar:mActionMeasureArea",
  "mAttributesToolBar:mActionMeasureBearing"
]
```

### 4.6 Add a "Layout Manager" button ✅

This is a worked example of the question *"can we add a Layout Manager
button?"* — **yes.** Layouts are intentionally excluded by default (the design
target assumes users don't publish print maps), but nothing stops you adding
them back.

The three layout/report actions live on QGIS's file toolbar (`mFileToolBar`),
with these object names:

| Action | Object name |
| :-- | :-- |
| Layout Manager | `mActionShowLayoutManager` |
| New Print Layout | `mActionNewPrintLayout` |
| New Report | `mActionNewReport` |

**Option A — a single Layout Manager button.** Add one line to `mMainToolBar`'s
`items`:

```json
"separator",
"mFileToolBar:mActionShowLayoutManager",
"separator",
```

**Option B — a layout dropdown** (manager + new layout + new report):

```json
[
  "mFileToolBar:mActionShowLayoutManager",
  "mFileToolBar:mActionNewPrintLayout",
  "mFileToolBar:mActionNewReport"
]
```

Reload the plugin, toggle QGIS Light off and on, and a Layout Manager button
appears. Clicking it opens the genuine QGIS Layout Manager.

Notes:

- If `mFileToolBar:mActionShowLayoutManager` ever fails to resolve in your QGIS
  version, the same action exists in the Project menu — use
  `mProjectMenu:mActionShowLayoutManager` instead (any named widget, including
  menus, works as a token parent).
- The **Layout Designer** opens as a separate top-level window. QGIS Light only
  simplifies the main window, so the designer keeps its full interface — QGIS
  Light does not simplify the layout editor itself.

### 4.7 Add a whole new toolbar

Add a new key under `toolbars` with a unique object name:

```json
"mFieldworkToolBar": {
  "title": "Fieldwork",
  "area": "right",
  "items": [
    "mAttributesToolBar:mActionIdentify",
    "mDigitizeToolBar:mActionAddFeature"
  ]
}
```

### 4.8 Add or remove a processing algorithm

Edit the `items` list of the `raster` or `vector` group under `algorithms`. Add
an algorithm id (find it with the console snippet in [4.2](#42-discovering-object-names-the-most-important-skill)):

```json
"native:buffer",
"native:pointsalonglines",
```

`section:Heading` lines insert captions in the dropdown. To create an entirely
new algorithm group, add a new key under `algorithms` (with `icon` and `items`)
and reference it from a toolbar with `algorithms:<yourname>`.

A processing algorithm id can also be placed **directly** in a toolbar's
`items` (without a group) — it becomes a standalone button that opens that
algorithm's dialog.

### 4.9 Keep a panel visible

Add it to `panels`. To keep the Browser panel docked on the left:

```json
"panels": {
  "Browser": "fixed:left",
  ...
}
```

Use `fixed` for always-on undockable panels, `hidden:<area>` for panels that
should stay out of the way until a tool needs them.

### 4.10 Show or hide status-bar widgets

Add `"<objectName>": false` under `statusbar` to hide a widget; remove the line
to keep it. The stock config hides the locator search box and rotation
controls.

### 4.11 Re-enable a data provider

Add the provider's name to `data_sources` or `data_items` under `providers`.
Remember: re-enabling a previously removed provider needs a **QGIS restart**.

---

## 5. What config alone can and cannot do

**Can do (config only):**

- Add, remove, reorder any existing QGIS / plugin tool.
- Create dropdown groups and extra toolbars.
- Choose toolbar/panel placement and which panels show.
- Curate the processing-algorithm shortlist.
- Hide status-bar widgets and data providers.

**Cannot do without Python changes:**

- Add brand-new tools that run custom Python logic.
- Rename or re-icon an individual reused action (it keeps QGIS's original label
  and icon — only `algorithms` *group* buttons get a custom icon).
- Restructure or partially keep the menu bar (it is hidden wholesale).
- Show or hide tools conditionally (e.g. by layer type or user role).
- Simplify the Layout Designer or the attribute-table windows.
- Add custom widgets (sliders, dropdowns of layers, search boxes).

---

## 6. Ideas for expansion (these need Python changes)

These would extend `qgis_light.py`, not just `config.json`:

- **In-app config editor / settings dialog** — let teachers tweak the toolbar
  without hand-editing JSON.
- **Multiple presets** — ship several `config.json` profiles (e.g. "vector
  basics", "raster analysis") and switch between them.
- **User-owned config location** — load `config.json` from the QGIS profile
  directory if present, so plugin upgrades don't overwrite customizations.
  (Currently the config is read only from inside the plugin folder.)
- **Custom action injection** — a token type that runs an arbitrary Python
  callable, enabling purpose-built buttons ("Load today's class dataset",
  "Upload observations").
- **Per-token visibility rules** — show/hide tools based on the active layer's
  geometry type or a "skill level" setting.
- **Localization** — translate `title`/`section` strings via Qt's translation
  system for non-English classrooms.
- **A guided first-run wizard** — walk a new user through enabling the mode and
  choosing a preset.
- **Granular menu simplification** — instead of hiding the entire menu bar,
  rebuild a trimmed menu bar from tokens (same mechanism as toolbars).
- **Live config reload** — re-read `config.json` and rebuild without a full
  plugin reload.

The token-resolution architecture ([2.5](#25-token-resolution--the-core-mechanism))
is the natural extension point: most new capabilities are a new token type
handled inside `getItems()` plus, where needed, a new `config.json` section.

---

## 7. Troubleshooting

| Symptom | Likely cause |
| :-- | :-- |
| A button is missing after a config edit | Token didn't resolve — check the "QGIS Light" log tab for `Invalid identifier token` / `Invalid parent object name`. Re-verify names with the console snippets in [4.2](#42-discovering-object-names-the-most-important-skill). |
| Plugin won't load at all | `config.json` is not valid JSON (trailing comma, missing bracket/quote). |
| Edit had no effect | The plugin wasn't reloaded — `config.json` is read only at construction. Reload via Plugin Reloader, then toggle off/on. |
| A plugin's tool (e.g. QuickMapServices) is missing | That plugin loaded after QGIS Light, or isn't installed. QGIS Light depends on **QuickMapServices** and **DataPlotly**. |
| Removed data provider still gone after disabling QGIS Light | Provider removal needs a QGIS **restart** to undo. |
| Interface broke and toggle won't fix it | Switch QGIS **user profile**, or clear the `qgislight/` keys in `QgsSettings`. |

---

## 8. References

- Plugin source: `src/qgis-light/qgis_light.py`, `src/qgis-light/config.json`
- Project README — [`README.md`](../README.md) (design scope and rationale)
- Codebase guide — [`CLAUDE.md`](../CLAUDE.md)
- QGIS action/menu object names — [`qgisapp.ui` in the QGIS source](https://github.com/qgis/QGIS/blob/master/src/ui/qgisapp.ui)
- [QgisInterface class (PyQGIS docs)](https://qgis.org/pyqgis/master/gui/QgisInterface.html)
- [Working with user profiles (QGIS docs)](https://docs.qgis.org/latest/en/docs/user_manual/introduction/qgis_configuration.html#working-with-user-profiles)
- Background paper: Girgin, S., Gohil, J., and Mydur, I. (2025), *A streamlined
  GIS interface for Citizen Science activities: QGIS Light*,
  https://doi.org/10.5194/isprs-archives-XLVIII-4-W13-2025-127-2025
