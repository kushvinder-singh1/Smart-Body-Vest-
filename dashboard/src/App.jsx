import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { Container, Card } from 'react-bootstrap'
import { Sun, Moon, BarChart3, ChevronDown, ChevronUp } from 'lucide-react'
import {
  subscribeToSensors,
  subscribeToCommand,
  subscribeToAuth,
  logout,
  loadUserProfile,
  saveUserProfile,
  isFirebaseConfigured,
} from './firebase'
import AuthPage from './AuthPage'
import MetricCard from './components/MetricCard'
import HeatingGauge from './components/HeatingGauge'
import StatusBar from './components/StatusBar'
import AnalysisPanel from './components/AnalysisPanel'

function normalizeSensorsPayload(payload) {
  if (!payload || typeof payload !== 'object') return {}
  const sensor = payload.sensor && typeof payload.sensor === 'object' ? payload.sensor : payload

  const toNum = (v) => {
    if (typeof v === 'number') return v
    if (typeof v === 'string') {
      const s = v.trim()
      if (!s) return null
      const n = Number(s)
      return Number.isNaN(n) ? null : n
    }
    return null
  }

  const temp    = toNum(sensor.body_temperature_C) ?? toNum(sensor.temp)      ?? null
  const pulse   = toNum(sensor.pulse_bpm)           ?? toNum(sensor.pulse)    ?? null
  const battery = toNum(sensor.battery_percent)     ?? toNum(sensor.battery)  ?? null
  const pad1    = toNum(sensor.pad1_pwm_0_100)      ?? toNum(sensor.pad1)     ?? null
  const pad2    = toNum(sensor.pad2_pwm_0_100)      ?? toNum(sensor.pad2)     ?? null

  return { temp, pulse, battery, pad1, pad2 }
}

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1, delayChildren: 0.2 } },
}
const item = { hidden: { opacity: 0, y: 20 }, show: { opacity: 1, y: 0 } }

export default function App() {
  // ── auth ──────────────────────────────────────────────────────────────────
  const [user, setUser]           = useState(null)
  const [authReady, setAuthReady] = useState(false)

  // ── sensor data ───────────────────────────────────────────────────────────
  const [sensors, setSensors]     = useState(null)
  const [command, setCommand]     = useState(null)
  const [connected, setConnected] = useState(false)
  const [history, setHistory]     = useState([])
  const lastHistoryKeyRef         = useRef(null)

  // ── UI ────────────────────────────────────────────────────────────────────
  const [showAnalysis, setShowAnalysis] = useState(false)

  // ── profile ───────────────────────────────────────────────────────────────
  const [profile, setProfile] = useState({
    age_years: '', height_cm: '', weight_kg: '', gender_0_1: '1',
  })
  const [profileSubmitted, setProfileSubmitted] = useState(false)
  const [profileError, setProfileError]         = useState('')

  // ── theme ─────────────────────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = window.localStorage.getItem('dashboard-theme')
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  // ── subscriptions ─────────────────────────────────────────────────────────
  useEffect(() => {
    if (!isFirebaseConfigured) { setAuthReady(true); return }
    const unsub = subscribeToAuth(async (u) => {
      setUser(u)
      setAuthReady(true)
      setProfileError('')
      setProfileSubmitted(false)
      if (u?.uid) {
        const existing = await loadUserProfile(u.uid)
        if (existing) {
          setProfile({
            age_years:  String(existing.age_years  ?? ''),
            height_cm:  String(existing.height_cm  ?? ''),
            weight_kg:  String(existing.weight_kg  ?? ''),
            gender_0_1: String(existing.gender_0_1 ?? '1'),
          })
          setProfileSubmitted(true)
        }
      }
    })
    return () => unsub()
  }, [])

  useEffect(() => {
    if (!isFirebaseConfigured) return
    const unsubSensors = subscribeToSensors((data) => { setSensors(data); setConnected(true) })
    const unsubCmd     = subscribeToCommand((data) => setCommand(data))
    return () => { unsubSensors(); unsubCmd() }
  }, [])

  useEffect(() => {
    document.body.dataset.theme = theme
    document.documentElement.setAttribute('data-bs-theme', theme === 'light' ? 'light' : 'dark')
    window.localStorage.setItem('dashboard-theme', theme)
  }, [theme])

  useEffect(() => {
    if (!sensors) return
    const tsRaw =
      sensors?.timestamp ?? sensors?.ts ?? sensors?.time ??
      sensors?.sensor?.timestamp ?? sensors?.sensor?.ts ?? sensors?.sensor?.time ?? null
    const ts = typeof tsRaw === 'number' ? tsRaw : Date.now()
    const norm = normalizeSensorsPayload(sensors)
    const point = {
      ts,
      temp:    norm.temp,
      pulse:   norm.pulse,
      battery: norm.battery,
      pad1: Number(command?.pad1 ?? norm.pad1 ?? sensors?.pad1_pwm_0_100 ?? 0),
      pad2: Number(command?.pad2 ?? norm.pad2 ?? sensors?.pad2_pwm_0_100 ?? 0),
    }
    const key = `${point.ts}|${point.temp}|${point.pulse}|${point.battery}|${point.pad1}|${point.pad2}`
    if (lastHistoryKeyRef.current === key) return
    lastHistoryKeyRef.current = key
    setHistory((prev) => {
      const next = [...prev, point]
      return next.length > 120 ? next.slice(next.length - 120) : next
    })
  }, [sensors, command])

  // ── derived values ────────────────────────────────────────────────────────
  const norm    = normalizeSensorsPayload(sensors)
  const temp    = norm.temp    ?? null
  const pulse   = norm.pulse   ?? null
  const battery = norm.battery ?? null
  const pad1    = command?.pad1 ?? norm.pad1 ?? sensors?.pad1_pwm_0_100 ?? 0
  const pad2    = command?.pad2 ?? norm.pad2 ?? sensors?.pad2_pwm_0_100 ?? 0

  const isSafe =
    temp != null && temp >= 35 && temp <= 39 &&
    pulse != null && pulse >= 40 && pulse <= 120

  const comfort = (() => {
    if (temp == null || pulse == null) return { label: 'Waiting for data',   detail: 'Vest will adjust once readings arrive.',      tone: 'secondary' }
    if (temp < 35)                     return { label: 'You may feel cold',   detail: 'Increase heating or move to a warmer place.', tone: 'warning'   }
    if (temp > 38.5 || pulse > 120)   return { label: 'Too warm / stressed', detail: 'Reduce heating and take a short break.',      tone: 'danger'    }
    return                                    { label: 'Comfortable',         detail: 'You are within the target comfort range.',    tone: 'success'   }
  })()

  const padIntensityLabel = (pct) => {
    if (pct <= 5)  return 'Off'
    if (pct <= 35) return 'Low'
    if (pct <= 70) return 'Medium'
    return 'High'
  }

  // ── profile submit ────────────────────────────────────────────────────────
  const submitProfile = async (e) => {
    e.preventDefault()
    setProfileError('')
    const age    = Number(profile.age_years)
    const height = Number(profile.height_cm)
    const weight = Number(profile.weight_kg)
    const gender = Number(profile.gender_0_1)
    if (!Number.isFinite(age)    || age    <  5  || age    > 100) return setProfileError('Enter age between 5 and 100')
    if (!Number.isFinite(height) || height <  90 || height > 230) return setProfileError('Enter height in cm between 90 and 230')
    if (!Number.isFinite(weight) || weight <  20 || weight > 250) return setProfileError('Enter weight in kg between 20 and 250')
    if (!user?.uid) return setProfileError('Please login first.')
    const payload = { age_years: age, height_cm: height, weight_kg: weight, gender_0_1: gender === 1 ? 1 : 0 }
    if (isFirebaseConfigured) await saveUserProfile(user.uid, payload)
    setProfileSubmitted(true)
  }

  // ── render ────────────────────────────────────────────────────────────────

  // Avoid flashing AuthPage before Firebase resolves the session
  if (!authReady) return (
    <div style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span className="spinner-border text-secondary" />
    </div>
  )

  // Not logged in → show the dedicated auth page
  if (!user) return <AuthPage />

  // Logged in → show the dashboard
  return (
    <div className="min-vh-100">
      <div className="dashboard-bg" />
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />

      {!isFirebaseConfigured && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="alert alert-warning text-center rounded-0 mb-0 py-2 border-0"
          style={{ background: 'rgba(251,191,36,0.15)' }}
        >
          Add Firebase Web config to <code className="text-warning">dashboard/.env</code>
        </motion.div>
      )}

      {/* ── header ── */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="dashboard-header py-4"
      >
        <Container>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <h1 className="h5 mb-0 d-flex align-items-center gap-3">
              <span className="fs-3" style={{ color: 'var(--teal)', filter: 'drop-shadow(0 0 10px rgba(0,229,204,0.5))' }}>◇</span>
              <span className="logo-text">Smart Heating Vest</span>
            </h1>
            <div className="d-flex align-items-center gap-3">
              <StatusBar connected={connected} safe={isSafe} />
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary rounded-pill d-flex align-items-center gap-1 theme-toggle-btn"
                onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              >
                {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
                <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary rounded-pill"
                onClick={() => { if (window.confirm('Log out?')) logout() }}
              >
                Logout
              </button>
            </div>
          </div>
        </Container>
      </motion.header>

      {/* ── greeting bar ── */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        style={{ borderBottom: '1px solid var(--card-border)', background: 'rgba(255,255,255,0.02)' }}
        className="py-2"
      >
        <Container>
          <span className="text-muted">
            Hi,{' '}
            <span style={{ color: 'var(--teal)', fontWeight: 600 }}>
              {user.displayName || user.email?.split('@')[0]}
            </span>
            {' '}— welcome back.
          </span>
        </Container>
      </motion.div>

      {/* ── main content ── */}
      <main className="py-5">
        <Container>

          {/* ── profile form (shown until submitted) ── */}
          {!profileSubmitted && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-4">
              <Card className="glass-card border-0">
                <Card.Body className="p-4">
                  <h6 className="section-title mb-2">Enter User Details </h6>
                  <form className="row g-3" onSubmit={submitProfile}>
                    <div className="col-md-3">
                      <label className="form-label">Age</label>
                      <input className="form-control" type="number" value={profile.age_years}
                        onChange={(e) => setProfile((p) => ({ ...p, age_years: e.target.value }))} required />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Height (cm)</label>
                      <input className="form-control" type="number" step="0.1" value={profile.height_cm}
                        onChange={(e) => setProfile((p) => ({ ...p, height_cm: e.target.value }))} required />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Weight (kg)</label>
                      <input className="form-control" type="number" step="0.1" value={profile.weight_kg}
                        onChange={(e) => setProfile((p) => ({ ...p, weight_kg: e.target.value }))} required />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Gender</label>
                      <select className="form-select" value={profile.gender_0_1}
                        onChange={(e) => setProfile((p) => ({ ...p, gender_0_1: e.target.value }))}>
                        <option value="1">Male</option>
                        <option value="0">Female</option>
                      </select>
                    </div>
                    {profileError && <div className="col-12 text-warning small">{profileError}</div>}
                    <div className="col-12">
                      <button className="btn btn-primary" type="submit">Save Profile &amp; Start</button>
                    </div>
                  </form>
                </Card.Body>
              </Card>
            </motion.div>
          )}

          {/* ── metric cards ── */}
          <motion.div variants={container} initial="hidden" animate="show" className="row g-4 mb-5">
            <motion.div variants={item} className="col-md-4">
              <MetricCard label="Body Temperature" value={temp != null ? `${temp.toFixed(1)}°C` : '--'}
                accent="coral" icon="Thermometer" range={{ min: 35, max: 39 }} current={temp} />
            </motion.div>
            <motion.div variants={item} className="col-md-4">
              <MetricCard label="Heart Rate" value={pulse != null ? pulse : '--'} unit="bpm"
                accent="teal" icon="Heart" range={{ min: 40, max: 120 }} current={pulse} />
            </motion.div>
            <motion.div variants={item} className="col-md-4">
              <MetricCard label="Battery" value={battery != null ? `${battery.toFixed(0)}%` : '--'}
                accent="violet" icon="Battery" range={{ min: 0, max: 100 }} current={battery} />
            </motion.div>
            <motion.div variants={item} className="col-12 mt-2">
              <Card className="glass-card border-0">
                <Card.Body className="d-flex flex-column flex-md-row justify-content-between align-items-start gap-2">
                  <div>
                    <small className="text-uppercase fw-bold text-muted">Comfort</small>
                    <div className={`fw-semibold text-${comfort.tone}`}>{comfort.label}</div>
                    <small className="text-muted">{comfort.detail}</small>
                  </div>
                  <span className="badge rounded-pill bg-opacity-10 border"
                    style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}>
                    Temp {temp != null ? `${temp.toFixed(1)}°C` : '--'} · Pulse {pulse ?? '--'} bpm
                  </span>
                </Card.Body>
              </Card>
            </motion.div>
          </motion.div>

          {/* ── heating gauges ── */}
          <motion.h6 initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="section-title">
            Heating Control
          </motion.h6>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.4 }} className="row g-4 mb-5">
            <div className="col-md-6">
              <HeatingGauge label="Pad 1" value={pad1} color="teal" />
              <div className="text-center mt-2 text-muted small">{padIntensityLabel(pad1)} · {Number(pad1).toFixed(0)}%</div>
            </div>
            <div className="col-md-6">
              <HeatingGauge label="Pad 2" value={pad2} color="coral" />
              <div className="text-center mt-2 text-muted small">{padIntensityLabel(pad2)} · {Number(pad2).toFixed(0)}%</div>
            </div>
          </motion.div>

          {/* ── analysis ── */}
          <motion.h6 initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.55 }} className="section-title">
            Analysis
          </motion.h6>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.58, duration: 0.4 }} className="mb-4">
            <Card className="glass-card border-0" role="button" tabIndex={0}
              onClick={() => setShowAnalysis((v) => !v)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setShowAnalysis((v) => !v) }}
              aria-expanded={showAnalysis}>
              <Card.Body className="p-4 d-flex align-items-center justify-content-between gap-3">
                <div className="d-flex align-items-center gap-3">
                  <span className="d-inline-flex align-items-center justify-content-center rounded-4"
                    style={{ width: 44, height: 44, border: '1px solid var(--card-border)', background: 'rgba(255,255,255,0.03)', color: 'var(--teal)' }}>
                    <BarChart3 size={20} />
                  </span>
                  <div>
                    <div className="fw-bold" style={{ fontSize: 16 }}>Analysis graphs</div>
                    <div className="text-muted" style={{ fontSize: 13 }}>
                      Click to {showAnalysis ? 'hide' : 'show'} real-time trends and training plots
                    </div>
                  </div>
                </div>
                <div className="d-flex align-items-center gap-2 text-muted" style={{ fontSize: 13 }}>
                  <span>{showAnalysis ? 'Hide' : 'Show'}</span>
                  {showAnalysis ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                </div>
              </Card.Body>
            </Card>
          </motion.div>
          {showAnalysis && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="mb-5">
              <AnalysisPanel history={history} comfortRange={{ min: 36, max: 37.5 }} />
            </motion.div>
          )}

          {/* ── system status ── */}
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6, duration: 0.4 }}>
            <Card className="glass-card border-0">
              <Card.Body className="p-4">
                <h6 className="section-title mb-3">System Status</h6>
                <div className="d-flex flex-wrap gap-4">
                  <span className={`d-flex align-items-center gap-2 ${connected ? 'text-success' : 'text-secondary'}`}>
                    <span className={`pulse-dot ${connected ? 'bg-success' : 'bg-secondary'}`}
                      style={{ animationPlayState: connected ? 'running' : 'paused' }} />
                    <span className="fw-semibold">{connected ? 'Cloud connected' : 'Waiting for data...'}</span>
                  </span>
                  <span className={`d-flex align-items-center gap-2 ${isSafe ? 'text-success' : 'text-warning'}`}>
                    <span className={`pulse-dot ${isSafe ? 'bg-success' : 'bg-warning'}`} />
                    <span className="fw-semibold">
                      {isSafe
                        ? 'All systems nominal'
                        : temp != null && pulse != null
                          ? `Outside comfort range (T=${temp.toFixed(1)}°C, HR=${pulse} bpm)`
                          : 'Check thresholds / missing data'}
                    </span>
                  </span>
                </div>
              </Card.Body>
            </Card>
          </motion.div>

        </Container>
      </main>
    </div>
  )
}
