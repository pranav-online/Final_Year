import React, { useRef, useEffect } from 'react';

const PARTICLE_COUNT = 70;
const NODE_COUNT = 14;

export default function AnimatedBackground({ diseaseDetected = false }) {
  const canvasRef = useRef(null);
  const rafRef = useRef(null);
  const mouseRef = useRef({ x: -9999, y: -9999 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let W, H;

    const resize = () => { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; };
    resize();
    window.addEventListener('resize', resize);

    /* ── Colors ─────────────────────────────────── */
    const C = diseaseDetected
      ? { p: [231,76,60], n: [192,57,43], pulse: [243,156,18] }
      : { p: [82,183,136], n: [45,106,79], pulse: [116,198,157] };

    /* ── Particles ──────────────────────────────── */
    const particles = Array.from({ length: PARTICLE_COUNT }, () => ({
      x: Math.random() * W, y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.25 - 0.08,
      r: Math.random() * 2 + 0.5, o: Math.random() * 0.25 + 0.05,
    }));

    /* ── Neural Nodes ───────────────────────────── */
    const nodes = Array.from({ length: NODE_COUNT }, () => ({
      x: Math.random() * W, y: H * 0.55 + Math.random() * H * 0.4,
      r: Math.random() * 3 + 2.5, phase: Math.random() * Math.PI * 2,
    }));

    /* ── Connections (nearest pairs) ────────────── */
    const conns = [];
    for (let i = 0; i < nodes.length; i++)
      for (let j = i + 1; j < nodes.length; j++) {
        const d = Math.hypot(nodes[i].x - nodes[j].x, nodes[i].y - nodes[j].y);
        if (d < 320) conns.push({ a: i, b: j });
      }

    /* ── Energy Pulses ──────────────────────────── */
    const pulses = [];

    /* ── Mouse ──────────────────────────────────── */
    const onMouse = (e) => { mouseRef.current = { x: e.clientX, y: e.clientY }; };
    window.addEventListener('mousemove', onMouse);

    /* ── Visibility ─────────────────────────────── */
    let visible = true;
    const onVis = () => { visible = !document.hidden; };
    document.addEventListener('visibilitychange', onVis);

    /* ── Loop ───────────────────────────────────── */
    let t = 0;
    const loop = () => {
      rafRef.current = requestAnimationFrame(loop);
      if (!visible) return;
      t += 0.016;
      const breath = Math.sin(t * 0.08) * 0.5 + 0.5;
      const mx = mouseRef.current.x, my = mouseRef.current.y;

      ctx.clearRect(0, 0, W, H);

      /* connections */
      for (const c of conns) {
        const a = nodes[c.a], b = nodes[c.b];
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = `rgba(${C.n},${0.04 + breath * 0.03})`;
        ctx.lineWidth = 0.7; ctx.stroke();
      }

      /* nodes */
      for (const nd of nodes) {
        const pulse = Math.sin(t * 1.2 + nd.phase) * 0.5 + 0.5;
        const sz = nd.r + pulse * 2.5;
        const op = 0.1 + pulse * 0.12 + breath * 0.04;

        const g = ctx.createRadialGradient(nd.x, nd.y, 0, nd.x, nd.y, sz * 4);
        g.addColorStop(0, `rgba(${C.n},${op})`);
        g.addColorStop(1, `rgba(${C.n},0)`);
        ctx.beginPath(); ctx.arc(nd.x, nd.y, sz * 4, 0, Math.PI * 2);
        ctx.fillStyle = g; ctx.fill();

        ctx.beginPath(); ctx.arc(nd.x, nd.y, sz, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${C.n},${op + 0.08})`; ctx.fill();

        /* mouse glow */
        const md = Math.hypot(mx - nd.x, my - nd.y);
        if (md < 160) {
          const mg = ctx.createRadialGradient(nd.x, nd.y, 0, nd.x, nd.y, sz * 6);
          mg.addColorStop(0, `rgba(${C.p},${0.25 * (1 - md / 160)})`);
          mg.addColorStop(1, `rgba(${C.p},0)`);
          ctx.beginPath(); ctx.arc(nd.x, nd.y, sz * 6, 0, Math.PI * 2);
          ctx.fillStyle = mg; ctx.fill();
        }
      }

      /* particles */
      for (const p of particles) {
        const dx = p.x - mx, dy = p.y - my;
        const md = Math.hypot(dx, dy);
        if (md < 100 && md > 0) { p.vx += (dx / md) * 0.015; p.vy += (dy / md) * 0.015; }

        p.x += p.vx; p.y += p.vy;
        if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
        if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
        p.vx *= 0.998; p.vy *= 0.998;

        ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${C.p},${p.o})`; ctx.fill();
      }

      /* spawn pulses */
      if (Math.random() < 0.008 && conns.length > 0)
        pulses.push({ ci: Math.floor(Math.random() * conns.length), prog: 0, spd: 0.004 + Math.random() * 0.008 });

      /* draw pulses */
      for (let i = pulses.length - 1; i >= 0; i--) {
        const pl = pulses[i]; pl.prog += pl.spd;
        if (pl.prog >= 1) { pulses.splice(i, 1); continue; }
        const a = nodes[conns[pl.ci].a], b = nodes[conns[pl.ci].b];
        const px = a.x + (b.x - a.x) * pl.prog;
        const py = a.y + (b.y - a.y) * pl.prog;
        const pg = ctx.createRadialGradient(px, py, 0, px, py, 7);
        pg.addColorStop(0, `rgba(${C.pulse},0.55)`);
        pg.addColorStop(1, `rgba(${C.pulse},0)`);
        ctx.beginPath(); ctx.arc(px, py, 7, 0, Math.PI * 2);
        ctx.fillStyle = pg; ctx.fill();
      }
    };

    rafRef.current = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener('resize', resize);
      window.removeEventListener('mousemove', onMouse);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [diseaseDetected]);

  /* ── Floating Leaves (CSS-driven) ────────────── */
  const leafStyle = (i) => ({
    position: 'absolute',
    width: 14 + i * 5, height: 8 + i * 3,
    background: diseaseDetected ? 'rgba(192,57,43,0.08)' : 'rgba(82,183,136,0.08)',
    borderRadius: '50% 0 50% 0',
    top: `${10 + i * 14}%`,
    left: `-30px`,
    opacity: 0.3 + (i % 3) * 0.1,
    animation: `leafDrift${i % 3} ${18 + i * 7}s linear infinite`,
    animationDelay: `${i * 4}s`,
    transform: `rotate(${i * 30}deg)`,
  });

  return (
    <>
      <canvas ref={canvasRef} style={{
        position: 'fixed', inset: 0, width: '100vw', height: '100vh',
        zIndex: 0, pointerEvents: 'none',
      }} />
      <div style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none', overflow: 'hidden' }}>
        {[0,1,2,3,4,5].map(i => <div key={i} style={leafStyle(i)} />)}
      </div>
      <style>{`
        @keyframes leafDrift0 { 0%{transform:translateX(-40px) rotate(0deg)} 100%{transform:translateX(${typeof window!=='undefined'?window.innerWidth+80:1400}px) rotate(360deg)} }
        @keyframes leafDrift1 { 0%{transform:translateX(-40px) rotate(15deg)} 100%{transform:translateX(${typeof window!=='undefined'?window.innerWidth+80:1400}px) rotate(-345deg)} }
        @keyframes leafDrift2 { 0%{transform:translateX(-40px) rotate(-20deg)} 100%{transform:translateX(${typeof window!=='undefined'?window.innerWidth+80:1400}px) rotate(340deg)} }
      `}</style>
    </>
  );
}
