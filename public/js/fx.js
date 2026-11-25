/* Efectos visuales de los rediseños. Sin dependencias. Respeta prefers-reduced-motion. */
(function () {
  var d = document, root = d.documentElement;
  root.classList.add('js');
  var calm = matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine = matchMedia('(hover: hover) and (pointer: fine)').matches;

  /* Cabecera: cambia al hacer scroll */
  var top = d.querySelector('.top');
  /* Parallax suave de la foto de portada + progreso para animar el panel */
  var himgs = d.querySelectorAll('.hero:not(.plain) .hero-img img');
  var ticking = false;
  function onScroll() {
    var y = window.scrollY || 0;
    if (top) top.classList.toggle('scrolled', y > 24);
    if (himgs.length && !calm && y < 1400) { var tr = 'translate3d(0,' + (y * 0.22).toFixed(1) + 'px,0) scale(1.08)'; himgs.forEach(function (im) { im.style.transform = tr; }); }
    ticking = false;
  }
  addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  /* Aparición al hacer scroll */
  var targets = d.querySelectorAll('.sec h2, .sec .lead, .card:not(.act), .gal figure, .book, .chips, .sec > .wrap > p');
  if ('IntersectionObserver' in window && !calm) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    targets.forEach(function (el, i) {
      el.setAttribute('data-r', ''); el.style.setProperty('--d', ((i % 5) * 70) + 'ms'); io.observe(el);
    });
  }

  /* Tarjetas: inclinación 3D y brillo que sigue al dedo o al ratón */
  if (!calm) {
    d.querySelectorAll('.card.stay, .card.room, .card.offer').forEach(function (c) {
      if (c.querySelector('.mini')) return;
      function move(ev) {
        var r = c.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        c.style.setProperty('--ry', ((x - .5) * 9).toFixed(2) + 'deg');
        c.style.setProperty('--rx', ((.5 - y) * 9).toFixed(2) + 'deg');
        c.style.setProperty('--mx', (x * 100).toFixed(1) + '%');
        c.style.setProperty('--my', (y * 100).toFixed(1) + '%');
        c.classList.add('tilt');
      }
      function leave() { c.classList.remove('tilt'); c.style.removeProperty('--rx'); c.style.removeProperty('--ry'); }
      c.addEventListener('pointermove', move); c.addEventListener('pointerleave', leave); c.addEventListener('pointerup', leave);
    });
  }

  d.querySelectorAll('.cards').forEach(function (c) { if (c.querySelector('.card.room, .card.stay')) c.classList.add('snap'); });

  /* Carruseles: arrastre con ratón (el táctil usa el desplazamiento nativo con imán) */
  if (fine) {
    d.querySelectorAll('.cards.snap').forEach(function (s) {
      var down = false, sx = 0, sl = 0, moved = false;
      s.addEventListener('pointerdown', function (e) { if (e.pointerType !== 'mouse') return; down = true; moved = false; sx = e.clientX; sl = s.scrollLeft; });
      addEventListener('pointerup', function () { down = false; s.classList.remove('drag'); });
      s.addEventListener('pointermove', function (e) {
        if (!down) return; var dx = e.clientX - sx; if (Math.abs(dx) > 4) { moved = true; s.classList.add('drag'); }
        s.scrollLeft = sl - dx;
      });
      s.addEventListener('click', function (e) { if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; } }, true);
    });
  }

  /* Desplegable de alojamientos (táctil y teclado) */
  d.querySelectorAll('.has-sub').forEach(function (li) {
    var b = li.querySelector('button');
    b.addEventListener('click', function (e) { e.stopPropagation(); var o = li.classList.toggle('open'); b.setAttribute('aria-expanded', o); });
    li.addEventListener('keydown', function (e) { if (e.key === 'Escape') { li.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); b.focus(); } });
    d.addEventListener('click', function (e) { if (!li.contains(e.target)) { li.classList.remove('open'); b.setAttribute('aria-expanded', 'false'); } });
  });

  /* Barra de reserva: va al motor (o al contacto si aún no hay Mirai) con el alojamiento elegido */
  d.querySelectorAll('.bookbar').forEach(function (f) {
    f.addEventListener('submit', function (e) {
      var o = f.querySelector('option:checked'); if (o && o.dataset.url) { e.preventDefault(); location.href = o.dataset.url; }
    });
  });

  /* Estaciones: fotos según las fechas de la estancia */
  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }
  var SDEl = d.getElementById('seasons-data'), SD = null; try { SD = SDEl ? JSON.parse(SDEl.textContent) : null; } catch (e) {}
  var lang = d.documentElement.lang || 'es', cur = null;
  function seasonOf(m, dd) {
    var w = SD.windows, k;
    for (k in w) { var a = w[k][0], b = w[k][1], x = m * 100 + dd, A = a[0] * 100 + a[1], B = b[0] * 100 + b[1];
      if (A <= B ? (x >= A && x <= B) : (x >= A || x <= B)) return k; }
    return 'winter';
  }
  function setSeason(s) {
    if (!SD || !s) return;
    var first = cur === null; cur = s; d.body.dataset.season = s;
    d.querySelectorAll('[data-s-img]').forEach(function (im) {
      var on = im.dataset.sImg === s;
      if (on && im.dataset.src) { im.src = im.dataset.src; im.removeAttribute('data-src'); }
      im.classList.toggle('on', on);
    });
    d.querySelectorAll('[data-s] ').forEach(function (el) {
      if (el.matches('button[data-s]')) el.setAttribute('aria-selected', el.dataset.s === s ? 'true' : 'false');
      else if (el.classList.contains('s-panel')) el.hidden = el.dataset.s !== s;
    });
    d.querySelectorAll('.sdetect b').forEach(function (b) { b.textContent = SD.names[lang] ? SD.names[lang][s] : s; });
    d.querySelectorAll('.s-panel:not([hidden]) .cards.snap').forEach(function (c) { c.scrollLeft = 0; });
    /* precarga el resto de estaciones cuando el navegador esté libre */
    if (first) setTimeout(function () { d.querySelectorAll('[data-s-img][data-src]').forEach(function (im) { var i = new Image(); i.src = im.dataset.src; }); }, 1500);
  }
  function seasonFromDate(v) { var p = (v || '').split('-'); if (p.length === 3) setSeason(seasonOf(+p[1], +p[2])); }
  if (SD) {
    var q = new URLSearchParams(location.search).get('estacion'), manual = lsGet('lcr_season'), ci = lsGet('lcr_checkin'), t0 = new Date(); t0.setDate(t0.getDate() + SD.offset);
    if (q && SD.names.es[q]) setSeason(q);
    else if (manual && SD.names.es[manual]) setSeason(manual);
    else if (ci && /^\d{4}-\d{2}-\d{2}$/.test(ci) && ci >= iso(new Date())) seasonFromDate(ci);
    else setSeason(seasonOf(t0.getMonth() + 1, t0.getDate()));
    d.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-s], .s-arrow'); if (!b) return;
      var s = b.dataset.s;
      if (!s) { var o = ['winter', 'spring', 'summer', 'autumn'], i = (o.indexOf(cur) + (+b.dataset.dir) + 4) % 4; s = o[i]; }
      lsSet('lcr_season', s); setSeason(s);
    });
  }

  /* Motor de reservas (Mirai): fechas, noches y adultos */
  function iso(x) { return x.getFullYear() + '-' + String(x.getMonth() + 1).padStart(2, '0') + '-' + String(x.getDate()).padStart(2, '0'); }
  d.querySelectorAll('form[data-tpl]').forEach(function (f) {
    var di = f.querySelector('input[type=date]'), t = new Date(), def = new Date(); def.setDate(def.getDate() + (SD ? SD.offset : 7));
    di.min = iso(t); var sv = lsGet('lcr_checkin'); di.value = (sv && sv >= iso(t)) ? sv : iso(def);
    di.addEventListener('change', function () { if (di.value) { lsSet('lcr_checkin', di.value); lsDel('lcr_season'); seasonFromDate(di.value); } });
    f.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = di.value.split('-'); if (v.length < 3) return;
      var ci = encodeURIComponent(v[2] + '/' + v[1] + '/' + v[0]), n = f.elements.nights.value, a = parseInt(f.elements.adults.value, 10) || 2;
      var pt = encodeURIComponent(btoa(JSON.stringify([{ adults: a, children: [] }])));
      var ch = (f.elements.hotel && f.elements.hotel.value) || f.dataset.chain || '66013';
      location.href = f.dataset.tpl.replace('{chain}', ch).replace('{checkin}', ci).replace('{nights}', n).replace('{parties}', pt);
    });
  });
  /* Enlaces a Mirai con fecha ya pasada → siempre una fecha futura */
  d.querySelectorAll('a[href*="bookingstep1"]').forEach(function (a) {
    try {
      var u = new URL(a.href), c = (u.searchParams.get('checkin') || '').split('/'); if (c.length < 3) return;
      var dt = new Date(+c[2], +c[1] - 1, +c[0]), now = new Date(); now.setHours(0, 0, 0, 0);
      if (dt < now) { var n = new Date(now); n.setDate(n.getDate() + 7); u.searchParams.set('checkin', ('0' + n.getDate()).slice(-2) + '/' + ('0' + (n.getMonth() + 1)).slice(-2) + '/' + n.getFullYear()); a.href = u.toString(); }
    } catch (e) {}
  });

  /* Panel de reserva en móvil: botón que abre y cierra los campos */
  d.querySelectorAll('.dock').forEach(function (k) {
    var b = k.querySelector('.dock-open'); if (!b) return;
    b.addEventListener('click', function () { var o = k.classList.toggle('open'); b.setAttribute('aria-expanded', o); });
  });

  /* Carruseles de fotos dentro de las tarjetas */
  d.querySelectorAll('[data-mini]').forEach(function (m) {
    var tr = m.querySelector('.mini-track'), dots = m.querySelector('.mini-dots'), n = tr.children.length;
    if (dots) { for (var i = 0; i < n; i++) dots.appendChild(d.createElement('i')); }
    function cur() { return Math.round(tr.scrollLeft / Math.max(1, tr.clientWidth)); }
    function upd() { if (!dots) return; var c = cur(); [].forEach.call(dots.children, function (x, i) { x.classList.toggle('on', i === c); }); }
    var tk = false; tr.addEventListener('scroll', function () { if (!tk) { tk = true; requestAnimationFrame(function () { upd(); tk = false; }); } }, { passive: true });
    function go(dir) { var c = cur() + dir; if (c < 0) c = n - 1; if (c >= n) c = 0; tr.scrollTo({ left: c * tr.clientWidth, behavior: calm ? 'auto' : 'smooth' }); }
    var pv = m.querySelector('.prev'), nx = m.querySelector('.next');
    if (pv) pv.addEventListener('click', function (e) { e.preventDefault(); go(-1); });
    if (nx) nx.addEventListener('click', function (e) { e.preventDefault(); go(1); });
    upd();
  });

  /* Vídeo de portada: respeta «reducir movimiento» y se puede pausar */
  var vid = d.querySelector('video.hv'), vt = d.querySelector('.vid-toggle');
  if (vid) {
    if (calm) { vid.pause(); vid.removeAttribute('autoplay'); }
    function lab() { if (!vt) return; var p = vid.paused; vt.textContent = p ? '▶' : '❚❚'; vt.setAttribute('aria-label', p ? vt.dataset.play : vt.dataset.pause); }
    if (vt) vt.addEventListener('click', function () { if (vid.paused) vid.play(); else vid.pause(); lab(); });
    vid.addEventListener('error', function () { vid.style.display = 'none'; if (vt) vt.style.display = 'none'; });
    vid.addEventListener('play', lab); vid.addEventListener('pause', lab);
    lab();
  }
})();
