# Ocean Compound Extremes Infographic — Adding or Updating an Element

The current page separates content, presentation, behavior, and image assets:

- `Ocean Compound Extremes Infographic - scrolling.html` — semantic markup and copy
- `ocean-infographic.css` — design tokens, layout, typography, and states
- `ocean-infographic.js` — component lifecycle, charts, and interactions
- `ocean-map-helpers.js` — event data and pure map helpers
- `ocean-map-draw.js` — D3 map rendering
- `assets/img/` — every image used by the page

## 1. Find the right place

The HTML contains a two-column shell:

- `[data-ocx-left]` contains the sticky map, legend, and mechanism explorer.
- `[data-ocx-right]` contains the scrolling narrative panels and footer.
- `[data-ocx-dist]` is the two-column grid for the frequency, size, and season cards.

Search for a panel's visible heading or its `data-screen-label`. The source order now matches the
rendered order; JavaScript does not move panels after the page loads.

## 2. Add markup

Copy the nearest semantically similar panel, then:

1. Give the new element a descriptive `ocx-…` class.
2. Keep content and accessibility attributes in the HTML.
3. Put static visual declarations in `ocean-infographic.css`, not a `style` attribute.
4. Add a `data-*` hook only when JavaScript needs to find or update the element.
5. Use a real `<button>` for actions and provide an accessible name for non-text graphics.

Do not add runtime DOM moves to `_arrangeLayout()`. If placement is wrong, correct the HTML
structure or CSS grid/flex rules directly.

## 3. Follow the design system

Reusable colors are custom properties at the top of `ocean-infographic.css`, including:

- `--ocx-ink` — dark navy
- `--ocx-page` — page cream
- `--ocx-panel` — card cream
- `--ocx-border` — card border
- `--ocx-orange`, `--ocx-teal`, `--ocx-amber` — accent colors
- `--ocx-body`, `--ocx-muted` — body copy

Use Barlow Condensed for headings and labels and Source Sans 3 for body text. Reuse an existing
panel, heading, or utility class when it represents the same visual role. Add a modifier class for
an intentional variation instead of overriding styles inline.

## 4. Add behavior only when needed

Static elements require no JavaScript. For interactive elements:

1. Add a stable `data-*` hook in the template.
2. Bind listeners in the relevant initialization method in `ocean-infographic.js`.
3. Remove listeners or observers in `componentWillUnmount()` when they are attached to `window`,
   `document`, or another long-lived object.
4. Keep data and calculations out of rendering functions where practical.
5. Use CSS classes for static and hover/focus states; reserve direct `.style` updates for values
   that are genuinely computed at runtime, such as chart positions or live colors.

The mechanism explorer uses `data-m="…"` and `data-preset="…"` hooks inside `mechRef`. Its behavior
lives in the `_mech*` methods. The chart and map methods use React refs declared at the top of the
component class.

## 5. Map-related changes

The map's image fields live under `assets/img/`:

- `assets/img/annual/` — total, yearly, regional, and named-event fields
- `assets/img/definition_2015/` — MHW, OAX, compound, and combined definition fields

`ocean-map-helpers.js` defines the asset root and event records. `ocean-map-draw.js` constructs the
SVG and its interactions. The projection is fixed to equirectangular because the pre-baked images
are aligned to that projection.

To change bins or colors, edit the relevant script in `python/`, rebuild the images, and keep the
manifest and HTML legend synchronized. The build scripts write directly to `assets/img/…`.

## 6. Verify the change

Serve the directory rather than opening the HTML through `file://`:

```bash
python3 -m http.server 8000
```

Check at the intended 1400 px-or-wider layout and at a narrower viewport. Confirm that:

- no panel moved or changed size unintentionally;
- the browser console has no errors or missing assets;
- map hovers, year bars, table rows, definitions, and mechanism controls still work;
- keyboard focus is visible and interactive elements have accessible names;
- no new static `style="…"` or `style-*` attributes were introduced.
