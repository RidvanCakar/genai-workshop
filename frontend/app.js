// MatchBrief — modern takım rehberi

const queryInput = document.getElementById("query");
const runBtn = document.getElementById("run-btn");
const welcome = document.getElementById("welcome");
const dashboard = document.getElementById("dashboard");
const errorBox = document.getElementById("error-box");
const heroContent = document.getElementById("hero-content");
const heroBg = document.getElementById("hero-bg");
const heroStats = document.getElementById("hero-stats");
const sourceLink = document.getElementById("source-link");
const loadingOverlay = document.getElementById("loading-overlay");

let teamData = null;
let activeTab = "general";
let aiCache = {};
let aiSection = "general";

// ── Helpers ──

function esc(s) {
  if (!s) return "";
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function showError(msg) {
  errorBox.innerHTML = `<span>⚠</span><span>${esc(msg)}</span>`;
  errorBox.classList.remove("hidden");
}

function hideError() {
  errorBox.classList.add("hidden");
}

function showLoading(text = "Takım bilgileri yükleniyor...") {
  document.getElementById("loading-text").textContent = text;
  loadingOverlay.classList.remove("hidden");
}

function hideLoading() {
  loadingOverlay.classList.add("hidden");
}

function formatDate(dateStr) {
  if (!dateStr) return { day: "—", mon: "" };
  const d = new Date(dateStr + "T00:00:00");
  const months = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
  return { day: d.getDate(), mon: months[d.getMonth()] };
}

function formatCapacity(n) {
  if (!n) return "—";
  return Number(n).toLocaleString("tr-TR") + " kişi";
}

function cardHeader(title) {
  return `<div class="card-header"><h3>${esc(title)}</h3><div class="card-header-line"></div></div>`;
}

function infoRow(label, value) {
  return `<div class="info-row"><span class="label">${esc(label)}</span><span class="value">${value}</span></div>`;
}

function emptyState(icon, text) {
  return `<div class="empty-state"><div class="empty-state-icon">${icon}</div>${esc(text)}</div>`;
}

function setTab(tab) {
  activeTab = tab;
  document.querySelectorAll(".tab-btn").forEach((b) => {
    b.classList.toggle("active", b.dataset.tab === tab);
  });
  document.querySelectorAll(".panel").forEach((p) => {
    p.classList.toggle("active", p.id === `panel-${tab}`);
  });
  if (tab === "ai" && !aiCache[aiSection]) loadAiBrief(aiSection);
}

// ── Render: Hero ──

function renderHero(data) {
  const { profile, images, stadium } = data;

  heroBg.style.backgroundImage = images.banner
    ? `url('${esc(images.banner)}')`
    : "none";

  const badgeHtml = images.badge
    ? `<div class="hero-badge-wrap"><div class="hero-badge-glow"></div><img class="hero-badge" src="${esc(images.badge)}" alt="${esc(profile.name)}" /></div>`
    : `<div class="hero-badge-placeholder">⚽</div>`;

  const modePill = data.brief_mode === "upcoming"
    ? `<span class="pill live">Yaklaşan maç</span>`
    : `<span class="pill neutral">Sezon arası</span>`;

  heroContent.innerHTML = `
    ${badgeHtml}
    <div class="hero-info">
      <h2>${esc(profile.name)}</h2>
      <div class="hero-meta">
        ${profile.league ? `<span class="pill">${esc(profile.league)}</span>` : ""}
        ${profile.country ? `<span class="pill neutral">${esc(profile.country)}</span>` : ""}
        ${profile.founded ? `<span class="pill neutral">Est. ${esc(String(profile.founded))}</span>` : ""}
        ${modePill}
      </div>
    </div>`;

  heroStats.innerHTML = `
    <div class="hero-stat">
      <div class="hero-stat-value">${data.players.length}</div>
      <div class="hero-stat-label">Oyuncu</div>
    </div>
    <div class="hero-stat">
      <div class="hero-stat-value">${data.upcoming_events.length || "—"}</div>
      <div class="hero-stat-label">Yaklaşan Maç</div>
    </div>
    <div class="hero-stat">
      <div class="hero-stat-value">${stadium.capacity ? formatCapacity(stadium.capacity).replace(" kişi", "") : "—"}</div>
      <div class="hero-stat-label">Kapasite</div>
    </div>
    <div class="hero-stat">
      <div class="hero-stat-value">${profile.manager ? esc(profile.manager.split(" ").slice(-1)[0]) : "—"}</div>
      <div class="hero-stat-label">Teknik Direktör</div>
    </div>`;

  sourceLink.innerHTML = data.source_url
    ? `Veri: <a href="${esc(data.source_url)}" target="_blank" rel="noopener">TheSportsDB</a>`
    : "";
}

// ── Render: Genel ──

function managerCard(profile) {
  if (!profile.manager) {
    return `<div class="manager-card">${emptyState("👔", "Teknik direktör bilgisi yok.")}</div>`;
  }
  const photo = profile.manager_photo
    ? `<img class="manager-photo" src="${esc(profile.manager_photo)}" alt="${esc(profile.manager)}" loading="lazy" />`
    : `<div class="manager-photo-placeholder">👔</div>`;
  return `
    <div class="manager-card">
      ${photo}
      <div class="manager-name">${esc(profile.manager)}</div>
      ${profile.manager_nationality ? `<div class="manager-nat">${esc(profile.manager_nationality)}</div>` : ""}
    </div>`;
}

function renderGeneral(data) {
  const p = data.profile;
  const s = data.stadium;
  const webUrl = p.website
    ? (p.website.startsWith("http") ? p.website : "https://" + p.website)
    : null;

  document.getElementById("panel-general").innerHTML = `
    <div class="grid-2">
      <div class="card">
        ${cardHeader("Teknik Direktör")}
        ${managerCard(p)}
      </div>
      <div class="card">
        ${cardHeader("Takım Bilgisi")}
        ${infoRow("Lig", esc(p.league || "—"))}
        ${infoRow("Ülke", esc(p.country || "—"))}
        ${infoRow("Kuruluş", esc(p.founded || "—"))}
        ${webUrl ? infoRow("Web sitesi", `<a href="${esc(webUrl)}" target="_blank" rel="noopener">${esc(p.website)}</a>`) : ""}
      </div>
    </div>
    <div class="grid-2" style="margin-top:1rem">
      <div class="card">
        ${cardHeader("Stadyum Özeti")}
        ${infoRow("Stadyum", esc(s.name || "—"))}
        ${infoRow("Kapasite", esc(formatCapacity(s.capacity)))}
        ${infoRow("Konum", esc(s.location || "—"))}
      </div>
      <div class="card">
        ${cardHeader("Sezon")}
        ${infoRow("Kadro", `${data.players.length} oyuncu`)}
        ${infoRow("Yaklaşan maç", data.upcoming_events.length || "Yok")}
        ${infoRow("Son maç", data.last_events.length ? `${data.last_events.length} kayıt` : "Yok")}
      </div>
    </div>
    ${p.description ? `
      <div class="card" style="margin-top:1rem">
        ${cardHeader("Hakkında")}
        <p class="desc">${esc(p.description)}</p>
      </div>` : ""}`;
}

// ── Render: Kadro ──

function renderSquad(data) {
  const players = data.players;
  const panel = document.getElementById("panel-squad");

  if (!players.length) {
    panel.innerHTML = `<div class="card">${emptyState("👥", "Kadro bilgisi bulunamadı.")}</div>`;
    return;
  }

  const cards = players.map((pl) => {
    const photo = pl.photo
      ? `<img class="player-photo" src="${esc(pl.photo)}" alt="${esc(pl.name)}" loading="lazy" />`
      : `<div class="player-photo-placeholder">👤</div>`;
    return `
      <div class="player-card">
        ${photo}
        <div class="player-info">
          <div class="player-name">${esc(pl.name)}</div>
          <div class="player-pos">${esc(pl.position || "—")}</div>
          <div class="player-nat">${esc(pl.nationality || "")}</div>
        </div>
      </div>`;
  }).join("");

  panel.innerHTML = `
    <div class="card">
      ${cardHeader(`Kadro · ${players.length} oyuncu`)}
      <div class="notice">
        <span class="notice-icon">ℹ</span>
        <span>TheSportsDB ücretsiz API en fazla ${data.players_limit ?? 10} oyuncu döndürür.</span>
      </div>
      <div class="player-grid">${cards}</div>
    </div>`;
}

// ── Render: Maçlar ──

function renderMatches(data) {
  const upcoming = data.upcoming_events;
  const last = data.last_events;

  document.getElementById("panel-matches").innerHTML = `
    <div class="card" style="margin-bottom:1rem">
      <div class="section-label">Yaklaşan Maçlar</div>
      <div class="match-list">
        ${upcoming.length ? upcoming.map(matchCard).join("") : emptyState("📅", "Yaklaşan maç bulunmuyor.")}
      </div>
    </div>
    <div class="card">
      <div class="section-label">Son Maçlar</div>
      <div class="match-list">
        ${last.length ? last.map(matchCard).join("") : emptyState("🏁", "Son maç verisi yok.")}
      </div>
    </div>`;
}

function matchCard(m) {
  const { day, mon } = formatDate(m.date);
  const hasScore = m.home_score != null && m.away_score != null;

  if (hasScore) {
    const homeBadge = m.home_badge
      ? `<img class="match-team-badge" src="${esc(m.home_badge)}" alt="" loading="lazy" />`
      : "";
    const awayBadge = m.away_badge
      ? `<img class="match-team-badge" src="${esc(m.away_badge)}" alt="" loading="lazy" />`
      : "";
    return `
    <div class="match-card match-card--result">
      <div class="match-date"><div class="day">${day}</div><div class="mon">${mon}</div></div>
      <div class="match-fixture">
        <div class="match-team match-team--home">
          <span class="match-team-name">${esc(m.home_team || "—")}</span>
          ${homeBadge}
        </div>
        <div class="match-score">${esc(m.home_score)} - ${esc(m.away_score)}</div>
        <div class="match-team match-team--away">
          ${awayBadge}
          <span class="match-team-name">${esc(m.away_team || "—")}</span>
        </div>
      </div>
    </div>`;
  }

  const thumb = m.thumb
    ? `<img class="match-badge" src="${esc(m.thumb)}" alt="" loading="lazy" />`
    : "";
  return `
    <div class="match-card">
      <div class="match-date"><div class="day">${day}</div><div class="mon">${mon}</div></div>
      <div class="match-body">
        <div class="match-title">${esc(m.title || `${m.home_team} vs ${m.away_team}`)}</div>
        <div class="match-sub">
          ${m.time ? esc(m.time.slice(0, 5)) + " · " : ""}
          ${esc(m.venue || "—")}${m.league ? " · " + esc(m.league) : ""}
        </div>
      </div>
      ${thumb}
    </div>`;
}

// ── Render: Stadyum ──

function renderStadium(data) {
  const s = data.stadium;

  const heroHtml = s.image
    ? `<div class="stadium-hero">
        <img src="${esc(s.image)}" alt="${esc(s.name)}" loading="lazy" />
        <div class="stadium-hero-label">${esc(s.name || "Stadyum")}</div>
       </div>`
    : "";

  document.getElementById("panel-stadium").innerHTML = `
    ${heroHtml}
    <div class="card">
      ${cardHeader(s.name ? "Detaylar" : "Stadyum")}
      ${infoRow("Kapasite", esc(formatCapacity(s.capacity)))}
      ${infoRow("Konum", esc(s.location || "—"))}
      ${s.description ? `<p class="desc" style="margin-top:0.75rem">${esc(s.description)}</p>` : ""}
    </div>`;
}

// ── Render: AI ──

function renderAiPanel() {
  document.getElementById("panel-ai").innerHTML = `
    <div class="ai-card">
      <div class="ai-header">
        <div class="ai-sparkle">✦</div>
        <div>
          <h3>AI Brifing</h3>
          <span>Powered by Gemini</span>
        </div>
      </div>
      <div class="ai-section-btns">
        ${aiBtn("general", "Genel")}
        ${aiBtn("squad", "Kadro")}
        ${aiBtn("matches", "Maçlar")}
        ${aiBtn("stadium", "Stadyum")}
      </div>
      <div class="ai-box" id="ai-result">Bir konu seç — AI sana özel brifing hazırlasın.</div>
    </div>`;

  document.querySelectorAll(".ai-section-btns button").forEach((b) => {
    b.addEventListener("click", () => {
      aiSection = b.dataset.section;
      document.querySelectorAll(".ai-section-btns button").forEach((x) =>
        x.classList.toggle("active", x.dataset.section === aiSection)
      );
      loadAiBrief(aiSection);
    });
  });
}

function aiBtn(section, label) {
  return `<button data-section="${section}" class="${section === aiSection ? "active" : ""}">${label}</button>`;
}

async function loadAiBrief(section) {
  const box = document.getElementById("ai-result");
  if (!box || !teamData) return;

  if (aiCache[section]) {
    box.textContent = aiCache[section];
    box.classList.remove("loading");
    return;
  }

  box.classList.add("loading");
  box.innerHTML = `<div class="spinner"></div><span>AI brifing hazırlanıyor...</span>`;

  try {
    const res = await fetch("/match-brief", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team: teamData.team_name, section }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      box.classList.remove("loading");
      box.textContent = err.detail || `Hata: ${res.status}`;
      return;
    }
    const data = await res.json();
    aiCache[section] = data.result;
    box.classList.remove("loading");
    box.textContent = data.result;
  } catch (e) {
    box.classList.remove("loading");
    box.textContent = "Ağ hatası: " + e.message;
  }
}

// ── Main search ──

function renderAll(data) {
  teamData = data;
  aiCache = {};
  aiSection = "general";
  renderHero(data);
  renderGeneral(data);
  renderSquad(data);
  renderMatches(data);
  renderStadium(data);
  renderAiPanel();
  setTab("general");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function search(teamOverride) {
  const team = (teamOverride || queryInput.value).trim();
  if (!team) { showError("Lütfen bir takım adı yaz."); return; }

  queryInput.value = team;
  hideError();
  runBtn.disabled = true;
  showLoading(`${team} yükleniyor...`);

  try {
    const res = await fetch("/team-info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const detail = err.detail;
      const msg = typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => d.msg).join(", ")
          : `Hata: ${res.status}`;
      showError(msg);
      return;
    }

    const data = await res.json();
    welcome.classList.add("hidden");
    dashboard.classList.remove("hidden");
    renderAll(data);
  } catch (e) {
    showError("Ağ hatası: " + e.message);
  } finally {
    runBtn.disabled = false;
    hideLoading();
  }
}

// ── Events ──

runBtn.addEventListener("click", () => search());
queryInput.addEventListener("keydown", (e) => { if (e.key === "Enter") search(); });

document.getElementById("tabs").addEventListener("click", (e) => {
  const btn = e.target.closest(".tab-btn");
  if (btn) setTab(btn.dataset.tab);
});

document.getElementById("quick-teams").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (chip) search(chip.dataset.team);
});
