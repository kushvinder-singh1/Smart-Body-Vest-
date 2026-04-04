import { useMemo, useState } from 'react'
import { Card, Row, Col, Button } from 'react-bootstrap'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  Legend,
} from 'recharts'

const timeFmt = new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })

function fmtTime(ts) {
  if (!ts) return ''
  return timeFmt.format(new Date(ts))
}

function StatPill({ label, value }) {
  return (
    <span
      className="badge rounded-pill bg-opacity-10 border"
      style={{ borderColor: 'var(--offline-border)', color: 'var(--text-muted)', fontSize: 12, padding: '8px 12px' }}
    >
      <span className="fw-semibold" style={{ color: 'var(--text)' }}>
        {value}
      </span>
      <span className="ms-2">{label}</span>
    </span>
  )
}

function TrainingPlot({ title, src }) {
  const [missing, setMissing] = useState(false)

  return (
    <Card className="glass-card border-0 h-100">
      <Card.Body className="p-3">
        <div className="fw-bold mb-2" style={{ fontSize: 14 }}>
          {title}
        </div>
        {missing ? (
          <div
            className="rounded-3 d-flex align-items-center justify-content-center text-center p-3"
            style={{
              border: '1px dashed var(--card-border)',
              color: 'var(--text-muted)',
              minHeight: 160,
              fontSize: 13,
              background: 'rgba(255,255,255,0.02)',
            }}
          >
            Plot not found.
            <br />
            Copy it to <code>/dashboard/public/plots</code>
          </div>
        ) : (
          <img
            src={src}
            alt={title}
            className="w-100 rounded-3"
            style={{ border: '1px solid var(--card-border)', background: 'rgba(255,255,255,0.02)' }}
            onError={() => setMissing(true)}
          />
        )}
      </Card.Body>
    </Card>
  )
}

export default function AnalysisPanel({ history, comfortRange = { min: 36, max: 37.5 } }) {
  const data = useMemo(() => {
    const arr = Array.isArray(history) ? history : []
    return arr
      .filter((d) => d && d.ts)
      .map((d) => ({
        ...d,
        t: fmtTime(d.ts),
      }))
  }, [history])

  const latest = data.length ? data[data.length - 1] : null

  const avg = (key) => {
    const vals = data.map((d) => d[key]).filter((v) => typeof v === 'number' && !Number.isNaN(v))
    if (!vals.length) return null
    return vals.reduce((a, b) => a + b, 0) / vals.length
  }

  const avgTemp = avg('temp')
  const avgPulse = avg('pulse')
  const avgBattery = avg('battery')

  const plots = [
    { title: 'Temperature over time', src: '/plots/01_temperature_over_time.png' },
    { title: 'Pads vs temperature', src: '/plots/02_pads_vs_temperature.png' },
    { title: 'Distributions', src: '/plots/03_distributions.png' },
    { title: 'LSTM: predicted vs real', src: '/plots/04_lstm_predicted_vs_real.png' },
  ]

  return (
    <div className="analysis-panel">
      <Row className="g-4">
        <Col lg={12}>
          <Card className="glass-card border-0">
            <Card.Body className="p-4">
              <div className="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3 mb-3">
                <div>
                  <h6 className="section-title mb-1">Real-time analysis</h6>
                  <div className="text-muted" style={{ fontSize: 14 }}>
                    Last {data.length} samples{latest?.t ? ` · Updated ${latest.t}` : ''}
                  </div>
                </div>
                <div className="d-flex flex-wrap gap-2">
                  <StatPill label="Avg temp" value={avgTemp != null ? `${avgTemp.toFixed(1)}°C` : '--'} />
                  <StatPill label="Avg pulse" value={avgPulse != null ? `${avgPulse.toFixed(0)} bpm` : '--'} />
                  <StatPill label="Avg battery" value={avgBattery != null ? `${avgBattery.toFixed(0)}%` : '--'} />
                </div>
              </div>

              <div className="analysis-chart">
                <ResponsiveContainer width="100%" height={320}>
                  <LineChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid stroke="rgba(148, 163, 184, 0.18)" strokeDasharray="4 6" />
                    <XAxis dataKey="t" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                    <YAxis yAxisId="temp" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <YAxis yAxisId="pulse" orientation="right" tick={{ fontSize: 12 }} domain={['auto', 'auto']} />
                    <Tooltip
                      contentStyle={{
                        background: 'var(--bg-card)',
                        border: '1px solid var(--card-border)',
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <ReferenceLine yAxisId="temp" y={comfortRange.min} stroke="rgba(245, 158, 11, 0.6)" strokeDasharray="6 6" />
                    <ReferenceLine yAxisId="temp" y={comfortRange.max} stroke="rgba(245, 158, 11, 0.6)" strokeDasharray="6 6" />
                    <Line
                      yAxisId="temp"
                      type="monotone"
                      dataKey="temp"
                      name="Temp (°C)"
                      stroke="var(--teal)"
                      dot={false}
                      strokeWidth={2}
                    />
                    <Line
                      yAxisId="pulse"
                      type="monotone"
                      dataKey="pulse"
                      name="Pulse (bpm)"
                      stroke="var(--violet)"
                      dot={false}
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <Row className="g-3 mt-2">
                <Col lg={6}>
                  <div className="analysis-mini">
                    <div className="fw-bold mb-2" style={{ fontSize: 14 }}>
                      Battery (%)
                    </div>
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={data}>
                        <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="4 6" />
                        <XAxis dataKey="t" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--card-border)',
                            borderRadius: 12,
                            fontSize: 12,
                          }}
                        />
                        <Line type="monotone" dataKey="battery" stroke="var(--cyan)" dot={false} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Col>
                <Col lg={6}>
                  <div className="analysis-mini">
                    <div className="fw-bold mb-2" style={{ fontSize: 14 }}>
                      Heating output (%)
                    </div>
                    <ResponsiveContainer width="100%" height={180}>
                      <LineChart data={data}>
                        <CartesianGrid stroke="rgba(148, 163, 184, 0.16)" strokeDasharray="4 6" />
                        <XAxis dataKey="t" tick={{ fontSize: 12 }} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 12 }} domain={[0, 100]} />
                        <Tooltip
                          contentStyle={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--card-border)',
                            borderRadius: 12,
                            fontSize: 12,
                          }}
                        />
                        <Line type="monotone" dataKey="pad1" name="Pad 1" stroke="var(--teal)" dot={false} strokeWidth={2} />
                        <Line type="monotone" dataKey="pad2" name="Pad 2" stroke="var(--coral)" dot={false} strokeWidth={2} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Col>
              </Row>
            </Card.Body>
          </Card>
        </Col>

        <Col lg={12}>
          <Card className="glass-card border-0">
            <Card.Body className="p-4">
              <div className="d-flex flex-column flex-md-row align-items-start align-items-md-center justify-content-between gap-3 mb-3">
                <div>
                  <h6 className="section-title mb-1">Model / training plots</h6>
                  <div className="text-muted" style={{ fontSize: 14 }}>
                    These appear automatically when the PNGs exist in <code>/dashboard/public/plots</code>.
                  </div>
                </div>
              </div>
              <Row className="g-3">
                {plots.map((p) => (
                  <Col key={p.src} md={6} lg={3}>
                    <TrainingPlot title={p.title} src={p.src} />
                  </Col>
                ))}
              </Row>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

