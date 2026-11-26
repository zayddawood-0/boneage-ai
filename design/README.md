# Design reference — BoneAge AI frontend

These files are the source of the approved UI design. The React frontend must reproduce them **exactly**: same layout, spacing, sizes, colours, fonts, copy, icons, states and light/dark themes.

They were exported from a design canvas, so they are a **specification, not runnable pages**. Read them as HTML + inline CSS; do not try to open them in a browser or import them.

## Screens

| File | Screen | Route (suggested) |
|---|---|---|
| `Login.html` | Sign in | `/login` |
| `Main.html` | Dashboard (light) | `/` |
| `Dark.html` | Dashboard (dark) — same markup as `Main.html`, opens in dark theme. Reference for how dark mode should look. | — |
| `NewAnalysis.html` | New analysis (3 steps) | `/analysis/new` |
| `Queue.html` | Review queue | `/queue` |
| `Case.html` | Case report | `/cases/:id` |
| `Patients.html` | Patients | `/patients` |
| `Model.html` | Model performance | `/model` |
| `Settings.html` | Settings | `/settings` |

Links between screens use `href="X.dc.html"` — map each to the route above.

## How to read the format

- Everything visual is inside `<x-dc> … </x-dc>`. Styles are **inline** (`style="…"`); copy them into Tailwind classes or CSS modules value-for-value.
- `<helmet>` holds the Google Fonts link (IBM Plex Sans + IBM Plex Mono) and a few base styles.
- `{{ name }}` is a value bound from the component's logic at the bottom of each file (`class Component extends DCLogic { renderVals() { … } }`). `renderVals()` is where the data, computed styles and event handlers live.
- `<sc-for list="{{ rows }}" as="r">` = `rows.map(r => …)`.
- `<sc-if value="{{ cond }}">` = `{cond && …}`.
- `onClick="{{ fn }}"` = an onClick handler; `this.setState` = React state.
- `{{ rootStyle }}` on the root element sets the **theme CSS variables**. The `LIGHT` and `DARK` strings in `renderVals()` are the complete token sets — use them as-is for `:root` / `[data-theme="dark"]`.
- `var(--…)` in inline styles refers to those tokens. A few colours are fixed in both themes (sidebar `#1C1917`, primary button `#24614B` with white text, X-ray panel `#0E0D0C`, heatmap gradient).
- Text in square brackets like `[Doctor name]`, `[__] mo`, `[v_._]` is a placeholder to be filled with real data.
- Sample table rows in `renderVals()` are mock data; replace them with API data but keep the same shape and formatting (e.g. ages as `9y 2m`, gaps as `−2y 4m`).
