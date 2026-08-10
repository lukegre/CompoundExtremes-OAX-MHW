# Building a scroll-driven "paper infographic" from a LaTeX/PDF manuscript

A pattern guide for agents. The deliverable is a single-page website that turns one
scientific paper into an explorable graphic: **a persistent visual on the left, a
scrolling narrative on the right, where narrative elements drive the visual.**

`index.html` + `ocean-infographic.{css,js}` in this repo is a reference implementation.
Nothing below depends on that paper's subject — swap the domain content and the
structure holds.

---

## 0. Before anything else: ask for visual references

The structure in this guide is fixed; the *look* is not, and you should not invent it.
Your first message to the user asks for inspiration:

> Before I start — drop me a few visual references for the theme and colours.
> Anything works: links to infographics or data-journalism pieces you like,
> screenshots, a poster or book spread, a palette, or an existing figure/slide
> template you want the page to match. Two or three is plenty. If you have a brand
> or institutional style (colours, fonts, logo), send that too.
>
> If you'd rather I just pick something, say so and I'll propose a direction first.

From what comes back, extract and **write down explicitly** before coding:

- a page background and a slightly lighter canvas tone for the stage column
- one accent hue per key quantity in the paper (two or three total, no more)
- a display face for headings/labels and a body face — plus how they are loaded
- the register: printed-poster, editorial, clinical/technical, playful
- ink and muted text colours, rule/border colour, and how emphasis is marked

Define all of it as CSS custom properties in one block at the top of the stylesheet
and never hard-code a colour below it. Restate the palette back to the user and get
a yes before you build out the sections — retrofitting a theme across a page like
this is far more work than agreeing on it up front. If the user declines to give
references, propose two contrasting directions in a sentence each and let them choose.

---

## 1. What you are building (the invariant)

```
┌──────────────────────────────────────────── sticky title bar ─────────┐
├────────────────────────────┬──────────────────────────────────────────┤
│  LEFT: STAGE (sticky)      │  RIGHT: STORY (scrolls)                  │
│                            │                                          │
│  ┌──────────────────────┐  │   [credits: paper title, authors, venue] │
│  │  primary visual      │  │   [intro: one paragraph — the claim]     │
│  │  = the paper's       │  │   ┌────────────────────────────────────┐ │
│  │    object of study   │  │   │ SECTION — claim 1                  │ │
│  │  + state badge       │  │   │  → its affordance sets stage state │ │
│  └──────────────────────┘  │   └────────────────────────────────────┘ │
│  ┌──────────────────────┐  │   ┌────────────────────────────────────┐ │
│  │  legend (reactive)   │  │   │ SECTION — claim 2                  │ │
│  └──────────────────────┘  │   │  → …                               │ │
│  ┌──────────────────────┐  │   └────────────────────────────────────┘ │
│  │  optional secondary: │  │   ┌────────────────────────────────────┐ │
│  │  controllable model  │  │   │ SECTION — claim 3                  │ │
│  └──────────────────────┘  │   └────────────────────────────────────┘ │
│                            │   […one section per claim, in order…]    │
│                            │   [footer: abbreviations, data, funding] │
└────────────────────────────┴──────────────────────────────────────────┘
```

Three rules define the genre:

1. **The stage never leaves the viewport** while the story scrolls past it.
2. **Every story section that mentions a quantity offers a way to see it** — hover,
   focus, drag, or click — and that interaction mutates the stage, not the story.
3. **The stage returns to a neutral default state** when the interaction ends. The
   reader can never get lost.

---

## 2. Extracting the story from the paper

Read the PDF/LaTeX and produce an intermediate plan **before writing any HTML**.

### 2a. Choose the stage

Find the paper's **primary object of study** — the thing every result is a statement
about. Usually one figure carries it. Ask: *what does the reader need to keep looking
at for the whole page to make sense?* That becomes the stage. It must be able to hold
many different states of the same shape (a field over space, a phase diagram, a
network, a genome track), because every story section will ask it for one.

If no single visual can hold the whole argument, the paper needs two pages, not a
split stage. If a second visual is genuinely necessary, put it *below* the primary one
in the sticky stack and let it be the one the reader manipulates directly.

### 2b. Derive the story from the argument, not from the assets

Read the paper for its **line of reasoning** and write that out as an ordered list of
claims — one sentence each, in the order a reader must accept them. Typically:

1. what the phenomenon is, and why it matters (from the abstract/intro)
2. how it is defined and measured, precisely enough to trust the rest
3. the headline result — where/when/how much
4. the structure inside that result — what varies, and along which axis
5. the mechanism or explanation offered
6. the caveats, and how the numbers were arrived at

**Each claim becomes one story section.** Only *then* ask what evidence the paper
already has for that claim, and pick the representation that fits the claim's shape:

| Shape of the claim | Fitting representation |
|---|---|
| "these are the terms; they combine like *this*" | small cards or a flow glyph, each hoverable |
| "it varies along an ordered axis" | bars/line over that axis; one position = one stage state |
| "these particular instances stand out" | a sortable list; one row = one stage state |
| "the population is skewed / splits like this" | one proportional graphic and a short sentence |
| "X pushes one way, Y the other" | a controllable schematic: one or two inputs, live readouts |
| "here is how we decided what counts" | a numbered walkthrough of a single worked case |

Do **not** transcribe the paper's figures and tables in order. A table in the paper
may become a hover target, a proportional graphic, or nothing at all. Conversely, a
claim made only in prose may deserve a section the paper never illustrated.

Write the resulting section list, with the claim and the chosen representation for
each, and **confirm it with the user before writing markup.** Aim for **6–9
sections** — beyond that the stage stops feeling connected to the text.

Numbers rule: **only put a number on the page if it appears in the manuscript.**
Anything illustrative or conceptual must be labelled as such in the UI text
(e.g. a control preset named `"… · concept"` beside one named `"… · observed"`).

Fixed furniture, independent of the argument: credits (title, authors, venue) at the
top of the story column; an intro paragraph carrying claim 1; a footer with
abbreviations, data source, and funding.

---

## 3. File layout

```
index.html                 markup only — no logic, no numbers you can avoid
<name>.css                 all layout + styling; owns the sticky mechanics
<name>.js                  one component class: refs, lifecycle, all interactions
<name>-draw.js             pure drawing of the stage (d3/SVG/canvas)
<name>-helpers.js          pure data + math, exported consts (the paper's numbers)
content.json               every user-visible string, keyed by dotted path
assets/img/<field>/…       pre-baked stage images, one per state + a manifest.json
python/build_*.py          offline scripts that bake those images from source data
```

Two separations do the heavy lifting:

- **Data out of code.** `helpers.js` exports plain arrays/objects (the case list, the
  yearly series, category sets). Adding a case = editing one array literal.
- **Copy out of markup.** Every text node that a non-coder might edit carries
  `data-ocx-content="section.key"` and is filled from `content.json` at mount, with
  the HTML text as the fallback so the page reads correctly before/without the fetch.

```js
root.querySelectorAll("[data-ocx-content]").forEach((el) => {
  const val = el.getAttribute("data-ocx-content")
    .split(".").reduce((o, k) => (o == null ? undefined : o[k]), CONTENT);
  if (typeof val === "string") el.innerHTML = val;
});
```

---

## 4. Column proportions

The stage/story ratio is a load-bearing decision, not a styling detail. Two
constraints fight each other: the stage wants width (it carries the detail the whole
page refers to), and the story wants a comfortable measure (~45–75 characters per
line). Resolve them with a ratio plus floors, never with percentages alone.

**Start from 2 : 1 in the stage's favour** and adjust for the stage's natural aspect:

| Stage aspect | Suggested stage : story |
|---|---|
| wide (≈2:1 or wider — a field over a wide domain) | 2 : 1 to 7 : 3 |
| roughly square (matrix, scatter, phase diagram) | 3 : 2 |
| tall or portrait (a stacked track, a tree) | 1 : 1, or reconsider the split entirely |

```css
.shell        { display: flex; flex-wrap: wrap; gap: 28px; align-items: flex-start; }
[data-left]   { flex: 2 1 0; min-width: 560px; }   /* stage: grows, has a floor */
[data-right]  { flex: 1 1 0; min-width: 360px; }   /* story: the measure floor   */
```

Why `flex: <n> 1 0` and not `width: 66%`:

- the ratio survives the gap without `calc()`;
- both floors are respected, and `flex-wrap` makes the columns stack by themselves
  once they can't both fit — the same breakpoint your media query targets;
- the story column's `min-width` is the real constraint. Below roughly 340–360 px the
  measure collapses and the prose becomes unreadable, so set that floor from the body
  font size and defend it.

**Cap the stage against viewport height, not just width.** A sticky stage is only
sticky if it fits on screen. The stage's total height (visual + legend + any secondary
panel) must stay under `100vh − title-bar height`, so bound its width by the height it
implies:

```css
[data-left] { max-width: min(<absolute cap>, calc(<k>vh - <chrome>px)); }
```

where `<k>` is `100 × stage-aspect-ratio` (a 2:1 visual → about `200vh`) and
`<chrome>` accounts for the title bar, legend, and gaps. On a short, wide window this
narrows the stage instead of letting it grow past the fold — the one case a pure
width-based layout always gets wrong.

Also worth fixing deliberately:

- **An overall page width band.** This layout has a genuine minimum below which it is
  a different design (this implementation uses `min-width: 1400px` with a dismissible
  banner, and `max-width: 2000px; margin: 0 auto` so it doesn't sprawl on 4K).
- **Gap over borders.** One consistent column gap (24–32 px) reads better than a rule;
  let the stage column's own canvas tone create the boundary.
- **Below the stacking breakpoint the ratio is meaningless** — both columns go full
  width, the stage un-sticks, and section order carries the narrative instead.

Sanity check before adding content: at your widest and narrowest supported widths, and
at a deliberately short viewport (~700 px tall), the stage must be fully visible while
any story section is in view.

---

## 5. The sticky two-column mechanic

This is the part that is easy to get subtly wrong. Use **CSS sticky, not scroll
listeners**, plus one JS height sync.

```css
.shell            { display: flex; }              /* or grid: 2fr 1fr */
[data-left]       { position: relative; align-self: stretch; }
[data-left-pin]   { position: relative; width: 100%; min-height: 0; }
[data-left-stack] { position: sticky; top: <title-bar height>; }
[data-title]      { position: sticky; top: 0; z-index: 100; }
```

- The **pin** is a plain block whose *height* defines how far the sticky stack can
  travel. The **stack** is what actually sticks.
- JS keeps the pin as tall as the taller of (right column, stack), so the stage
  un-sticks exactly when the story ends — no trailing gap, no early handoff:

```js
const sync = () => {
  if (matchMedia("(max-width:900px)").matches) { pin.style.height = "auto"; return; }
  pin.style.height = Math.max(right.offsetHeight, stack.offsetHeight) + "px";
};
new ResizeObserver(sync).observe(right);   // and observe(stack)
addEventListener("resize", () => requestAnimationFrame(sync));
requestAnimationFrame(sync);
```

Use `offsetHeight`, not `getBoundingClientRect().height` — it ignores transient
overflow while stage layers cross-fade.

Other details worth copying:

- `scroll-margin-top: <title height + gap>` on every right-column child, so anchor
  jumps and scroll-snap don't hide sections under the sticky title.
- Tooltips must be `position: fixed` children of the root. A `position: relative`
  inherited from a generic root rule puts them in flow and grows the page.
- Below ~900 px, collapse to one column: stack goes `position: static`, stage first,
  story after. Interactions become tap-based (`onFocus`/`onBlur` alongside hover).
- If the design genuinely needs width, show a dismissible non-blocking banner
  (`role="alert"`) rather than degrading silently.

---

## 6. The interaction contract

Give the stage a small imperative API, attached to its DOM node by the drawing
module. The component never reaches into the stage's internals:

```js
el.__setField(url)                  // swap the displayed field/raster/layer
el.__setActive(key, on)             // emphasise one marker
el.__highlight(mode, opts)          // spotlight a region, dim the rest
el.__setBadge(text)                 // caption what is currently shown
```

Every story interaction then reduces to *set state → restore state*:

```js
defineOn:  () => this._setField("mhw", true)     // hover / focus
defineOff: () => this._setField("mhw", false)    // leave / blur  → back to default
rowEnter:  (k) => { this._setActive(k,1); this._setField(k,1); this._setBadge(k); }
```

Requirements that make it feel good:

- **Debounce the leave**, not the enter. A short timer on `off` prevents flicker when
  the pointer crosses between two adjacent cards.
- **Preload every field image** at mount (`new Image().src = url` over the manifest)
  so a hover swaps instantly. Cross-fade two layers; never leave three stacked.
- **The badge is mandatory.** Whenever the stage is not in its default state, a badge
  says what it is showing (`"2015 · compound"`, `"TOTAL · 1982–2024"`).
- **The legend is reactive** too — title, caption, and swatch update with the field.
- **Every interactive block wears a marker**: a small `INTERACTIVE` / `TRY IT` pill
  with a `data-tip` describing the affordance. Readers do not discover hover.
- **Keyboard parity**: `tabIndex="0"`, `role="button"`, `aria-label` describing the
  stage change, and `onFocus`/`onBlur` mirroring `onMouseEnter`/`onMouseLeave`.

---

## 7. Pre-bake the heavy visuals

Do not compute scientific fields in the browser. Offline scripts (`python/build_*.py`)
render each state to a transparent PNG/SVG and emit a manifest:

```json
{ "levels": [...], "colors": [...], "labels": [...],
  "default": "total", "template": "assets/img/annual/{field}.png",
  "fields": { "total": {...}, "1982": {...}, "mhw": {...} } }
```

The client only knows: manifest → URL → `__setField(url)`. Benefits: identical
colour mapping to the paper's figures, instant interaction, and a map that still
renders if a CDN is blocked.

Version every asset URL (`?v=YYYYMMDD`) from one constant, and bump it whenever a
shared module or baked image changes — otherwise a cached module against a new page
blanks the stage.

---

## 8. Robustness rules (learned the hard way)

- **Isolate every draw.** Wrap each chart's init in its own `try/catch` and log a
  warning. One failed dependency must not blank the whole page.
- **Time-box CDN waits.** Poll for the library, reject after ~10 s, and let the
  individual `try/catch` blocks degrade gracefully.
- `Promise.allSettled` for the parallel loads (libs, manifests, content), not
  `Promise.all`.
- Apply content twice: once synchronously at mount (usual cache hit → no flash of
  fallback copy) and again when the fetch settles.

---

## 9. Design conventions that carry the "print infographic" feel

- Paper-tinted page background; the stage column carries its own lighter canvas, bled
  into the root padding by a `::before` so it meets the viewport edge cleanly.
- Two families: a condensed display face for headings/labels, a humanist sans for
  body. One accent handwriting face for asides, used sparingly.
- One hue per key quantity in the paper (ideally no more than two or three), assigned
  once and used everywhere that quantity appears — icons, list markers, chart series,
  schematic fills. Colour becomes a legend the reader never has to be told.
- Inline hand-drawn SVG glyphs rather than an icon font: a few paths each, keeps the
  page self-contained, and matches the printed-infographic register.
- Numbers are large and typographic; the sentence around them is small.

---

## 10. Build order for an agent

0. **Ask for visual references (§0)** and agree the palette, typefaces, and register.
   Land them as CSS custom properties before writing any component.
1. Read the PDF/LaTeX. Produce the claim list and section plan of §2. **Confirm with
   the user.**
2. Extract the paper's numbers into `helpers.js` as exported literals, with a comment
   per field naming its source (table, figure, or section).
3. Write the offline bake script and the manifest for the stage's states; generate
   the assets and eyeball one.
4. Fix the column ratio and floors (§4), then build the two-column shell and sticky
   mechanics with placeholder blocks. Verify the handoff and the stage-fits-viewport
   check at your widest and narrowest widths, plus a short (~700 px tall) window,
   before adding any content.
5. Add story sections one at a time; for each, wire its interaction to the stage API
   and add the TRY IT pill, ARIA labels, and keyboard handlers in the same pass.
6. Build the interactive model last — it is the most bespoke piece.
7. Extract all copy to `content.json`, leaving the HTML fallbacks in place.
8. Final pass: badge text for every state, legend reactivity, leave-debounce, asset
   versions bumped, console clean on load.

Ship a note (`HOW-TO-ADD-AN-ELEMENT.md`) telling the next editor which single array
or JSON key to touch for each kind of change.
