/* ─── PMB Leads Mobile App ─── */
const PAGE = 30;
const WA_MSG = (name) =>
  `Namaste, I'm from PMB Jan Aushadhi Kendra, Chelakottukara Thrissur – No.1 Govt Health Centre dealer in Kerala. We supply 2,000+ generic medicines at 50–90% less than branded prices. Can we connect with the medical officer at ${name}?`;

const PRESETS = {
  hi:   t => /district|general|taluk|medical college|women/i.test(t),
  phc:  t => /PHC|FHC|CHC|primary health|family health|community health/i.test(t),
  hosp: t => /hospital|medical college/i.test(t),
  all:  () => true,
  phone:() => true,   // handled separately
};

let ALL = [];
let filtered = [];
let page = 0;
let activePreset = 'hi';
let activeDistricts = new Set();
let searchQ = '';
let deferredInstall = null;

// ─── boot ───
window.addEventListener('DOMContentLoaded', () => {
  fetch('leads.json')
    .then(r => r.json())
    .then(d => { ALL = d.leads || []; init(); })
    .catch(() => showToast('Could not load leads.json'));
});

window.addEventListener('beforeinstallprompt', e => {
  e.preventDefault();
  deferredInstall = e;
  document.getElementById('installBtn').classList.remove('hidden');
});
document.getElementById('installBtn').addEventListener('click', () => {
  if (deferredInstall) { deferredInstall.prompt(); deferredInstall = null; }
});
document.getElementById('refreshBtn').addEventListener('click', () => location.reload());

function init() {
  buildDistrictRow();
  buildPresetRow();
  document.getElementById('search').addEventListener('input', e => {
    searchQ = e.target.value.trim().toLowerCase();
    applyFilters();
  });
  applyFilters();
  // infinite scroll
  const obs = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting) loadMore();
  });
  obs.observe(document.getElementById('sentinel'));
}

// ─── district chips ───
function buildDistrictRow() {
  const districts = [...new Set(ALL.map(r => r.d).filter(Boolean))].sort();
  const row = document.getElementById('districtRow');
  row.innerHTML = '';
  const all = document.createElement('button');
  all.className = 'chip chip-on flex-shrink-0';
  all.textContent = 'All districts';
  all.dataset.dist = '__all__';
  all.addEventListener('click', () => toggleDistrict('__all__', all));
  row.appendChild(all);
  districts.forEach(d => {
    const b = document.createElement('button');
    b.className = 'chip chip-off flex-shrink-0';
    b.textContent = d;
    b.dataset.dist = d;
    b.addEventListener('click', () => toggleDistrict(d, b));
    row.appendChild(b);
  });
}

function toggleDistrict(dist, btn) {
  if (dist === '__all__') {
    activeDistricts.clear();
    document.querySelectorAll('#districtRow [data-dist]').forEach(b => {
      b.className = b.dataset.dist === '__all__'
        ? 'chip chip-on flex-shrink-0'
        : 'chip chip-off flex-shrink-0';
    });
  } else {
    const allBtn = document.querySelector('#districtRow [data-dist="__all__"]');
    allBtn.className = 'chip chip-off flex-shrink-0';
    if (activeDistricts.has(dist)) {
      activeDistricts.delete(dist);
      btn.className = 'chip chip-off flex-shrink-0';
    } else {
      activeDistricts.add(dist);
      btn.className = 'chip chip-on flex-shrink-0';
    }
    if (activeDistricts.size === 0) {
      allBtn.className = 'chip chip-on flex-shrink-0';
    }
  }
  applyFilters();
}

// ─── preset chips ───
function buildPresetRow() {
  document.querySelectorAll('#presetRow [data-preset]').forEach(btn => {
    btn.addEventListener('click', () => {
      activePreset = btn.dataset.preset;
      document.querySelectorAll('#presetRow [data-preset]').forEach(b =>
        b.className = 'chip ' + (b === btn ? 'chip-on' : 'chip-off'));
      applyFilters();
    });
  });
}

// ─── filtering ───
function applyFilters() {
  const predType = PRESETS[activePreset] || (() => true);
  const onlyPhone = activePreset === 'phone';
  filtered = ALL.filter(r => {
    if (activeDistricts.size > 0 && !activeDistricts.has(r.d)) return false;
    if (!predType(r.t)) return false;
    if (onlyPhone && !r.p) return false;
    if (searchQ) {
      const hay = `${r.n} ${r.a} ${r.o} ${r.d}`.toLowerCase();
      if (!hay.includes(searchQ)) return false;
    }
    return true;
  });
  page = 0;
  document.getElementById('list').innerHTML = '';
  updateStats();
  loadMore();
}

function updateStats() {
  const withPhone = filtered.filter(r => r.p).length;
  document.getElementById('stats').textContent =
    `${filtered.length.toLocaleString()} facilities · ${withPhone.toLocaleString()} with phone`;
}

// ─── rendering ───
function loadMore() {
  if (page * PAGE >= filtered.length) return;
  const slice = filtered.slice(page * PAGE, (page + 1) * PAGE);
  const list = document.getElementById('list');
  slice.forEach(r => list.appendChild(makeCard(r)));
  page++;
}

function typeColor(t) {
  if (/district|general hospital/i.test(t)) return 'bg-purple-100 text-purple-700';
  if (/taluk/i.test(t)) return 'bg-blue-100 text-blue-700';
  if (/medical college/i.test(t)) return 'bg-rose-100 text-rose-700';
  if (/CHC|community/i.test(t)) return 'bg-yellow-100 text-yellow-700';
  if (/FHC|family/i.test(t)) return 'bg-orange-100 text-orange-700';
  if (/PHC|primary/i.test(t)) return 'bg-brand-100 text-brand-700';
  if (/women/i.test(t)) return 'bg-pink-100 text-pink-700';
  return 'bg-slate-100 text-slate-600';
}

function makeCard(r) {
  const div = document.createElement('div');
  div.className = 'card active:scale-[.98] transition-transform cursor-pointer';
  div.innerHTML = `
    <div class="flex items-start gap-3">
      <div class="flex-1 min-w-0">
        <div class="font-semibold text-[15px] leading-snug truncate">${esc(r.n)}</div>
        <div class="flex items-center gap-1.5 mt-1 flex-wrap">
          <span class="text-xs px-2 py-0.5 rounded-full font-medium ${typeColor(r.t)}">${esc(r.t)}</span>
          ${r.d ? `<span class="text-xs text-slate-500">${esc(r.d)}</span>` : ''}
        </div>
        ${r.a ? `<div class="text-xs text-slate-500 mt-1.5 line-clamp-1">${esc(r.a)}</div>` : ''}
      </div>
      ${r.p ? `<div class="text-brand-600 text-xl shrink-0">📞</div>` : ''}
    </div>
    <div class="flex gap-2 mt-3">
      ${r.p ? `<button onclick="waClick(event,'${encodeURIComponent(r.p)}','${encodeURIComponent(r.n)}')"
        class="flex-1 bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium py-2 rounded-xl flex items-center justify-center gap-1.5">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M20.52 3.449C12.831-3.984.106 1.407.101 11.893c0 2.096.549 4.14 1.595 5.945L0 24l6.335-1.652C8.044 23.096 9.959 23.58 11.9 23.58c10.447 0 15.855-12.603 8.62-20.131zM11.9 21.56c-1.786 0-3.535-.484-5.054-1.402l-.36-.214-3.75.982.999-3.648-.235-.374A9.88 9.88 0 011.98 11.893c0-5.48 4.458-9.934 9.94-9.934 2.655 0 5.151 1.036 7.027 2.916a9.878 9.878 0 012.903 7.014c-.005 5.483-4.463 9.671-9.95 9.671z"/></svg>
        WhatsApp</button>` : ''}
      ${r.p ? `<button onclick="callClick(event,'${encodeURIComponent(r.p)}')"
        class="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 rounded-xl flex items-center justify-center gap-1.5">
        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.6 3.4 2 2 0 0 1 3.59 1h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.55a16 16 0 0 0 6 6l.92-.92a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
        Call</button>` : ''}
      <button onclick="openModal(event, this)" data-idx="${filtered.indexOf(r)}"
        class="${r.p ? '' : 'flex-1 '}bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium py-2 px-3 rounded-xl flex items-center justify-center gap-1">
        Info ›</button>
    </div>`;
  return div;
}

function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── actions ───
function waClick(e, encPhone, encName) {
  e.stopPropagation();
  const phone = decodeURIComponent(encPhone);
  const name  = decodeURIComponent(encName);
  let p = phone.replace(/\D/g,'');
  if (p.length === 10) p = '91' + p;
  const url = `https://wa.me/${p}?text=${encodeURIComponent(WA_MSG(name))}`;
  window.open(url, '_blank');
}
function callClick(e, encPhone) {
  e.stopPropagation();
  window.location.href = `tel:${decodeURIComponent(encPhone)}`;
}

// ─── detail modal ───
function openModal(e, btn) {
  e.stopPropagation();
  const r = filtered[parseInt(btn.dataset.idx)];
  if (!r) return;
  document.getElementById('mName').textContent = r.n || '—';
  document.getElementById('mMeta').textContent = [r.t, r.d].filter(Boolean).join(' · ');

  let html = '';
  if (r.a) html += row('📍','Address', esc(r.a));
  if (r.p) {
    let p = r.p.replace(/\D/g,''); if(p.length===10) p='91'+p;
    html += row('📞','Phone',
      `<a href="tel:${esc(r.p)}" class="text-brand-600 font-medium">${esc(r.p)}</a>`);
  }
  if (r.e) html += row('✉️','Email',
    `<a href="mailto:${esc(r.e)}" class="text-blue-600 break-all">${esc(r.e)}</a>`);
  if (r.w) html += row('🌐','Website',
    `<a href="${esc(r.w)}" target="_blank" class="text-blue-600 break-all">${esc(r.w)}</a>`);
  if (r.o) html += row('🏛️','Operator', esc(r.o));

  // action buttons
  let btns = '';
  if (r.p) {
    let p = r.p.replace(/\D/g,''); if(p.length===10) p='91'+p;
    btns += `<a href="https://wa.me/${p}?text=${encodeURIComponent(WA_MSG(r.n))}" target="_blank"
      class="flex-1 bg-brand-600 text-white text-sm font-medium py-2.5 rounded-xl flex items-center justify-center gap-1.5">
      💬 WhatsApp</a>`;
    btns += `<a href="tel:${esc(r.p)}"
      class="flex-1 bg-slate-100 text-slate-700 text-sm font-medium py-2.5 rounded-xl flex items-center justify-center gap-1.5">
      📞 Call</a>`;
  }
  if (r.y && r.x) {
    btns += `<a href="https://www.google.com/maps/?q=${r.y},${r.x}" target="_blank"
      class="flex-1 bg-blue-50 text-blue-700 text-sm font-medium py-2.5 rounded-xl flex items-center justify-center gap-1.5">
      📍 Maps</a>`;
  }
  if (btns) html += `<div class="flex gap-2 pt-1">${btns}</div>`;

  document.getElementById('mBody').innerHTML = html || '<p class="text-slate-400 text-sm">No extra details available.</p>';
  document.getElementById('modal').classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function row(icon, label, val) {
  return `<div class="flex gap-3 items-start">
    <span class="text-xl leading-none shrink-0 mt-0.5">${icon}</span>
    <div class="min-w-0"><div class="text-xs text-slate-400 uppercase tracking-wide">${label}</div>
    <div class="text-sm mt-0.5">${val}</div></div></div>`;
}

function closeModal() {
  document.getElementById('modal').classList.add('hidden');
  document.body.style.overflow = '';
}
document.getElementById('modal').addEventListener('click', e => {
  if (e.target === document.getElementById('modal')) closeModal();
});
document.addEventListener('keydown', e => { if (e.key==='Escape') closeModal(); });

// ─── toast ───
let toastTimer;
function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3000);
}
