import { motion } from 'framer-motion'
import { Card } from 'react-bootstrap'
import { Thermometer, Heart, Battery } from 'lucide-react'

const accentClasses = {
  teal: 'metric-teal',
  coral: 'metric-coral',
  violet: 'metric-violet',
}

const iconMap = {
  Thermometer,
  Heart,
  Battery,
}

export default function MetricCard({ label, value, unit = '', accent = 'teal', icon, range, current }) {
  const accentClass = accentClasses[accent] || 'metric-teal'
  const Icon = iconMap[icon] || Thermometer

  let progress = 0
  if (range && current != null) {
    const { min, max } = range
    progress = Math.max(0, Math.min(100, ((current - min) / (max - min)) * 100))
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
    >
      <Card className={`glass-card border-0 h-100 ${accentClass}`}>
        <Card.Body className="p-4">
          <div className="metric-card-inner">
            <div className="d-flex justify-content-between align-items-start mb-3">
              <small className="text-uppercase fw-bold" style={{ color: 'var(--text-muted)', letterSpacing: '0.15em' }}>
                {label}
              </small>
              <Icon size={24} strokeWidth={1.5} style={{ color: 'var(--accent)', opacity: 0.9 }} />
            </div>
            <div className="d-flex align-items-baseline gap-2">
              <motion.span
                key={value}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="display-4 fw-bold value-display"
                style={{ color: 'var(--accent)', textShadow: '0 0 30px var(--glow)' }}
              >
                {value}
              </motion.span>
              {unit && <span className="text-muted fs-6 fw-medium">{unit}</span>}
            </div>
            {range && current != null && (
              <div className="progress-glow mt-3">
                <motion.div
                  className="progress-glow-fill"
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.8, ease: [0.4, 0, 0.2, 1] }}
                />
              </div>
            )}
          </div>
        </Card.Body>
      </Card>
    </motion.div>
  )
}
