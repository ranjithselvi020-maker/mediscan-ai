// MEDISCAN AI v2 — Main JavaScript (Upgraded)
'use strict';

// ── PWA Service Worker Registration ──────────────────────────────────────────
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./service-worker.js')
      .then(reg => console.log('SW Registered', reg))
      .catch(err => console.log('SW Registration Failed', err));
  });
}

// ── PWA Install Logic ────────────────────────────────────────────────────────
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  // Show install button or toast if desired
  console.log('PWA Install Prompt available');
});

// ── State ──────────────────────────────────────────────────────────────────
const state = {
  activeMode: 'scan',
  scanType: 'chest_xray',
  currentResult: null,
};

// ── Helpers ───────────────────────────────────────────────────────────────
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];
const el = (tag, cls, html = '') => { const e = document.createElement(tag); if (cls) e.className = cls; if (html) e.innerHTML = html; return e; };

function showToast(msg, type = 'info') {
  const t = el('div', `toast toast-${type}`, msg);
  Object.assign(t.style, {
    position: 'fixed', bottom: '24px', right: '24px', zIndex: 9999,
    background: type === 'error' ? 'rgba(255,77,109,0.9)' : type === 'success' ? 'rgba(6,214,160,0.9)' : 'rgba(0,200,255,0.9)',
    color: '#fff', padding: '12px 20px', borderRadius: '10px',
    fontSize: '0.88rem', fontWeight: '600', boxShadow: '0 4px 20px rgba(0,0,0,0.4)',
    animation: 'fadeIn .3s ease',
  });
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

function setLoading(btn, loading, text = 'Analyzing...') {
  if (loading) { btn.disabled = true; btn.dataset.orig = btn.textContent; btn.textContent = text; }
  else { btn.disabled = false; btn.textContent = btn.dataset.orig || 'Analyze'; }
}

function renderMarkdown(text) {
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^## (.+)$/gm, '<h3 style="color:var(--accent);margin:8px 0 4px;font-size:.9rem">$1</h3>')
    .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid var(--accent);padding-left:10px;color:var(--text-muted);margin:6px 0">$1</blockquote>')
    .replace(/\n/g, '<br>');
}

// ── Skeleton Loader Control ───────────────────────────────────────────────
function toggleSkeleton(panelId, show) {
  const skeleton = $(`#${panelId}Skeleton`);
  const content = $(`#${panelId}Content`);
  if (!skeleton || !content) return;
  if (show) {
    skeleton.style.display = 'block';
    content.style.display = 'none';
    $(`#${panelId}Panel`).classList.add('visible');
  } else {
    skeleton.style.display = 'none';
    content.style.display = 'block';
  }
}

// ── PDF Export ────────────────────────────────────────────────────────────
async function exportToPDF(title, contentId) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const content = document.getElementById(contentId);
  if (!content) return;

  doc.setFontSize(22);
  doc.setTextColor(0, 200, 255);
  doc.text("Mediscan AI - Clinical Report", 20, 20);

  doc.setFontSize(12);
  doc.setTextColor(100, 100, 100);
  doc.text(`Generated on: ${new Date().toLocaleString()}`, 20, 30);

  doc.setFontSize(16);
  doc.setTextColor(0, 0, 0);
  doc.text(title, 20, 45);

  const text = content.innerText;
  const splitText = doc.splitTextToSize(text, 170);
  doc.setFontSize(11);
  doc.text(splitText, 20, 55);

  doc.save(`Mediscan_Report_${Date.now()}.pdf`);
  showToast('PDF Exported Successfully!', 'success');
}

// ── Counter Animation ────────────────────────────────────────────────────
function animateCounters() {
  $$('.stat-val[data-target]').forEach(el => {
    const target = parseFloat(el.dataset.target);
    const isFloat = el.dataset.float === 'true';
    const duration = 1400;
    const start = performance.now();
    function update(now) {
      const t = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3);
      const val = eased * target;
      el.textContent = isFloat ? val.toFixed(1) : Math.round(val);
      if (t < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });
}

function animateConfidence(targetPct, fillEl, valEl) {
  if (!fillEl) return;
  const duration = 900;
  const start = performance.now();
  function update(now) {
    const t = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - t, 3);
    const val = eased * targetPct;
    fillEl.style.width = val + '%';
    if (valEl) valEl.textContent = val.toFixed(1) + '%';
    if (t < 1) requestAnimationFrame(update);
  }
  setTimeout(() => requestAnimationFrame(update), 120);
}

// ── Particle Canvas ──────────────────────────────────────────────────────
function initParticles() {
  const canvas = document.getElementById('particleCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let particles = [];
  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  resize();
  window.addEventListener('resize', resize);
  for (let i = 0; i < 60; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 2 + 0.5,
      dx: (Math.random() - 0.5) * 0.4,
      dy: (Math.random() - 0.5) * 0.4,
      a: Math.random() * 0.5 + 0.1,
    });
  }
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0,200,255,${p.a})`;
      ctx.fill();
      p.x += p.dx; p.y += p.dy;
      if (p.x < 0 || p.x > canvas.width) p.dx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.dy *= -1;
    });
    // Draw connecting lines
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dist = Math.hypot(particles[i].x - particles[j].x, particles[i].y - particles[j].y);
        if (dist < 120) {
          ctx.beginPath();
          ctx.strokeStyle = `rgba(0,200,255,${0.08 * (1 - dist / 120)})`;
          ctx.lineWidth = 0.5;
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.stroke();
        }
      }
    }

    if (isCanvasVisible) {
      animationFrameId = requestAnimationFrame(draw);
    }
  }

  // Throttle animation when not in viewport
  let isCanvasVisible = true;
  let animationFrameId;
  const heroSection = document.querySelector('.hero');
  if (heroSection) {
    const observer = new IntersectionObserver((entries) => {
      isCanvasVisible = entries[0].isIntersecting;
      if (isCanvasVisible && !animationFrameId) {
        draw();
      } else if (!isCanvasVisible && animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
      }
    }, { threshold: 0 });
    observer.observe(heroSection);
  } else {
    draw(); // fallback
  }
}

// ── Live Stats ─────────────────────────────────────────────────────────────
async function loadLiveStats() {
  try {
    const r = await fetch('/api/stats');
    const d = await r.json();
    const box = document.getElementById('liveStatsContent');
    if (!box) return;
    box.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
        <div style="text-align:center;padding:8px;background:rgba(0,200,255,.05);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:1.2rem;font-weight:800;color:var(--accent)">${d.total}</div>
          <div style="font-size:.68rem;color:var(--text-muted)">Total Scans</div>
        </div>
        <div style="text-align:center;padding:8px;background:rgba(0,255,163,.05);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:1.2rem;font-weight:800;color:var(--accent3)">${d.avg_confidence}%</div>
          <div style="font-size:.68rem;color:var(--text-muted)">Avg Accuracy</div>
        </div>
        <div style="text-align:center;padding:8px;background:rgba(0,119,255,.05);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:1.2rem;font-weight:800;color:#4fc3f7">${d.scans}</div>
          <div style="font-size:.68rem;color:var(--text-muted)">Images</div>
        </div>
        <div style="text-align:center;padding:8px;background:rgba(255,209,102,.05);border-radius:8px;border:1px solid var(--border)">
          <div style="font-size:1.2rem;font-weight:800;color:var(--warning)">${d.prescriptions}</div>
          <div style="font-size:.68rem;color:var(--text-muted)">Prescriptions</div>
        </div>
      </div>`;
  } catch { }
}

// ── Mode Switching ─────────────────────────────────────────────────────────
function switchMode(mode) {
  state.activeMode = mode;
  $$('.mode-tab').forEach(t => t.classList.toggle('active', t.dataset.mode === mode));
  $$('.mode-view').forEach(v => v.classList.toggle('hidden', v.dataset.view !== mode));
}

// ── Rx Input Mode Switch (Image vs Text) ──────────────────────────────────
function switchRxMode(mode) {
  const imgSection = document.getElementById('rxImageSection');
  const txtSection = document.getElementById('rxTextSection');
  const imgTab = document.getElementById('rxImgTab');
  const txtTab = document.getElementById('rxTxtTab');
  if (!imgSection) return;
  if (mode === 'image') {
    imgSection.style.display = 'block';
    txtSection.style.display = 'none';
    imgTab?.classList.add('active');
    txtTab?.classList.remove('active');
  } else {
    imgSection.style.display = 'none';
    txtSection.style.display = 'block';
    txtTab?.classList.add('active');
    imgTab?.classList.remove('active');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  animateCounters();
  loadLiveStats();
  $$('.mode-tab').forEach(tab => tab.addEventListener('click', () => switchMode(tab.dataset.mode)));
  switchMode('scan');
  initUpload();
  initScanOptions();
  initAngleToolbar();
  initRxImageUpload();
  initPrescription();
  initMedicineSearch();
  initTrainForm();
  initQualityPanel();
  initChat();
  initPrescriptionCamera();

  // Show angle toolbar when scan file is picked
  const fi = $('#fileInput');
  fi?.addEventListener('change', () => { if (fi.files[0]) window._showAngleToolbar?.(); });
  $('#dropZone')?.addEventListener('drop', () => setTimeout(() => window._showAngleToolbar?.(), 100));
});

// ── Scan Angle Toolbar ─────────────────────────────────────────────────────
function initAngleToolbar() {
  const toolbar = $('#angleToolbar');
  const slider = $('#angleSlider');
  const badge = $('#angleBadge');
  const presetBtns = $$('.angle-btn');
  const preview = $('#previewImg');
  const reBtn = $('#reAnalyzeBtn');
  const ccwBtn = $('#rotateCCW');
  const cwBtn = $('#rotateCW');
  const resetBtn = $('#resetAngle');

  if (!toolbar) return;

  let currentAngle = 0;

  function setAngle(deg) {
    // Normalise to 0-359
    currentAngle = ((deg % 360) + 360) % 360;
    if (preview) preview.style.transform = `rotate(${currentAngle}deg)`;
    if (slider) slider.value = currentAngle;
    if (badge) badge.textContent = `${currentAngle}°`;
    // Highlight matching preset button
    presetBtns.forEach(b => {
      b.classList.toggle('active', parseInt(b.dataset.angle) === currentAngle);
    });
  }

  // Preset buttons
  presetBtns.forEach(b => b.addEventListener('click', () => setAngle(parseInt(b.dataset.angle))));

  // Slider
  slider?.addEventListener('input', () => setAngle(parseInt(slider.value)));

  // CCW / CW / Reset
  ccwBtn?.addEventListener('click', () => setAngle(currentAngle - 90));
  cwBtn?.addEventListener('click', () => setAngle(currentAngle + 90));
  resetBtn?.addEventListener('click', () => setAngle(0));

  // Re-analyze: render rotated image to canvas → upload as blob → POST to /api/upload
  reBtn?.addEventListener('click', async () => {
    if (!preview?.src || !preview.src.startsWith('data:') && !preview.src.startsWith('blob:') && !preview.complete) {
      showToast('Upload an image first.', 'error'); return;
    }
    const img = preview;
    // Draw rotated frame onto off-screen canvas
    const rad = (currentAngle * Math.PI) / 180;
    const sw = img.naturalWidth || img.width;
    const sh = img.naturalHeight || img.height;
    // After rotation the bounding box may swap w/h for 90/270
    const cos = Math.abs(Math.cos(rad));
    const sin = Math.abs(Math.sin(rad));
    const cw = Math.round(sw * cos + sh * sin);
    const ch = Math.round(sw * sin + sh * cos);
    const canvas = document.createElement('canvas');
    canvas.width = cw; canvas.height = ch;
    const ctx = canvas.getContext('2d');
    ctx.translate(cw / 2, ch / 2);
    ctx.rotate(rad);
    ctx.drawImage(img, -sw / 2, -sh / 2, sw, sh);

    canvas.toBlob(async blob => {
      const fileName = `rotated_${currentAngle}deg.png`;
      const form = new FormData();
      form.append('file', blob, fileName);
      form.append('scan_type', state.scanType || 'chest_xray');
      form.append('angle', currentAngle);

      const analyzeBtn = $('#analyzeBtn');
      setLoading(reBtn, true, `⏳ Analyzing at ${currentAngle}°…`);
      const panel = $('#scanResultsPanel');
      try {
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (!res.ok || data.error) { showToast(data.error || 'Analysis failed.', 'error'); return; }
        renderScanResult(data.data, '#scanResultsPanel', currentAngle);
        showToast(`✅ Re-analyzed at ${currentAngle}°!`, 'success');
        setTimeout(() => panel?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
        loadLiveStats();
      } catch (e) {
        showToast('Re-analysis failed. Is the server running?', 'error');
      } finally {
        setLoading(reBtn, false);
      }
    }, 'image/png');
  });

  // Show toolbar whenever a scan image is loaded
  window._showAngleToolbar = () => { if (toolbar) toolbar.style.display = 'block'; };
  window._hideAngleToolbar = () => { if (toolbar) toolbar.style.display = 'none'; setAngle(0); };
}

// ── Prescription Image Upload (OCR) ────────────────────────────────────────
function initRxImageUpload() {
  const zone = $('#rxDropZone');
  const input = $('#rxFileInput');
  const btn = $('#analyzeRxImgBtn');
  const preview = $('#rxPreviewImg');
  const loadBar = $('#rxLoadingBar');

  if (!zone) return;

  zone.addEventListener('click', () => input?.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragging');
    const f = e.dataTransfer.files[0];
    if (f) handleRxFileSelect(f);
  });
  input?.addEventListener('change', () => { if (input.files[0]) handleRxFileSelect(input.files[0]); });

  function handleRxFileSelect(file) {
    const allowed = ['image/png', 'image/jpeg', 'image/bmp', 'image/tiff', 'image/webp'];
    if (!allowed.includes(file.type)) { showToast('Invalid file type!', 'error'); return; }
    if (file.size > 20 * 1024 * 1024) { showToast('File too large! Max 20MB.', 'error'); return; }
    const reader = new FileReader();
    reader.onload = e => { if (preview) { preview.src = e.target.result; preview.style.display = 'block'; } };
    reader.readAsDataURL(file);
    const title = zone.querySelector('.drop-title');
    const sub = zone.querySelector('.drop-sub');
    if (title) title.textContent = file.name;
    if (sub) sub.textContent = `${(file.size / 1024).toFixed(1)} KB — ready to extract`;
    if (input) input._file = file;
  }

  btn?.addEventListener('click', async () => {
    if (!input?._file) { showToast('Please upload a prescription image first.', 'error'); return; }
    setLoading(btn, true, '⏳ Running OCR…');
    if (loadBar) loadBar.style.display = 'block';
    try {
      const form = new FormData();
      form.append('file', input._file);
      const res = await fetch('/api/upload-prescription', { method: 'POST', body: form });
      const data = await res.json();
      if (data.error) {
        showToast(data.error, 'error');
        toggleSkeleton('rx', false);
        // Still show raw OCR text if available
        if (data.raw_text) {
          const panel = $('#rxContent');
          if (panel) {
            panel.style.display = 'block';
            panel.innerHTML = `
              <div class="glass" style="padding:20px">
                <div class="section-title">🔍 OCR Extracted Text</div>
                <pre style="white-space:pre-wrap;font-size:.8rem;color:var(--text-muted);line-height:1.6;margin-top:8px;padding:12px;background:rgba(0,0,0,.3);border-radius:8px;border:1px solid var(--border)">${data.raw_text}</pre>
              </div>`;
          }
        }
        return;
      }
      toggleSkeleton('rx', false);
      // Show OCR text banner
      const panel = $('#rxContent');
      if (panel && data.data?.raw_text) {
        const ocr = el('div', 'glass');
        ocr.style.cssText = 'padding:16px 20px;margin-bottom:16px;';
        ocr.innerHTML = `
          <div class="section-title" style="margin-bottom:8px">🔍 OCR Extracted Text</div>
          <pre style="white-space:pre-wrap;font-size:.78rem;color:var(--text-muted);line-height:1.6;max-height:120px;overflow:auto;padding:10px;background:rgba(0,0,0,.3);border-radius:8px;border:1px solid var(--border)">${data.data.raw_text}</pre>`;
        panel.style.display = 'block';
        panel.appendChild(ocr);
      }
      renderPrescriptionResult(data.data, '#rxContent');
      showToast('Prescription extracted & analyzed!', 'success');
      loadLiveStats();
      setTimeout(() => $('#rxResultsPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 200);
    } catch (e) {
      showToast('OCR failed — check the server is running.', 'error');
      toggleSkeleton('rx', false);
    } finally {
      setLoading(btn, false);
      if (loadBar) loadBar.style.display = 'none';
    }
  });
}

// ── Scan Upload ────────────────────────────────────────────────────────────
function initUpload() {
  const zone = $('#dropZone');
  const input = $('#fileInput');
  const btn = $('#analyzeBtn');
  const preview = $('#previewImg');
  const loadBar = $('#loadingBar');

  if (!zone) return;

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragging'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));
  zone.addEventListener('drop', e => {
    e.preventDefault(); zone.classList.remove('dragging');
    const f = e.dataTransfer.files[0];
    if (f) handleFileSelect(f);
  });
  input.addEventListener('change', () => { if (input.files[0]) handleFileSelect(input.files[0]); });

  function handleFileSelect(file) {
    const allowed = ['image/png', 'image/jpeg', 'image/bmp', 'image/tiff', 'image/webp', 'image/gif'];
    if (!allowed.includes(file.type)) { showToast('Invalid file type! Use PNG/JPG/JPEG/BMP/TIFF.', 'error'); return; }
    if (file.size > 20 * 1024 * 1024) { showToast('File too large! Max 20MB.', 'error'); return; }
    const reader = new FileReader();
    reader.onload = e => { preview.src = e.target.result; preview.style.display = 'block'; };
    reader.readAsDataURL(file);
    zone.querySelector('.drop-title').textContent = file.name;
    zone.querySelector('.drop-sub').textContent = `${(file.size / 1024).toFixed(1)} KB — ready to analyze`;
    btn.dataset.file = 'ready';
    input._file = file;

    // Check HIPAA status if file is selected
    const hipaaCheck = $('#hipaaCheck');
    if (hipaaCheck && hipaaCheck.checked) {
      btn.disabled = false;
      btn.style.opacity = '1';
      btn.style.cursor = 'pointer';
    }
  }

  // HIPAA Checkbox Logic
  const hipaaCheck = $('#hipaaCheck');
  if (hipaaCheck) {
    hipaaCheck.addEventListener('change', (e) => {
      if (e.target.checked && input._file) {
        btn.disabled = false;
        btn.style.opacity = '1';
        btn.style.cursor = 'pointer';
      } else {
        btn.disabled = true;
        btn.style.opacity = '0.5';
        btn.style.cursor = 'not-allowed';
      }
    });
  }

  btn.addEventListener('click', async () => {
    if (!input._file) { showToast('Please select a medical image first.', 'error'); return; }
    if (hipaaCheck && !hipaaCheck.checked) { showToast('Please confirm PII anonymization first.', 'warning'); return; }

    // OPTIMISTIC UI UPDATE: Trigger immediately to reduce perceived latency
    setLoading(btn, true, '⏳ Analyzing…');
    loadBar.style.display = 'block';
    const beam = $('#scanBeam');
    if (beam) beam.style.display = 'block';
    toggleSkeleton('scan', true);

    setTimeout(async () => {
      try {
        const form = new FormData();
        form.append('file', input._file);
        form.append('scan_type', state.scanType);
        const res = await fetch('/api/upload', { method: 'POST', body: form });
        const data = await res.json();
        if (data.error) {
          showToast(data.error, 'error');
          toggleSkeleton('scan', false);
          return;
        }
        toggleSkeleton('scan', false);
        if (data.analysis_type === 'prescription') {
          renderPrescriptionResult(data.data, '#scanContent');
        } else {
          renderScanResult(data.data, '#scanContent');
        }
        showToast('Analysis complete!', 'success');
        loadLiveStats();
        setTimeout(() => {
          document.getElementById('scanResultsPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
      } catch (e) {
        showToast('Network error — is the server running?', 'error');
      } finally {
        setLoading(btn, false);
        loadBar.style.display = 'none';
        const beam = $('#scanBeam');
        if (beam) beam.style.display = 'none';
      }
    }, 10); // Release main thread briefly to allow UI to render skeleton
  });
}

function initScanOptions() {
  $$('.scan-opt').forEach(opt => {
    opt.addEventListener('click', () => {
      $$('.scan-opt').forEach(o => o.classList.remove('selected'));
      opt.classList.add('selected');
      state.scanType = opt.dataset.type;
    });
  });
}

// ── Render Scan Result ─────────────────────────────────────────────────────
// ── Heatmap Overlay ───────────────────────────────────────────────────────────
function renderHeatmap(rois) {
  const preview = $('#previewImg');
  let canvas = document.getElementById('heatmapCanvas');
  if (!canvas || !preview || !rois?.length) {
    if (canvas) canvas.style.display = 'none';
    return;
  }
  // Sync canvas size to image
  const rect = preview.getBoundingClientRect();
  canvas.width = rect.width || preview.offsetWidth || 400;
  canvas.height = rect.height || preview.offsetHeight || 400;
  canvas.style.display = 'block';
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  rois.forEach((roi, idx) => {
    const x = roi.x * canvas.width;
    const y = roi.y * canvas.height;
    const r = roi.r * Math.min(canvas.width, canvas.height);
    // Animate with a slight delay per ROI
    setTimeout(() => {
      // Pulsing radial gradient
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, roi.color || 'rgba(255,80,80,0.6)');
      grad.addColorStop(0.6, roi.color ? roi.color.replace('0.', '0.25') : 'rgba(255,80,80,0.2)');
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
      // Border ring
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.strokeStyle = (roi.color || 'rgba(255,80,80,0.9)').replace(/,[\d.]+\)$/, ',0.8)');
      ctx.lineWidth = 2;
      ctx.stroke();
      // Label
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.max(10, canvas.width * 0.025)}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.shadowColor = 'rgba(0,0,0,0.8)';
      ctx.shadowBlur = 4;
      ctx.fillText(roi.label || '', x, y + r + 14);
      ctx.shadowBlur = 0;
    }, idx * 200);
  });
}

// ── Differential Diagnosis ────────────────────────────────────────────────────
function renderDifferential(differential, panel) {
  if (!differential?.length) return;
  const dd = el('div', 'mt-16');
  dd.innerHTML = `
    <div class="section-title">🔀 Differential Diagnoses</div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:6px">
      ${differential.map(d => `<span style="padding:4px 12px;border-radius:50px;background:rgba(0,200,255,.08);border:1px solid var(--border);font-size:.78rem;color:var(--text-muted)">${d}</span>`).join('')}
    </div>`;
  panel.appendChild(dd);
}

// ── Render Scan Result ─────────────────────────────────────────────────────────
function renderScanResult(data, panelSel, angle) {
  const panel = $(panelSel || '#scanResultsPanel');
  if (!panel) return;
  panel.classList.add('visible');
  panel.innerHTML = '';
  panel.classList.add('fade-in');

  const sevClass = { Normal: 'sev-normal', Moderate: 'sev-moderate', High: 'sev-high', Critical: 'sev-critical' }[data.severity] || 'sev-moderate';

  // Header
  const hdr = el('div', 'result-header');
  const angleBadge = (angle && angle !== 0) ? `<span style="background:rgba(0,200,255,.15);border:1px solid var(--accent);color:var(--accent);font-size:.75rem;padding:2px 10px;border-radius:20px;margin-left:6px">🔄 ${angle}°</span>` : '';
  hdr.innerHTML = `
    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
      <span class="scan-badge">${data.scan_icon || '🏥'} ${data.scan_type}</span>
      <span style="font-size:.88rem;color:var(--text-muted)">· ${data.condition}</span>${angleBadge}
    </div>
    <span class="severity-badge ${sevClass}">${data.severity}</span>`;
  panel.appendChild(hdr);

  // Confidence (animated count-up)
  const conf = el('div', 'confidence-section');
  conf.innerHTML = `
    <div class="confidence-label"><span>AI Confidence</span><span class="confidence-val" id="confVal">0%</span></div>
    <div class="confidence-bar"><div class="confidence-fill" id="confFill"></div></div>`;
  panel.appendChild(conf);
  animateConfidence(data.confidence, document.getElementById('confFill'), document.getElementById('confVal'));

  // ROI Heatmap
  if (data.rois?.length) {
    const hmNote = el('div');
    hmNote.innerHTML = `<div style="font-size:.75rem;color:var(--accent);margin:6px 0">🔥 Heatmap overlay active — highlighted regions indicate findings</div>`;
    panel.appendChild(hmNote);
    setTimeout(() => renderHeatmap(data.rois), 300);
  }

  // Differential
  renderDifferential(data.differential, panel);

  // Quality
  if (data.quality_info) renderQuality(data.quality_info);

  // Findings
  const fl = el('div');
  fl.innerHTML = '<div class="section-title">📋 Findings</div>';
  const ul = el('ul', 'findings-list');
  (data.findings || []).forEach((f, idx) => {
    const li = el('li', 'finding-item');
    li.style.animationDelay = `${idx * 65}ms`;
    li.innerHTML = `<span class="finding-dot"></span><span>${f}</span>`;
    ul.appendChild(li);
  });
  fl.appendChild(ul);
  panel.appendChild(fl);

  // Report
  if (data.report) {
    const rb = el('div');
    rb.innerHTML = `
      <div class="section-title">📄 Clinical Report</div>
      <div style="position:relative">
        <div class="report-box" id="clinicalReport">${data.report}</div>
        <div style="display:flex;gap:8px;margin-top:8px">
          <button class="btn btn-outline btn-sm" id="copyEMRBtn" onclick="copyToEMR()" style="background:rgba(16,185,129,0.1); border-color:var(--success); color:var(--success)">📋 Copy to EMR</button>
          <button class="btn btn-outline btn-sm" onclick="exportToPDF('Medical Scan Analysis', 'clinicalReport')">📥 Download PDF</button>
          <button class="btn btn-outline btn-sm" onclick="window.print()">🖨️ Print</button>
        </div>
      </div>`;
    panel.appendChild(rb);

    // Attach data to window for EMR copy function
    window.__currentEMRData = {
      type: data.scan_type,
      condition: data.condition,
      severity: data.severity,
      report: data.report
    };
  }

  // Recommendations
  if (data.recommendations?.length) {
    const rc = el('div');
    rc.innerHTML = `<div class="section-title">✅ Recommendations</div>
      <div class="reco-list">${data.recommendations.map((r, i) => `<div class="reco-item"><span class="reco-num">${i + 1}.</span><span>${r}</span></div>`).join('')}</div>`;
    panel.appendChild(rc);
  }

  // Translate
  const tr = el('div', 'mt-16');
  tr.innerHTML = `
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-outline btn-sm" id="translateBtn">🌐 🇮🇳 Tamil</button>
      <button class="btn btn-outline btn-sm" id="translateTangBtn">🌐 🔡 Tanglish</button>
    </div>
    <div class="tamil-box" id="tamilBox"></div>
    <div class="tanglish-box" id="tanglishBox"></div>`;
  panel.appendChild(tr);

  $('#translateBtn', panel)?.addEventListener('click', async () => {
    const btn = $('#translateBtn', panel);
    btn.textContent = '⏳…'; btn.disabled = true;
    await translateText(data.report, 'tamilBox', 'translate');
    btn.textContent = '🌐 🇮🇳 Tamil'; btn.disabled = false;
  });
  $('#translateTangBtn', panel)?.addEventListener('click', async () => {
    const btn = $('#translateTangBtn', panel);
    btn.textContent = '⏳…'; btn.disabled = true;
    await translateText(data.report, 'tanglishBox', 'translate-tanglish');
    btn.textContent = '🌐 🔡 Tanglish'; btn.disabled = false;
  });
}

// ── Copy Report ──────────────────────────────────────────────────────────
function copyReport() {
  const box = document.getElementById('clinicalReport');
  if (!box) return;
  navigator.clipboard.writeText(box.innerText).then(() => {
    const btn = document.getElementById('copyReportBtn');
    if (btn) { btn.textContent = '✅ Copied!'; setTimeout(() => btn.textContent = '📋 Copy Report', 2000); }
  });
}

// ── Quality Panel ─────────────────────────────────────────────────────────────
function initQualityPanel() {
  const qp = $('#qualityPanel');
  if (qp) qp.style.display = 'none';
}
function renderQuality(q) {
  const qp = $('#qualityPanel');
  if (!qp) return;
  qp.style.display = 'block';
  const m = q.metrics || {};
  ['sharpness', 'brightness', 'contrast'].forEach(k => {
    const bar = $(`#q_${k}`);
    if (bar) { setTimeout(() => bar.style.width = (m[k] || 50) + '%', 200); }
    const lbl = $(`#q_${k}_val`);
    if (lbl) lbl.textContent = (m[k] || 0).toFixed(0) + '%';
  });
  const issues = $('#qualityIssues');
  if (issues) issues.innerHTML = (q.issues || []).map(i => `<div class="quality-issue">${i}</div>`).join('');
}

// ── Translate ──────────────────────────────────────────────────────────────
async function translateText(text, targetId, mode = 'translate') {
  try {
    const endpoint = mode === 'translate-tanglish' ? '/api/translate-tanglish' : '/api/translate';
    const r = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const d = await r.json();
    const box = document.getElementById(targetId);
    if (box) {
      box.textContent = d.translated;
      box.style.display = 'block';
      // Hide other translation boxes in the same parent if they exist
      const parent = box.parentElement;
      if (parent) {
        if (targetId.includes('tamil')) {
          const tanglish = parent.querySelector('[id*="tanglish"]');
          if (tanglish) tanglish.style.display = 'none';
        } else {
          const tamil = parent.querySelector('[id*="tamil"]');
          if (tamil) tamil.style.display = 'none';
        }
      }
    }
  } catch (e) {
    showToast('Translation failed', 'error');
  }
}

// ── Prescription Mode ──────────────────────────────────────────────────────
function initPrescription() {
  const analyzeTextBtn = $('#analyzeTextBtn');
  if (!analyzeTextBtn) return;

  analyzeTextBtn?.addEventListener('click', async () => {
    const txt = $('#rxTextArea')?.value.trim();
    if (!txt) { showToast('Enter prescription text', 'error'); return; }
    setLoading(analyzeTextBtn, true, '⏳ Analyzing…');
    try {
      const r = await fetch('/api/analyze-prescription', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text: txt }) });
      const d = await r.json();
      if (d.error) { showToast(d.error, 'error'); return; }
      renderPrescriptionResult(d.data, '#rxResultsPanel');
      showToast('Done!', 'success');
      loadLiveStats();
      setTimeout(() => {
        document.getElementById('rxResultsPanel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 200);
    } catch { showToast('Failed', 'error'); }
    finally { setLoading(analyzeTextBtn, false); }
  });
}

// ── Dosage Schedule ───────────────────────────────────────────────────────────
function renderDosageSchedule(schedule, panel) {
  if (!schedule?.length) return;
  const ds = el('div', 'mt-16');
  ds.innerHTML = `<div class="section-title">📅 Dosage Schedule</div>`;
  const table = document.createElement('table');
  table.style.cssText = 'width:100%;border-collapse:collapse;margin-top:10px;font-size:.8rem';
  table.innerHTML = `
    <thead>
      <tr style="border-bottom:1px solid var(--border)">
        <th style="padding:8px;text-align:left;color:var(--text-muted)">Medicine</th>
        <th style="padding:8px;text-align:center">🌅 Morning</th>
        <th style="padding:8px;text-align:center">☀️ Afternoon</th>
        <th style="padding:8px;text-align:center">🌙 Night</th>
        <th style="padding:8px;text-align:center">🤰 Preg.</th>
        <th style="padding:8px;text-align:center">🍺 Alcohol</th>
        <th style="padding:8px;text-align:center">🚗 Drive</th>
      </tr>
    </thead>
    <tbody>${schedule.map(s => {
    const safe = s.safety || {};
    const pregColor = { 'A': '#22c55e', 'B': '#4fc3f7', 'C': '#f59e0b', 'D': '#ef4444', 'X': '#dc2626' }[safe.pregnancy] || 'var(--text-muted)';
    return `<tr style="border-bottom:1px solid rgba(255,255,255,.05)">
        <td style="padding:8px;font-weight:600">${s.name}<div style="font-size:.7rem;color:var(--text-muted)">${s.dosage}</div></td>
        <td style="text-align:center">${s.morning ? '✅' : '—'}</td>
        <td style="text-align:center">${s.afternoon ? '✅' : '—'}</td>
        <td style="text-align:center">${s.night ? '✅' : '—'}</td>
        <td style="text-align:center;font-weight:700;color:${pregColor}">${safe.pregnancy || '?'}</td>
        <td style="text-align:center">${safe.alcohol ? '⚠️' : '✅'}</td>
        <td style="text-align:center">${safe.driving ? '⚠️' : '✅'}</td>
      </tr>`;
  }).join('')}</tbody>`;
  ds.appendChild(table);
  panel.appendChild(ds);
}

function renderPrescriptionResult(data, panelSel) {
  const panel = $(panelSel);
  if (!panel) return;
  panel.style.display = 'block';
  panel.innerHTML = '';
  panel.classList.add('fade-in');

  if (!data.medicines?.length) {
    panel.innerHTML = `<div class="empty-state"><span class="empty-icon">💊</span><p>No medicines identified. Ensure prescription is clear and legible.</p>
    ${data.raw_text ? `<pre style="font-size:.75rem;margin-top:12px;color:var(--text-muted);white-space:pre-wrap">${data.raw_text}</pre>` : ''}</div>`;
    return;
  }

  // Summary
  const sum = el('div', 'glass', `<p style="font-size:.85rem;padding:12px 16px;color:var(--accent3)">✅ ${data.summary || ''}</p>`);
  panel.appendChild(sum);

  // Timings
  if (Object.keys(data.timings_detected || {}).length) {
    const tc = el('div', 'mt-16');
    tc.innerHTML = `<div class="section-title">⏰ Dosage Codes</div><div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">
      ${Object.entries(data.timings_detected).map(([k, v]) => `<span style="padding:3px 10px;border-radius:50px;background:rgba(0,200,255,.08);border:1px solid var(--border);font-size:.76rem;color:var(--accent)"><strong>${k.toUpperCase()}</strong> = ${v}</span>`).join('')}
    </div>`;
    panel.appendChild(tc);
  }

  // Dosage Schedule (NEW)
  if (data.dosage_schedule?.length) {
    renderDosageSchedule(data.dosage_schedule, panel);
  }

  // Medicines
  const mh = el('div', 'mt-16');
  mh.innerHTML = `<div class="section-title">💊 Identified Medicines (${data.medicines.length})</div>`;
  panel.appendChild(mh);

  data.medicines.forEach(med => {
    const card = el('div', 'medicine-card fade-in');
    card.innerHTML = `
      <div class="med-name">${med.name}</div>
      <div class="med-category">${med.category || '—'}</div>
      <div class="med-detail"><strong>Uses:</strong> ${(med.uses || []).join(', ') || '—'}</div>
      <div class="med-detail"><strong>Dosage:</strong> ${med.dosage || 'As directed'}</div>
      <div class="med-detail"><strong>Alternatives:</strong> ${(med.alternatives || []).join(', ') || '—'}</div>
      <div class="med-warnings">${(med.warnings || []).map(w => `<span class="warn-tag">⚠ ${w}</span>`).join('')}</div>`;
    panel.appendChild(card);
  });

  // Interactions
  if (data.interactions?.length) {
    const ih = el('div', 'mt-16');
    ih.innerHTML = `<div class="section-title">⚠️ Drug Interactions</div>`;
    data.interactions.forEach(int => {
      const cls = { 'CRITICAL': 'int-critical', 'HIGH': 'int-high', 'MODERATE': 'int-moderate' }[int.severity] || 'int-moderate';
      const alert = el('div', `interaction-alert ${cls}`);
      alert.innerHTML = `<span class="int-label">${int.severity}:</span>${int.message}`;
      ih.appendChild(alert);
    });
    panel.appendChild(ih);
  }

  // Translate
  const tr = el('div', 'mt-16');
  tr.innerHTML = `
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="btn btn-outline btn-sm" id="translateRxBtn">🌐 🇮🇳 Tamil</button>
      <button class="btn btn-outline btn-sm" id="translateTangRxBtn">🌐 🔡 Tanglish</button>
      <button class="btn btn-outline btn-sm" onclick="exportToPDF('Prescription Analysis', 'rxResultsPanel')">📥 Download PDF</button>
    </div>
    <div class="tamil-box" id="tamilRxBox"></div>
    <div class="tanglish-box" id="tanglishRxBox"></div>`;
  panel.appendChild(tr);

  $('#translateRxBtn', panel)?.addEventListener('click', async () => {
    const btn = $('#translateRxBtn', panel);
    btn.textContent = '⏳…'; btn.disabled = true;
    await translateText(data.summary, 'tamilRxBox', 'translate');
    btn.textContent = '🌐 🇮🇳 Tamil'; btn.disabled = false;
  });
  $('#translateTangRxBtn', panel)?.addEventListener('click', async () => {
    const btn = $('#translateTangRxBtn', panel);
    btn.textContent = '⏳…'; btn.disabled = true;
    await translateText(data.summary, 'tanglishRxBox', 'translate-tanglish');
    btn.textContent = '🌐 🔡 Tanglish'; btn.disabled = false;
  });
}

// ── Medicine Search ────────────────────────────────────────────────────────
function initMedicineSearch() {
  const input = $('#medSearchInput');
  const btn = $('#searchBtn');
  const results = $('#searchResults');
  if (!input || !btn || !results) return;

  const renderSearchResults = (meds, q) => {
    results.innerHTML = '';
    if (!meds || !meds.length) {
      results.innerHTML = `
        <div class="empty-state">
          <span class="empty-icon" style="font-size:2.5rem;opacity:0.3">💡</span>
          <p style="margin-bottom:15px">No matches found for "<strong>${q}</strong>"</p>
          <button class="btn btn-outline btn-sm" onclick="showTrainWith('${q}')">🧠 Train Mediscan on "${q}"</button>
        </div>`;
      return;
    }

    results.innerHTML = `<div style="font-size:.78rem;color:var(--text-muted);margin-bottom:12px">Found ${meds.length} matches:</div>`;

    meds.forEach(med => {
      const card = el('div', 'medicine-card fade-in');
      card.innerHTML = `
        <div class="med-name">${med.name}</div>
        <div class="med-category">${med.category || 'Medicine'}</div>
        <div class="med-detail"><strong>Uses:</strong> ${(med.uses || []).join(', ') || '—'}</div>
        <div class="med-detail"><strong>Dosage:</strong> ${med.dosage || 'As directed'}</div>
        <div class="med-warnings">${(med.warnings || []).map(w => `<span class="warn-tag">⚠ ${w}</span>`).join('')}</div>
      `;
      results.appendChild(card);
    });
  };

  const doSearch = async () => {
    const q = input.value.trim();
    if (!q) return;
    setLoading(btn, true, '🔍');
    try {
      const r = await fetch(`/api/search-medicine?q=${encodeURIComponent(q)}`);
      const d = await r.json();
      renderSearchResults(d.results, q);
    } catch {
      showToast('Search failed', 'error');
    } finally {
      setLoading(btn, false);
    }
  };

  let debounceTimer;
  input.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const q = input.value.trim();
    if (q.length >= 3) {
      debounceTimer = setTimeout(doSearch, 400);
    }
  });

  btn.addEventListener('click', doSearch);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
}

// ── Train AI (Add Custom Medicine) ────────────────────────────────────────────
function initTrainForm() {
  const form = $('#trainForm');
  if (!form) return;
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const name = $('#trainName')?.value.trim();
    const category = $('#trainCategory')?.value.trim() || 'Custom';
    const uses = $('#trainUses')?.value.trim();
    const dosage = $('#trainDosage')?.value.trim();
    const warnings = $('#trainWarnings')?.value.trim();
    if (!name) { showToast('Medicine name is required', 'error'); return; }
    const submitBtn = form.querySelector('[type=submit]');
    setLoading(submitBtn, true, '⏳ Training…');
    try {
      const r = await fetch('/api/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category, uses, dosage, warnings })
      });
      const d = await r.json();
      if (d.error) { showToast(d.error, 'error'); return; }
      showToast(d.message || `✅ '${name}' trained!`, 'success');
      form.reset();
      loadLiveStats();
    } catch { showToast('Training failed', 'error'); }
    finally { setLoading(submitBtn, false); }
  });
}

// ── Chat Interface ────────────────────────────────────────────────────────
async function initChat() {
  const input = $('#chatInput');
  const btn = $('#chatBtn');
  const msgs = $('#chatMessages');
  const reasoning = $('#aiReasoning');
  const stepsCont = $('#reasoningSteps');
  if (!input || !btn || !msgs) return;

  const addMsg = (text, isBot = true) => {
    const m = el('div', isBot ? 'bot-msg' : 'user-msg');
    m.style.animation = 'fadeInUp 0.3s ease-out';
    m.innerHTML = isBot ? `<div style="display:flex;gap:10px">
      <div style="font-size:1.2rem">🤖</div>
      <div class="msg-content">${renderMarkdown(text)}</div>
    </div>` : renderMarkdown(text);
    msgs.appendChild(m);
    msgs.scrollTop = msgs.scrollHeight;
  };

  const doChat = async () => {
    const q = input.value.trim();
    if (!q) return;
    addMsg(q, false);
    input.value = '';

    // OPTIMISTIC UI: Show typing skeleton instantly
    setLoading(btn, true, '…');
    if (reasoning) reasoning.style.display = 'none';

    const loadId = 'bot-typing-' + Date.now();
    const typingMsg = el('div', 'bot-msg');
    typingMsg.id = loadId;
    typingMsg.style.animation = 'fadeInUp 0.3s ease-out';
    typingMsg.innerHTML = `<div style="display:flex;gap:10px">
      <div style="font-size:1.2rem">🤖</div>
      <div class="msg-content"><span style="opacity:0.6">typing...</span></div>
    </div>`;
    msgs.appendChild(typingMsg);
    msgs.scrollTop = msgs.scrollHeight;

    setTimeout(async () => {
      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, context: state.currentResult })
        });
        const data = await res.json();

        const typingEl = document.getElementById(loadId);
        if (typingEl) typingEl.remove();

        if (data.reasoning && data.reasoning.length && reasoning) {
          reasoning.style.display = 'block';
          stepsCont.innerHTML = data.reasoning.map(step => `<div style="margin-bottom:4px">◦ ${step}</div>`).join('');
        }
        addMsg(data.answer || "I'm sorry, I couldn't process that.");
      } catch {
        const typingEl = document.getElementById(loadId);
        if (typingEl) typingEl.remove();
        addMsg("Connection error.");
      } finally {
        setLoading(btn, false);
      }
    }, 10);
  };

  btn.addEventListener('click', doChat);
  input.addEventListener('keydown', e => { if (e.key === 'Enter') doChat(); });
}

// ── Prescription Camera ───────────────────────────────────────────────────
function initPrescriptionCamera() {
  const openBtn = $('#openCamBtn');
  const captureBtn = $('#captureBtn');
  const closeBtn = $('#closeCamBtn');
  const video = $('#rxVideo');
  const container = $('#cameraContainer');
  const canvas = $('#rxCaptureCanvas');
  const preview = $('#rxPreviewImg');
  const input = $('#rxFileInput');

  if (!openBtn || !video) return;

  let stream = null;

  openBtn.onclick = async () => {
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
      video.srcObject = stream;
      container.style.display = 'block';
      openBtn.parentElement.style.display = 'none';
    } catch (e) {
      showToast('Camera access denied or not available.', 'error');
    }
  };

  const stopCam = () => {
    if (stream) stream.getTracks().forEach(track => track.stop());
    container.style.display = 'none';
    openBtn.parentElement.style.display = 'block';
  };

  closeBtn.onclick = stopCam;

  captureBtn.onclick = () => {
    const w = video.videoWidth;
    const h = video.videoHeight;
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, w, h);

    canvas.toBlob(blob => {
      const file = new File([blob], 'captured_rx.jpg', { type: 'image/jpeg' });
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      input.files = dataTransfer.files;
      const url = URL.createObjectURL(file);
      preview.src = url;
      preview.style.display = 'block';
      input._file = file;
      stopCam();
      showToast('Photo captured!', 'success');
    }, 'image/jpeg', 0.9);
  };
}

// ── Search-to-Train Integration ──────────────────────────────────────────
async function showTrainWith(medName) {
  const encodedName = encodeURIComponent(medName.charAt(0).toUpperCase() + medName.slice(1));
  window.location.href = `admin.html?train=${encodedName}`;
}

// ── Global Helper: EMR Copy ────────────────────────────────────────────────
window.copyToEMR = async function () {
  const d = window.__currentEMRData;
  if (!d) return;
  const dateStr = new Date().toISOString().split('T')[0];
  const emrText = `--- MediScan AI Clinical Summary ---\nDate: ${dateStr}\nModality: ${d.type}\nPrimary Finding: ${d.condition}\nSeverity: ${d.severity}\n\nClinical Report:\n${d.report}\n\n[End of AI Report]`;
  try {
    await navigator.clipboard.writeText(emrText);
    showToast('Copied to Clipboard for EMR', 'success');
  } catch (e) {
    showToast('Failed to copy. Try selecting the text manually.', 'error');
  }
};

window.copyReport = async function () {
  const t = document.getElementById('clinicalReport')?.innerText || '';
  if (!t) return;
  try { await navigator.clipboard.writeText(t); showToast('Report Copied!', 'success'); }
  catch (e) { showToast('Copy failed', 'error'); }
};

// ── Reveal Animations (Scroll) ───────────────────────────────────────────
function revealCards() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('active');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });

  $$('.reveal').forEach(el => observer.observe(el));
}
