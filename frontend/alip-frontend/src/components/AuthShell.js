import React, { useEffect, useState } from 'react';
import './AuthShell.css';

const leafParticles = [
  { left: '8%', duration: '18s', delay: '0s', size: '1rem', icon: '\u{1F343}' },
  { left: '20%', duration: '14s', delay: '3s', size: '0.8rem', icon: '\u{1F33F}' },
  { left: '75%', duration: '20s', delay: '1s', size: '1.2rem', icon: '\u{1F343}' },
  { left: '88%', duration: '16s', delay: '5s', size: '0.9rem', icon: '\u{1F331}' },
  { left: '50%', duration: '22s', delay: '8s', size: '0.7rem', icon: '\u{1F343}' },
  { left: '35%', duration: '15s', delay: '11s', size: '1rem', icon: '\u{1F33F}' },
  { left: '62%', duration: '19s', delay: '4s', size: '0.85rem', icon: '\u{1F331}' }
];

export default function AuthShell({ mode, eyebrow, title, subtitle, children }) {
  const [introDone, setIntroDone] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const fadeTimer = setTimeout(() => setIntroDone(true), 3400);
    const showTimer = setTimeout(() => setVisible(true), 4100);

    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(showTimer);
    };
  }, []);

  return (
    <div className="auth-theme">
      {!visible && (
        <div className={`auth-intro ${introDone ? 'fade-out' : ''}`}>
          <div className="auth-intro-leaf">{'\u{1F33F}'}</div>
          <div className="auth-intro-wordmark">ALIP</div>
          <div className="auth-intro-sub">AgriLink Intelligence Platform</div>
          <div className="auth-intro-bar">
            <div className="auth-intro-bar-fill" />
          </div>
        </div>
      )}

      <div className={`auth-main ${visible ? 'visible' : ''}`}>
        <nav className="auth-nav">
          <div className="auth-nav-logo">
            <div className="auth-nav-logo-icon">{'\u{1F33F}'}</div>
            ALIP<span className="auth-dot">.</span>
          </div>
          <div className="auth-nav-pill">{mode === 'register' ? 'New Account' : 'Secure Access'}</div>
        </nav>

        <section className="auth-hero">
          <div className="auth-bg-layer">
            <div className="auth-bg-glow-1" />
            <div className="auth-bg-glow-2" />
            <div className="auth-bg-grid" />
          </div>

          {leafParticles.map((leaf, index) => (
            <div
              className="auth-leaf-particle"
              key={`${leaf.icon}-${index}`}
              style={{
                left: leaf.left,
                animationDuration: leaf.duration,
                animationDelay: leaf.delay,
                fontSize: leaf.size
              }}
            >
              {leaf.icon}
            </div>
          ))}

          <div className="auth-hero-content">
            <div className="auth-hero-eyebrow">
              <div className="auth-eyebrow-dot" />
              <span className="auth-eyebrow-text">{eyebrow}</span>
            </div>

            <h1 className="auth-hero-title">
              <span className="auth-title-alip">{title}</span>
              <span className="auth-title-sub-serif">{subtitle}</span>
            </h1>

            <div className="auth-card">
              {children}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
