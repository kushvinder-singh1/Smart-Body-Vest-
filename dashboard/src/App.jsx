import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Container, Card } from 'react-bootstrap'
import { Sun, Moon, AlertTriangle } from 'lucide-react'
import {
  subscribeToSensors,
  subscribeToCommand,
  subscribeToAuth,
  logout,
  loadUserProfile,
  saveUserProfile,
  setDeviceStatus,
  isFirebaseConfigured,
} from './firebase'
import MetricCard from './components/MetricCard'
import HeatingGauge from './components/HeatingGauge'
import StatusBar from './components/StatusBar'
import logo from './logo.png'
import { listenToCurrentUser } from './firebase'

// ─── CONSTANTS ────────────────────────────────────────────────────────────────

const PAD_LABEL_TO_PCT  = { off: 0, low: 33.33, medium: 66.66, high: 100 }

const PAD_IDLE_TIMEOUT_MS = 10 * 60 * 1000
const PAD_IDLE_WARN_MS    =  9 * 60 * 1000

const TEMP_SENSOR_MIN   = 34
const TEMP_SAFETY_OFF   = 39
const TEMP_SAFETY_LOW   = 35
const PULSE_REDUCE_HEAT = 120

// ─── FALLBACK HEATING ─────────────────────────────────────────────────────────

function getFallbackHeatingLevel(temp) {
  if (temp === null || temp === 0) return 'off'
  if (temp < 35)                   return 'high'
  if (temp < 35.5)                 return 'medium'
  if (temp < 36)                   return 'low'
  return 'off'
}

// ─── NORMALISE SENSORS ────────────────────────────────────────────────────────

function normalizeSensorsPayload(payload) {
  if (!payload || typeof payload !== 'object') return {}

  const sensor =
    payload.sensor && typeof payload.sensor === 'object' ? payload.sensor : payload

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

  const toPadLabel = (v) => {
    if (typeof v === 'string') {
      const s = v.trim().toLowerCase()
      if (['off', 'low', 'medium', 'high'].includes(s)) return s
    }
    return null
  }

  let temp         = toNum(sensor.body_temperature_C) ?? toNum(sensor.temp)     ?? null
  let pulse        = toNum(sensor.pulse_bpm)           ?? toNum(sensor.pulse)   ?? null
  let battery      = toNum(sensor.battery_percent)     ?? toNum(sensor.battery) ?? null
  let motionSensor = toNum(sensor.motion) ?? null

  if (temp !== null && temp <= TEMP_SENSOR_MIN) {
    temp         = 0
    pulse        = 0
    motionSensor = 0
  }

  const heatingLevel = payload?.heating?.level ?? null
  const pad1 = toPadLabel(heatingLevel)
  const pad2 = toPadLabel(heatingLevel)

  return { temp, pulse, battery, pad1, pad2, motion: motionSensor }
}

// ─── ANIMATION VARIANTS ───────────────────────────────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
}
const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show:   { opacity: 1, y: 0 },
}

// ─── COMPONENT ────────────────────────────────────────────────────────────────

export default function App() {
  const navigate = useNavigate()

  // auth
  const [user,      setUser]      = useState(null)
  const [authReady, setAuthReady] = useState(false)

  // sensors
  const [sensors,   setSensors]   = useState(null)
  const [command,   setCommand]   = useState(null)
  const [connected, setConnected] = useState(false)
  const [history,   setHistory]   = useState([])
  const lastHistoryKeyRef         = useRef(null)

  // pad idle
  const [showPadWarning, setShowPadWarning] = useState(false)
  const [deviceIdle,     setDeviceIdle]     = useState(false)
  const padIdleTimerRef                     = useRef(null)
  const padIdleWarnRef                      = useRef(null)

  // profile
  const [profile, setProfile] = useState({
    age_years: '', height_cm: '', weight_kg: '', gender_0_1: '1',
  })
  const [profileSubmitted, setProfileSubmitted] = useState(false)
  const [profileError,     setProfileError]     = useState('')

  // theme
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = window.localStorage.getItem('dashboard-theme')
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  // ─── AUTH SUBSCRIPTION ────────────────────────────────────────────────────

  useEffect(() => {
    if (!isFirebaseConfigured) {
      setAuthReady(true)
      return
    }
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
        } else {
          navigate('/profile')
        }
      }
    })
    return () => unsub()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── SENSOR SUBSCRIPTION (user-scoped) ───────────────────────────────────

  useEffect(() => {
    let sensorUnsub = null
    let commandUnsub = null
    const currentUIDRef = { current: null }

    const unsubMeta = listenToCurrentUser((uid) => {
      if (!uid) {
        setSensors(null)
        setConnected(false)
        return
      }

      if (uid === currentUIDRef.current) return

      if (sensorUnsub) sensorUnsub()
      if (commandUnsub) commandUnsub()

      currentUIDRef.current = uid

      sensorUnsub = subscribeToSensors(uid, (data) => {
        setSensors(data)
        setConnected(true)
      })

      commandUnsub = subscribeToCommand((data) => {
        setCommand(data)
      })
    })

    return () => {
      if (sensorUnsub) sensorUnsub()
      if (commandUnsub) commandUnsub()
      if (unsubMeta) unsubMeta()
    }
  }, [])

  // ─── THEME SYNC ───────────────────────────────────────────────────────────

  useEffect(() => {
    document.body.dataset.theme = theme
    document.documentElement.setAttribute(
      'data-bs-theme',
      theme === 'light' ? 'light' : 'dark'
    )
    window.localStorage.setItem('dashboard-theme', theme)
  }, [theme])

  // ─── AUTH REDIRECT ────────────────────────────────────────────────────────

  useEffect(() => {
    if (authReady && !user) navigate('/auth')   // ← unauthenticated → auth page
  }, [authReady, user]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── HISTORY RING-BUFFER ──────────────────────────────────────────────────

  useEffect(() => {
    if (!sensors) return
    const tsRaw =
      sensors?.timestamp ?? sensors?.ts ?? sensors?.time ??
      sensors?.sensor?.timestamp ?? sensors?.sensor?.ts ??
      sensors?.sensor?.time ?? null
    const ts = typeof tsRaw === 'number' ? tsRaw : Date.now()
    const norm = normalizeSensorsPayload(sensors)
    const point = {
      ts,
      temp:    norm.temp,
      pulse:   norm.pulse,
      battery: norm.battery,
      pad1:    command?.level ?? 'off',
      pad2:    command?.level ?? 'off',
    }
    const key = `${point.ts}|${point.temp}|${point.pulse}|${point.battery}|${point.pad1}|${point.pad2}`
    if (lastHistoryKeyRef.current === key) return
    lastHistoryKeyRef.current = key
    setHistory((prev) => {
      const next = [...prev, point]
      return next.length > 120 ? next.slice(next.length - 120) : next
    })
  }, [sensors, command])

  // ─── DERIVED VALUES ───────────────────────────────────────────────────────

  const norm        = normalizeSensorsPayload(sensors)
  const temp        = norm.temp    ?? null
  const pulse       = norm.pulse   ?? null
  const battery     = norm.battery ?? null
  const motionVal   = norm.motion  ?? null
  const motionLabel = motionVal === 1 ? 'Active' : motionVal === 0 ? 'Still' : '--'

  const rawPadLabel =
    (
      sensors?.heat_level ??
      sensors?.sensor?.heat_level ??
      command?.level ??
      ''
    )
      .toLowerCase() || null

  const safetyOverride = (() => {
    if (temp === 0 || temp === null) return null
    if (temp >= TEMP_SAFETY_OFF)     return 'off'
    if (temp <= TEMP_SAFETY_LOW)     return 'off'
    if (pulse !== null && pulse >= PULSE_REDUCE_HEAT) {
      const reduce = { high: 'medium', medium: 'low', low: 'off', off: 'off' }
      return reduce[rawPadLabel] ?? 'low'
    }
    return null
  })()

  const isFallback    = !rawPadLabel || temp === 0 || temp === null
  const fallbackLevel = getFallbackHeatingLevel(temp)

  const pad1Label = safetyOverride ?? (isFallback ? fallbackLevel : rawPadLabel)
  const pad2Label = pad1Label
  const pad1Pct   = PAD_LABEL_TO_PCT[pad1Label] ?? 0
  const pad2Pct   = PAD_LABEL_TO_PCT[pad2Label] ?? 0

  const isSafe =
    temp  != null && temp  > TEMP_SENSOR_MIN && temp  < TEMP_SAFETY_OFF &&
    pulse != null && pulse > 0               && pulse < PULSE_REDUCE_HEAT

  const comfort = (() => {
    if (temp === 0 || temp === null || pulse === 0 || pulse === null)
      return { label: 'Vest not detected',          detail: 'No valid readings — please wear the vest properly.',        tone: 'secondary' }
    if (temp >= TEMP_SAFETY_OFF)
      return { label: 'Overheating — heating off',  detail: 'Temperature too high. Heating has been disabled.',          tone: 'danger'    }
    if (temp <= TEMP_SAFETY_LOW)
      return { label: 'Too cold — heating off',     detail: 'Temperature below safe threshold. Check vest fit.',         tone: 'warning'   }
    if (pulse >= PULSE_REDUCE_HEAT)
      return { label: 'High heart rate',            detail: 'Heating level reduced until pulse normalises.',             tone: 'warning'   }
    if (isFallback && temp > TEMP_SENSOR_MIN)
      return { label: 'Warming up',                 detail: 'Fallback heating active — waiting for model data.',         tone: 'info'      }
    return   { label: 'Comfortable',                detail: 'You are within the target comfort range.',                  tone: 'success'   }
  })()

  // ─── PAD IDLE DETECTION ───────────────────────────────────────────────────

  useEffect(() => {
    if (!user?.uid) {
      clearTimeout(padIdleTimerRef.current)
      clearTimeout(padIdleWarnRef.current)
      return
    }

    const padIsOff = !pad1Label || pad1Label === 'off'

    if (padIsOff) {
      if (!padIdleTimerRef.current) {
        padIdleWarnRef.current = setTimeout(() => {
          setShowPadWarning(true)
        }, PAD_IDLE_WARN_MS)

        padIdleTimerRef.current = setTimeout(() => {
          padIdleTimerRef.current = null
          padIdleWarnRef.current  = null
          setShowPadWarning(false)
          setDeviceIdle(true)
          setDeviceStatus(user.uid, 'idle')
        }, PAD_IDLE_TIMEOUT_MS)
      }
    } else {
      clearTimeout(padIdleTimerRef.current)
      clearTimeout(padIdleWarnRef.current)
      padIdleTimerRef.current = null
      padIdleWarnRef.current  = null
      setShowPadWarning(false)
      if (deviceIdle) {
        setDeviceIdle(false)
        setDeviceStatus(user.uid, 'active')
      }
    }
  }, [pad1Label, user?.uid]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    return () => {
      clearTimeout(padIdleTimerRef.current)
      clearTimeout(padIdleWarnRef.current)
    }
  }, [])

  // ─── PROFILE SUBMIT ───────────────────────────────────────────────────────

  const submitProfile = async (e) => {
    e.preventDefault()
    setProfileError('')
    const age    = Number(profile.age_years)
    const height = Number(profile.height_cm)
    const weight = Number(profile.weight_kg)
    const gender = Number(profile.gender_0_1)
    if (!Number.isFinite(age)    || age    <  5  || age    > 100) { setProfileError('Enter age between 5 and 100');          return }
    if (!Number.isFinite(height) || height <  90 || height > 230) { setProfileError('Enter height in cm between 90 and 230'); return }
    if (!Number.isFinite(weight) || weight <  20 || weight > 250) { setProfileError('Enter weight in kg between 20 and 250'); return }
    if (!user?.uid) { setProfileError('Please login first.'); return }
    const payload = {
      age_years:  age,
      height_cm:  height,
      weight_kg:  weight,
      gender_0_1: gender === 1 ? 1 : 0,
    }
    if (isFirebaseConfigured) await saveUserProfile(user.uid, payload)
    setProfileSubmitted(true)
  }

  // ─── LOADING GUARD ────────────────────────────────────────────────────────

  if (!authReady || !user) {
    return (
      <div style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span className="spinner-border text-secondary" />
      </div>
    )
  }

  // ─── RENDER ───────────────────────────────────────────────────────────────

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
          Add Firebase Web config to{' '}
          <code className="text-warning">dashboard/.env</code>
        </motion.div>
      )}

      <AnimatePresence>
        {showPadWarning && !deviceIdle && (
          <motion.div
            key="pad-warn"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.25 }}
            className="d-flex justify-content-center align-items-center gap-3 py-2 px-3 rounded-0 border-0"
            style={{ background: 'rgba(251,191,36,0.15)', color: '#fbbf24' }}
          >
            <AlertTriangle size={16} />
            <span>
              Heating pads have been off for 9 minutes — vest will be marked idle in 1 minute.
            </span>
          </motion.div>
        )}

        {deviceIdle && (
          <motion.div
            key="pad-idle"
            initial={{ opacity: 0, y: -16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ duration: 0.25 }}
            className="d-flex justify-content-center align-items-center gap-3 py-2 px-3 rounded-0 border-0"
            style={{ background: 'rgba(99,102,241,0.15)', color: '#a5b4fc' }}
          >
            <AlertTriangle size={16} />
            <span>
              Vest marked as <strong>idle</strong> — heating pads off for 10+ minutes.
              Monitoring continues.
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="dashboard-header py-4"
      >
        <Container>
          <div className="d-flex justify-content-between align-items-center flex-wrap gap-2">
            <h1 className="h5 mb-0 d-flex align-items-center gap-3">
              <img
                src={logo}
                alt="Logo"
                style={{ height: '32px', width: '32px', objectFit: 'contain' }}
              />
              <span
                className="logo-text"
                style={{
                  fontFamily: "var(--font-display)",
                  fontSize: "2.05rem",
                  fontWeight: 700,
                  letterSpacing: "0.5px"
                }}
              >
                HeatSync
              </span>
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
                onClick={() => navigate('/profile')}
              >
                Profile
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary rounded-pill"
                onClick={() => {
                  if (window.confirm('Log out?')) {
                    logout()
                    navigate('/')   // ← after logout go to landing
                  }
                }}
              >
                Logout
              </button>
            </div>
          </div>
        </Container>
      </motion.header>

      {/* Greeting bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        style={{
          borderBottom: '1px solid var(--card-border)',
          background: 'rgba(255,255,255,0.02)',
        }}
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

      {/* Main content */}
      <main className="py-5">
        <Container>

          {/* Metric cards */}
          <motion.div
            variants={containerVariants}
            initial="hidden"
            animate="show"
            className="row g-4 mb-5"
          >
            <motion.div variants={itemVariants} className="col-md-4">
              <MetricCard
                label="Body Temperature"
                value={temp != null && temp > 0 ? `${temp.toFixed(1)}°C` : '--'}
                accent="coral"
                icon="Thermometer"
                range={{ min: 35, max: 39 }}
                current={temp}
              />
            </motion.div>
            <motion.div variants={itemVariants} className="col-md-4">
              <MetricCard
                label="Heart Rate"
                value={pulse != null && pulse > 0 ? pulse : '--'}
                unit="bpm"
                accent="teal"
                icon="Heart"
                range={{ min: 40, max: 120 }}
                current={pulse}
              />
            </motion.div>
            <motion.div variants={itemVariants} className="col-md-4">
              <MetricCard
                label="Motion"
                value={motionVal !== null && motionVal > 0 ? motionLabel : '--'}
                accent="violet"
                icon="Activity"
              />
            </motion.div>

            <motion.div variants={itemVariants} className="col-12 mt-2">
              <Card className="glass-card border-0">
                <Card.Body className="d-flex flex-column flex-md-row justify-content-between align-items-start gap-2">
                  <div>
                    <small className="text-uppercase fw-bold text-muted">Comfort</small>
                    <div className={`fw-semibold text-${comfort.tone}`}>{comfort.label}</div>
                    <small className="text-muted">{comfort.detail}</small>
                  </div>
                  <span
                    className="badge rounded-pill bg-opacity-10 border"
                    style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}
                  >
                    Temp {temp != null && temp > 0 ? `${temp.toFixed(1)}°C` : '--'}
                    {' · '}
                    Pulse {pulse != null && pulse > 0 ? pulse : '--'} bpm
                  </span>
                </Card.Body>
              </Card>
            </motion.div>
          </motion.div>

          {/* Heating gauges */}
          <motion.h6
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="section-title"
          >
            Heating Control
          </motion.h6>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.4 }}
            className="row g-4 mb-5"
          >
            <div className="col-md-6">
              <HeatingGauge label="Pad 1" value={pad1Pct} color="teal" />
            </div>
            <div className="col-md-6">
              <HeatingGauge label="Pad 2" value={pad2Pct} color="coral" />
            </div>
          </motion.div>

          {/* System status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.4 }}
          >
            <Card className="glass-card border-0">
              <Card.Body className="p-4">
                <h6 className="section-title mb-3">System Status</h6>
                <div className="d-flex flex-wrap gap-4">

                  <span className={`d-flex align-items-center gap-2 ${connected ? 'text-success' : 'text-secondary'}`}>
                    <span
                      className={`pulse-dot ${connected ? 'bg-success' : 'bg-secondary'}`}
                      style={{ animationPlayState: connected ? 'running' : 'paused' }}
                    />
                    <span className="fw-semibold">
                      {connected ? 'Cloud connected' : 'Waiting for data...'}
                    </span>
                  </span>

                  <span className={`d-flex align-items-center gap-2 ${isSafe ? 'text-success' : 'text-warning'}`}>
                    <span className={`pulse-dot ${isSafe ? 'bg-success' : 'bg-warning'}`} />
                    <span className="fw-semibold">
                      {isSafe
                        ? 'All systems nominal'
                        : temp != null && temp > 0 && pulse != null && pulse > 0
                          ? `Outside comfort range (T=${temp.toFixed(1)}°C, HR=${pulse} bpm)`
                          : 'Check vest — no valid readings'}
                    </span>
                  </span>

                  {deviceIdle && (
                    <span className="d-flex align-items-center gap-2" style={{ color: '#a5b4fc' }}>
                      <span
                        className="pulse-dot"
                        style={{ background: '#a5b4fc', animationPlayState: 'paused' }}
                      />
                      <span className="fw-semibold">Device idle</span>
                    </span>
                  )}
                </div>
              </Card.Body>
            </Card>
          </motion.div>
        </Container>
      </main>
    </div>
  )
}
