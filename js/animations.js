/* ═══════════════════════════════════════════════════════════════════════
   MediScan AI v2 — TOTAL ANIMATION ENGINE
   File: static/js/animations.js
   Loaded after DOM is ready. Zero dependencies.
   ═══════════════════════════════════════════════════════════════════════ */
'use strict';

(function () {

    /* ──────────────────────────────────────────────────────────────────────
       0.  UTILITY
    ────────────────────────────────────────────────────────────────────── */
    const q = (s, p = document) => p.querySelector(s);
    const qq = (s, p = document) => [...p.querySelectorAll(s)];
    const raf = requestAnimationFrame;

    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
    function mapRange(v, a1, b1, a2, b2) { return a2 + (b2 - a2) * ((v - a1) / (b1 - a1)); }

    /* ──────────────────────────────────────────────────────────────────────
       1.  ANIMATED AURORA BACKGROUND (canvas layer behind particles)
    ────────────────────────────────────────────────────────────────────── */
    function initAurora() {
        const canvas = document.createElement('canvas');
        canvas.id = 'auroraCanvas';
        canvas.style.cssText = `
      position:fixed;inset:0;z-index:-2;pointer-events:none;
      opacity:0;transition:opacity 1.2s ease;
    `;
        document.body.prepend(canvas);
        setTimeout(() => canvas.style.opacity = '1', 100);

        const ctx = canvas.getContext('2d');
        let W, H, t = 0;

        const orbs = [
            { x: 0.2, y: 0.2, r: 0.45, col: [0, 120, 255], speed: 0.00012 },
            { x: 0.8, y: 0.8, r: 0.40, col: [0, 200, 255], speed: 0.00009 },
            { x: 0.6, y: 0.1, r: 0.35, col: [120, 0, 255], speed: 0.00015 },
            { x: 0.1, y: 0.7, r: 0.30, col: [0, 255, 163], speed: 0.00011 },
            { x: 0.9, y: 0.3, r: 0.28, col: [0, 80, 200], speed: 0.00008 },
        ];

        function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
        resize();
        window.addEventListener('resize', resize);

        function draw() {
            ctx.clearRect(0, 0, W, H);
            orbs.forEach(o => {
                const cx = (o.x + Math.sin(t * o.speed * 2 + o.x * 10) * 0.15) * W;
                const cy = (o.y + Math.cos(t * o.speed + o.y * 8) * 0.12) * H;
                const rad = o.r * Math.min(W, H);
                const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rad);
                const [r, gr, b] = o.col;
                g.addColorStop(0, `rgba(${r},${gr},${b},0.18)`);
                g.addColorStop(0.5, `rgba(${r},${gr},${b},0.07)`);
                g.addColorStop(1, `rgba(${r},${gr},${b},0)`);
                ctx.fillStyle = g;
                ctx.beginPath();
                ctx.arc(cx, cy, rad, 0, Math.PI * 2);
                ctx.fill();
            });
            t++;
            raf(draw);
        }
        draw();
    }

    /* ──────────────────────────────────────────────────────────────────────
       2.  CURSOR PARTICLE TRAIL
    ────────────────────────────────────────────────────────────────────── */
    function initCursorTrail() {
        const MAX = 20;
        const dots = [];
        let mx = -999, my = -999;

        for (let i = 0; i < MAX; i++) {
            const d = document.createElement('div');
            d.style.cssText = `
        position:fixed;width:6px;height:6px;border-radius:50%;
        background:rgba(0,200,255,${(1 - i / MAX) * 0.7});
        pointer-events:none;z-index:9999;
        transform:translate(-50%,-50%);
        transition:opacity .3s;
      `;
            document.body.appendChild(d);
            dots.push({ el: d, x: 0, y: 0 });
        }

        let positions = Array(MAX).fill({ x: 0, y: 0 });

        window.addEventListener('mousemove', e => { mx = e.clientX; my = e.clientY; });

        function animate() {
            positions = [{ x: mx, y: my }, ...positions.slice(0, MAX - 1)];
            dots.forEach((d, i) => {
                d.x = lerp(d.x, positions[i].x, 0.45);
                d.y = lerp(d.y, positions[i].y, 0.45);
                const scale = 1 - i / MAX;
                d.el.style.left = d.x + 'px';
                d.el.style.top = d.y + 'px';
                d.el.style.transform = `translate(-50%,-50%) scale(${scale})`;
                d.el.style.opacity = mx === -999 ? '0' : `${scale * 0.65}`;
            });
            raf(animate);
        }
        animate();
    }

    /* ──────────────────────────────────────────────────────────────────────
       3.  CLICK RIPPLE (global — anywhere on page)
    ────────────────────────────────────────────────────────────────────── */
    function initClickRipple() {
        document.addEventListener('click', e => {
            const r = document.createElement('div');
            const size = 60;
            r.style.cssText = `
        position:fixed;
        left:${e.clientX - size / 2}px;top:${e.clientY - size / 2}px;
        width:${size}px;height:${size}px;border-radius:50%;
        border:2px solid rgba(0,200,255,0.7);
        pointer-events:none;z-index:9998;
        animation:clickRipple .55s ease-out forwards;
      `;
            document.body.appendChild(r);
            r.addEventListener('animationend', () => r.remove());
        });

        // Inject keyframe if not present
        if (!document.getElementById('rippleKf')) {
            const s = document.createElement('style');
            s.id = 'rippleKf';
            s.textContent = `
        @keyframes clickRipple {
          from { transform:scale(0.2); opacity:1; }
          to   { transform:scale(3);   opacity:0; }
        }
      `;
            document.head.appendChild(s);
        }
    }

    /* ──────────────────────────────────────────────────────────────────────
       4.  3D TILT on glass cards
    ────────────────────────────────────────────────────────────────────── */
    function initTilt() {
        qq('.glass').forEach(card => {
            let tx = 0, ty = 0, active = false;

            card.addEventListener('mouseenter', () => { active = true; });
            card.addEventListener('mouseleave', () => {
                active = false;
                tx = ty = 0;
                card.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)';
                card.style.boxShadow = '';
            });
            card.addEventListener('mousemove', e => {
                if (!active) return;
                const rect = card.getBoundingClientRect();
                const px = (e.clientX - rect.left) / rect.width - 0.5;
                const py = (e.clientY - rect.top) / rect.height - 0.5;
                tx = lerp(tx, px, 0.12);
                ty = lerp(ty, py, 0.12);
                const rotX = clamp(-ty * 14, -8, 8);
                const rotY = clamp(tx * 14, -8, 8);
                card.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.02)`;
                card.style.boxShadow = `
          ${-rotY * 2}px ${rotX * 2}px 40px rgba(0,200,255,0.18),
          0 8px 32px rgba(0,0,0,0.5)
        `;
            });
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       5.  MAGNETIC BUTTONS
    ────────────────────────────────────────────────────────────────────── */
    function initMagneticButtons() {
        qq('.btn-primary, .mode-tab').forEach(btn => {
            btn.addEventListener('mousemove', e => {
                const rect = btn.getBoundingClientRect();
                const dx = e.clientX - (rect.left + rect.width / 2);
                const dy = e.clientY - (rect.top + rect.height / 2);
                btn.style.transform = `translate(${dx * 0.2}px, ${dy * 0.2}px)`;
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = '';
                btn.style.transition = 'transform 0.4s cubic-bezier(0.34,1.56,0.64,1)';
                setTimeout(() => btn.style.transition = '', 400);
            });
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       6.  TYPED-TEXT hero subtitle (rewrites with a blinking cursor)
    ────────────────────────────────────────────────────────────────────── */
    function initTypedHero() {
        const p = q('.hero p');
        if (!p) return;
        const fullText = p.textContent.trim();
        p.textContent = '';
        p.style.opacity = '1';

        const cursor = document.createElement('span');
        cursor.textContent = '|';
        cursor.style.cssText = 'color:var(--accent);animation:blink .8s step-end infinite;font-weight:300;';
        p.appendChild(cursor);

        // inject blink keyframe
        if (!document.getElementById('blinkKf')) {
            const s = document.createElement('style');
            s.id = 'blinkKf';
            s.textContent = `@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }`;
            document.head.appendChild(s);
        }

        let i = 0;
        function type() {
            if (i < fullText.length) {
                p.insertBefore(document.createTextNode(fullText[i++]), cursor);
                setTimeout(type, i === 1 ? 600 : 18 + Math.random() * 14);
            } else {
                setTimeout(() => { cursor.remove(); }, 2400);
            }
        }
        setTimeout(type, 900);
    }

    /* ──────────────────────────────────────────────────────────────────────
       7.  SCANNER LINE on drop-zone
    ────────────────────────────────────────────────────────────────────── */
    function initScannerLine() {
        qq('.drop-zone').forEach(zone => {
            if (zone.querySelector('.scanner-line')) return;
            zone.style.position = 'relative';
            zone.style.overflow = 'hidden';

            const line = document.createElement('div');
            line.className = 'scanner-line';
            line.style.cssText = `
        position:absolute;left:0;right:0;height:2px;
        background:linear-gradient(90deg,transparent,rgba(0,200,255,0.9),transparent);
        box-shadow:0 0 12px rgba(0,200,255,0.8);
        animation:scanDown 2.8s ease-in-out infinite;
        pointer-events:none;z-index:10;top:0;
      `;
            zone.appendChild(line);

            if (!document.getElementById('scanKf')) {
                const s = document.createElement('style');
                s.id = 'scanKf';
                s.textContent = `
          @keyframes scanDown {
            0%   { top:0%;   opacity:0; }
            5%   { opacity:1; }
            50%  { top:100%; opacity:1; }
            95%  { opacity:1; }
            100% { top:100%; opacity:0; }
          }
        `;
                document.head.appendChild(s);
            }
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       8.  GLITCH effect on nav title (brief, repeating)
    ────────────────────────────────────────────────────────────────────── */
    function initGlitch() {
        const title = q('.nav-title');
        if (!title) return;

        const chars = '▓█░▒▤▣▥▦▧▨▩';
        const original = title.textContent;

        function glitch() {
            let count = 0;
            const iv = setInterval(() => {
                title.textContent = original.split('').map((c, i) =>
                    Math.random() < 0.15 ? chars[Math.floor(Math.random() * chars.length)] : c
                ).join('');
                if (++count > 6) {
                    clearInterval(iv);
                    title.textContent = original;
                }
            }, 45);
        }

        // Run once on load, then every 8–14s
        setTimeout(glitch, 1800);
        setInterval(glitch, 10000 + Math.random() * 4000);
        q('.nav-brand')?.addEventListener('mouseenter', glitch);
    }

    /* ──────────────────────────────────────────────────────────────────────
       9.  SCROLL REVEAL — elements animate in as they enter viewport
    ────────────────────────────────────────────────────────────────────── */
    function initScrollReveal() {
        const targets = qq(`
      .glass, .mode-tab, .scan-opt, .stat,
      .finding-item, .medicine-card, .reco-item,
      .stat-pill, .hist-card, .filter-tab
    `);

        targets.forEach((el, i) => {
            if (!el.dataset.revealed) {
                el.style.opacity = '0';
                el.style.transform = 'translateY(20px)';
                el.style.transition = `opacity 0.5s ease, transform 0.5s ease`;
            }
        });

        const obs = new IntersectionObserver(entries => {
            entries.forEach(e => {
                if (e.isIntersecting && !e.target.dataset.revealed) {
                    const idx = targets.indexOf(e.target);
                    setTimeout(() => {
                        e.target.style.opacity = '1';
                        e.target.style.transform = 'translateY(0)';
                        e.target.dataset.revealed = '1';
                    }, (idx % 6) * 60);
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.08 });

        targets.forEach(el => obs.observe(el));
    }

    /* ──────────────────────────────────────────────────────────────────────
       10.  NAV ANIMATED BORDER (bottom gradient sweep)
    ────────────────────────────────────────────────────────────────────── */
    function initNavBorder() {
        const nav = q('nav');
        if (!nav) return;
        let pos = 0;
        function tick() {
            pos = (pos + 0.4) % 360;
            nav.style.borderBottomColor = `hsl(${pos},100%,60%)`;
            nav.style.borderBottomWidth = '1px';
            nav.style.borderBottomStyle = 'solid';
            raf(tick);
        }
        tick();
    }

    /* ──────────────────────────────────────────────────────────────────────
       11.  NEON TEXT PULSE on hero h1 gradient text
    ────────────────────────────────────────────────────────────────────── */
    function initNeonH1() {
        const h1 = q('.hero h1');
        if (!h1) return;
        let t = 0;
        function tick() {
            t += 0.018;
            const glow = Math.sin(t) * 0.5 + 0.5; // 0–1
            h1.style.filter = `drop-shadow(0 0 ${6 + glow * 16}px rgba(0,200,255,${0.3 + glow * 0.3}))`;
            raf(tick);
        }
        tick();
    }

    /* ──────────────────────────────────────────────────────────────────────
       12.  PARTICLE BURST on scan-option click
    ────────────────────────────────────────────────────────────────────── */
    function initScanOptBurst() {
        qq('.scan-opt').forEach(opt => {
            opt.addEventListener('click', e => {
                const rect = opt.getBoundingClientRect();
                const cx = rect.left + rect.width / 2;
                const cy = rect.top + rect.height / 2;
                for (let i = 0; i < 12; i++) {
                    const angle = (i / 12) * Math.PI * 2;
                    const dist = 40 + Math.random() * 30;
                    const p = document.createElement('div');
                    p.style.cssText = `
            position:fixed;width:5px;height:5px;border-radius:50%;
            background:rgba(0,200,255,0.9);pointer-events:none;z-index:9999;
            left:${cx}px;top:${cy}px;transform:translate(-50%,-50%);
          `;
                    document.body.appendChild(p);
                    const dx = Math.cos(angle) * dist;
                    const dy = Math.sin(angle) * dist;
                    p.animate([
                        { transform: 'translate(-50%,-50%) scale(1)', opacity: 1 },
                        { transform: `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(0)`, opacity: 0 }
                    ], { duration: 500 + Math.random() * 250, easing: 'cubic-bezier(0,0,0.2,1)', fill: 'forwards' })
                        .finished.then(() => p.remove());
                }
            });
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       13.  CINEMATIC PAGE ENTRANCE (staggered reveal on first load)
    ────────────────────────────────────────────────────────────────────── */
    function initCinematicEntrance() {
        const seq = [
            { sel: 'nav', delay: 0, dur: 600, from: { opacity: 0, transform: 'translateY(-40px)' } },
            { sel: '.hero-badge', delay: 200, dur: 500, from: { opacity: 0, transform: 'scale(0.6)' } },
            { sel: '.hero h1', delay: 350, dur: 700, from: { opacity: 0, transform: 'translateY(30px)' } },
            { sel: '.hero-stats', delay: 600, dur: 600, from: { opacity: 0, transform: 'translateY(20px)' } },
            { sel: '.heartbeat', delay: 800, dur: 400, from: { opacity: 0 } },
            { sel: '.mode-tabs', delay: 700, dur: 500, from: { opacity: 0, transform: 'translateY(20px)' } },
            { sel: '.main-layout', delay: 850, dur: 700, from: { opacity: 0, transform: 'translateY(24px)' } },
        ];

        seq.forEach(({ sel, delay, dur, from }) => {
            const el = q(sel);
            if (!el) return;
            Object.assign(el.style, from, { transition: 'none' });
            setTimeout(() => {
                el.style.transition = `opacity ${dur}ms cubic-bezier(0.22,1,0.36,1), transform ${dur}ms cubic-bezier(0.22,1,0.36,1)`;
                el.style.opacity = '1';
                el.style.transform = 'none';
            }, delay);
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       14.  LOADING BAR NEON SHIMMER (enhance existing loading bar)
    ────────────────────────────────────────────────────────────────────── */
    function initLoadingBarObserver() {
        // Watch for the loading bar to become visible and add extra neon trail
        const observer = new MutationObserver(() => {
            qq('.loading-bar').forEach(bar => {
                if (bar.style.display !== 'none' && !bar.dataset.neon) {
                    bar.dataset.neon = '1';
                    bar.style.boxShadow = '0 0 16px rgba(0,200,255,0.7), 0 0 40px rgba(0,200,255,0.3)';
                } else if (bar.style.display === 'none') {
                    delete bar.dataset.neon;
                    bar.style.boxShadow = '';
                }
            });
        });
        observer.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['style'] });
    }

    /* ──────────────────────────────────────────────────────────────────────
       15.  HERO-STATS COUNTER with eased animation
    ────────────────────────────────────────────────────────────────────── */
    function initStatCounters() {
        qq('.stat-val[data-target]').forEach(el => {
            const target = parseFloat(el.dataset.target);
            if (isNaN(target)) return;
            let start = null;
            const dur = 1600;

            function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

            function step(ts) {
                if (!start) start = ts;
                const prog = Math.min((ts - start) / dur, 1);
                el.textContent = Math.round(easeOut(prog) * target);
                if (prog < 1) raf(step);
                else el.textContent = target;
            }

            setTimeout(() => raf(step), 700);
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       16.  RE-INIT tilt/reveal when results panel is shown
           (MutationObserver watching DOM changes)
    ────────────────────────────────────────────────────────────────────── */
    function initDynamicReinit() {
        const obs = new MutationObserver(() => {
            initTilt();
            // stagger any new finding-items
            qq('.finding-item:not([data-anim])').forEach((el, i) => {
                el.dataset.anim = '1';
                el.style.opacity = '0';
                el.style.transform = 'translateX(-16px)';
                setTimeout(() => {
                    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                    el.style.opacity = '1';
                    el.style.transform = 'none';
                }, i * 70);
            });
            // stagger new medicine-cards
            qq('.medicine-card:not([data-anim])').forEach((el, i) => {
                el.dataset.anim = '1';
                el.style.opacity = '0';
                el.style.transform = 'translateY(12px)';
                setTimeout(() => {
                    el.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
                    el.style.opacity = '1';
                    el.style.transform = 'none';
                }, i * 55);
            });
        });
        obs.observe(document.body, { childList: true, subtree: true });
    }

    /* ──────────────────────────────────────────────────────────────────────
       17.  FLOATING PARTICLES in hero area (subtle, medical-themed)
    ────────────────────────────────────────────────────────────────────── */
    function initHeroParticles() {
        const hero = q('.hero');
        if (!hero) return;
        const symbols = ['✚', '⊕', '◉', '⬡', '⬢', '+'];

        for (let i = 0; i < 8; i++) {
            const p = document.createElement('span');
            const sym = symbols[Math.floor(Math.random() * symbols.length)];
            p.textContent = sym;
            const size = 10 + Math.random() * 10;
            const startX = Math.random() * 100;
            const dur = 8 + Math.random() * 10;
            const delay = -Math.random() * dur;
            p.style.cssText = `
        position:absolute;
        left:${startX}%;bottom:-20px;
        font-size:${size}px;
        color:rgba(0,200,255,${0.08 + Math.random() * 0.1});
        pointer-events:none;user-select:none;
        animation:heroFloat ${dur}s ${delay}s linear infinite;
        z-index:0;
      `;
            hero.style.position = 'relative';
            hero.style.overflow = 'hidden';
            hero.appendChild(p);
        }

        if (!document.getElementById('heroFloatKf')) {
            const s = document.createElement('style');
            s.id = 'heroFloatKf';
            s.textContent = `
        @keyframes heroFloat {
          0%   { transform:translateY(0) rotate(0deg);   opacity:0; }
          10%  { opacity:1; }
          90%  { opacity:0.6; }
          100% { transform:translateY(-110vh) rotate(360deg); opacity:0; }
        }
      `;
            document.head.appendChild(s);
        }
    }

    /* ──────────────────────────────────────────────────────────────────────
       18.  BRAND CYBER-REVEAL (Scramble animation for Mediscan-AI)
    ────────────────────────────────────────────────────────────────────── */
    function initBrandReveal() {
        const brandEls = qq('#brandNameNav, #brandNameHero');
        const targetText = "Mediscan-AI";
        const chars = "ABCDEFGHIJKLM-NOPQRSTUVWXYZ0123456789$#@&";

        brandEls.forEach(el => {
            let iteration = 0;
            let interval = null;

            const startScramble = () => {
                clearInterval(interval);
                iteration = 0;
                interval = setInterval(() => {
                    el.innerText = targetText
                        .split("")
                        .map((letter, index) => {
                            if (index < iteration) return targetText[index];
                            return chars[Math.floor(Math.random() * chars.length)];
                        })
                        .join("");

                    if (iteration >= targetText.length) {
                        clearInterval(interval);
                        el.innerText = targetText;
                    }
                    iteration += 1 / 3;
                }, 30);
            };

            // Trigger on hover
            el.style.cursor = 'pointer';
            el.addEventListener('mouseenter', startScramble);

            // Initial reveal
            setTimeout(startScramble, 1200);
        });
    }

    /* ──────────────────────────────────────────────────────────────────────
       INIT — run all modules
    ────────────────────────────────────────────────────────────────────── */
    function init() {
        initAurora();
        initCinematicEntrance();
        initCursorTrail();
        initClickRipple();
        initGlitch();
        initNeonH1();
        initNavBorder();
        initHeroParticles();
        initTypedHero();
        initScannerLine();
        initStatCounters();
        initScanOptBurst();
        initMagneticButtons();
        initTilt();
        initScrollReveal();
        initDynamicReinit();
        initLoadingBarObserver();
        initBrandReveal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
