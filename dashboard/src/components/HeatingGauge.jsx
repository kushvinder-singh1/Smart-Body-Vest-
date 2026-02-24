import { motion } from 'framer-motion'
import { Card } from 'react-bootstrap'

const colorConfig = {
  teal: { stroke: '#00e5cc', glow: 'rgba(0, 229, 204, 0.6)' },
  coral: { stroke: '#ff6b4a', glow: 'rgba(255, 107, 74, 0.6)' },
}

export default function HeatingGauge({ label, value, color = 'teal' }) {
  const pct = Math.min(100, Math.max(0, Number(value) || 0))
  const { stroke, glow } = colorConfig[color] || colorConfig.teal

  const circumference = 2 * Math.PI * 45
  const offset = circumference - (pct / 100) * circumference

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <Card className="glass-card border-0 text-center">
        <Card.Body className="p-4">
          <div className="position-relative d-inline-block mb-3">
            <svg width={160} height={160} viewBox="0 0 100 100" className="gauge-svg">
              <defs>
                <linearGradient id={`gauge-grad-${color}`} x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor={stroke} />
                  <stop offset="100%" stopColor={glow} />
                </linearGradient>
              </defs>
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="rgba(255,255,255,0.04)"
                strokeWidth="12"
              />
              <motion.circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke={`url(#gauge-grad-${color})`}
                strokeWidth="12"
                strokeDasharray={circumference}
                initial={{ strokeDashoffset: circumference }}
                animate={{ strokeDashoffset: offset }}
                transition={{ duration: 1, ease: [0.4, 0, 0.2, 1] }}
                strokeLinecap="round"
                transform="rotate(-90 50 50)"
                style={{ filter: `drop-shadow(0 0 10px ${glow})` }}
              />
            </svg>
            <div className="position-absolute top-50 start-50 translate-middle">
              <motion.span
                key={pct}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                className="fw-bold value-display"
                style={{ fontSize: '2rem', color: stroke, textShadow: `0 0 20px ${glow}` }}
              >
                {pct.toFixed(0)}
              </motion.span>
              <span className="text-muted ms-1" style={{ fontSize: '1rem' }}>%</span>
            </div>
          </div>
          <span className="text-uppercase fw-bold" style={{ color: 'var(--text-muted)', letterSpacing: '0.2em' }}>
            {label}
          </span>
        </Card.Body>
      </Card>
    </motion.div>
  )
}
