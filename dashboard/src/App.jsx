import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Container, Row, Col, Card } from 'react-bootstrap'
import { Sun, Moon } from 'lucide-react'
import { subscribeToSensors, subscribeToCommand, isFirebaseConfigured } from './firebase'
import MetricCard from './components/MetricCard'
import HeatingGauge from './components/HeatingGauge'
import StatusBar from './components/StatusBar'

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.2 },
  },
}

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
}

function App() {
  const [sensors, setSensors] = useState(null)
  const [command, setCommand] = useState(null)
  const [connected, setConnected] = useState(false)
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'dark'
    const stored = window.localStorage.getItem('dashboard-theme')
    if (stored === 'light' || stored === 'dark') return stored
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches
      ? 'light'
      : 'dark'
  })

  useEffect(() => {
    if (!isFirebaseConfigured) return
    const unsubSensors = subscribeToSensors((data) => {
      setSensors(data)
      setConnected(true)
    })
    const unsubCmd = subscribeToCommand((data) => setCommand(data))
    return () => {
      unsubSensors()
      unsubCmd()
    }
  }, [])

  useEffect(() => {
    document.body.dataset.theme = theme
    document.documentElement.setAttribute('data-bs-theme', theme === 'light' ? 'light' : 'dark')
    window.localStorage.setItem('dashboard-theme', theme)
  }, [theme])

  const temp = sensors?.body_temperature_C ?? null
  const pulse = sensors?.pulse_bpm ?? null
  const battery = sensors?.battery_percent ?? null
  const pad1 = command?.pad1 ?? sensors?.pad1_pwm_0_100 ?? 0
  const pad2 = command?.pad2 ?? sensors?.pad2_pwm_0_100 ?? 0

  const isSafe = temp != null && temp >= 35 && temp <= 39 && pulse != null && pulse >= 40 && pulse <= 120

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
          style={{ background: 'rgba(251, 191, 36, 0.15)' }}
        >
          Add Firebase Web config to <code className="text-warning">dashboard/.env</code>
        </motion.div>
      )}
      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="dashboard-header py-4"
      >
        <Container>
          <div className="d-flex justify-content-between align-items-center">
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
            </div>
          </div>
        </Container>
      </motion.header>

      <main className="py-5">
        <Container>
          <motion.div
            variants={container}
            initial="hidden"
            animate="show"
            className="row g-4 mb-5"
          >
            <motion.div variants={item} className="col-md-4">
              <MetricCard
                label="Body Temperature"
                value={temp != null ? `${temp.toFixed(1)}°C` : '--'}
                accent="coral"
                icon="Thermometer"
                range={{ min: 35, max: 39 }}
                current={temp}
              />
            </motion.div>
            <motion.div variants={item} className="col-md-4">
              <MetricCard
                label="Heart Rate"
                value={pulse != null ? pulse : '--'}
                unit="bpm"
                accent="teal"
                icon="Heart"
                range={{ min: 40, max: 120 }}
                current={pulse}
              />
            </motion.div>
            <motion.div variants={item} className="col-md-4">
              <MetricCard
                label="Battery"
                value={battery != null ? `${battery.toFixed(0)}%` : '--'}
                accent="violet"
                icon="Battery"
                range={{ min: 0, max: 100 }}
                current={battery}
              />
            </motion.div>
          </motion.div>

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
              <HeatingGauge label="Pad 1" value={pad1} color="teal" />
            </div>
            <div className="col-md-6">
              <HeatingGauge label="Pad 2" value={pad2} color="coral" />
            </div>
          </motion.div>

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
                    <span className={`pulse-dot ${connected ? 'bg-success' : 'bg-secondary'}`} style={{ animationPlayState: connected ? 'running' : 'paused' }} />
                    <span className="fw-semibold">{connected ? 'Cloud connected' : 'Waiting for data...'}</span>
                  </span>
                  <span className={`d-flex align-items-center gap-2 ${isSafe ? 'text-success' : 'text-warning'}`}>
                    <span className={`pulse-dot ${isSafe ? 'bg-success' : 'bg-warning'}`} />
                    <span className="fw-semibold">{isSafe ? 'All systems nominal' : 'Check thresholds'}</span>
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

export default App
