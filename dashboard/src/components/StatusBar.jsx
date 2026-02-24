import { motion } from 'framer-motion'

export default function StatusBar({ connected, safe }) {
  return (
    <div className="d-flex gap-2">
      <motion.span
        className={`status-pill ${connected ? 'live' : 'offline'}`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
      >
        <span className={`pulse-dot me-2 ${connected ? 'bg-success' : 'bg-secondary'}`} style={{ display: 'inline-block', animationPlayState: connected ? 'running' : 'paused' }} />
        {connected ? 'Live' : 'Offline'}
      </motion.span>
      <motion.span
        className={`status-pill ${safe ? 'safe' : 'check'}`}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
      >
        <span className={`pulse-dot me-2 ${safe ? 'bg-success' : 'bg-warning'}`} style={{ display: 'inline-block' }} />
        {safe ? 'Safe' : 'Check'}
      </motion.span>
    </div>
  )
}
