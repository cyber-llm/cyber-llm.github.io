// Project page behaviour: figure tabs, click-to-zoom lightbox, BibTeX copy, active nav link, reveal on scroll.
(function () {
  // 正文配图加载完成后去掉占位底纹。
  document.querySelectorAll('.fig img').forEach(function (img) {
    function done() { img.classList.add('is-loaded'); }
    if (img.complete && img.naturalWidth) done(); else img.addEventListener('load', done, { once: true });
  });

  // tabs inside each figure viewer
  document.querySelectorAll('.viewer').forEach(function (v) {
    var tabs = Array.from(v.querySelectorAll('.tab'));
    function select(tab) {
      tabs.forEach(function (other) {
        other.setAttribute('aria-selected', String(other === tab));
        other.tabIndex = other === tab ? 0 : -1;
      });
      v.querySelectorAll('.fig').forEach(function (figure) { figure.hidden = figure.id !== tab.getAttribute('aria-controls'); });
    }
    tabs.forEach(function (tab, index) {
      tab.addEventListener('click', function () { select(tab); });
      tab.addEventListener('keydown', function (event) {
        var target;
        if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
        if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
        if (event.key === 'Home') target = 0;
        if (event.key === 'End') target = tabs.length - 1;
        if (target !== undefined) { event.preventDefault(); select(tabs[target]); tabs[target].focus(); }
      });
    });
  });

  // lightbox
  var lb = document.getElementById('lightbox');
  var lbImg = lb.querySelector('img');
  var lbCap = lb.querySelector('.lb-cap');
  var viewport = lb.querySelector('.lb-viewport');
  var stage = lb.querySelector('.lb-stage');
  var zoomIn = lb.querySelector('.lb-in');
  var zoomOut = lb.querySelector('.lb-out');
  var levels = [1, 1.5, 2, 3, 4, 6, 8];
  var level = 0;
  var baseWidth = 1;
  var aspect = 1;
  var last = null;
  var previousOverflow = '';
  var pointer = null;
  var sessionOpen = false;

  function resizeImage(next) {
    var rx = (viewport.scrollLeft + viewport.clientWidth / 2) / Math.max(1, stage.scrollWidth);
    var ry = (viewport.scrollTop + viewport.clientHeight / 2) / Math.max(1, stage.scrollHeight);
    level = Math.max(0, Math.min(levels.length - 1, next));
    lbImg.style.width = baseWidth * levels[level] + 'px';
    lbImg.style.height = baseWidth * levels[level] / aspect + 'px';
    lb.querySelector('.lb-scale').textContent = Math.round(levels[level] * 100) + '%';
    zoomOut.disabled = level === 0;
    zoomIn.disabled = level === levels.length - 1;
    viewport.scrollLeft = rx * stage.scrollWidth - viewport.clientWidth / 2;
    viewport.scrollTop = ry * stage.scrollHeight - viewport.clientHeight / 2;
  }
  function fit() {
    if (!lb.open) return;
    baseWidth = Math.max(1, Math.min(viewport.clientWidth - 48, (viewport.clientHeight - 48) * aspect));
    resizeImage(0);
    viewport.scrollTo(0, 0);
  }
  function open(button) {
    var image = button.querySelector('img');
    var cap = button.closest('figure').querySelector('figcaption');
    last = document.activeElement;
    previousOverflow = document.body.style.overflow;
    aspect = Number(image.getAttribute('width')) / Number(image.getAttribute('height'));
    fallback = button.dataset.fallback || '';
    lbImg.src = button.dataset.full;
    lbImg.alt = image.alt;
    lbCap.textContent = Array.from(cap.querySelectorAll('span')).map(function (part) { return part.textContent.trim(); }).join(' · ');
    var download = lb.querySelector('.lb-download');
    download.href = button.dataset.full;
    download.download = button.dataset.download;
    lb.showModal();
    sessionOpen = true;
    document.body.style.overflow = 'hidden';
    fit();
    lb.querySelector('.lb-close').focus();
  }
  function stopDrag() { pointer = null; viewport.classList.remove('dragging'); }
  function restorePage() {
    if (!sessionOpen) return;
    sessionOpen = false;
    document.body.style.overflow = previousOverflow;
    lbImg.removeAttribute('src');
    stopDrag();
    if (last && last.isConnected) last.focus({ preventScroll: true });
  }
  function close() { if (lb.open) lb.close(); restorePage(); }
  lb.addEventListener('close', restorePage);
  lb.addEventListener('cancel', function (event) { event.preventDefault(); close(); });
  lbImg.addEventListener('load', fit);
  // 矢量原图过大或浏览器拒绝渲染时，退回 2400px 位图，保证放大查看始终可用。
  var fallback = '';
  lbImg.addEventListener('error', function () {
    if (fallback && lbImg.getAttribute('src') !== fallback) { lbImg.src = fallback; return; }
    lbCap.textContent = 'The figure could not be loaded. Close and try again.';
  });
  lb.querySelector('.lb-close').addEventListener('click', close);
  lb.querySelector('.lb-fit').addEventListener('click', fit);
  zoomIn.addEventListener('click', function () { resizeImage(level + 1); });
  zoomOut.addEventListener('click', function () { resizeImage(level - 1); });
  lb.addEventListener('click', function (event) { if (event.target === lb) close(); });
  lb.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') { event.preventDefault(); close(); }
    if (event.key === '+' || event.key === '=') { event.preventDefault(); resizeImage(level + 1); }
    if (event.key === '-') { event.preventDefault(); resizeImage(level - 1); }
    if (event.key === '0') { event.preventDefault(); fit(); }
  });
  viewport.addEventListener('pointerdown', function (event) {
    if (event.pointerType !== 'mouse' || event.button !== 0 || level === 0) return;
    pointer = { id: event.pointerId, x: event.clientX, y: event.clientY, left: viewport.scrollLeft, top: viewport.scrollTop };
    viewport.setPointerCapture(event.pointerId);
    viewport.classList.add('dragging');
    event.preventDefault();
  });
  viewport.addEventListener('pointermove', function (event) {
    if (!pointer || pointer.id !== event.pointerId) return;
    viewport.scrollLeft = pointer.left + pointer.x - event.clientX;
    viewport.scrollTop = pointer.top + pointer.y - event.clientY;
  });
  viewport.addEventListener('pointerup', stopDrag);
  viewport.addEventListener('pointercancel', stopDrag);
  viewport.addEventListener('lostpointercapture', stopDrag);
  viewport.addEventListener('wheel', function (event) {
    if (!event.ctrlKey) return;
    event.preventDefault();
    resizeImage(level + (event.deltaY < 0 ? 1 : -1));
  }, { passive: false });
  if ('ResizeObserver' in window) new ResizeObserver(function () { if (lb.open) fit(); }).observe(viewport);
  document.querySelectorAll('button.zoom').forEach(function (button) {
    button.addEventListener('click', function () { open(button); });
    button.closest('figure').querySelector('.figure-expand').addEventListener('click', function () { open(button); });
  });

  // copy BibTeX
  var copy = document.querySelector('.copy');
  if (copy) {
    copy.addEventListener('click', function () {
      var text = document.getElementById('bibtex').textContent;
      var done = function () { copy.textContent = 'Copied ✓'; setTimeout(function () { copy.textContent = 'Copy'; }, 1600); };
      var failed = function () { copy.textContent = 'Select to copy'; };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(done, failed);
      } else {
        var ta = document.createElement('textarea'); ta.value = text; document.body.appendChild(ta); ta.select();
        try { if (document.execCommand('copy')) done(); else failed(); } catch (err) { failed(); }
        document.body.removeChild(ta);
      }
    });
  }

  // 窄屏目录支持键盘关闭，图签与导航均保留可见焦点。
  var menu = document.querySelector('.menu-toggle');
  var nav = document.querySelector('.nav-links');
  function closeMenu() { nav.classList.remove('is-open'); menu.setAttribute('aria-expanded', 'false'); }
  menu.addEventListener('click', function () {
    var expanded = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(expanded));
    nav.classList.toggle('is-open', expanded);
  });
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && nav.classList.contains('is-open')) { closeMenu(); menu.focus(); }
  });
  document.addEventListener('click', function (event) { if (!event.target.closest('.nav')) closeMenu(); });
  var compact = window.matchMedia('(max-width: 1020px)');
  compact.addEventListener('change', closeMenu);

  // active nav link
  var links = Array.prototype.slice.call(document.querySelectorAll('.nav-links a'));
  links.forEach(function (link) { link.addEventListener('click', closeMenu); });
  // 目录高亮、进度和返回顶部共用一次滚动测量，避免多个滚动循环。
  var sections = links.map(function (link) { return document.querySelector(link.getAttribute('href')); });
  var progress = document.querySelector('.reading-progress');
  var progressLine = progress.querySelector('span');
  var topLink = document.querySelector('.back-top');
  var navigation = document.querySelector('.nav');
  var pending = false;
  var activeIndex = -1;
  function updateReadingState() {
    pending = false;
    var range = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
    var fraction = Math.min(1, Math.max(0, window.scrollY / range));
    progressLine.style.transform = 'scaleX(' + fraction + ')';
    progress.setAttribute('aria-valuenow', String(Math.round(fraction * 100)));
    navigation.classList.toggle('is-scrolled', window.scrollY > 24);
    topLink.hidden = window.scrollY < 650;
    var next = -1;
    var readingLine = Math.min(220, window.innerHeight * .25);
    sections.forEach(function (section, index) { if (section.getBoundingClientRect().top <= readingLine) next = index; });
    if (activeIndex !== next) {
      activeIndex = next;
      links.forEach(function (link, index) {
        link.classList.toggle('active', index === next);
        if (index === next) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
    }
  }
  function scheduleReadingState() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(updateReadingState);
  }
  window.addEventListener('scroll', scheduleReadingState, { passive: true });
  window.addEventListener('resize', scheduleReadingState, { passive: true });
  if ('ResizeObserver' in window) new ResizeObserver(scheduleReadingState).observe(document.body);
  document.fonts.ready.then(scheduleReadingState);
  updateReadingState();

  // 只为尚未进入视口的元素添加一次性入场，匹配 .reveal.in 模式。
  var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  var revealObserver = null;
  function setupReveals() {
    if (revealObserver) revealObserver.disconnect();
    var cards = document.querySelectorAll('.reveal');
    cards.forEach(function (card) { card.classList.remove('in'); });
    if (reducedMotion.matches || !('IntersectionObserver' in window)) {
      cards.forEach(function (card) { card.classList.add('in'); });
      return;
    }
    revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('in');
        revealObserver.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -20px 0px', threshold: .04 });
    cards.forEach(function (card) {
      var rect = card.getBoundingClientRect();
      if (rect.top < window.innerHeight + 50) {
        card.classList.add('in');
      } else {
        revealObserver.observe(card);
      }
    });
  }
  reducedMotion.addEventListener('change', setupReveals);
  setupReveals();

  // 统计数字进入视口时从 0 递增；含区间或多个数字的词条保持原样（尊重 reduce 偏好）。
  (function () {
    if (reducedMotion.matches || !('IntersectionObserver' in window)) return;
    function run(el) {
      var raw = el.textContent.trim();
      var token = raw.match(/[\d,]+(?:\.\d+)?/);
      if (!token) return;
      if ((raw.replace(/,/g, '').match(/\d+(?:\.\d+)?/g) || []).length !== 1) return;
      var numStr = token[0];
      var at = raw.indexOf(numStr);
      var prefix = raw.slice(0, at), suffix = raw.slice(at + numStr.length);
      var hasComma = numStr.indexOf(',') >= 0;
      var decimals = (numStr.split('.')[1] || '').length;
      var target = parseFloat(numStr.replace(/,/g, ''));
      if (!isFinite(target)) return;
      el.classList.add('counting');
      var startTime = null, duration = 1150;
      function fmt(v) {
        var out = decimals ? v.toFixed(decimals) : String(Math.round(v));
        if (hasComma) out = Number(out).toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
        return prefix + out + suffix;
      }
      function tick(now) {
        if (startTime === null) startTime = now;
        var p = Math.min(1, (now - startTime) / duration);
        el.textContent = fmt(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(tick); else el.textContent = raw;
      }
      requestAnimationFrame(tick);
    }
    var counters = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        counters.unobserve(entry.target);
        run(entry.target);
      });
    }, { threshold: .55 });
    document.querySelectorAll('.ov-stat b, .sec-stats b').forEach(function (el) { counters.observe(el); });
  })();

  function syncVisibility() {
    document.body.classList.toggle('page-inactive', document.hidden);
    if (!document.hidden) scheduleReadingState();
  }
  document.addEventListener('visibilitychange', syncVisibility);
  syncVisibility();
})();

// 指针彗星拖尾：只在鼠标移动时绘制，静止后停止动画循环；触屏与减少动态效果时不启用。
(function () {
  var canvas = document.getElementById('cursor-comet');
  if (!canvas || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var ctx = canvas.getContext('2d');
  var dpr = 1, trail = [], raf = 0, LIFE = 420;
  function resize() {
    dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  function draw() {
    var now = performance.now();
    trail = trail.filter(function (p) { return now - p.t < LIFE; });
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    if (trail.length < 2) { raf = 0; canvas.classList.remove('visible'); return; }
    ctx.lineCap = 'round';
    for (var i = 1; i < trail.length; i++) {
      var a = trail[i - 1], b = trail[i], k = (1 - (now - b.t) / LIFE) * (i / trail.length);
      ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(47,95,224,' + (k * .2).toFixed(3) + ')';
      ctx.lineWidth = 1 + k * 5; ctx.stroke();
    }
    var tip = trail[trail.length - 1], g = ctx.createRadialGradient(tip.x, tip.y, 0, tip.x, tip.y, 16);
    g.addColorStop(0, 'rgba(47,95,224,.2)'); g.addColorStop(1, 'rgba(47,95,224,0)');
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(tip.x, tip.y, 16, 0, Math.PI * 2); ctx.fill();
    raf = requestAnimationFrame(draw);
  }
  resize();
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('mousemove', function (event) {
    if (reduce.matches) return;
    trail.push({ x: event.clientX, y: event.clientY, t: performance.now() });
    if (trail.length > 40) trail.shift();
    canvas.classList.add('visible');
    if (!raf) raf = requestAnimationFrame(draw);
  }, { passive: true });
})();
