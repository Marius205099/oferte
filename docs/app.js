const $ = (id) => document.getElementById(id);
const PAGE = 48;
const fmt = new Intl.NumberFormat("ro-RO", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const lei = (v) => fmt.format(v) + " lei";
const norm = (s) => (s || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

let all = [], storeNames = {}, activeStores = new Set(), shown = PAGE, current = [];

async function init() {
  let data;
  try {
    data = await (await fetch("data/oferte.json", { cache: "no-cache" })).json();
  } catch {
    $("meta").textContent = "Nu există încă date. Prima scanare rulează în curând.";
    return;
  }
  // _main = numele fara partea "pentru X / compatibil X", ca "husa pentru iphone 15" sa nu apara la "iphone 15"
  all = data.produse.map((p) => {
    const n = norm(p.nume);
    return { ...p, _n: n, _main: n.split(/\b(?:pentru|compatibil[a]?|compatibile|for)\b/)[0] };
  });
  data.magazine.forEach((m) => (storeNames[m.id] = m.nume));
  const d = new Date(data.actualizat);
  $("meta").textContent = `${all.length.toLocaleString("ro-RO")} produse din ${data.magazine.filter((m) => m.produse).length} magazine · actualizat ${d.toLocaleString("ro-RO", { dateStyle: "medium", timeStyle: "short" })}`;

  $("stores").innerHTML = data.magazine.filter((m) => m.produse).map((m) =>
    `<button type="button" class="chip" data-store="${esc(m.id)}" aria-pressed="false">${esc(m.nume)}<small>${m.produse}</small></button>`).join("");
  $("cat").innerHTML += data.cautari.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  $("status").innerHTML = data.magazine.map((m) =>
    `<li><a href="${esc(m.url)}" target="_blank" rel="noopener">${esc(m.nume)}</a>: ${m.produse} produse${m.erori ? ` · <span class="bad">${m.erori} erori (${esc(m.ultima_eroare)})</span>` : ""}</li>`).join("");

  readHash();
  render();
}

function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  $("q").value = h.get("q") || "";
  $("cat").value = h.get("cat") || "";
  $("disc").value = h.get("d") || "0";
  $("sort").value = h.get("s") || "disc";
  $("pmin").value = h.get("min") || "";
  $("pmax").value = h.get("max") || "";
  $("noacc").checked = h.get("acc") !== "1";
  activeStores = new Set((h.get("m") || "").split(",").filter(Boolean));
  document.querySelectorAll(".chip").forEach((b) => b.setAttribute("aria-pressed", activeStores.has(b.dataset.store)));
}

function writeHash() {
  const h = new URLSearchParams();
  const set = (k, v, def = "") => v && v !== def && h.set(k, v);
  set("q", $("q").value.trim()); set("cat", $("cat").value); set("d", $("disc").value, "0");
  set("s", $("sort").value, "disc"); set("min", $("pmin").value); set("max", $("pmax").value);
  set("m", [...activeStores].join(","));
  if (!$("noacc").checked) h.set("acc", "1");
  history.replaceState(null, "", h.toString() ? "#" + h : location.pathname);
}

function filter() {
  const words = norm($("q").value).split(/\s+/).filter(Boolean);
  const cat = $("cat").value, minDisc = +$("disc").value;
  const pmin = parseFloat($("pmin").value) || 0, pmax = parseFloat($("pmax").value) || Infinity;
  const noAcc = $("noacc").checked;
  const res = all.filter((p) =>
    (!activeStores.size || activeStores.has(p.magazin)) &&
    (!cat || p.cautari.includes(cat)) &&
    p.reducere_pct >= minDisc && p.pret >= pmin && p.pret <= pmax &&
    words.every((w) => (noAcc ? p._main : p._n).includes(w)));
  const by = {
    disc: (a, b) => b.reducere_pct - a.reducere_pct || a.pret - b.pret,
    asc: (a, b) => a.pret - b.pret,
    desc: (a, b) => b.pret - a.pret,
    save: (a, b) => ((b.pret_referinta || b.pret) - b.pret) - ((a.pret_referinta || a.pret) - a.pret),
  }[$("sort").value];
  return res.sort(by);
}

function card(p) {
  const img = p.imagine ? `<img src="${esc(p.imagine)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : "";
  const old = p.pret_referinta ? `<span class="old" title="${p.sursa_reducere === "istoric" ? "cel mai mare preț văzut în ultimele 60 de zile" : "preț vechi afișat de magazin"}">${lei(p.pret_referinta)}</span>` : "";
  const low = p.zile_istoric >= 7 && p.pret <= p.pret_minim_60z ?`<span class="hint">Cel mai mic preț din ultimele 60 de zile</span>` : "";
  return `<a class="card" href="${esc(p.url)}" target="_blank" rel="noopener nofollow">
    ${p.reducere_pct > 0 ? `<span class="badge">-${p.reducere_pct}%</span>` : ""}
    <div class="img">${img}</div>
    <div class="body">
      <span class="store">${esc(storeNames[p.magazin] || p.magazin)}</span>
      <span class="name">${esc(p.nume)}</span>
      <div class="prices"><span class="now">${lei(p.pret)}</span>${old}</div>
      ${low}
    </div></a>`;
}

function renderCompare(list) {
  const box = $("compare");
  if (!$("q").value.trim() || !list.length) { box.hidden = true; return; }
  // ignora produsele mult sub pretul median (huse, folii) ca sa nu para "cel mai ieftin"
  const sorted = list.map((p) => p.pret).sort((a, b) => a - b);
  const floor = sorted[Math.floor(sorted.length / 2)] * 0.25;
  const best = {};
  for (const p of list) if (p.pret >= floor && (!best[p.magazin] || p.pret < best[p.magazin].pret)) best[p.magazin] = p;
  const rows = Object.values(best).sort((a, b) => a.pret - b.pret);
  box.hidden = false;
  box.innerHTML = `<h2>Cel mai mic preț pentru „${esc($("q").value.trim())}”, pe magazin</h2><ol>` + rows.map((p) =>
    `<li><b>${esc(storeNames[p.magazin])}</b><span class="p">${lei(p.pret)}</span><a href="${esc(p.url)}" target="_blank" rel="noopener nofollow">${esc(p.nume)}</a></li>`).join("") + "</ol>";
}

function render(reset = true) {
  if (reset) { current = filter(); shown = PAGE; writeHash(); renderCompare(current); }
  $("count").textContent = `${current.length.toLocaleString("ro-RO")} rezultate`;
  $("grid").innerHTML = current.length
    ? current.slice(0, shown).map(card).join("")
    : `<p class="empty">Niciun produs găsit. Încearcă alt termen sau scoate din filtre.<br>Pentru produse noi, adaugă termenul în <code>config.json</code>.</p>`;
  $("more").hidden = shown >= current.length;
}

$("searchForm").addEventListener("submit", (e) => { e.preventDefault(); render(); });
let t;
$("q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 200); });
["cat", "disc", "sort", "noacc"].forEach((id) => $(id).addEventListener("change", () => render()));
["pmin", "pmax"].forEach((id) => $(id).addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 300); }));
$("stores").addEventListener("click", (e) => {
  const b = e.target.closest(".chip"); if (!b) return;
  const id = b.dataset.store;
  activeStores.has(id) ? activeStores.delete(id) : activeStores.add(id);
  b.setAttribute("aria-pressed", activeStores.has(id));
  render();
});
$("more").addEventListener("click", () => { shown += PAGE; render(false); });
$("reset").addEventListener("click", () => { history.replaceState(null, "", location.pathname); readHash(); render(); });

init();
