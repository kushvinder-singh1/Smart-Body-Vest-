import { Link } from 'react-router-dom'
import logo from './logo.png'

export default function Landing() {
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

        .ld *, .ld *::before, .ld *::after { box-sizing: border-box; margin: 0; padding: 0; }

        .ld {
          --teal: #1D9E75;
          --teal-light: #5DCAA5;
          --teal-glow: rgba(29,158,117,0.18);
          --coral: #D85A30;
          --coral-light: #F0997B;
          --coral-glow: rgba(216,90,48,0.14);
          --night: #07100D;
          --surface: #111F1A;
          --surface2: #162219;
          --surface3: #1C2E26;
          --muted: #4B6B5E;
          --text: #E4EDE9;
          --text-dim: #8AABA0;
          --font-display: 'Syne', sans-serif;
          --font-body: 'DM Sans', sans-serif;
          background: var(--night);
          color: var(--text);
          font-family: var(--font-body);
          font-size: 17px;
          line-height: 1.65;
          overflow-x: hidden;
          min-height: 100dvh;
          position: relative;
        }

        .ld-noise {
          position: fixed; inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
          pointer-events: none; z-index: 0; opacity: 0.6;
        }

        .ld-grid {
          position: fixed; inset: 0;
          background-image:
            linear-gradient(rgba(29,158,117,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(29,158,117,0.04) 1px, transparent 1px);
          background-size: 48px 48px;
          pointer-events: none; z-index: 0;
        }

        .ld > * { position: relative; z-index: 1; }

        /* ── NAV ── */
        .ld-nav {
          position: fixed; top: 0; left: 0; right: 0; z-index: 100;
          display: flex; align-items: center; justify-content: space-between;
          padding: 18px 48px;
          background: rgba(7,16,13,0.72);
          backdrop-filter: blur(16px);
          border-bottom: 1px solid rgba(29,158,117,0.12);
        }
        .ld-logo {
          font-family: var(--font-display);
          font-size: 1.5rem; font-weight: 800;
          color: var(--teal-light); letter-spacing: -0.5px; text-decoration: none;
        }
        .ld-nav-links { display: flex; gap: 32px; list-style: none; }
        .ld-nav-links a {
          color: var(--text-dim); text-decoration: none;
          font-size: 0.9rem; font-weight: 400; transition: color 0.2s;
        }
        .ld-nav-links a:hover { color: var(--teal-light); }
        .ld-nav-auth { display: flex; align-items: center; gap: 10px; }
        .ld-btn-signin {
          background: transparent; color: var(--text-dim);
          border: 1px solid rgba(255,255,255,0.15);
          padding: 8px 20px; border-radius: 100px;
          font-family: var(--font-body); font-size: 0.88rem; font-weight: 400;
          cursor: pointer; text-decoration: none; transition: border-color 0.2s, color 0.2s;
        }
        .ld-btn-signin:hover { border-color: var(--teal); color: var(--teal-light); }
        .ld-btn-register {
          background: var(--teal); color: #fff; border: none;
          padding: 9px 22px; border-radius: 100px;
          font-family: var(--font-body); font-size: 0.88rem; font-weight: 500;
          cursor: pointer; text-decoration: none; transition: background 0.2s, transform 0.15s;
        }
        .ld-btn-register:hover { background: var(--teal-light); transform: translateY(-1px); }

        /* ── HERO ── */
        .ld-hero {
          min-height: 100dvh;
          display: grid; grid-template-columns: 1fr 1fr;
          align-items: center; padding: 120px 48px 80px;
          position: relative; overflow: hidden;
        }
        .ld-hero-glow {
          position: absolute; width: 720px; height: 720px;
          background: radial-gradient(circle, rgba(29,158,117,0.15) 0%, transparent 70%);
          right: -80px; top: 50%; transform: translateY(-50%);
          pointer-events: none; border-radius: 50%;
        }
        .ld-hero-glow2 {
          position: absolute; width: 400px; height: 400px;
          background: radial-gradient(circle, rgba(216,90,48,0.1) 0%, transparent 70%);
          left: 10%; bottom: 5%; pointer-events: none; border-radius: 50%;
        }
        .ld-hero-text { max-width: 560px; }
        .ld-eyebrow {
          display: inline-flex; align-items: center; gap: 8px;
          background: var(--teal-glow); border: 1px solid rgba(29,158,117,0.3);
          color: var(--teal-light); font-size: 0.78rem; font-weight: 500;
          letter-spacing: 0.1em; text-transform: uppercase;
          padding: 5px 14px; border-radius: 100px; margin-bottom: 28px;
        }
        .ld-eyebrow::before {
          content: ''; width: 6px; height: 6px; border-radius: 50%;
          background: var(--teal-light); animation: ld-pulse 2s ease-in-out infinite;
        }
        @keyframes ld-pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(0.7); }
        }
        .ld-hero-title {
          font-family: var(--font-display);
          font-size: clamp(3rem, 5vw, 5rem); font-weight: 800;
          line-height: 1.0; letter-spacing: -2px; margin-bottom: 24px; color: #fff;
        }
        .ld-hero-title .ac1 { color: var(--teal-light); }
        .ld-hero-title .ac2 { color: var(--coral-light); }
        .ld-hero-sub {
          font-size: 1.1rem; color: var(--text-dim); line-height: 1.7;
          font-weight: 300; max-width: 440px;
        }

        /* ── MOCKUP ── */
        .ld-visual { display: flex; justify-content: center; align-items: center; padding-left: 40px; }
        .ld-mockup-wrap { position: relative; width: 100%; max-width: 480px; }
        .ld-mockup-card {
          background: var(--surface);
          border: 1px solid rgba(29,158,117,0.18); border-radius: 20px; padding: 28px;
          box-shadow: 0 40px 100px rgba(0,0,0,0.5), 0 0 0 1px rgba(29,158,117,0.06);
          position: relative; overflow: hidden;
        }
        .ld-mockup-card::before {
          content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(93,202,165,0.5), transparent);
        }
        .ld-mockup-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
        .ld-mockup-logo { font-family: var(--font-display); font-size: 1.1rem; font-weight: 700; color: var(--teal-light); }
        .ld-mockup-status {
          display: flex; align-items: center; gap: 6px; font-size: 0.75rem;
          color: var(--teal-light); background: var(--teal-glow);
          border: 1px solid rgba(29,158,117,0.2); padding: 4px 10px; border-radius: 100px;
        }
        .ld-status-dot {
          width: 6px; height: 6px; border-radius: 50%; background: var(--teal-light);
          animation: ld-pulse 1.5s ease-in-out infinite;
        }
        .ld-metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 20px; }
        .ld-metric-box {
          background: var(--surface2); border: 1px solid rgba(255,255,255,0.05);
          border-radius: 12px; padding: 14px 12px; text-align: center;
        }
        .ld-metric-label {
          font-size: 0.68rem; color: var(--text-dim);
          text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px;
        }
        .ld-metric-value { font-family: var(--font-display); font-size: 1.3rem; font-weight: 700; color: #fff; }
        .ld-metric-value.coral { color: var(--coral-light); }
        .ld-metric-value.teal  { color: var(--teal-light); }
        .ld-metric-value.violet { color: #c4b5fd; }
        .ld-comfort {
          background: var(--surface2); border: 1px solid rgba(29,158,117,0.15);
          border-radius: 12px; padding: 14px 16px;
          display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;
        }
        .ld-comfort-label { font-size: 0.75rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 2px; }
        .ld-comfort-status { font-size: 0.9rem; font-weight: 500; color: var(--teal-light); }
        .ld-comfort-badge {
          font-size: 0.72rem; background: var(--teal-glow);
          border: 1px solid rgba(29,158,117,0.25); color: var(--teal-light);
          padding: 4px 10px; border-radius: 100px; white-space: nowrap;
        }
        .ld-pads { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        .ld-pad-card {
          background: var(--surface2); border: 1px solid rgba(255,255,255,0.05);
          border-radius: 12px; padding: 14px 12px;
        }
        .ld-pad-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-dim); margin-bottom: 10px; }
        .ld-pad-track { height: 6px; background: rgba(255,255,255,0.07); border-radius: 3px; overflow: hidden; margin-bottom: 6px; }
        .ld-pad-fill { height: 100%; border-radius: 3px; animation: ld-heat 3s ease-in-out infinite; }
        .ld-pad-fill.teal  { background: linear-gradient(90deg, #1D9E75, #5DCAA5); width: 66%; }
        .ld-pad-fill.coral { background: linear-gradient(90deg, #D85A30, #F0997B); width: 33%; }
        @keyframes ld-heat { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .ld-pad-level { font-size: 0.82rem; font-weight: 500; color: var(--text); }
        .ld-badge-float {
          position: absolute; background: var(--surface3);
          border: 1px solid rgba(29,158,117,0.25); border-radius: 12px;
          padding: 10px 14px; font-size: 0.78rem; color: var(--text-dim);
          white-space: nowrap; box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }
        .ld-badge-float strong { color: var(--teal-light); display: block; font-weight: 600; font-size: 0.9rem; }
        .ld-badge-float.left  { left: -70px; top: 30%; }
        .ld-badge-float.btm   { right: -50px; bottom: 20%; }

        /* ── STATS ── */
        .ld-stats {
          border-top: 1px solid rgba(29,158,117,0.1);
          border-bottom: 1px solid rgba(29,158,117,0.1);
          padding: 40px 48px;
          display: grid; grid-template-columns: repeat(4, 1fr);
        }
        .ld-stat { text-align: center; padding: 0 20px; border-right: 1px solid rgba(29,158,117,0.1); }
        .ld-stat:last-child { border-right: none; }
        .ld-stat-num {
          font-family: var(--font-display); font-size: 2.4rem; font-weight: 800;
          color: var(--teal-light); letter-spacing: -1px; line-height: 1; margin-bottom: 4px;
        }
        .ld-stat-label { font-size: 0.85rem; color: var(--text-dim); font-weight: 300; }

        /* ── FEATURES ── */
        .ld-features { padding: 100px 48px; }
        .ld-eyebrow-center { text-align: center; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.12em; color: var(--teal-light); font-weight: 500; margin-bottom: 16px; }
        .ld-section-title {
          font-family: var(--font-display); font-size: clamp(2rem, 3.5vw, 3rem);
          font-weight: 800; color: #fff; text-align: center; letter-spacing: -1px;
          line-height: 1.1; margin-bottom: 16px;
        }
        .ld-section-sub {
          text-align: center; color: var(--text-dim); font-size: 1.05rem;
          font-weight: 300; max-width: 520px; margin: 0 auto 64px; line-height: 1.7;
        }
        .ld-features-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; max-width: 1100px; margin: 0 auto; }
        .ld-feature-card {
          background: var(--surface); border: 1px solid rgba(255,255,255,0.06);
          border-radius: 20px; padding: 32px 28px;
          transition: border-color 0.25s, transform 0.2s; position: relative; overflow: hidden;
        }
        .ld-feature-card::before {
          content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(93,202,165,0.25), transparent);
          opacity: 0; transition: opacity 0.3s;
        }
        .ld-feature-card:hover { border-color: rgba(29,158,117,0.3); transform: translateY(-4px); }
        .ld-feature-card:hover::before { opacity: 1; }
        .ld-feature-icon {
          width: 48px; height: 48px; border-radius: 12px;
          display: flex; align-items: center; justify-content: center;
          margin-bottom: 20px; font-size: 22px;
        }
        .ld-feature-icon.teal   { background: var(--teal-glow); border: 1px solid rgba(29,158,117,0.25); }
        .ld-feature-icon.coral  { background: var(--coral-glow); border: 1px solid rgba(216,90,48,0.25); }
        .ld-feature-icon.violet { background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.2); }
        .ld-feature-name { font-family: var(--font-display); font-size: 1.15rem; font-weight: 700; color: #fff; margin-bottom: 10px; letter-spacing: -0.3px; }
        .ld-feature-desc { color: var(--text-dim); font-size: 0.92rem; line-height: 1.65; font-weight: 300; }

        /* ── HOW ── */
        .ld-how {
          padding: 80px 48px 100px;
          background: linear-gradient(180deg, transparent, rgba(14,26,22,0.5), transparent);
        }
        .ld-how-steps {
          display: grid; grid-template-columns: repeat(4, 1fr);
          max-width: 1000px; margin: 0 auto; position: relative;
        }
        .ld-how-steps::before {
          content: ''; position: absolute; top: 28px; left: 12.5%; right: 12.5%; height: 1px;
          background: linear-gradient(90deg, transparent, rgba(29,158,117,0.3), rgba(29,158,117,0.3), transparent);
        }
        .ld-step { text-align: center; padding: 0 16px; }
        .ld-step-num {
          width: 56px; height: 56px; border-radius: 50%;
          background: var(--surface2); border: 1px solid rgba(29,158,117,0.3);
          display: flex; align-items: center; justify-content: center;
          margin: 0 auto 20px;
          font-family: var(--font-display); font-size: 1.1rem; font-weight: 800;
          color: var(--teal-light); position: relative; z-index: 1; transition: background 0.2s, border-color 0.2s;
        }
        .ld-step:hover .ld-step-num { background: var(--teal-glow); border-color: var(--teal-light); }
        .ld-step-title { font-family: var(--font-display); font-size: 1rem; font-weight: 700; color: #fff; margin-bottom: 8px; }
        .ld-step-desc { font-size: 0.85rem; color: var(--text-dim); font-weight: 300; line-height: 1.6; }

        /* ── SAFETY ── */
        .ld-safety { padding: 80px 48px; }
        .ld-safety-inner { max-width: 1100px; margin: 0 auto; display: grid; grid-template-columns: 1fr 1fr; gap: 60px; align-items: center; }
        .ld-safety-visual {
          background: var(--surface); border: 1px solid rgba(29,158,117,0.15);
          border-radius: 20px; padding: 32px; position: relative; overflow: hidden;
        }
        .ld-safety-visual::before {
          content: ''; position: absolute; inset: 0;
          background: radial-gradient(circle at 30% 70%, rgba(29,158,117,0.08), transparent 60%);
          pointer-events: none;
        }
        .ld-safety-rule {
          display: flex; align-items: flex-start; gap: 14px;
          padding: 14px 0; border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .ld-safety-rule:last-child { border-bottom: none; }
        .ld-rule-icon {
          width: 36px; height: 36px; border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          font-size: 16px; flex-shrink: 0; margin-top: 2px;
        }
        .ld-rule-icon.ok   { background: rgba(29,158,117,0.15); }
        .ld-rule-icon.warn { background: rgba(216,90,48,0.12); }
        .ld-rule-title { font-size: 0.9rem; font-weight: 500; color: var(--text); margin-bottom: 2px; }
        .ld-rule-desc  { font-size: 0.8rem; color: var(--text-dim); font-weight: 300; line-height: 1.5; }
        .ld-safety-text h2 {
          font-family: var(--font-display); font-size: clamp(1.8rem, 2.5vw, 2.5rem);
          font-weight: 800; color: #fff; letter-spacing: -1px; line-height: 1.1; margin-bottom: 20px;
        }
        .ld-safety-text p { color: var(--text-dim); font-weight: 300; font-size: 1rem; line-height: 1.75; margin-bottom: 16px; }

        /* ── CTA ── */
        .ld-cta { padding: 80px 48px 100px; text-align: center; position: relative; }
        .ld-cta-glow {
          position: absolute; width: 600px; height: 300px;
          background: radial-gradient(ellipse, rgba(29,158,117,0.12) 0%, transparent 70%);
          left: 50%; top: 50%; transform: translate(-50%, -50%); pointer-events: none;
        }
        .ld-cta-inner { position: relative; z-index: 1; }
        .ld-cta-title {
          font-family: var(--font-display); font-size: clamp(2.2rem, 4vw, 3.8rem);
          font-weight: 800; color: #fff; letter-spacing: -1.5px; line-height: 1.05; margin-bottom: 20px;
        }
        .ld-cta-sub { color: var(--text-dim); font-size: 1.05rem; font-weight: 300; margin-bottom: 40px; max-width: 420px; margin-left: auto; margin-right: auto; }
        .ld-cta-actions { display: flex; align-items: center; justify-content: center; gap: 20px; }
        .ld-btn-large {
          background: var(--teal); color: #fff; border: none;
          padding: 18px 40px; border-radius: 100px;
          font-family: var(--font-body); font-size: 1.05rem; font-weight: 500;
          cursor: pointer; text-decoration: none; transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
        }
        .ld-btn-large:hover { background: var(--teal-light); transform: translateY(-2px); box-shadow: 0 20px 60px rgba(29,158,117,0.4); }
        .ld-btn-outline-large {
          background: transparent; color: var(--text-dim);
          border: 1px solid rgba(255,255,255,0.15);
          padding: 18px 40px; border-radius: 100px;
          font-family: var(--font-body); font-size: 1.05rem; font-weight: 400;
          cursor: pointer; text-decoration: none; transition: border-color 0.2s, color 0.2s, transform 0.15s;
        }
        .ld-btn-outline-large:hover { border-color: var(--teal); color: var(--teal-light); transform: translateY(-2px); }

        /* ── FOOTER ── */
        .ld-footer {
          border-top: 1px solid rgba(29,158,117,0.1); padding: 32px 48px;
          display: flex; align-items: center; justify-content: space-between;
        }
        .ld-footer-logo { font-family: var(--font-display); font-size: 1.1rem; font-weight: 800; color: var(--teal-light); text-decoration: none; }
        .ld-footer-copy { font-size: 0.82rem; color: var(--muted); }

        /* ── ANIMATIONS ── */
        @keyframes ld-fadeUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
        .ld-anim { opacity: 0; animation: ld-fadeUp 0.65s ease forwards; }
        .ld-d1 { animation-delay: 0.1s; } .ld-d2 { animation-delay: 0.25s; }
        .ld-d3 { animation-delay: 0.4s; } .ld-d4 { animation-delay: 0.55s; }

        /* ── RESPONSIVE ── */
        @media (max-width: 900px) {
          .ld-nav { padding: 16px 24px; }
          .ld-nav-links { display: none; }
          .ld-hero { grid-template-columns: 1fr; padding: 100px 24px 60px; gap: 48px; }
          .ld-visual { padding-left: 0; }
          .ld-badge-float { display: none; }
          .ld-stats { grid-template-columns: repeat(2, 1fr); gap: 24px 0; padding: 40px 24px; }
          .ld-stat:nth-child(2) { border-right: none; }
          .ld-features { padding: 60px 24px; }
          .ld-features-grid { grid-template-columns: 1fr; }
          .ld-how { padding: 60px 24px; }
          .ld-how-steps { grid-template-columns: repeat(2, 1fr); gap: 40px; }
          .ld-how-steps::before { display: none; }
          .ld-safety { padding: 60px 24px; }
          .ld-safety-inner { grid-template-columns: 1fr; gap: 40px; }
          .ld-cta { padding: 60px 24px 80px; }
          .ld-cta-actions { flex-direction: column; }
          .ld-footer { flex-direction: column; gap: 12px; text-align: center; padding: 24px; }
        }
      `}</style>

      <div className="ld">
        <div className="ld-noise" />
        <div className="ld-grid" />

        {/* NAV */}
        <nav className="ld-nav">
          <span className="ld-logo" style={{display:"flex",alignItems:"center",gap:"10px"}}>
          <img src={logo} alt="HeatSync" style={{height:"36px",width:"36px",objectFit:"contain"}} />
          HeatSync
        </span>
          <ul className="ld-nav-links">
            <li><a href="#features">Features</a></li>
            <li><a href="#how">How it works</a></li>
            <li><a href="#safety">Safety</a></li>
          </ul>
          <div className="ld-nav-auth">
            <Link to="/auth?mode=login" className="ld-btn-signin">Sign in</Link>
            <Link to="/auth?mode=register" className="ld-btn-register">Register</Link>
          </div>
        </nav>

        {/* HERO */}
        <section className="ld-hero">
          <div className="ld-hero-glow" />
          <div className="ld-hero-glow2" />
          <div className="ld-hero-text">
            <div className="ld-eyebrow ld-anim ld-d1">Adaptive heating intelligence</div>
            <h1 className="ld-hero-title ld-anim ld-d2">
              Your body.<br />
              <span className="ac1">Always warm.</span><br />
              <span className="ac2">Always safe.</span>
            </h1>
            <p className="ld-hero-sub ld-anim ld-d3">
              HeatSync is a smart heated vest that reads your biometrics in real time — automatically adjusting warmth based on your body temperature, heart rate, and movement.
            </p>
          </div>
          <div className="ld-visual ld-anim ld-d3">
            <div className="ld-mockup-wrap">
              <div className="ld-badge-float left"><strong>36.4°C</strong>Body temp nominal</div>
              <div className="ld-badge-float btm"><strong>72 bpm</strong>Heart rate stable</div>
              <div className="ld-mockup-card">
                <div className="ld-mockup-header">
                  <div className="ld-mockup-logo" style={{display:"flex",alignItems:"center",gap:"7px"}}>
                  <img src={logo} alt="HeatSync" style={{height:"22px",width:"22px",objectFit:"contain"}} />
                  HeatSync
                </div>
                  <div className="ld-mockup-status"><div className="ld-status-dot" />Cloud connected</div>
                </div>
                <div className="ld-metrics">
                  <div className="ld-metric-box"><div className="ld-metric-label">Temp</div><div className="ld-metric-value coral">36.4°</div></div>
                  <div className="ld-metric-box"><div className="ld-metric-label">Pulse</div><div className="ld-metric-value teal">72 bpm</div></div>
                  <div className="ld-metric-box"><div className="ld-metric-label">Motion</div><div className="ld-metric-value violet">Active</div></div>
                </div>
                <div className="ld-comfort">
                  <div><div className="ld-comfort-label">Comfort status</div><div className="ld-comfort-status">Comfortable</div></div>
                  <div className="ld-comfort-badge">T 36.4° · HR 72 bpm</div>
                </div>
                <div style={{fontSize:'0.72rem',textTransform:'uppercase',letterSpacing:'0.06em',color:'var(--text-dim)',marginBottom:'10px'}}>Heating Control</div>
                <div className="ld-pads">
                  <div className="ld-pad-card"><div className="ld-pad-title">Pad 1</div><div className="ld-pad-track"><div className="ld-pad-fill teal" /></div><div className="ld-pad-level">Medium</div></div>
                  <div className="ld-pad-card"><div className="ld-pad-title">Pad 2</div><div className="ld-pad-track"><div className="ld-pad-fill coral" /></div><div className="ld-pad-level">Low</div></div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STATS */}
        <div className="ld-stats">
          <div className="ld-stat"><div className="ld-stat-num">±0.1°</div><div className="ld-stat-label">Temperature precision</div></div>
          <div className="ld-stat"><div className="ld-stat-num">&lt;2s</div><div className="ld-stat-label">Sensor response time</div></div>
          <div className="ld-stat"><div className="ld-stat-num">4</div><div className="ld-stat-label">Adaptive heat levels</div></div>
          <div className="ld-stat"><div className="ld-stat-num">24/7</div><div className="ld-stat-label">Real-time monitoring</div></div>
        </div>

        {/* FEATURES */}
        <section className="ld-features" id="features">
          <p className="ld-eyebrow-center">What makes it different</p>
          <h2 className="ld-section-title">Built around your biology</h2>
          <p className="ld-section-sub">Most heated vests have a dial. HeatSync has a brain — one that reads your body and responds instantly.</p>
          <div className="ld-features-grid">
            {[
              { icon: '🌡️', cls: 'teal',   name: 'Live body temperature',    desc: 'Continuous core temperature sensing — not ambient air. The vest responds to you, not the weather around you.' },
              { icon: '❤️', cls: 'coral',  name: 'Heart rate awareness',      desc: 'Pulse is tracked every second. If your heart rate spikes, heating automatically steps down to keep you safe.' },
              { icon: '⚡', cls: 'violet', name: 'Motion-adaptive logic',     desc: 'Moving actively generates heat. HeatSync detects motion and scales output accordingly — no unnecessary warmth.' },
              { icon: '🔒', cls: 'teal',   name: 'Multi-layer safety system', desc: 'Hard cutoffs at thermal thresholds. Automatic heating shutdown if temperature exceeds safe limits.' },
              { icon: '📡', cls: 'coral',  name: 'Cloud-synced dashboard',    desc: 'Every metric streams to your real-time dashboard. History, trends, and safety alerts — all in one place.' },
              { icon: '🔋', cls: 'violet', name: 'Idle detection',            desc: 'Pads auto-idle after 10 minutes of inactivity, preserving battery and signalling via dashboard that the vest isn\'t being worn.' },
            ].map(f => (
              <div className="ld-feature-card" key={f.name}>
                <div className={`ld-feature-icon ${f.cls}`}>{f.icon}</div>
                <div className="ld-feature-name">{f.name}</div>
                <p className="ld-feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* HOW IT WORKS */}
        <section className="ld-how" id="how">
          <p className="ld-eyebrow-center">How it works</p>
          <h2 className="ld-section-title">Smart warmth in four steps</h2>
          <p className="ld-section-sub">From skin sensor to heating pad — the loop closes in under two seconds.</p>
          <div className="ld-how-steps">
            {[
              { n: '01', title: 'Sense',   desc: 'Sensors read your body temperature, pulse, and motion continuously.' },
              { n: '02', title: 'Analyse', desc: 'The model evaluates your biometrics and current heating state in real time.' },
              { n: '03', title: 'Decide',  desc: 'A heat level — off, low, medium, or high — is computed with safety overrides applied.' },
              { n: '04', title: 'Respond', desc: 'The command reaches the vest pads in under two seconds. Your dashboard updates live.' },
            ].map(s => (
              <div className="ld-step" key={s.n}>
                <div className="ld-step-num">{s.n}</div>
                <div className="ld-step-title">{s.title}</div>
                <p className="ld-step-desc">{s.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* SAFETY */}
        <section className="ld-safety" id="safety">
          <div className="ld-safety-inner">
            <div className="ld-safety-visual">
              <div style={{fontFamily:'var(--font-display)',fontSize:'1.05rem',fontWeight:700,color:'#fff',marginBottom:'20px',letterSpacing:'-0.3px'}}>Safety rules — always enforced</div>
              {[
                { cls: 'ok',   icon: '✅', title: 'Heating shuts off above 39°C',   desc: 'If body temperature exceeds the upper safe limit, all pads are immediately disabled.' },
                { cls: 'warn', icon: '⚠️', title: 'Heating shuts off below 35°C',   desc: 'A reading below the lower threshold indicates the vest may not be worn — pads disable safely.' },
                { cls: 'warn', icon: '❤️‍🔥', title: 'High pulse reduces heat level', desc: 'If heart rate exceeds 120 bpm, heating steps down one level to prevent overheating during exertion.' },
                { cls: 'ok',   icon: '🔋', title: '10-minute idle auto-shutoff',    desc: 'Pads off for 10 minutes? The vest marks itself idle — you\'re warned at 9 minutes, with full monitoring continuing.' },
              ].map(r => (
                <div className="ld-safety-rule" key={r.title}>
                  <div className={`ld-rule-icon ${r.cls}`}>{r.icon}</div>
                  <div><div className="ld-rule-title">{r.title}</div><p className="ld-rule-desc">{r.desc}</p></div>
                </div>
              ))}
            </div>
            <div className="ld-safety-text">
              <h2>Safety isn't a feature.<br />It's the foundation.</h2>
              <p>HeatSync is built around the principle that warmth should never come at the cost of wellbeing. Every heating decision passes through a safety layer before reaching the pads.</p>
              <p>Temperature bounds, heart rate monitoring, motion context, and idle detection all work in parallel — so the vest never does something your body isn't ready for.</p>
              <p>Every safety override is visible in your dashboard in real time. No black boxes.</p>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="ld-cta" id="cta">
          <div className="ld-cta-glow" />
          <div className="ld-cta-inner">
            <h2 className="ld-cta-title">Stay warm.<br />Stay in control.</h2>
            <p className="ld-cta-sub">Create an account to get started, or sign in to your dashboard.</p>
            <div className="ld-cta-actions">
              <Link to="/auth?mode=register" className="ld-btn-large">Register</Link>
              <Link to="/auth?mode=login" className="ld-btn-outline-large">Sign in</Link>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="ld-footer">
          <span className="ld-footer-logo">HeatSync</span>
          <p className="ld-footer-copy">© 2026 HeatSync. All rights reserved.</p>
        </footer>
      </div>
    </>
  )
}