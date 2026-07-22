// Ocean Compound Extremes infographic component logic.
// Loaded before support.js; the tiny inline bootstrap passes in the runtime-owned React/DCLogic.
(function registerOceanInfographic() {
  "use strict";

  // ---- Editable copy ------------------------------------------------------
  // All human-readable text lives in content.json. Elements in index.html opt
  // in with a data-ocx-content="dotted.path" attribute; _applyContent() below
  // fills them (innerHTML, so inline <b>/<i>/<a> markup works). The fetch is
  // kicked off at load time — well before React downloads from the CDN — so the
  // content object is almost always ready by first paint. If content.json is
  // missing or malformed, the fallback text baked into index.html is shown.
  var OCX_CONTENT = null;
  var OCX_CONTENT_READY = fetch("./content.json?v=20260722")
    .then(function (r) {
      return r.ok ? r.json() : null;
    })
    .then(function (j) {
      OCX_CONTENT = j;
      return j;
    })
    .catch(function () {
      return null;
    });

  window.createOceanInfographicComponent =
    function createOceanInfographicComponent(DCLogic, React) {
      return class Component extends DCLogic {
        rootRef = React.createRef();
        mapRef = React.createRef();
        lineRef = React.createRef();
        donutRef = React.createRef();
        dotsRef = React.createRef();
        tableRef = React.createRef();
        tipRef = React.createRef();
        mapWrapRef = React.createRef();
        markersRef = React.createRef();
        legendSwatchRef = React.createRef();
        legendTitleRef = React.createRef();
        legendCaptionRef = React.createRef();
        mechRef = React.createRef();
        yearBadgeRef = React.createRef();
        viewportWarningRef = React.createRef();
        _mech = { regime: "psr", event: 0.83, preset: "blob" };

        // Bump _ASSET_V whenever ocean-map-helpers.js / ocean-map-draw.js change, so browsers don't
        // serve a stale cached copy of a shared module against a newer page (which blanks the map+charts).
        static _ASSET_V = "20260722";
        static _DEFINITION_DIR = "./assets/img/definition_2015/";
        // Append the asset version so a re-baked image never serves stale from cache.
        _ver(u) {
          return u
            ? u + (u.includes("?") ? "&" : "?") + "v=" + Component._ASSET_V
            : u;
        }
        _helpers() {
          return import("./ocean-map-helpers.js?v=" + Component._ASSET_V);
        }
        get events() {
          return this._H ? this._H.EVENTS : [];
        }
        get _yearArea() {
          return this._H ? this._H.YEAR_AREA : {};
        }
        get _ninoYears() {
          return this._H ? this._H.NINO_YEARS : new Set();
        }
        get _ninaYears() {
          return this._H ? this._H.NINA_YEARS : new Set();
        }

        renderVals() {
          return {
            rootRef: this.rootRef,
            mapRef: this.mapRef,
            lineRef: this.lineRef,
            donutRef: this.donutRef,
            dotsRef: this.dotsRef,
            tableRef: this.tableRef,
            tipRef: this.tipRef,
            mapWrapRef: this.mapWrapRef,
            markersRef: this.markersRef,
            legendSwatchRef: this.legendSwatchRef,
            legendTitleRef: this.legendTitleRef,
            legendCaptionRef: this.legendCaptionRef,
            mechRef: this.mechRef,
            yearBadgeRef: this.yearBadgeRef,
            viewportWarningRef: this.viewportWarningRef,
            dismissViewportWarning: () => {
              if (this.viewportWarningRef.current)
                this.viewportWarningRef.current.hidden = true;
            },
            defMhwOn: () => this._setDefinitionField("mhw", true),
            defMhwOff: () => this._setDefinitionField("mhw", false),
            defOaxOn: () => this._setDefinitionField("oax", true),
            defOaxOff: () => this._setDefinitionField("oax", false),
            defIntersectionOn: () =>
              this._setDefinitionField("intersection", true),
            defIntersectionOff: () =>
              this._setDefinitionField("intersection", false),
            defCexOn: () => this._setDefinitionField("cex", true),
            defCexOff: () => this._setDefinitionField("cex", false),
            hlLowOn: () => this._mapHighlight("high"),
            hlHighOn: () => this._mapHighlight("min"),
            hlOff: () => this._mapHighlight(null),
          };
        }

        // Fill every [data-ocx-content] element from content.json. Safe to call
        // repeatedly and before content has loaded (no-op until it has).
        _applyContent() {
          const root = this.rootRef.current;
          if (!root || !OCX_CONTENT) return;
          root.querySelectorAll("[data-ocx-content]").forEach((el) => {
            const path = el.getAttribute("data-ocx-content");
            let val = OCX_CONTENT;
            for (const k of path.split(".")) {
              val = val == null ? undefined : val[k];
            }
            if (typeof val === "string") el.innerHTML = val;
          });
        }

        async componentDidMount() {
          // Apply now if content already resolved (usual case → no flash of the
          // fallback text), and again once the fetch settles for a slow load.
          this._applyContent();
          OCX_CONTENT_READY.then(() => this._applyContent());
          this._arrangeLayout();
          // Each load is isolated: a failure loading the shared module, d3/topojson, or the manifest must
          // NOT abort the whole mount (that would blank the map AND every chart). Draw whatever we can.
          try {
            this._H = await this._helpers();
          } catch (e) {
            console.warn("helpers import failed", e);
          }
          await Promise.allSettled([
            this._libs(),
            this._loadManifest(),
            this._loadDefinitionManifest(),
          ]);
          try {
            await this._drawMap();
          } catch (e) {
            console.warn("map", e);
          }
          try {
            this._drawDonut();
          } catch (e) {
            console.warn("donut", e);
          }
          try {
            this._drawDots();
          } catch (e) {
            console.warn("dots", e);
          }
          try {
            this._drawLine();
          } catch (e) {
            console.warn("line", e);
          }
          try {
            this._wireTable();
          } catch (e) {
            console.warn("table", e);
          }
          try {
            this._mechInit();
          } catch (e) {
            console.warn("mech", e);
          }
        }
        _arrangeLayout() {
          const root = this.rootRef.current;
          if (!root) return;
          const right = root.querySelector("[data-ocx-right]");
          const pin = root.querySelector("[data-ocx-map-pin]");
          const stack = root.querySelector("[data-ocx-left-stack]");
          const syncHandoff = () => {
            if (!right || !pin || !stack) return;
            if (window.matchMedia("(max-width:900px)").matches) {
              pin.style.height = "auto";
              return;
            }
            // offsetHeight ignores transient image overflow while map fields crossfade.
            pin.style.height =
              Math.max(right.offsetHeight, stack.offsetHeight) + "px";
          };
          this._syncHandoff = syncHandoff;
          requestAnimationFrame(syncHandoff);
          if (window.ResizeObserver) {
            if (this._handoffObserver) this._handoffObserver.disconnect();
            this._handoffObserver = new ResizeObserver(syncHandoff);
            this._handoffObserver.observe(right);
            this._handoffObserver.observe(stack);
          }
          if (!this._handoffResize) {
            this._handoffResize = () =>
              requestAnimationFrame(this._syncHandoff || (() => {}));
            window.addEventListener("resize", this._handoffResize);
          }
        }
        componentWillUnmount() {
          if (this._handoffObserver) this._handoffObserver.disconnect();
          if (this._handoffResize)
            window.removeEventListener("resize", this._handoffResize);
          if (this._definitionLeaveTimer)
            clearTimeout(this._definitionLeaveTimer);
        }
        componentDidUpdate() {
          this._applyContent();
          if (window.d3) {
            try {
              this._drawMap();
            } catch (e) {}
          }
        }

        // Wait for the d3 + topojson CDN scripts, but give up after ~10s so a blocked CDN degrades to
        // "charts that need d3 fail in their own try/catch" instead of hanging the whole mount forever.
        _libs() {
          return new Promise((res, rej) => {
            const t0 = Date.now();
            const c = () => {
              if (window.d3 && window.topojson) return res();
              if (Date.now() - t0 > 10000)
                return rej(new Error("d3/topojson not loaded"));
              setTimeout(c, 60);
            };
            c();
          });
        }

        // Load the annual manifest (levels, colors, labels, year list, file templates) and preload
        // every field image so hovering a bar swaps the map instantly. Default field is the total.
        async _loadManifest() {
          if (this._manifest) return;
          try {
            const H = this._H || (await this._helpers());
            if (!H || !H.loadManifest) return; // stale/missing module — leave map field empty, don't throw
            const m = await H.loadManifest();
            if (!m) return;
            this._manifest = m;
            this._curYear = null; // null => the summed total
            // preload total + each year + the two spotlight region images
            const dir = H.ANNUAL_ASSET_DIR;
            const eventFiles = m.events ? Object.values(m.events) : [];
            const urls = [
              dir + m.total,
              dir + m.regionHigh,
              dir + m.regionLow,
              ...m.years.map((y) => H.fieldImageUrl(m, y, dir)),
              ...eventFiles.map((f) => dir + f),
            ].map((u) => this._ver(u));
            this._imgCache = urls.map((u) => {
              const im = new Image();
              im.src = u;
              return im;
            });
          } catch (e) {
            console.warn("manifest load failed", e);
          }
        }

        // Load the three 2015 fields used by the definition-card hover interaction.
        async _loadDefinitionManifest() {
          if (this._definitionManifest) return;
          try {
            const dir = Component._DEFINITION_DIR;
            const response = await fetch(this._ver(dir + "manifest.json"));
            if (!response.ok) throw new Error("HTTP " + response.status);
            const manifest = await response.json();
            this._definitionManifest = manifest;
            const urls = Object.values(manifest.fields || {}).map((field) =>
              this._ver(dir + field.file),
            );
            this._definitionImgCache = urls.map((url) => {
              const image = new Image();
              image.src = url;
              return image;
            });
          } catch (e) {
            console.warn("definition manifest load failed", e);
          }
        }

        get ROTATE() {
          return this._H ? this._H.ROTATE : 150;
        }

        _fieldUrl(year) {
          return this._H
            ? this._ver(this._H.fieldImageUrl(this._manifest, year))
            : null;
        }

        _eventUrl(key) {
          if (!this._manifest || !this._manifest.events) return null;
          const f = this._manifest.events[key];
          return f ? this._ver(this._H.ANNUAL_ASSET_DIR + f) : null;
        }

        _definitionUrl(key) {
          const field =
            this._definitionManifest &&
            this._definitionManifest.fields &&
            this._definitionManifest.fields[key];
          return field
            ? this._ver(Component._DEFINITION_DIR + field.file)
            : null;
        }

        // Paint the legend swatches + the map subtitle/caption directly from the manifest colours.
        _syncLegend() {
          const m = this._manifest,
            el = this.legendSwatchRef.current;
          if (!m || !el) return;
          const definition =
            this._activeDefinition &&
            this._definitionManifest &&
            this._definitionManifest.fields[this._activeDefinition];
          const colors = definition ? definition.colors : m.colors;
          const spans = el.querySelectorAll("span");
          colors.forEach((c, i) => {
            if (spans[i]) spans[i].style.background = c;
          });
          const title = this.legendTitleRef.current,
            caption = this.legendCaptionRef.current;
          if (definition) {
            if (this._activeDefinition === "intersection") {
              if (title)
                title.textContent = "MHW + OAX + COMPOUND EXTREMES · 2015";
              if (caption)
                caption.textContent =
                  "Red shows MHW months, teal shows OAX months, and the warm scale shows compound months at each location.";
            } else {
              if (title)
                title.textContent = `WHERE DID ${definition.label.toUpperCase()}S OCCUR IN 2015?`;
              const article = this._activeDefinition === "oax" ? "an" : "a";
              if (caption)
                caption.textContent = `Months spent in ${article} ${definition.label.toLowerCase()} at each location during 2015.`;
            }
          } else {
            if (title) title.textContent = "WHERE DO COMPOUND EXTREMES HAPPEN?";
            if (caption)
              caption.innerHTML =
                "Total months spent in a compound (OAX&nbsp;∩&nbsp;MHW) extreme at each location.";
          }
        }

        // Definition cards temporarily replace the normal all-years/year field with the corresponding
        // 2015 MHW, OAX or compound count. Event markers are hidden because they describe a different
        // layer (the nine largest named compound events across the full record).
        _setDefinitionField(key, on) {
          const field =
            this._definitionManifest &&
            this._definitionManifest.fields &&
            this._definitionManifest.fields[key];
          const el = this.mapRef.current;
          if (on) {
            if (this._definitionLeaveTimer) {
              clearTimeout(this._definitionLeaveTimer);
              this._definitionLeaveTimer = null;
            }
            if (!field || !el || !el.__oceSetField) return;
            this._activeDefinition = key;
            el.__oceSetField(this._definitionUrl(key));
            if (this.markersRef.current) {
              this.markersRef.current.style.opacity = "0";
              this.markersRef.current.style.visibility = "hidden";
            }
            const badge = this.yearBadgeRef.current;
            if (badge && !badge.classList.contains("oce-ev-box")) {
              badge.textContent =
                key === "intersection"
                  ? "2015 · MHW + OAX + COMPOUND"
                  : `2015 · ${field.shortLabel} EXTREME-MONTHS`;
              badge.style.color = field.colors[2];
            }
            this._syncLegend();
            return;
          }
          // Ignore a stale leave/blur from a card that is no longer the active one.
          if (this._activeDefinition !== key) return;
          if (this._definitionLeaveTimer)
            clearTimeout(this._definitionLeaveTimer);
          // Let the pointer cross the small gaps between definition controls without briefly restoring
          // the all-years field. Entering another control cancels this timer and swaps 2015 → 2015.
          this._definitionLeaveTimer = setTimeout(() => {
            this._definitionLeaveTimer = null;
            if (this._activeDefinition !== key) return;
            this._activeDefinition = null;
            this._restoreField();
            if (this.markersRef.current) {
              this.markersRef.current.style.opacity = "1";
              this.markersRef.current.style.visibility = "visible";
            }
            const badge = this.yearBadgeRef.current;
            if (badge && !badge.classList.contains("oce-ev-box")) {
              badge.textContent = this._restingBadgeText();
              badge.style.color = "#f2b45a";
            }
            this._syncLegend();
          }, 120);
        }

        // The badge's resting label: the current year, or TOTAL · <range> when no year is selected.
        _restingBadgeText() {
          const m = this._manifest;
          if (this._curYear != null) return String(this._curYear);
          return m
            ? "TOTAL · " + m.years[0] + "–" + m.years[m.years.length - 1]
            : "TOTAL · 1982–2024";
        }
        // Restore the ocean field the current year selection implies (year, or the summed total).
        _restoreField(options) {
          if (!this._manifest) return;
          const el = this.mapRef.current;
          const url = this._fieldUrl(
            this._curYear == null ? null : this._curYear,
          );
          if (el && el.__oceSetField && url) el.__oceSetField(url, options);
        }
        // Swap the ocean field shown on the map: a specific year, or null for the summed total.
        // Also updates the small badge over the map. Safe to call before the map/manifest are ready.
        // Leaves the badge alone while it's expanded into an event info box (event hover owns it then).
        _setMapYear(year) {
          if (!this._manifest) return;
          this._curYear = year == null ? null : year;
          // Adjacent year columns are scrubbed rapidly. Paint each field immediately
          // instead of leaving two full-map layers in overlapping opacity transitions.
          this._restoreField({ instant: true });
          const badge = this.yearBadgeRef.current;
          if (badge && !badge.classList.contains("oce-ev-box")) {
            if (year == null) badge.textContent = this._restingBadgeText();
            else {
              const cover = this._yearArea[year] || 0;
              badge.textContent = `${year} \u2022 ${Number(cover.toFixed(1))} % COVER`;
            }
          }
        }

        // Swap the map field to a single event's footprint on hover; restore to the
        // currently-selected field (year or total) on mouse-out. Independent of the
        // year-bar swap path (_setMapYear/_setActiveYear), which it must not disturb.
        _setEventField(key, on) {
          if (!this._manifest) return;
          const el = this.mapRef.current;
          // Make the active marker's fill fully transparent so its footprint raster shows through underneath
          // (the dark highlight ring from _setActive stays, so the location is still marked). Restore the base
          // fill on leave. While transparent, flip the in-circle number to dark ('.oce-num') so it stays
          // legible against the light footprint — the event LABEL text (name/year, outside the circle) is untouched.
          const map = this.markersRef.current || this.mapRef.current;
          if (map) {
            const g = map.querySelector(`g[data-key="${key}"]`);
            if (g) {
              const c = g.querySelector(".oce-c");
              if (c)
                c.setAttribute(
                  "fill-opacity",
                  on ? 0 : (this.props.circleOpacity ?? 0.9),
                );
              g.querySelectorAll(".oce-num").forEach((t) =>
                t.setAttribute("fill", on ? "#12222c" : "#fff"),
              );
            }
          }
          if (on) {
            const url = this._eventUrl(key);
            if (!url) return; // no footprint for this key -> leave field as-is
            if (el && el.__oceSetField) el.__oceSetField(url);
          } else {
            // restore the field only; the badge is collapsed + re-labelled by _setEventBadge (which animates it)
            this._restoreField();
          }
        }

        // The top-left badge doubles as an event info panel. Marker and table-row hover both expand it into
        // the same full info box, so either interaction presents the event details directly on the map.
        // on=false collapses it back to the resting label (TOTAL/year).
        _setEventBadge(key, on, expand) {
          const badge = this.yearBadgeRef.current;
          if (!badge) return;
          const from = badge.getBoundingClientRect(); // FLIP: capture the size BEFORE the content/class swap
          if (on) {
            const ev = this.events.find((e) => e.key === key);
            if (!ev) return;
            if (expand) {
              badge.classList.add("oce-ev-box");
              badge.innerHTML = this._tipHtml(ev);
            } else {
              badge.classList.remove("oce-ev-box");
              badge.textContent = ev.name.toUpperCase() + " · " + ev.year;
            }
          } else {
            badge.classList.remove("oce-ev-box");
            badge.textContent = this._restingBadgeText();
          }
          this._animateBadge(badge, from);
        }
        // FLIP-animate the badge between its pill and info-box sizes: measure the natural target size after
        // the content swap, pin the pre-swap size, force a reflow, then transition width+height+padding to
        // the target. overflow:hidden (set in CSS) clips the content so it reveals/hides as the box resizes.
        _animateBadge(badge, from) {
          if (this._badgeDone) this._badgeDone(); // wrap up any in-flight animation first
          badge.style.transition = "none";
          badge.style.width = "";
          badge.style.height = ""; // settle at the natural target size
          const to = badge.getBoundingClientRect();
          if (
            Math.abs(to.width - from.width) < 0.5 &&
            Math.abs(to.height - from.height) < 0.5
          ) {
            badge.style.transition = "";
            return;
          }
          badge.style.width = from.width + "px";
          badge.style.height = from.height + "px";
          void badge.offsetWidth; // force reflow so the start size sticks
          badge.style.transition =
            "width .2s ease, height .2s ease, padding .2s ease";
          badge.style.width = to.width + "px";
          badge.style.height = to.height + "px";
          const done = () => {
            badge.style.transition = "";
            badge.style.width = "";
            badge.style.height = "";
            badge.removeEventListener("transitionend", done);
            if (this._badgeTimer) {
              clearTimeout(this._badgeTimer);
              this._badgeTimer = null;
            }
            this._badgeDone = null;
          };
          this._badgeDone = done;
          badge.addEventListener("transitionend", done);
          this._badgeTimer = setTimeout(done, 280); // fallback in case transitionend doesn't fire
        }

        _colorScale() {
          if (!this._H)
            return window.d3
              .scaleSequential(window.d3.interpolateYlOrRd)
              .domain([2.5, 4.05]);
          return this._H.circleColorScale(window.d3, this.props.intensityScale);
        }

        _tip(html, ev) {
          const t = this.tipRef.current;
          if (!t) return;
          if (html === null) {
            t.style.opacity = 0;
            return;
          }
          t.innerHTML = html;
          t.style.opacity = 1;
          t.style.left =
            Math.min(ev.clientX + 14, (window.innerWidth || 1200) - 292) + "px";
          t.style.top =
            Math.min(ev.clientY + 14, (window.innerHeight || 900) - 150) + "px";
        }
        _tipHtml(e) {
          return this._H ? this._H.tipHtml(e) : "";
        }

        async _drawMap() {
          const d3 = window.d3,
            topojson = window.topojson,
            el = this.mapRef.current;
          if (!el || !this._H) return;
          const Draw =
            this._Draw ||
            (this._Draw = await import(
              "./ocean-map-draw.js?v=" + Component._ASSET_V
            ));
          if (!this._world) this._world = await Draw.loadWorld(topojson);
          const self = this;
          this._syncLegend();
          const dir = this._H.ANNUAL_ASSET_DIR;
          const m = this._manifest;
          Draw.drawMap({
            d3,
            topojson,
            el,
            markersEl: this.markersRef.current,
            world: this._world,
            rotate: this.ROTATE,
            bgPageColor: "#f4efe3",
            landColor: "#e6ddc7",
            borderColor: "#b7ab8d",
            fieldImageUrl: this._fieldUrl(this._curYear ?? null),
            regionHighUrl: m ? this._ver(dir + m.regionHigh) : null,
            regionLowUrl: m ? this._ver(dir + m.regionLow) : null,
            events: this.events,
            colorScale: this._colorScale(),
            circleScale: this.props.circleScale,
            circleOpacity: this.props.circleOpacity ?? 0.9,
            rasterOpacity: this.props.rasterOpacity ?? 0.9,
            // Markers are hover-only: hover expands the info box + swaps the footprint. No click interaction.
            onHover: (key, on) => {
              self._setActive(key, on);
              self._setEventField(key, on);
              self._setEventBadge(key, on, true);
            },
          });
          // re-assert the current year badge (componentDidUpdate re-runs _drawMap)
          this._setMapYear(this._curYear ?? null);
        }

        _drawDonut() {
          const d3 = window.d3,
            el = this.donutRef.current;
          if (!el) return;
          el.innerHTML = "";
          const self = this;
          const data = [
            { v: 75, c: "#1f9aa6", label: "&lt; 1 million km&sup2;" },
            { v: 16, c: "#e6a54e", label: "1&ndash;2 million km&sup2;" },
            { v: 9, c: "#c8531f", label: "&gt; 2 million km&sup2;" },
          ];
          const S = 148,
            svg = d3
              .select(el)
              .append("svg")
              .attr("viewBox", `0 0 ${S} ${S}`)
              .attr("width", "100%");
          const g = svg
            .append("g")
            .attr("transform", `translate(${S / 2},${S / 2})`);
          const arc = d3
            .arc()
            .innerRadius(44)
            .outerRadius(70)
            .padAngle(0.015)
            .cornerRadius(2);
          const arcHover = d3
            .arc()
            .innerRadius(44)
            .outerRadius(75)
            .padAngle(0.015)
            .cornerRadius(2);
          const pie = d3
            .pie()
            .sort(null)
            .value((d) => d.v);
          g.selectAll("path")
            .data(pie(data))
            .join("path")
            .attr("d", arc)
            .attr("fill", (d) => d.data.c)
            .style("cursor", "pointer")
            .on("mouseenter", function (ev, d) {
              d3.select(this).transition().duration(140).attr("d", arcHover);
            })
            .on("mousemove", function (ev, d) {
              if (self.props.showTooltips !== false)
                self._tip(
                  `<b>${d.data.v}%</b> of events<br>${d.data.label}`,
                  ev,
                );
            })
            .on("mouseleave", function (ev, d) {
              d3.select(this).transition().duration(140).attr("d", arc);
              self._tip(null);
            });
          g.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "-0.1em")
            .attr("font-family", "Barlow Condensed,sans-serif")
            .attr("font-weight", 700)
            .attr("font-size", 12)
            .attr("letter-spacing", "0.04em")
            .attr("fill", "#12222c")
            .text("SIZE OF");
          g.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "1em")
            .attr("font-family", "Barlow Condensed,sans-serif")
            .attr("font-weight", 700)
            .attr("font-size", 12)
            .attr("letter-spacing", "0.04em")
            .attr("fill", "#12222c")
            .text("EVENT");
        }

        _drawDots() {
          const d3 = window.d3,
            el = this.dotsRef.current;
          if (!el) return;
          el.innerHTML = "";
          const cols = 10,
            rows = 10,
            gap = 10.5,
            r = 3.2,
            pad = 5;
          const W = pad * 2 + (cols - 1) * gap,
            H = pad * 2 + (rows - 1) * gap;
          const svg = d3
            .select(el)
            .append("svg")
            .attr("viewBox", `0 0 ${W} ${H}`)
            .attr("width", "100%");
          let i = 0;
          for (let y = 0; y < rows; y++)
            for (let x = 0; x < cols; x++) {
              const giant = i < 20;
              svg
                .append("circle")
                .attr("cx", pad + x * gap)
                .attr("cy", pad + y * gap)
                .attr("r", giant ? r + 0.8 : r)
                .attr("fill", giant ? "#c8531f" : "#c3bda8");
              i++;
            }
        }

        _drawLine() {
          const d3 = window.d3,
            el = this.lineRef.current;
          if (!el) return;
          el.innerHTML = "";
          const self = this;
          const W = 420,
            H = 190,
            m = { t: 18, r: 8, b: 34, l: 24 };
          const svg = d3
            .select(el)
            .append("svg")
            .attr("viewBox", `0 0 ${W} ${H}`)
            .attr("width", "100%");
          const years = d3.range(1982, 2025);
          const areaMap = this._yearArea,
            nino = this._ninoYears,
            nina = this._ninaYears;
          const x = d3
            .scaleBand()
            .domain(years)
            .range([m.l, W - m.r])
            .paddingInner(0.24);
          const y = d3
            .scaleLinear()
            .domain([0, 37])
            .range([H - m.b, m.t]);
          svg
            .append("line")
            .attr("x1", m.l)
            .attr("y1", H - m.b)
            .attr("x2", W - m.r)
            .attr("y2", H - m.b)
            .attr("stroke", "#c7bfa6");
          [0, 10, 20, 30].forEach((v) => {
            svg
              .append("text")
              .attr("x", m.l - 4)
              .attr("y", y(v) + 3.5)
              .attr("text-anchor", "end")
              .attr("font-size", 10)
              .attr("fill", "#9a927a")
              .text(v);
          });
          svg
            .append("text")
            .attr("x", m.l)
            .attr("y", H - 3)
            .attr("text-anchor", "start")
            .attr("font-size", 10)
            .attr("font-weight", 400)
            .attr("fill", "#7a725c")
            .text("1982");
          svg
            .append("text")
            .attr("x", W - m.r)
            .attr("y", H - 3)
            .attr("text-anchor", "end")
            .attr("font-size", 10)
            .attr("font-weight", 400)
            .attr("fill", "#7a725c")
            .text("2024");
          const colFor = (yr) =>
            nino.has(yr) ? "#c0392b" : nina.has(yr) ? "#2f6fae" : "#c7bfa6";
          const plotTop = m.t,
            plotBot = H - m.b,
            step = x.step(),
            gap = step - x.bandwidth();
          const gHi = svg.append("g").attr("data-role", "col-hi"); // faint full-column highlight (behind bars)
          const gb = svg.append("g").attr("data-role", "bars"); // the visible bars
          const gHit = svg.append("g").attr("data-role", "hit"); // transparent full-height/width hover targets (front)
          years.forEach((yr) => {
            const v = areaMap[yr] || 0.3;
            const cx = x(yr) - gap / 2; // full column spans bar + surrounding gap (no dead zones)
            // faint column shade that fades in on hover \u2014 the visual cue for the whole-column hit area
            const hi = gHi
              .append("rect")
              .attr("x", cx)
              .attr("y", plotTop)
              .attr("width", step)
              .attr("height", plotBot - plotTop)
              .attr("fill", "#12222c")
              .attr("opacity", 0)
              .style("transition", "opacity 160ms ease")
              .style("pointer-events", "none");
            const bar = gb
              .append("rect")
              .attr("class", "oce-bar")
              .attr("data-year", yr)
              .attr("x", x(yr))
              .attr("y", y(v))
              .attr("width", x.bandwidth())
              .attr("height", plotBot - y(v))
              .attr("rx", 1)
              .attr("fill", colFor(yr))
              .attr("fill-opacity", 0.85)
              .style("transition", "fill-opacity 160ms ease")
              .style("pointer-events", "none");
            // hit target: full plot height, full column width \u2014 hovering anywhere in the column triggers the year.
            // (No data-year here: handlers close over `yr`, and it keeps _setActive's rect[data-year] styling to the bars only.)
            const showCoverTip = (ev) => {
              if (self.props.showTooltips !== false) {
                const phase = nino.has(yr)
                  ? "El Ni\u00F1o"
                  : nina.has(yr)
                    ? "La Ni\u00F1a"
                    : "Neutral";
                self._tip(
                  `<b>Percent cover</b><br>${yr} &middot; ${phase}: <b>${v.toFixed(1)}%</b>`,
                  ev,
                );
              }
            };
            gHit
              .append("rect")
              .attr("x", cx)
              .attr("y", plotTop)
              .attr("width", step)
              .attr("height", plotBot - plotTop)
              .attr("fill", "transparent")
              .style("cursor", "pointer")
              .on("mouseenter", function (ev) {
                bar
                  .attr("fill-opacity", 1)
                  .attr("stroke", "#12222c")
                  .attr("stroke-width", 1);
                hi.attr("opacity", 0.05);
                self._setActiveYear(yr, true);
                self._setMapYear(yr);
                showCoverTip(ev);
              })
              .on("mousemove", function (ev) {
                showCoverTip(ev);
              })
              .on("mouseleave", function () {
                bar.attr("fill-opacity", 0.85).attr("stroke", "none");
                hi.attr("opacity", 0);
                self._setActiveYear(yr, false);
                self._setMapYear(null);
                self._tip(null);
              });
          });
          const lg = svg
            .append("g")
            .attr("transform", `translate(${m.l + 4},${m.t + 2})`);
          lg.append("rect")
            .attr("x", 0)
            .attr("y", -7)
            .attr("width", 10)
            .attr("height", 9)
            .attr("rx", 1.5)
            .attr("fill", "#c0392b");
          lg.append("text")
            .attr("x", 15)
            .attr("y", 1)
            .attr("font-size", 10)
            .attr("fill", "#c0392b")
            .attr("font-weight", 400)
            .text("El Ni\u00F1o");
          lg.append("rect")
            .attr("x", 0)
            .attr("y", 7)
            .attr("width", 10)
            .attr("height", 9)
            .attr("rx", 1.5)
            .attr("fill", "#2f6fae");
          lg.append("text")
            .attr("x", 15)
            .attr("y", 15)
            .attr("font-size", 10)
            .attr("fill", "#2f6fae")
            .attr("font-weight", 400)
            .text("La Ni\u00F1a");
        }

        _mapHighlight(mode) {
          const el = this.mapRef.current;
          if (el && el.__oceHighlight)
            el.__oceHighlight(mode, {
              strength: this.props.spotlightStrength ?? 0.78,
              fadeMs: this.props.spotlightFadeMs ?? 220,
              rasterOpacity: this.props.rasterOpacity ?? 0.85,
            });
        }
        _setActive(key, on) {
          const ev = this.events.find((e) => e.key === key);
          if (!ev) return;
          const map = this.markersRef.current || this.mapRef.current;
          if (map) {
            const g = map.querySelector(`g[data-key="${key}"]`);
            if (g) {
              const c = g.querySelector(".oce-c");
              if (c) {
                c.setAttribute("stroke", on ? "#12222c" : "#fff");
                c.setAttribute("stroke-width", on ? "3.5" : "1.6");
              }
            }
          }
          const tb = this.tableRef.current;
          if (tb) {
            const row = tb.querySelector(`tr[data-key="${key}"]`);
            if (row) {
              row.style.background = on ? "#f2ead6" : "";
            }
          }
          const line = this.lineRef.current;
          if (line) {
            line
              .querySelectorAll(`rect[data-year="${ev.year}"]`)
              .forEach((b) => {
                if (on) {
                  b.setAttribute("stroke", "#12222c");
                  b.setAttribute("stroke-width", 1);
                  b.setAttribute("fill-opacity", 1);
                } else {
                  b.setAttribute("stroke", "none");
                  b.setAttribute("fill-opacity", 0.85);
                }
              });
          }
        }
        _setActiveYear(year, on) {
          const keys = this.events
            .filter((e) => e.year === year)
            .map((e) => e.key);
          keys.forEach((k) => this._setActive(k, on));
          const line = this.lineRef.current;
          if (line) {
            line.querySelectorAll(`rect[data-year="${year}"]`).forEach((b) => {
              if (on) {
                b.setAttribute("fill-opacity", 1);
              }
            });
          }
        }
        _wireSort() {
          const tb = this.tableRef.current;
          if (!tb) return;
          const self = this;
          const tbody = tb.querySelector("tbody");
          if (!tbody) return;
          const val = (row, type) => {
            const tds = row.querySelectorAll("td");
            if (type === "name") return tds[0].textContent.trim().toLowerCase();
            if (type === "year") return parseFloat(tds[1].textContent) || 0;
            if (type === "area") return parseFloat(tds[2].textContent) || 0;
            if (type === "dur") return parseFloat(tds[3].textContent) || 0;
            return 0;
          };
          this._sort = { col: null, dir: 1 };
          tb.querySelectorAll("th[data-sort]").forEach((th) => {
            th.addEventListener("click", () => {
              const col = th.getAttribute("data-sort");
              // numeric columns default to descending (largest first); name defaults ascending
              if (self._sort.col === col) {
                self._sort.dir *= -1;
              } else {
                self._sort.col = col;
                self._sort.dir = col === "name" ? 1 : -1;
              }
              const dir = self._sort.dir;
              const rows = [...tbody.querySelectorAll("tr")];
              rows.sort((a, b) => {
                const va = val(a, col),
                  vb = val(b, col);
                if (va < vb) return -1 * dir;
                if (va > vb) return 1 * dir;
                return 0;
              });
              rows.forEach((r) => tbody.appendChild(r));
              // update arrow indicators
              tb.querySelectorAll("span[data-arrow]").forEach((s) => {
                s.style.opacity = 0;
                s.textContent = "↕";
              });
              const arrow = tb.querySelector(`span[data-arrow="${col}"]`);
              if (arrow) {
                arrow.style.opacity = 1;
                arrow.textContent = dir > 0 ? "▲" : "▼";
              }
            });
          });
        }
        _wireTable() {
          const tb = this.tableRef.current;
          if (!tb) return;
          const self = this;
          this._wireSort();
          tb.querySelectorAll("tr[data-key]").forEach((row) => {
            const key = row.getAttribute("data-key");
            row.style.cursor = "pointer";
            row.addEventListener("mouseenter", () => {
              self._setActive(key, true);
              self._setEventField(key, true);
              self._setEventBadge(key, true, true);
            });
            row.addEventListener("mouseleave", () => {
              self._setActive(key, false);
              self._setEventField(key, false);
              self._setEventBadge(key, false);
              self._tip(null);
            });
          });
        }

        // ---- interactive "tug-of-war" mechanism explorer ----
        _mechClamp(x, a, b) {
          return Math.max(a, Math.min(b, x));
        }
        _mechSigned(x, digits = 2) {
          const sign = x > 0 ? "+" : x < 0 ? "−" : "";
          return `${sign}${Math.abs(x).toFixed(digits)}`;
        }
        _mechParams() {
          if (this._mech.regime === "psr")
            return {
              baseMix: 0.28,
              dicResponse: 0.15,
              title: "LOW– TO MID-LATITUDES (PSR)",
              sub: "Thermal and [H⁺] anomalies tend to align",
              desc: "Permanently stratified waters: warming raises [H⁺], while the opposing sDIC response is comparatively weak.",
            };
          return {
            baseMix: 0.88,
            dicResponse: 0.38,
            title: "MIXING- AND UPWELLING-DRIVEN REGIONS",
            sub: "Warming suppresses DIC-rich mixing or upwelling",
            desc: "At high latitudes and in the eastern equatorial Pacific, warming strengthens stratification and suppresses the DIC-rich mixing or upwelling pathway that usually raises [H⁺].",
          };
        }
        _mechCalc() {
          const p = this._mechParams(),
            event = this._mech.event;
          const isPsr = this._mech.regime === "psr";
          const stratification = isPsr
            ? 0.62 + event * 0.35
            : 0.12 + event * 0.78;
          const mixingSuppression = isPsr ? 0.82 : 0.93;
          const surfaceMixing =
            p.baseMix * (1 - mixingSuppression * stratification);

          // The named Blob preset uses Table 1's event magnitudes. Its driver split follows
          // the manuscript-wide compound-event balance in Figure 9 and closes to the observed net.
          if (this._mech.preset === "blob") {
            return {
              event,
              tempAnom: 1.4,
              thermalHplus: 0.41,
              dicHplus: -0.21,
              alkHplus: -0.02,
              hplusAnomaly: 0.18,
              stratification,
              surfaceMixing,
              alignment: "aligned",
              empirical: true,
            };
          }

          // Conceptual slider model. Coefficients are deliberately modest and expressed in
          // manuscript-scale nmol kg−1; they illustrate driver direction, not universal thresholds.
          const tempAnom = -1.5 + event * 3.5;
          const thermalHplus = 0.293 * tempAnom;
          const dicResponse =
            this._mech.preset === "equatorial" ? 0.46 : p.dicResponse;
          const dicHplus = -dicResponse * tempAnom;
          const alkHplus = -0.014 * tempAnom;
          const hplusAnomaly = thermalHplus + dicHplus + alkHplus;
          const alignment =
            tempAnom <= 0 ? "no-mhw" : hplusAnomaly > 0 ? "aligned" : "opposed";
          return {
            event,
            tempAnom,
            thermalHplus,
            dicHplus,
            alkHplus,
            hplusAnomaly,
            stratification,
            surfaceMixing,
            alignment,
            empirical: false,
          };
        }
        _mechRenderDots(n) {
          const g =
            this.mechRef.current &&
            this.mechRef.current.querySelector('[data-m="dicDots"]');
          if (!g) return;
          g.innerHTML = "";
          const field = { x: 110, y: 230, width: 350, height: 42 };
          for (let i = 0; i < n; i++) {
            const c = document.createElementNS(
              "http://www.w3.org/2000/svg",
              "circle",
            );
            c.setAttribute("cx", field.x + Math.random() * field.width);
            c.setAttribute("cy", field.y + Math.random() * field.height);
            c.setAttribute("r", 2 + Math.random() * 3);
            g.appendChild(c);
          }
        }
        _mechUpdate() {
          const root = this.mechRef.current;
          if (!root) return;
          const q = (s) => root.querySelector(`[data-m="${s}"]`);
          const slider = q("event");
          if (slider) this._mech.event = Number(slider.value);
          const c = this._mechCalc(),
            p = this._mechParams(),
            isPsr = this._mech.regime === "psr";
          const RED = "#c8531f",
            TEAL = "#1f9aa6",
            GREEN = "#3f7a4c";

          [
            ["psrBtn", "psr", RED],
            ["ssrBtn", "ssr", TEAL],
          ].forEach(([id, regime, color]) => {
            const button = q(id),
              active = this._mech.regime === regime;
            if (button) {
              button.style.background = active ? color : "transparent";
              button.style.color = active ? "#fff" : "#6f7873";
              button.setAttribute("aria-pressed", String(active));
            }
          });
          const desc = q("regimeDesc");
          if (desc) desc.textContent = p.desc;

          const gm = q("gaugeMarker");
          if (gm) gm.style.left = `calc(${Math.round(c.event * 100)}% - 2px)`;
          if (slider)
            slider.setAttribute(
              "aria-valuetext",
              `${this._mechSigned(c.tempAnom)} degrees Celsius`,
            );

          const ts = q("tempScore");
          if (ts) {
            ts.textContent = `${this._mechSigned(c.tempAnom)} °C`;
            ts.style.color =
              c.tempAnom < 0 ? TEAL : c.tempAnom > 0 ? RED : GREEN;
          }
          const th = q("thermalScore");
          if (th) {
            th.textContent = this._mechSigned(c.thermalHplus);
            th.style.color = c.thermalHplus < 0 ? TEAL : RED;
          }
          const ds = q("dicScore");
          if (ds) {
            ds.textContent = this._mechSigned(c.dicHplus);
            ds.style.color = c.dicHplus < 0 ? TEAL : RED;
          }
          const hs = q("hplusScore");
          if (hs) {
            hs.textContent = this._mechSigned(c.hplusAnomaly);
            hs.style.color =
              c.hplusAnomaly < 0 ? TEAL : c.hplusAnomaly > 0 ? RED : GREEN;
          }
          const ms = q("mixScore");
          if (ms)
            ms.textContent = `surface mixing: ${c.surfaceMixing < 0.18 ? "low" : c.surfaceMixing < 0.45 ? "moderate" : "high"}`;
          const as = q("alignmentScore");
          if (as) {
            as.textContent =
              c.alignment === "aligned"
                ? "aligned"
                : c.alignment === "opposed"
                  ? "opposed"
                  : "no MHW";
            as.style.color =
              c.alignment === "aligned"
                ? RED
                : c.alignment === "opposed"
                  ? TEAL
                  : GREEN;
          }
          const mt = q("mhwThreshold");
          if (mt)
            mt.textContent = c.empirical
              ? "above local Q95"
              : c.tempAnom <= 0
                ? "below local Q95"
                : "compare with local Q95";
          const ot = q("oaxThreshold");
          if (ot)
            ot.textContent = c.empirical
              ? "above local Q95"
              : c.hplusAnomaly <= 0
                ? "not an OAX response"
                : "compare with local Q95";
          const tn = q("thresholdNote");
          if (tn)
            tn.textContent = c.empirical
              ? "The Blob temperature (+1.40 °C) and net [H⁺] (+0.18 nmol/kg) are from Table 1. The driver split uses the manuscript’s mean compound-event balance (+0.41 thermal, −0.21 sDIC) with a small residual so the budget closes. Extremes use local, season-specific detrended Q95 thresholds."
              : "Conceptual response: driver directions follow the manuscript, but these are not measured event values. MHW and OAX are defined against separate local, season-specific detrended 95th-percentile thresholds—not universal absolute cutoffs.";

          const rt = q("regimeTitle");
          if (rt) rt.textContent = p.title;
          const rs = q("regimeSub");
          if (rs) rs.textContent = p.sub;
          const wt = q("waterTop");
          if (wt)
            wt.setAttribute(
              "fill",
              c.tempAnom > 0 ? "url(#mechHot)" : "url(#mechCool)",
            );
          const sl = q("stratLabel");
          if (sl)
            sl.textContent =
              c.stratification > 0.65
                ? "STRONG STRATIFICATION"
                : "WEAK / SEASONAL STRATIFICATION";

          const sw = 2 + c.stratification * 6.5;
          ["layer1", "layer2", "layer3"].forEach((id, idx) => {
            const line = q(id);
            if (line) {
              line.setAttribute("stroke-width", Math.max(1.5, sw - idx * 1.4));
              line.setAttribute(
                "opacity",
                this._mechClamp(0.2 + c.stratification - idx * 0.16, 0.16, 0.9),
              );
            }
          });

          const ha = q("heatArrows");
          if (ha)
            ha.setAttribute(
              "opacity",
              this._mechClamp((c.tempAnom + 0.3) / 1.8, 0, 1),
            );
          const ua = q("upwellArrows");
          if (ua)
            ua.setAttribute(
              "opacity",
              this._mechClamp(c.surfaceMixing * 1.35, 0.04, 0.9),
            );
          const bm = q("blockedMix");
          if (bm)
            bm.setAttribute(
              "opacity",
              !isPsr
                ? this._mechClamp((c.stratification - 0.42) * 1.75, 0, 1)
                : this._mechClamp((c.stratification - 0.84) * 0.28, 0, 0.14),
            );

          this._mechRenderDots(Math.round(100 * c.surfaceMixing));

          let heading, explain, color;
          if (c.empirical) {
            heading = "Observed OAX ∩ MHW";
            color = RED;
            explain =
              "The Blob preset uses the manuscript’s compound-event magnitudes: +1.40 °C and +0.18 nmol/kg [H⁺].";
          } else if (c.alignment === "no-mhw") {
            heading = "No MHW pathway";
            color = "#5a6b73";
            explain =
              "Cooling can raise [H⁺] through mixing or upwelling, but it cannot simultaneously be a marine heatwave.";
          } else if (c.alignment === "aligned") {
            heading = "Mechanisms aligned";
            color = RED;
            explain =
              "In permanently stratified waters, the thermal increase in [H⁺] outweighs the opposing sDIC response. Whether an extreme occurs still depends on the local Q95 thresholds.";
          } else {
            heading = "Mechanisms opposed";
            color = TEAL;
            explain =
              this._mech.preset === "equatorial"
                ? "El Niño warming suppresses DIC-rich upwelling, so [H⁺] falls even as temperature rises."
                : "Warming suppresses the mixing of DIC-rich water; that reduction in [H⁺] outweighs the direct thermal increase.";
          }
          const oh = q("outcomeHeading");
          if (oh) {
            oh.textContent = heading;
            oh.style.color = color;
          }
          const oe = q("outcomeExplain");
          if (oe) oe.textContent = explain;
        }
        _mechSetRegime(r) {
          this._mech.regime = r;
          this._mech.event = 0.7;
          this._mech.preset = null;
          const s =
            this.mechRef.current &&
            this.mechRef.current.querySelector('[data-m="event"]');
          if (s) s.value = this._mech.event;
          this._mechUpdate();
        }
        _mechInit() {
          const root = this.mechRef.current;
          if (!root) return;
          const psr = root.querySelector('[data-m="psrBtn"]'),
            ssr = root.querySelector('[data-m="ssrBtn"]'),
            slider = root.querySelector('[data-m="event"]');
          if (slider) slider.value = this._mech.event;
          if (psr)
            psr.addEventListener("click", () => this._mechSetRegime("psr"));
          if (ssr)
            ssr.addEventListener("click", () => this._mechSetRegime("ssr"));
          if (slider)
            slider.addEventListener("input", () => {
              this._mech.preset = null;
              this._mechUpdate();
            });
          root.querySelectorAll("[data-preset]").forEach((btn) => {
            btn.addEventListener("click", () => {
              const pr = btn.dataset.preset;
              if (pr === "blob" || pr === "reset") {
                this._mech.regime = "psr";
                this._mech.event = 0.83;
                this._mech.preset = "blob";
              } else if (pr === "highrare") {
                this._mech.regime = "ssr";
                this._mech.event = 0.78;
                this._mech.preset = null;
              } else if (pr === "equatorial") {
                this._mech.regime = "ssr";
                this._mech.event = 0.8;
                this._mech.preset = "equatorial";
              } else if (pr === "highmixed") {
                this._mech.regime = "ssr";
                this._mech.event = 0.3;
                this._mech.preset = null;
              }
              if (slider) slider.value = this._mech.event;
              this._mechUpdate();
            });
          });
          this._mechUpdate();
        }
      };
    };
})();
