import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Container, Card } from 'react-bootstrap'
import { ArrowLeft, User } from 'lucide-react'
import { loadUserProfile, saveUserProfile, subscribeToAuth, isFirebaseConfigured } from './firebase'
import logo from './logo.png'

export default function ProfilePage() {
  const navigate = useNavigate()

  const [user, setUser]                 = useState(null)
  const [profile, setProfile]           = useState({ age_years: '', height_cm: '', weight_kg: '', gender_0_1: '1' })
  const [profileError, setProfileError] = useState('')
  const [saved, setSaved]               = useState(false)
  const [loading, setLoading]           = useState(true)

  useEffect(() => {
    const unsub = subscribeToAuth(async (u) => {
      if (!u) { navigate('/'); return }
      setUser(u)
      if (u?.uid) {
        const existing = await loadUserProfile(u.uid)
        if (existing) {
          setProfile({
            age_years:  String(existing.age_years  ?? ''),
            height_cm:  String(existing.height_cm  ?? ''),
            weight_kg:  String(existing.weight_kg  ?? ''),
            gender_0_1: String(existing.gender_0_1 ?? '1'),
          })
        }
      }
      setLoading(false)
    })
    return () => unsub()
  }, [])

  const handleSubmit = async (e) => {
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
    setSaved(true)
    setTimeout(() => navigate('/dashboard'), 1500)  // ← was '/'
  }

  if (loading) return (
    <div style={{ minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <span className="spinner-border text-secondary" />
    </div>
  )

  return (
    <div className="min-vh-100">
      <div className="dashboard-bg" />
      <div className="orb orb-1" />
      <div className="orb orb-2" />

      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="dashboard-header py-4"
      >
        <Container>
          <div className="d-flex justify-content-between align-items-center">
            <h1 className="h5 mb-0 d-flex align-items-center gap-3">
              <img src={logo} alt="Logo" style={{ height: '32px', width: '32px', objectFit: 'contain' }} />
              <span className="logo-text" style={{ fontFamily: "var(--font-display)", fontSize: "2.05rem", fontWeight: 700, letterSpacing: "0.5px" }}>
                HeatSync
              </span>
            </h1>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary rounded-pill d-flex align-items-center gap-2"
              onClick={() => navigate('/dashboard')}  // ← was '/'
            >
              <ArrowLeft size={16} />
              Back to Dashboard
            </button>
          </div>
        </Container>
      </motion.header>

      <main className="py-5">
        <Container>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            style={{ maxWidth: 600, margin: '0 auto' }}
          >
            <div className="d-flex align-items-center gap-3 mb-4">
              <span className="d-inline-flex align-items-center justify-content-center rounded-4"
                style={{ width: 48, height: 48, border: '1px solid var(--card-border)', background: 'rgba(255,255,255,0.03)', color: 'var(--teal)' }}>
                <User size={22} />
              </span>
              <div>
                <h4 className="mb-0 fw-bold">User Profile</h4>
                <small className="text-muted">Used to personalise your heating vest settings</small>
              </div>
            </div>

            <Card className="glass-card border-0">
              <Card.Body className="p-4">
                {saved ? (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center py-4"
                  >
                    <div style={{ fontSize: '2.5rem' }}>✓</div>
                    <div className="fw-bold mt-2" style={{ color: 'var(--teal)' }}>Profile saved!</div>
                    <small className="text-muted">Redirecting to dashboard...</small>
                  </motion.div>
                ) : (
                  <form className="row g-3" onSubmit={handleSubmit}>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Age</label>
                      <input className="form-control" type="number" placeholder="e.g. 25"
                        value={profile.age_years}
                        onChange={(e) => setProfile((p) => ({ ...p, age_years: e.target.value }))} required />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Gender</label>
                      <select className="form-select" value={profile.gender_0_1}
                        onChange={(e) => setProfile((p) => ({ ...p, gender_0_1: e.target.value }))}>
                        <option value="1">Male</option>
                        <option value="0">Female</option>
                      </select>
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Height (cm)</label>
                      <input className="form-control" type="number" step="0.1" placeholder="e.g. 170"
                        value={profile.height_cm}
                        onChange={(e) => setProfile((p) => ({ ...p, height_cm: e.target.value }))} required />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label fw-semibold">Weight (kg)</label>
                      <input className="form-control" type="number" step="0.1" placeholder="e.g. 65"
                        value={profile.weight_kg}
                        onChange={(e) => setProfile((p) => ({ ...p, weight_kg: e.target.value }))} required />
                    </div>
                    {profileError && (
                      <div className="col-12">
                        <small className="text-warning">{profileError}</small>
                      </div>
                    )}
                    <div className="col-12 mt-2">
                      <button className="btn btn-primary w-100" type="submit">Save Profile</button>
                    </div>
                  </form>
                )}
              </Card.Body>
            </Card>
          </motion.div>
        </Container>
      </main>
    </div>
  )
}