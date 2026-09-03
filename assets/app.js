/* Stockings & Footjob Daily — frontend logic
 * 讀取 results/latest.json 並套用篩選 / 排序 / 分頁。
 * 資料格式參見 stockings_daily/main.py 的 write_results。
 */
(() => {
  "use strict";

  // ---- DOM ----
  const $ = (id) => document.getElementById(id);
  const grid = $("grid");
  const pager = $("pager");
  const summary = $("summary");
  const meta = $("meta");
  const tagChips = $("tagChips");
  const yearEl = $("year");
  yearEl.textContent = new Date().getFullYear();

  // ---- State ----
  const state = {
    raw: [],            // 全部影片物件
    filtered: [],       // 篩選後
    page: 1,
    pageSize: 24,
    sort: "uploaded_desc",
    filters: {
      q: "",
      source: "",
      topic: "",
      kwTag: "",        // 從 chips 選的關鍵字
      minViews: 0,
      minDur: 0,
      maxDur: 0,
      withinDays: 0,
    },
  };

  // ---- 關鍵字分群（與 config.yaml 對齊；前端 fallback） ----
  const TOPIC_KEYWORDS = {
    stockings: [
      "絲襪", "黑絲", "連褲襪", "褲襪",
      "stockings", "pantyhose", "tights",
      "パンスト", "タイツ", "ストッキング", "黒タイツ", "網タイツ"
    ],
    footjob: [
      "腳交", "足交", "足戯", "足技",
      "footjob", "foot fetish", "foot worship",
      "足コキ", "足フェチ", "足裏", "足舐め"
    ],
  };

  // ---- Utils ----
  const fmtNum = (n) => (n == null ? "—" : Number(n).toLocaleString());
  const fmtDur = (m) => {
    if (m == null) return "—";
    const mm = Math.round(m);
    if (mm < 60) return `${mm} 分鐘`;
    const h = Math.floor(mm / 60);
    const rest = mm % 60;
    return rest ? `${h} 時 ${rest} 分` : `${h} 時`;
  };
  const fmtDate = (iso) => {
    if (!iso) return "—";
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return "—";
      return d.toISOString().slice(0, 10);
    } catch { return "—"; }
  };
  const escapeHtml = (s) =>
    (s ?? "").toString()
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  function describe(v) {
    // 自動生一段「影片描述」：來源 / 觀看 / 時長 / 命中關鍵字
    const parts = [];
    parts.push(`來源：${v.source === "jable" ? "Jable.tv" : "MissAV"}`);
    if (v.views != null) parts.push(`觀看 ${fmtNum(v.views)} 次`);
    if (v.duration_min != null) parts.push(`時長 ${fmtDur(v.duration_min)}`);
    if (v.uploaded_at) parts.push(`上傳於 ${fmtDate(v.uploaded_at)}`);
    if (v.matched_keywords && v.matched_keywords.length) {
      parts.push(`命中關鍵字：${v.matched_keywords.join("、")}`);
    }
    return parts.join(" · ");
  }

  function topicOf(keywords = []) {
    const kws = keywords.map((k) => k.toLowerCase());
    let hasStock = false, hasFoot = false;
    for (const k of kws) {
      if (TOPIC_KEYWORDS.stockings.some((x) => x.toLowerCase() === k)) hasStock = true;
      if (TOPIC_KEYWORDS.footjob.some((x) => x.toLowerCase() === k)) hasFoot = true;
    }
    if (hasStock && hasFoot) return "兩者皆是";
    if (hasStock) return "絲襪";
    if (hasFoot) return "腳交";
    return "—";
  }

  // ---- Load data ----
  async function loadData() {
    try {
      const res = await fetch("results/latest.json", { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      state.raw = data.videos || [];
      meta.textContent = `資料日期 ${data.date || "—"} · 筆數 ${data.count ?? state.raw.length}`;
    } catch (e) {
      meta.textContent = "無法讀取 results/latest.json";
      grid.innerHTML = `<div class="empty">尚未有資料或讀取失敗：${escapeHtml(e.message)}<br/><br/>請先執行 <code>python -m stockings_daily.main</code> 或等待 GitHub Actions 第一次排程。</div>`;
      return;
    }

    buildTagChips();
    bindEvents();
    applyFilters();
  }

  // ---- Quick tag chips ----
  function buildTagChips() {
    const counts = new Map();
    for (const v of state.raw) {
      for (const k of v.matched_keywords || []) {
        counts.set(k, (counts.get(k) || 0) + 1);
      }
    }
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
    tagChips.innerHTML = top
      .map(([k, c]) => `<button class="chip" data-kw="${escapeHtml(k)}">${escapeHtml(k)} (${c})</button>`)
      .join("");
    tagChips.querySelectorAll(".chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        const kw = btn.dataset.kw;
        state.filters.kwTag = state.filters.kwTag === kw ? "" : kw;
        tagChips.querySelectorAll(".chip").forEach((b) =>
          b.classList.toggle("is-active", b.dataset.kw === state.filters.kwTag));
        applyFilters();
      });
    });
  }

  // ---- Filtering & sorting ----
  function applyFilters() {
    const f = state.filters;
    const q = (f.q || "").trim().toLowerCase();

    state.filtered = state.raw.filter((v) => {
      if (f.source && v.source !== f.source) return false;

      // 主題分類
      if (f.topic) {
        const kws = (v.matched_keywords || []).map((k) => k.toLowerCase());
        const inGroup = TOPIC_KEYWORDS[f.topic].some((x) => kws.includes(x.toLowerCase()));
        if (!inGroup) return false;
      }

      if (f.kwTag) {
        const has = (v.matched_keywords || []).some((k) => k === f.kwTag);
        if (!has) return false;
      }

      if (q && !(v.title || "").toLowerCase().includes(q)) return false;

      if (f.minViews && (v.views == null || v.views < f.minViews)) return false;
      if (f.minDur && (v.duration_min == null || v.duration_min < f.minDur)) return false;
      if (f.maxDur && (v.duration_min != null && v.duration_min > f.maxDur)) return false;
      if (f.withinDays && v.uploaded_at) {
        const d = new Date(v.uploaded_at);
        const cutoff = Date.now() - f.withinDays * 86400000;
        if (!isNaN(d.getTime()) && d.getTime() < cutoff) return false;
      }
      return true;
    });

    sortList();
    state.page = 1;
    render();
  }

  function sortList() {
    const cmp = {
      uploaded_desc: (a, b) => (Date.parse(b.uploaded_at) || 0) - (Date.parse(a.uploaded_at) || 0),
      views_desc:    (a, b) => (b.views || 0) - (a.views || 0),
      duration_desc: (a, b) => (b.duration_min || 0) - (a.duration_min || 0),
      duration_asc:  (a, b) => (a.duration_min || 0) - (b.duration_min || 0),
      title_asc:     (a, b) => (a.title || "").localeCompare(b.title || "", "zh-Hant"),
    }[state.sort] || ((a, b) => 0);
    state.filtered.sort(cmp);
  }

  // ---- Render ----
  function cardHtml(v) {
    const tagsAll = [...(v.matched_keywords || []), ...(v.tags || [])];
    const tagsHtml = tagsAll
      .slice(0, 8)
      .map((t) => {
        const isHit = (v.matched_keywords || []).includes(t);
        return `<span class="card__tag${isHit ? " is-hit" : ""}">#${escapeHtml(t)}</span>`;
      })
      .join("");
    const cover = v.cover || "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 9'><rect width='16' height='9' fill='%23222'/><text x='8' y='5' font-size='1.2' text-anchor='middle' fill='%23666'>no image</text></svg>";

    return `
      <article class="card">
        <a class="card__cover" href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer"
           style="background-image:url('${escapeHtml(cover)}')" aria-label="${escapeHtml(v.title)}">
          <span class="card__badge">${escapeHtml(v.source)}</span>
          ${v.duration_min != null ? `<span class="card__duration">${fmtDur(v.duration_min)}</span>` : ""}
        </a>
        <div class="card__body">
          <h3 class="card__title">
            <a href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(v.title || "(無標題)")}</a>
          </h3>
          <div class="card__meta">
            <span title="主題分類">🏷 ${escapeHtml(topicOf(v.matched_keywords))}</span>
            <span title="上傳日期">📅 ${fmtDate(v.uploaded_at)}</span>
            <span title="觀看數">👁 ${fmtNum(v.views)}</span>
          </div>
          <p class="card__desc">${escapeHtml(describe(v))}</p>
          <div class="card__tags">${tagsHtml}</div>
          <div class="card__actions">
            <a class="card__btn" href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer">前往原站</a>
            <a class="card__btn card__btn--alt" href="https://www.google.com/search?q=${encodeURIComponent((v.title || "") + " " + (v.source === "jable" ? "jable.tv" : "missav"))}"
               target="_blank" rel="noopener noreferrer">搜尋</a>
          </div>
        </div>
      </article>
    `;
  }

  function render() {
    const total = state.filtered.length;
    const size = state.pageSize;
    const pageCount = Math.max(1, Math.ceil(total / size));
    state.page = Math.min(state.page, pageCount);
    const start = (state.page - 1) * size;
    const slice = state.filtered.slice(start, start + size);

    summary.textContent = `共 ${total} 筆符合條件 · 第 ${state.page} / ${pageCount} 頁`;

    if (total === 0) {
      grid.innerHTML = `<div class="empty">沒有符合條件的影片，試著放寬篩選條件或重置。</div>`;
      pager.innerHTML = "";
      return;
    }
    grid.innerHTML = slice.map(cardHtml).join("");
    renderPager(pageCount);
  }

  function renderPager(pageCount) {
    const btn = (label, page, opts = {}) => {
      const dis = opts.disabled ? "disabled" : "";
      const cur = opts.current ? "is-current" : "";
      return `<button class="${cur}" data-page="${page}" ${dis}>${label}</button>`;
    };
    const parts = [];
    parts.push(btn("« 第一頁", 1, { disabled: state.page === 1 }));
    parts.push(btn("‹ 上一頁", state.page - 1, { disabled: state.page === 1 }));

    const window = 5;
    let s = Math.max(1, state.page - Math.floor(window / 2));
    let e = Math.min(pageCount, s + window - 1);
    s = Math.max(1, e - window + 1);
    for (let i = s; i <= e; i++) parts.push(btn(i, i, { current: i === state.page }));

    parts.push(btn("下一頁 ›", state.page + 1, { disabled: state.page === pageCount }));
    parts.push(btn("最後頁 »", pageCount, { disabled: state.page === pageCount }));
    pager.innerHTML = parts.join("");
    pager.querySelectorAll("button").forEach((b) => {
      b.addEventListener("click", () => {
        const p = parseInt(b.dataset.page, 10);
        if (!isNaN(p)) { state.page = p; render(); window.scrollTo({ top: 0, behavior: "smooth" }); }
      });
    });
  }

  // ---- Events ----
  function bindEvents() {
    const wire = (el, key, parse = (v) => v) => {
      el.addEventListener("input", () => { state.filters[key] = parse(el.value); applyFilters(); });
      el.addEventListener("change", () => { state.filters[key] = parse(el.value); applyFilters(); });
    };
    wire($("q"), "q");
    wire($("source"), "source");
    wire($("topic"), "topic");
    wire($("minViews"), "minViews", (v) => parseInt(v, 10) || 0);
    wire($("minDur"), "minDur", (v) => parseInt(v, 10) || 0);
    wire($("maxDur"), "maxDur", (v) => parseInt(v, 10) || 0);
    wire($("withinDays"), "withinDays", (v) => parseInt(v, 10) || 0);

    $("sort").addEventListener("change", (e) => { state.sort = e.target.value; sortList(); state.page = 1; render(); });
    $("pageSize").addEventListener("change", (e) => {
      const v = Math.max(4, Math.min(60, parseInt(e.target.value, 10) || 24));
      state.pageSize = v;
      state.page = 1;
      render();
    });

    $("resetBtn").addEventListener("click", () => {
      state.filters = { q: "", source: "", topic: "", kwTag: "", minViews: 0, minDur: 0, maxDur: 0, withinDays: 0 };
      state.sort = "uploaded_desc";
      state.pageSize = 24;
      $("q").value = ""; $("source").value = ""; $("topic").value = "";
      $("minViews").value = ""; $("minDur").value = ""; $("maxDur").value = "";
      $("withinDays").value = ""; $("pageSize").value = "24"; $("sort").value = "uploaded_desc";
      tagChips.querySelectorAll(".chip").forEach((b) => b.classList.remove("is-active"));
      applyFilters();
    });
  }

  // ---- Init ----
  loadData();
})();
