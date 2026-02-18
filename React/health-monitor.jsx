import { useState, useEffect, useRef } from "react";

const COLORS = {
  bg: "#0a0e1a",
  panel: "#0f1629",
  border: "#1e2d4a",
  accent1: "#00d4ff",
  accent2: "#ff4d6d",
  accent3: "#39ff14",
  accent4: "#ffb700",
  text: "#c8d8f0",
  muted: "#4a6080",
};

function useAnimatedValue(target, speed = 0.05) {
  const [value, setValue] = useState(target);
  const ref = useRef(target);
  useEffect(() => {
    let raf;
    const animate = () => {
      ref.current += (target - ref.current) * speed;
      setValue(parseFloat(ref.current.toFixed(2)));
      if (Math.abs(ref.current - target) > 0.01) raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [target]);
  return value;
}

function RadialGauge({ value, min, max, label, unit, color, size = 160 }) {
  const pct = (value - min) / (max - min);
  const angle = pct * 240 - 120;
  const r = size / 2 - 18;
  const cx = size / 2;
  const cy = size / 2;

  const polarToXY = (angleDeg, radius) => {
    const rad = ((angleDeg - 90) * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };

  const arcPath = (startAngle, endAngle, radius) => {
    const start = polarToXY(startAngle, radius);
    const end = polarToXY(endAngle, radius);
    const large = endAngle - startAngle > 180 ? 1 : 0;
    return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${large} 1 ${end.x} ${end.y}`;
  };

  const needle = polarToXY(angle, r - 10);

  return (
    <svg width={size} height={size} style={{ overflow: "visible" }}>
      {/* Track */}
      <path
        d={arcPath(-120 + 90, 120 + 90, r)}
        fill="none"
        stroke={COLORS.border}
        strokeWidth="8"
        strokeLinecap="round"
      />
      {/* Value arc */}
      <path
        d={arcPath(-120 + 90, angle + 90, r)}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeLinecap="round"
        style={{ filter: `drop-shadow(0 0 6px ${color})` }}
      />
      {/* Center circle */}
      <circle cx={cx} cy={cy} r="6" fill={color} style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
      {/* Needle */}
      <line x1={cx} y1={cy} x2={needle.x} y2={needle.y} stroke={color} strokeWidth="2" strokeLinecap="round" />
      {/* Value text */}
      <text x={cx} y={cy - 24} textAnchor="middle" fill={color} fontSize="22" fontFamily="'Courier New', monospace" fontWeight="bold">
        {typeof value === "number" ? value.toFixed(1) : value}
      </text>
      <text x={cx} y={cy - 8} textAnchor="middle" fill={COLORS.muted} fontSize="10" fontFamily="'Courier New', monospace">
        {unit}
      </text>
      <text x={cx} y={cy + 48} textAnchor="middle" fill={COLORS.text} fontSize="11" fontFamily="'Courier New', monospace" letterSpacing="2">
        {label}
      </text>
    </svg>
  );
}

function PulseWave({ color, bpm }) {
  const [offset, setOffset] = useState(0);
  const pathRef = useRef(null);
  useEffect(() => {
    let raf;
    let t = 0;
    const speed = bpm / 1200;
    const animate = () => {
      t += speed;
      setOffset(t % 1);
      raf = requestAnimationFrame(animate);
    };
    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [bpm]);

  const w = 300, h = 60;
  const generateECG = (phase) => {
    const points = [];
    for (let i = 0; i <= 100; i++) {
      const x = (i / 100) * w;
      const t = (i / 100 + phase) % 1;
      let y = h / 2;
      // Simulate ECG shape
      const p = (t % 1);
      if (p < 0.1) y = h / 2 + 5 * Math.sin(p * 10 * Math.PI);
      else if (p < 0.15) y = h / 2 - 25 * Math.sin((p - 0.1) * 20 * Math.PI);
      else if (p < 0.2) y = h / 2 + 10 * Math.sin((p - 0.15) * 20 * Math.PI);
      else y = h / 2 + 3 * Math.sin((p - 0.2) * 5 * Math.PI) * Math.exp(-(p - 0.2) * 10);
      points.push(`${i === 0 ? "M" : "L"} ${x} ${y}`);
    }
    return points.join(" ");
  };

  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <defs>
        <linearGradient id="fadeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={color} stopOpacity="0" />
          <stop offset="30%" stopColor={color} stopOpacity="1" />
          <stop offset="100%" stopColor={color} stopOpacity="1" />
        </linearGradient>
      </defs>
      <path d={generateECG(offset)} fill="none" stroke={`url(#fadeGrad)`} strokeWidth="2"
        style={{ filter: `drop-shadow(0 0 4px ${color})` }} />
    </svg>
  );
}

function MotionVisual({ active }) {
  const [dots, setDots] = useState([]);
  useEffect(() => {
    if (!active) { setDots([]); return; }
    const interval = setInterval(() => {
      setDots(prev => {
        const newDot = { id: Date.now(), x: 30 + Math.random() * 140, y: 20 + Math.random() * 60, life: 1 };
        return [...prev.filter(d => d.life > 0.1).map(d => ({ ...d, life: d.life - 0.15 })), newDot];
      });
    }, 80);
    return () => clearInterval(interval);
  }, [active]);

  return (
    <div style={{ position: "relative", width: 200, height: 100, margin: "0 auto" }}>
      <svg width="200" height="100" style={{ position: "absolute", inset: 0 }}>
        {/* Human silhouette */}
        <ellipse cx="100" cy="20" rx="12" ry="14" fill="none" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        <line x1="100" y1="34" x2="100" y2="72" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        <line x1="100" y1="45" x2="75" y2="62" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        <line x1="100" y1="45" x2="125" y2="62" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        <line x1="100" y1="72" x2="82" y2="96" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        <line x1="100" y1="72" x2="118" y2="96" stroke={active ? COLORS.accent3 : COLORS.muted} strokeWidth="2" />
        {active && dots.map(d => (
          <circle key={d.id} cx={d.x} cy={d.y} r="3" fill={COLORS.accent3} opacity={d.life}
            style={{ filter: "drop-shadow(0 0 4px #39ff14)" }} />
        ))}
      </svg>
    </div>
  );
}

function BatteryBar({ level }) {
  const color = level > 50 ? COLORS.accent3 : level > 20 ? COLORS.accent4 : COLORS.accent2;
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
      <div style={{ position: "relative", width: 60, height: 120, border: `2px solid ${color}`, borderRadius: 8, background: "#0a0e1a", boxShadow: `0 0 10px ${color}40` }}>
        {/* Battery tip */}
        <div style={{ position: "absolute", top: -8, left: "50%", transform: "translateX(-50%)", width: 20, height: 8, background: color, borderRadius: "3px 3px 0 0" }} />
        {/* Fill */}
        <div style={{
          position: "absolute", bottom: 2, left: 2, right: 2,
          height: `${level}%`,
          background: `linear-gradient(to top, ${color}, ${color}99)`,
          borderRadius: 6,
          transition: "height 0.5s ease",
          boxShadow: `0 0 8px ${color}`,
        }} />
        {/* Percentage text */}
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: 13, fontFamily: "'Courier New', monospace", fontWeight: "bold", zIndex: 1 }}>
          {level}%
        </div>
      </div>
      <span style={{ color, fontSize: 10, fontFamily: "'Courier New', monospace", letterSpacing: 2 }}>BATTERY</span>
    </div>
  );
}

function Panel({ children, title, accent, style = {} }) {
  return (
    <div style={{
      background: COLORS.panel,
      border: `1px solid ${accent}40`,
      borderRadius: 16,
      padding: 24,
      boxShadow: `0 0 20px ${accent}15, inset 0 0 30px #00000030`,
      position: "relative",
      overflow: "hidden",
      ...style,
    }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 2,
        background: `linear-gradient(90deg, transparent, ${accent}, transparent)`,
      }} />
      {title && (
        <div style={{ color: accent, fontSize: 10, letterSpacing: 3, fontFamily: "'Courier New', monospace", marginBottom: 16, textTransform: "uppercase" }}>
          ◈ {title}
        </div>
      )}
      {children}
    </div>
  );
}

function StatusDot({ active, color }) {
  return (
    <span style={{
      display: "inline-block", width: 8, height: 8, borderRadius: "50%",
      background: active ? color : COLORS.muted,
      boxShadow: active ? `0 0 6px ${color}` : "none",
      marginRight: 6,
      animation: active ? "pulse 1.5s ease-in-out infinite" : "none",
    }} />
  );
}

export default function HealthMonitor() {
  // Simulated sensor values
  const [rawTemp, setRawTemp] = useState(36.8);
  const [rawPulse, setRawPulse] = useState(72);
  const [motionActive, setMotionActive] = useState(false);
  const [battery, setBattery] = useState(78);
  const [time, setTime] = useState(new Date());

  const temp = useAnimatedValue(rawTemp, 0.03);
  const pulse = useAnimatedValue(rawPulse, 0.04);

  // Simulate sensor fluctuations
  useEffect(() => {
    const interval = setInterval(() => {
      setRawTemp(prev => Math.min(38.5, Math.max(35.5, prev + (Math.random() - 0.5) * 0.1)));
      setRawPulse(prev => Math.min(120, Math.max(50, prev + Math.floor((Math.random() - 0.5) * 4))));
      setMotionActive(Math.random() > 0.4);
      setBattery(prev => Math.max(5, prev - 0.05));
      setTime(new Date());
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  const tempStatus = temp > 37.5 ? "FEVER" : temp < 36 ? "HYPOTHERMIA" : "NORMAL";
  const pulseStatus = pulse > 100 ? "TACHYCARDIA" : pulse < 60 ? "BRADYCARDIA" : "NORMAL";

  return (
    <div style={{
      minHeight: "100vh",
      background: COLORS.bg,
      backgroundImage: "radial-gradient(ellipse at 20% 20%, #0a1a2e 0%, transparent 50%), radial-gradient(ellipse at 80% 80%, #0d1f0d 0%, transparent 50%)",
      padding: "24px",
      fontFamily: "'Courier New', monospace",
      color: COLORS.text,
    }}>
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(0.8); }
        }
        @keyframes scanline {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100vh); }
        }
        @keyframes flicker {
          0%, 100% { opacity: 1; }
          92% { opacity: 1; }
          93% { opacity: 0.8; }
          94% { opacity: 1; }
        }
      `}</style>

      {/* Scanline overlay */}
      <div style={{ position: "fixed", inset: 0, pointerEvents: "none", zIndex: 100, overflow: "hidden", opacity: 0.03 }}>
        <div style={{ position: "absolute", width: "100%", height: "2px", background: "#00d4ff", animation: "scanline 3s linear infinite" }} />
      </div>

      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 28, animation: "flicker 8s infinite" }}>
        <div>
          <div style={{ fontSize: 26, fontWeight: "bold", color: COLORS.accent1, letterSpacing: 4, textShadow: `0 0 20px ${COLORS.accent1}` }}>
            BIOMETRIC MONITOR
          </div>
          <div style={{ fontSize: 11, color: COLORS.muted, letterSpacing: 3, marginTop: 4 }}>
            REAL-TIME HEALTH SURVEILLANCE SYSTEM v2.4
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ color: COLORS.accent1, fontSize: 20, letterSpacing: 2 }}>
            {time.toLocaleTimeString()}
          </div>
          <div style={{ color: COLORS.muted, fontSize: 10, letterSpacing: 2 }}>
            {time.toLocaleDateString()}
          </div>
          <div style={{ marginTop: 6, display: "flex", gap: 8, justifyContent: "flex-end", alignItems: "center" }}>
            <StatusDot active color={COLORS.accent3} />
            <span style={{ fontSize: 9, color: COLORS.accent3, letterSpacing: 2 }}>SENSORS ONLINE</span>
          </div>
        </div>
      </div>

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 20, maxWidth: 1100, margin: "0 auto" }}>

        {/* Body Temperature */}
        <Panel title="Body Temperature" accent={COLORS.accent2}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <RadialGauge value={temp} min={34} max={42} label="TEMPERATURE" unit="°C" color={COLORS.accent2} size={170} />
            <div style={{ textAlign: "center" }}>
              <div style={{
                padding: "4px 16px", borderRadius: 20,
                background: tempStatus === "NORMAL" ? "#00ff0020" : "#ff000020",
                border: `1px solid ${tempStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2}`,
                color: tempStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2,
                fontSize: 11, letterSpacing: 3,
              }}>
                <StatusDot active color={tempStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2} />
                {tempStatus}
              </div>
              <div style={{ marginTop: 8, color: COLORS.muted, fontSize: 10 }}>
                Threshold: 37.5°C
              </div>
            </div>
          </div>
        </Panel>

        {/* Pulse Rate */}
        <Panel title="Pulse Rate" accent={COLORS.accent1}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <RadialGauge value={pulse} min={30} max={150} label="HEART RATE" unit="BPM" color={COLORS.accent1} size={170} />
            <PulseWave color={COLORS.accent1} bpm={pulse} />
            <div style={{
              padding: "4px 16px", borderRadius: 20,
              background: pulseStatus === "NORMAL" ? "#00ff0020" : "#ff000020",
              border: `1px solid ${pulseStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2}`,
              color: pulseStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2,
              fontSize: 11, letterSpacing: 3,
            }}>
              <StatusDot active color={pulseStatus === "NORMAL" ? COLORS.accent3 : COLORS.accent2} />
              {pulseStatus}
            </div>
          </div>
        </Panel>

        {/* Motion Sensor */}
        <Panel title="Motion Sensor" accent={COLORS.accent3}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 48, color: motionActive ? COLORS.accent3 : COLORS.muted, textShadow: motionActive ? `0 0 20px ${COLORS.accent3}` : "none", transition: "all 0.3s" }}>
              {motionActive ? "◉" : "○"}
            </div>
            <div style={{
              fontSize: 16, letterSpacing: 4,
              color: motionActive ? COLORS.accent3 : COLORS.muted,
              textShadow: motionActive ? `0 0 10px ${COLORS.accent3}` : "none",
            }}>
              {motionActive ? "MOTION DETECTED" : "NO MOTION"}
            </div>
            <MotionVisual active={motionActive} />
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, width: "100%", marginTop: 8 }}>
              {["PIR SENSOR", "ACCEL", "GYRO", "RADAR"].map(s => (
                <div key={s} style={{ padding: "6px 10px", borderRadius: 8, border: `1px solid ${COLORS.border}`, fontSize: 9, letterSpacing: 2, color: COLORS.muted, display: "flex", alignItems: "center" }}>
                  <StatusDot active={motionActive} color={COLORS.accent3} />
                  {s}
                </div>
              ))}
            </div>
          </div>
        </Panel>

        {/* Battery */}
        <Panel title="Power Status" accent={COLORS.accent4}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <BatteryBar level={Math.round(battery)} />
            <div style={{ width: "100%" }}>
              <div style={{ marginBottom: 8, color: COLORS.muted, fontSize: 9, letterSpacing: 2 }}>DISCHARGE RATE</div>
              <div style={{ height: 6, borderRadius: 3, background: COLORS.border, overflow: "hidden" }}>
                <div style={{ height: "100%", width: "15%", background: COLORS.accent4, borderRadius: 3, boxShadow: `0 0 6px ${COLORS.accent4}` }} />
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                <span style={{ fontSize: 9, color: COLORS.muted }}>0%</span>
                <span style={{ fontSize: 9, color: COLORS.accent4 }}>0.05%/cycle</span>
                <span style={{ fontSize: 9, color: COLORS.muted }}>100%</span>
              </div>
            </div>
            <div style={{ width: "100%", padding: 12, borderRadius: 8, background: "#1a1200", border: `1px solid ${COLORS.accent4}40` }}>
              <div style={{ fontSize: 9, color: COLORS.muted, letterSpacing: 2, marginBottom: 6 }}>POWER CELLS</div>
              {["MAIN CELL", "BACKUP", "SOLAR"].map((cell, i) => (
                <div key={cell} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                  <span style={{ fontSize: 9, color: COLORS.text }}>{cell}</span>
                  <div style={{ display: "flex", gap: 2 }}>
                    {[...Array(5)].map((_, j) => (
                      <div key={j} style={{ width: 10, height: 6, borderRadius: 2, background: j < (i === 0 ? 4 : i === 1 ? 3 : 2) ? COLORS.accent4 : COLORS.border, boxShadow: j < (i === 0 ? 4 : i === 1 ? 3 : 2) ? `0 0 4px ${COLORS.accent4}` : "none" }} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </div>

      {/* Bottom status bar */}
      <div style={{
        maxWidth: 1100, margin: "20px auto 0",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "12px 20px", borderRadius: 12,
        background: COLORS.panel, border: `1px solid ${COLORS.border}`,
        fontSize: 9, letterSpacing: 2, color: COLORS.muted,
      }}>
        <div><StatusDot active color={COLORS.accent1} />BLE CONNECTED</div>
        <div><StatusDot active color={COLORS.accent3} />ALL SYSTEMS NOMINAL</div>
        <div>FIRMWARE v2.4.1</div>
        <div>DATA RATE: 10Hz</div>
        <div><StatusDot active={battery > 20} color={COLORS.accent4} />{battery > 20 ? "POWER OK" : "LOW BATTERY"}</div>
      </div>
    </div>
  );
}
