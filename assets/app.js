/* Vendor Risk Assessment (TPRM) web app. No dependencies, no network. MIT License. */
(function () {
  "use strict";
  var T = window.TPRM;
  var STORAGE = "tprm-draft", SCHEMA = "vendor-risk-assessment/1.0", BLANK_KEY = "tprm-blank";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var factor = function (key, label) { var row = T.factors[key].filter(function (f) { return f[0] === label; })[0]; return row ? row[1] : null; };
  var ANSWER_SCORE = { "Yes": 1, "Partial": 0.5, "No": 0 };
  var RATING_ORDER = ["Critical", "High", "Medium", "Low"];
  var TIER_ORDER = ["Tier 1", "Tier 2", "Tier 3"];

  /* ---------- state ---------- */
  var state = { vendors: [], assessments: {}, current: "" };
  function blankVendor() {
    var n = state.vendors.length + 1;
    return { id: "VND-" + String(n).padStart(3, "0"), name: "", service: "", category: "", owner: "", data: "", crit: "", access: "", ai: "", location: "", contractEnd: "", status: "Onboarding", notes: "" };
  }
  function assessment(id) {
    if (!state.assessments[id]) state.assessments[id] = { date: "", assessor: "", status: "Not started", answers: {}, comments: {}, override: "", overrideReason: "", clauses: {} };
    return state.assessments[id];
  }
  function save() { try { localStorage.setItem(STORAGE, JSON.stringify(state)); } catch (e) { /* private mode */ } }
  function load() { try { var s = JSON.parse(localStorage.getItem(STORAGE) || "null"); if (s && s.vendors) importDoc(s); } catch (e) { /* unreadable saved state: keep the default */ } }

  /* ---------- model ---------- */
  function inherent(v) {
    var d = factor("data", v.data), c = factor("crit", v.crit), a = factor("access", v.access), i = factor("ai", v.ai);
    if (d == null || c == null || a == null || i == null) return null;
    return d * c * a * i;
  }
  function tierOf(v) { var s = inherent(v); if (s == null) return ""; return s >= T.tier1Min ? "Tier 1" : s >= T.tier2Min ? "Tier 2" : "Tier 3"; }
  function score(a) {
    var obtained = 0, available = 0, w3no = 0, answered = 0, byDomain = {};
    T.questions.forEach(function (q) {
      var ans = a.answers[q.id]; if (!ans) return; answered++;
      if (ans === "N/A") return;
      var d = byDomain[q.domain] || (byDomain[q.domain] = { o: 0, a: 0 });
      obtained += q.weight * ANSWER_SCORE[ans]; available += q.weight;
      d.o += q.weight * ANSWER_SCORE[ans]; d.a += q.weight;
      if (ans === "No" && q.weight === 3) w3no++;
    });
    var pct = available ? Math.round((obtained / available) * 1000) / 10 : null;
    var band = pct == null ? "" : T.bands.filter(function (b) { return pct >= b[1]; })[0][0];
    return { pct: pct, band: band, w3no: w3no, answered: answered, byDomain: byDomain };
  }
  function computedRating(tier, band) { return (tier && band && T.residual[tier]) ? T.residual[tier][band] : ""; }
  function overrideReason(a) { return String(a.overrideReason || "").trim(); }
  function overrideActive(a) { return !!a.override && !!overrideReason(a); }
  function finalRating(v, a) { var r = computedRating(tierOf(v), score(a).band); return overrideActive(a) ? a.override : r; }
  /* Dates are calendar dates (YYYY-MM-DD), never instants: no Date parsing, no UTC conversion, so the result is
     the same in every timezone. Month-end rule: the day is clamped to the last day of the target month
     (2026-01-31 + 1 month = 2026-02-28). */
  function pad2(n) { return String(n).padStart(2, "0"); }
  function isIsoDate(iso) {
    var p = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || ""); if (!p) return false;
    var mo = +p[2], d = +p[3]; return mo >= 1 && mo <= 12 && d >= 1 && d <= daysInMonth(+p[1], mo - 1);
  }
  function daysInMonth(y, m0) { return [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m0]; }
  function addMonths(iso, m) {
    if (!isIsoDate(iso)) return "";
    var y = +iso.slice(0, 4), m0 = +iso.slice(5, 7) - 1 + m, d = +iso.slice(8, 10);
    y += Math.floor(m0 / 12); m0 = ((m0 % 12) + 12) % 12;
    return y + "-" + pad2(m0 + 1) + "-" + pad2(Math.min(d, daysInMonth(y, m0)));
  }
  function todayIso() { var t = new Date(); return t.getFullYear() + "-" + pad2(t.getMonth() + 1) + "-" + pad2(t.getDate()); }
  function nextReview(v, a) { var t = tierOf(v); return t && a.date ? addMonths(a.date, T.cadence[t]) : ""; }
  function overdue(v, a) { var n = nextReview(v, a); return !!n && n < todayIso() && a.status !== "Complete"; }
  function clauseLevel(cl, tier) { return T.clauseLevels[cl[tier]] || ""; }
  function missingRequired(v, a) { var t = tierOf(v); if (!t) return null; return T.clauses.filter(function (c) { return c[t] === "R" && a.clauses[c.id] !== "Y"; }).length; }

  /* ---------- helpers ---------- */
  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { if (k === "text") n.textContent = attrs[k]; else if (k === "class") n.className = attrs[k]; else n.setAttribute(k, attrs[k]); });
    (children || []).forEach(function (c) { if (c != null) n.appendChild(typeof c === "string" ? document.createTextNode(c) : c); });
    return n;
  }
  function pill(v) { return v ? el("span", { class: "pill", "data-v": v, text: v }) : el("span", { class: "muted", text: "—" }); }
  function select(options, value, label, onchange, blank) {
    var s = el("select", { "aria-label": label });
    if (blank) s.appendChild(el("option", { value: "", text: blank }));
    options.forEach(function (o) { var v = Array.isArray(o) ? o[0] : o; var op = el("option", { value: v, text: v }); if (v === value) op.selected = true; s.appendChild(op); });
    s.addEventListener("change", function () { onchange(s.value); save(); });
    return s;
  }
  function input(value, label, onchange, type) {
    var i = el("input", { type: type || "text", "aria-label": label }); i.value = value || "";
    i.addEventListener("input", function () { onchange(i.value); save(); });
    return i;
  }
  function say(m) { $("#status").textContent = m; }

  /* ---------- inventory ---------- */
  function renderInventory() {
    var body = $("#inventory-body"); body.textContent = "";
    state.vendors.forEach(function (v, idx) {
      var scoreCell = el("td", { class: "w" }), tierCell = el("td");
      var refresh = function () { var s = inherent(v); scoreCell.textContent = s == null ? "—" : String(s); tierCell.textContent = ""; tierCell.appendChild(pill(tierOf(v))); renderVendorSelects(); };
      var tr = el("tr", null, [
        el("td", { class: "id" }, [input(v.id, "Vendor id", function (x) { var old = v.id; v.id = x; if (state.assessments[old]) { state.assessments[x] = state.assessments[old]; delete state.assessments[old]; } if (state.current === old) state.current = x; renderVendorSelects(); })]),
        el("td", null, [input(v.name, "Vendor name", function (x) { v.name = x; renderVendorSelects(); })]),
        el("td", null, [input(v.service, "Service", function (x) { v.service = x; })]),
        el("td", null, [select(T.categories, v.category, "Category", function (x) { v.category = x; }, "—")]),
        el("td", null, [input(v.owner, "Owner role", function (x) { v.owner = x; })]),
        el("td", null, [select(T.factors.data, v.data, "Data classification", function (x) { v.data = x; refresh(); }, "—")]),
        el("td", null, [select(T.factors.crit, v.crit, "Business criticality", function (x) { v.crit = x; refresh(); }, "—")]),
        el("td", null, [select(T.factors.access, v.access, "Access type", function (x) { v.access = x; refresh(); }, "—")]),
        el("td", null, [select(T.factors.ai, v.ai, "AI use", function (x) { v.ai = x; refresh(); }, "—")]),
        scoreCell, tierCell,
        el("td", null, [input(v.contractEnd, "Contract end", function (x) { v.contractEnd = x; }, "date")]),
        el("td", null, [select(T.statusInventory, v.status, "Status", function (x) { v.status = x; })]),
        el("td", null, [el("button", { type: "button", class: "btn btn-sm btn-danger", text: "Remove", "aria-label": "Remove " + (v.name || v.id) })])
      ]);
      tr.lastChild.firstChild.addEventListener("click", function () { state.vendors.splice(idx, 1); delete state.assessments[v.id]; if (state.current === v.id) state.current = ""; save(); renderAll(); });
      body.appendChild(tr);
      refresh();
    });
    if (!state.vendors.length) body.appendChild(el("tr", null, [el("td", { colspan: "14", class: "muted", text: "No vendors yet. Add one, or load the sample." })]));
  }

  /* ---------- vendor selects ---------- */
  function renderVendorSelects() {
    ["#q-vendor", "#c-vendor"].forEach(function (id) {
      var s = $(id); s.textContent = "";
      s.appendChild(el("option", { value: "", text: state.vendors.length ? "Select a vendor" : "Add vendors in the inventory first" }));
      state.vendors.forEach(function (v) { var o = el("option", { value: v.id, text: v.id + " · " + (v.name || "(unnamed)") + (tierOf(v) ? " · " + tierOf(v) : "") }); if (v.id === state.current) o.selected = true; s.appendChild(o); });
    });
  }
  function currentVendor() { return state.vendors.filter(function (v) { return v.id === state.current; })[0] || null; }

  /* ---------- questionnaire ---------- */
  /* The override only takes effect once a reason is given; the field is flagged until then. */
  function syncOverride(v, a) {
    var comp = computedRating(tierOf(v), score(a).band);
    $("#q-final").value = overrideActive(a) ? a.override + " (override)" : (a.override ? (comp || "—") + " (override ignored: add a reason)" : comp);
    var reason = $("#q-override-reason"), missing = !!a.override && !overrideReason(a);
    reason.required = !!a.override; reason.setAttribute("aria-invalid", missing ? "true" : "false");
    reason.setCustomValidity(missing ? "A reason is required when overriding the computed rating." : "");
  }
  function renderQuestionnaire() {
    var v = currentVendor(), body = $("#q-body"); body.textContent = "";
    var kp = $("#q-kpis"), bars = $("#q-bars"); kp.textContent = ""; bars.textContent = "";
    ["#q-date", "#q-assessor", "#q-status", "#q-override", "#q-override-reason"].forEach(function (id) { $(id).disabled = !v; });
    if (!v) { $("#q-computed").value = ""; $("#q-final").value = ""; body.appendChild(el("tr", null, [el("td", { colspan: "6", class: "muted", text: "Select a vendor above." })])); return; }
    var a = assessment(v.id);
    $("#q-date").value = a.date || ""; $("#q-assessor").value = a.assessor || ""; $("#q-status").value = a.status || "Not started";
    $("#q-override").value = a.override || ""; $("#q-override-reason").value = a.overrideReason || "";
    function refreshScores() {
      var sc = score(a), tier = tierOf(v), comp = computedRating(tier, sc.band);
      $("#q-computed").value = comp || (tier ? "answer the questionnaire" : "set the four factors in the inventory");
      syncOverride(v, a);
      kp.textContent = "";
      [["Inherent tier", tier || "—", "from the inventory"], ["Overall score", sc.pct == null ? "—" : sc.pct + " %", "weighted, N/A excluded"], ["Score band", sc.band || "—", "Strong · Adequate · Weak · Poor"],
       ["Answered", sc.answered + " / " + T.questions.length, "questions"], ["Weight-3 answered No", String(sc.w3no), "critical controls missing"], ["Next review", nextReview(v, a) || "—", "assessment date + cadence"]]
        .forEach(function (k) { kp.appendChild(el("div", { class: "kpi" }, [el("small", { text: k[0] }), el("b", { text: k[1] }), el("small", { text: k[2] })])); });
      bars.textContent = "";
      T.domains.forEach(function (d) {
        var x = sc.byDomain[d.code], p = x && x.a ? Math.round((x.o / x.a) * 100) : 0;
        var fill = el("div", { class: "fill" }); fill.style.width = p + "%";
        bars.appendChild(el("div", { class: "bar" }, [el("span", { text: d.name }), el("div", { class: "track", role: "img", "aria-label": d.name + " " + p + "%" }, [fill]), el("span", { class: "pct", text: x && x.a ? p + "%" : "—" })]));
      });
    }
    T.domains.forEach(function (d) {
      body.appendChild(el("tr", { class: "domain-row" }, [el("td", { colspan: "6", text: d.name })]));
      T.questions.filter(function (q) { return q.domain === d.code; }).forEach(function (q) {
        var tr = el("tr", { class: (a.answers[q.id] === "No" && q.weight === 3) ? "w3no" : "" });
        var sel = select(T.answers, a.answers[q.id] || "", "Answer to " + q.id, function (x) { if (x) a.answers[q.id] = x; else delete a.answers[q.id]; tr.className = (x === "No" && q.weight === 3) ? "w3no" : ""; refreshScores(); renderDashboard(); }, "—");
        var ta = el("textarea", { rows: "1", "aria-label": "Comment for " + q.id }); ta.value = a.comments[q.id] || "";
        ta.addEventListener("input", function () { a.comments[q.id] = ta.value; save(); });
        tr.appendChild(el("td", { class: "id", text: q.id })); tr.appendChild(el("td", { text: q.text })); tr.appendChild(el("td", { class: "w", text: String(q.weight) }));
        tr.appendChild(el("td", { class: "hint", text: q.evidence })); tr.appendChild(el("td", null, [sel])); tr.appendChild(el("td", null, [ta]));
        body.appendChild(tr);
      });
    });
    refreshScores();
  }

  /* ---------- contract ---------- */
  function renderContract() {
    var v = currentVendor(), body = $("#c-body"); body.textContent = "";
    if (!v) { $("#c-meta").textContent = ""; body.appendChild(el("tr", null, [el("td", { colspan: "5", class: "muted", text: "Select a vendor above." })])); return; }
    var a = assessment(v.id), tier = tierOf(v);
    function meta() { var m = missingRequired(v, a); $("#c-meta").textContent = tier ? tier + " · " + (m === 0 ? "all required clauses present" : m + " required clause(s) missing") : "Set the four risk factors in the inventory to know which clauses are required."; }
    T.clauses.forEach(function (c) {
      var lvl = tier ? clauseLevel(c, tier) : "";
      var sel = select(["Y", "N"], a.clauses[c.id] || "", "Clause " + c.id + " in contract", function (x) { if (x) a.clauses[c.id] = x; else delete a.clauses[c.id]; meta(); renderDashboard(); }, "—");
      body.appendChild(el("tr", null, [el("td", { class: "id", text: c.id }), el("td", { text: c.clause }), el("td", { class: "hint", text: c.why }), el("td", null, [pill(lvl)]), el("td", null, [sel])]));
    });
    meta();
  }

  /* ---------- dashboard ---------- */
  function renderDashboard() {
    var kp = $("#d-kpis"), counts = $("#d-counts"), body = $("#d-body"); kp.textContent = ""; counts.textContent = ""; body.textContent = "";
    var byTier = {}, byRating = {}, t1 = 0, t1done = 0, over = 0, complete = 0;
    state.vendors.forEach(function (v) {
      var a = assessment(v.id), t = tierOf(v), r = finalRating(v, a);
      if (t) byTier[t] = (byTier[t] || 0) + 1; if (r) byRating[r] = (byRating[r] || 0) + 1;
      if (t === "Tier 1") { t1++; if (a.status === "Complete") t1done++; }
      if (overdue(v, a)) over++; if (a.status === "Complete") complete++;
    });
    [["Vendors", String(state.vendors.length), "in the inventory"], ["Tier 1 coverage", t1 ? t1done + " / " + t1 : "—", "complete assessments"], ["Overdue reviews", String(over), "next review in the past, not complete"],
     ["Assessments complete", complete + " / " + state.vendors.length, ""], ["Critical or High", String((byRating.Critical || 0) + (byRating.High || 0)), "final rating"]]
      .forEach(function (k) { kp.appendChild(el("div", { class: "kpi" }, [el("small", { text: k[0] }), el("b", { text: k[1] }), el("small", { text: k[2] })])); });
    function distribution(title, subtitle, order, map) {
      var box = el("section", { class: "distribution", "aria-label": title }, [el("h3", { text: title }), el("p", { class: "muted", text: subtitle })]);
      order.forEach(function (k) {
        var value = map[k] || 0, total = state.vendors.length;
        box.appendChild(el("div", { class: "distribution-row", "data-rating": k }, [
          el("div", { class: "distribution-label" }, [pill(k), el("span", { text: value + " vendor" + (value === 1 ? "" : "s") })]),
          el("progress", { max: String(total || 1), value: String(value), "aria-label": k + ": " + value + " of " + total + " vendors" })
        ]));
      });
      var classified = order.reduce(function (n, k) { return n + (map[k] || 0); }, 0);
      box.appendChild(el("p", { class: "distribution-footnote", text: (state.vendors.length - classified) + " not yet classified · proportions of all vendors" }));
      return box;
    }
    counts.appendChild(distribution("Inherent exposure", "Vendor criticality before control assessment", TIER_ORDER, byTier));
    counts.appendChild(distribution("Residual risk profile", "Final ratings after assessment and overrides", RATING_ORDER, byRating));
    var queue = el("section", { class: "distribution review-queue", "aria-label": "Review priorities" }, [el("h3", { text: "Review priorities" }), el("p", { class: "muted", text: "Where your next conversation starts" })]);
    var pending = state.vendors.filter(function (v) { var a = assessment(v.id); return overdue(v, a) || finalRating(v, a) === "Critical" || finalRating(v, a) === "High"; });
    pending.sort(function (a, b) { return Number(overdue(b, assessment(b.id))) - Number(overdue(a, assessment(a.id))); });
    pending.slice(0, 3).forEach(function (v) {
      var a = assessment(v.id), reason = overdue(v, a) ? "Review overdue" : finalRating(v, a) + " residual risk";
      var button = el("button", { type: "button", class: "queue-item", "aria-label": "Review " + (v.name || v.id) }, [el("span", { class: "vendor-avatar", "aria-hidden": "true", text: (v.name || v.id).slice(0, 2).toUpperCase() }), el("span", { class: "queue-copy" }, [el("strong", { text: v.name || v.id }), el("small", { text: reason })]), el("span", { "aria-hidden": "true", text: "↗" })]);
      button.addEventListener("click", function () { state.current = v.id; save(); renderVendorSelects(); renderQuestionnaire(); renderContract(); showTab("tab-questionnaire"); $("#q-vendor").focus(); });
      queue.appendChild(button);
    });
    queue.appendChild(el("p", { class: "distribution-footnote", text: pending.length ? pending.length + " vendors flagged · overdue reviews shown first" : "No high/critical ratings or overdue reviews flagged. Unassessed vendors still need review." }));
    counts.appendChild(queue);
    state.vendors.forEach(function (v) {
      var a = assessment(v.id), sc = score(a), m = missingRequired(v, a);
      body.appendChild(el("tr", null, [el("td", { class: "id", text: v.id }), el("td", { text: v.name }), el("td", null, [pill(tierOf(v))]), el("td", { text: sc.pct == null ? "—" : sc.pct + " %" }), el("td", { text: sc.band || "—" }),
        el("td", null, [pill(finalRating(v, a))]), el("td", { text: a.status }), el("td", { text: a.date || "—" }), el("td", null, [el("span", { text: nextReview(v, a) || "—" }), overdue(v, a) ? el("span", { class: "pill", "data-v": "overdue", text: " overdue" }) : null]),
        el("td", null, [m == null ? el("span", { text: "—" }) : m ? el("span", { class: "pill", "data-v": "missing", text: String(m) }) : el("span", { text: "0" })])]));
    });
    if (!state.vendors.length) body.appendChild(el("tr", null, [el("td", { colspan: "10", class: "muted", text: "Nothing to report yet." })]));
  }

  function renderAll() { renderInventory(); renderVendorSelects(); renderQuestionnaire(); renderContract(); renderDashboard(); }

  /* ---------- export / import ---------- */
  function download(name, text, type) { var b = new Blob([text], { type: type || "application/json" }); var a = el("a", { href: URL.createObjectURL(b), download: name }); document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500); }
  function cell(v) { v = String(v == null ? "" : v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function summaryCsv() {
    var lines = [["id", "vendor", "tier", "inherent_score", "score_pct", "band", "computed_rating", "override", "override_reason", "final_rating", "status", "assessed", "next_review", "overdue", "missing_required_clauses"].join(",")];
    state.vendors.forEach(function (v) { var a = assessment(v.id), sc = score(a); lines.push([v.id, v.name, tierOf(v), inherent(v), sc.pct, sc.band, computedRating(tierOf(v), sc.band), a.override, a.overrideReason, finalRating(v, a), a.status, a.date, nextReview(v, a), overdue(v, a) ? "yes" : "no", missingRequired(v, a)].map(cell).join(",")); });
    return lines.join("\n");
  }
  function isObj(x) { return !!x && typeof x === "object" && !Array.isArray(x); }
  var VENDOR_TEXT = ["id", "name", "service", "category", "owner", "data", "crit", "access", "ai", "location", "contractEnd", "status", "notes"];
  /* Returns a list of problems; empty means the document is safe to load. Nothing is changed until it passes. */
  function validateDoc(doc) {
    var errs = [];
    if (!isObj(doc)) return ["the file is not a JSON object"];
    if (!Array.isArray(doc.vendors)) return ["missing \"vendors\" list"];
    var ids = {};
    doc.vendors.forEach(function (v, i) {
      var at = "vendor #" + (i + 1);
      if (!isObj(v)) { errs.push(at + " is not an object"); return; }
      if (typeof v.id !== "string" || !v.id.trim()) errs.push(at + " has no id");
      else if (ids[v.id]) errs.push(at + " repeats id " + v.id); else ids[v.id] = true;
      VENDOR_TEXT.forEach(function (k) { if (v[k] != null && typeof v[k] !== "string") errs.push(at + ": " + k + " must be text"); });
      if (v.contractEnd && !isIsoDate(v.contractEnd)) errs.push(at + ": contractEnd must be YYYY-MM-DD");
    });
    if (doc.assessments != null && !isObj(doc.assessments)) errs.push("\"assessments\" must be an object");
    else Object.keys(doc.assessments || {}).forEach(function (id) {
      var a = doc.assessments[id], at = "assessment " + id;
      if (!isObj(a)) { errs.push(at + " is not an object"); return; }
      if (!ids[id]) errs.push(at + " has no matching vendor");
      if (a.date && !isIsoDate(a.date)) errs.push(at + ": date must be YYYY-MM-DD");
      ["answers", "comments", "clauses"].forEach(function (k) { if (a[k] != null && !isObj(a[k])) errs.push(at + ": " + k + " must be an object"); });
      ["assessor", "status", "overrideReason"].forEach(function (k) { if (a[k] != null && typeof a[k] !== "string") errs.push(at + ": " + k + " must be text"); });
      if (a.override && RATING_ORDER.indexOf(a.override) < 0) errs.push(at + ": override must be one of " + RATING_ORDER.join(", "));
      if (a.override && !String(a.overrideReason || "").trim()) errs.push(at + ": override " + a.override + " has no reason");
    });
    if (doc.current != null && typeof doc.current !== "string") errs.push("\"current\" must be text");
    return errs;
  }
  function importDoc(doc) {
    var errs = validateDoc(doc);
    if (errs.length) throw new Error(errs.slice(0, 3).join("; ") + (errs.length > 3 ? " (+" + (errs.length - 3) + " more)" : "") + ". Nothing was changed.");
    var assessments = {};
    Object.keys(doc.assessments || {}).forEach(function (id) {
      var a = doc.assessments[id];
      assessments[id] = { date: a.date || "", assessor: a.assessor || "", status: a.status || "Not started", answers: a.answers || {}, comments: a.comments || {}, override: a.override || "", overrideReason: a.overrideReason || "", clauses: a.clauses || {} };
    });
    state = { vendors: doc.vendors.map(function (v) { var o = {}; VENDOR_TEXT.forEach(function (k) { o[k] = v[k] == null ? "" : v[k]; }); return o; }), assessments: assessments, current: doc.current || "" };
    return state.vendors.length;
  }
  function loadSample() {
    state = { vendors: JSON.parse(JSON.stringify(T.vendors)), assessments: {}, current: T.sample.vendor };
    var a = assessment(T.sample.vendor); a.date = T.sample.date; a.assessor = T.sample.assessor; a.status = "Complete";
    a.answers = JSON.parse(JSON.stringify(T.sample.answers)); a.comments = JSON.parse(JSON.stringify(T.sample.comments));
    T.clauses.forEach(function (c) { a.clauses[c.id] = (c.id === "CL-06" || c.id === "CL-15") ? "N" : "Y"; });
    var b = assessment("VND-003"); b.date = "2025-06-15"; b.status = "In review"; b.assessor = "Security Analyst, GRC team";
    var c = assessment("VND-001"); c.date = "2026-02-01"; c.status = "Complete"; c.assessor = "Head of Infrastructure"; c.override = "High"; c.overrideReason = "Single cloud provider for all production workloads; exit plan not yet documented.";
    T.questions.forEach(function (q) { c.answers[q.id] = q.domain === "AI" ? "N/A" : "Yes"; });
    T.clauses.forEach(function (cl) { c.clauses[cl.id] = cl.id === "CL-16" ? "N" : "Y"; });
    save();
  }

  /* ---------- theme ---------- */
  function applyTheme(t) {
    if (t) document.documentElement.setAttribute("data-theme", t); else document.documentElement.removeAttribute("data-theme");
    var dark = t === "dark" || (!t && window.matchMedia("(prefers-color-scheme: dark)").matches);
    $("#theme-toggle").textContent = dark ? "Light theme" : "Dark theme"; $("#theme-toggle").setAttribute("aria-pressed", String(dark));
  }

  /* ---------- init ---------- */
  function showTab(id) {
    document.querySelectorAll('[role="tab"]').forEach(function (t) { var on = t.id === id; t.setAttribute("aria-selected", String(on)); $("#" + t.getAttribute("aria-controls")).hidden = !on; });
  }
  function init() {
    load();
    $("#t1min").textContent = String(T.tier1Min); $("#t2min").textContent = String(T.tier2Min);
    T.statusAssessment.forEach(function (s) { $("#q-status").appendChild(el("option", { value: s, text: s })); });
    RATING_ORDER.forEach(function (r) { $("#q-override").appendChild(el("option", { value: r, text: r })); });
    document.querySelectorAll('[role="tab"]').forEach(function (t) { t.addEventListener("click", function () { showTab(t.id); }); });
    ["#q-vendor", "#c-vendor"].forEach(function (id) { $(id).addEventListener("change", function (e) { state.current = e.target.value; save(); renderVendorSelects(); renderQuestionnaire(); renderContract(); }); });
    $("#q-date").addEventListener("input", function (e) { var v = currentVendor(); if (v) { assessment(v.id).date = e.target.value; save(); renderQuestionnaire(); renderDashboard(); } });
    $("#q-assessor").addEventListener("input", function (e) { var v = currentVendor(); if (v) { assessment(v.id).assessor = e.target.value; save(); } });
    $("#q-status").addEventListener("change", function (e) { var v = currentVendor(); if (v) { assessment(v.id).status = e.target.value; save(); renderDashboard(); } });
    $("#q-override").addEventListener("change", function (e) { var v = currentVendor(); if (v) { assessment(v.id).override = e.target.value; save(); renderQuestionnaire(); renderDashboard(); } });
    $("#q-override-reason").addEventListener("input", function (e) { var v = currentVendor(); if (v) { var a = assessment(v.id); a.overrideReason = e.target.value; save(); syncOverride(v, a); renderDashboard(); } });
    $("#btn-add-vendor").addEventListener("click", function () { state.vendors.push(blankVendor()); save(); renderInventory(); renderVendorSelects(); renderDashboard(); });
    $("#btn-sample").addEventListener("click", function () { loadSample(); renderAll(); showTab("tab-dashboard"); $("#demo-banner").hidden = false; say("Sample loaded: six fictional vendors, worked questionnaire for " + T.sample.vendor + "."); });
    $("#btn-start-blank").addEventListener("click", function () { state = { vendors: [], assessments: {}, current: "" }; try { localStorage.removeItem(STORAGE); localStorage.setItem(BLANK_KEY, "1"); } catch (e) { /* ignore */ } $("#demo-banner").hidden = true; renderAll(); showTab("tab-inventory"); say("Blank assessment: add your vendors in the inventory."); });
    $("#btn-export").addEventListener("click", function () { download("tprm-" + todayIso() + ".json", JSON.stringify({ schema: SCHEMA, exported: new Date().toISOString(), vendors: state.vendors, assessments: state.assessments, current: state.current }, null, 2)); say("JSON exported."); });
    $("#btn-export-csv").addEventListener("click", function () { download("tprm-summary.csv", summaryCsv(), "text/csv"); say("Summary CSV exported."); });
    $("#file-import").addEventListener("change", function (e) { var f = e.target.files[0]; if (!f) return; var r = new FileReader(); r.onload = function () { try { var n = importDoc(JSON.parse(r.result)); save(); renderAll(); say("Imported " + n + " vendors."); } catch (err) { say("Import failed: " + err.message); } e.target.value = ""; }; r.readAsText(f); });
    $("#btn-print").addEventListener("click", function () { window.print(); });
    $("#btn-reset").addEventListener("click", function () { state = { vendors: [], assessments: {}, current: "" }; try { localStorage.removeItem(STORAGE); localStorage.setItem(BLANK_KEY, "1"); } catch (e) { /* ignore */ } $("#demo-banner").hidden = true; renderAll(); say("Reset."); });
    var saved = null; try { saved = localStorage.getItem("tprm-theme"); } catch (e) { /* ignore */ }
    applyTheme(saved || "light");
    $("#theme-toggle").addEventListener("click", function () { var cur = document.documentElement.getAttribute("data-theme"); var dark = cur === "dark" || (!cur && window.matchMedia("(prefers-color-scheme: dark)").matches); var next = dark ? "light" : "dark"; try { localStorage.setItem("tprm-theme", next); } catch (e) { /* ignore */ } applyTheme(next); });
    var blank = false; try { blank = localStorage.getItem(BLANK_KEY) === "1"; } catch (e) { /* ignore */ }
    /* first visit opens on the fictional sample, on the dashboard, so the results are visible straight away */
    if (!state.vendors.length && (/[?&]sample=1/.test(location.search) || !blank)) { loadSample(); renderAll(); showTab("tab-dashboard"); $("#demo-banner").hidden = false; } else renderAll();
  }
  document.addEventListener("DOMContentLoaded", init);
})();

