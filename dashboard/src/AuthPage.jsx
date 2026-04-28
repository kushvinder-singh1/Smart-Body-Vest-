import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { loginWithEmail, registerWithEmail, loginWithGoogle, loadUserProfile } from './firebase'
import logo from './logo.png'

// ─── tiny helpers ────────────────────────────────────────────────────────────
const GoogleIcon = () => (
  <svg width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M17.64 9.205c0-.639-.057-1.252-.164-1.841H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
    <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
    <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
    <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
  </svg>
)

const EyeIcon = ({ open }) => open ? (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
  </svg>
) : (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
    <line x1="1" y1="1" x2="23" y2="23"/>
  </svg>
)

function friendlyAuthError(err) {
  const code = err?.code || ''
  switch (code) {
    case 'auth/invalid-email':           return 'Please enter a valid email address.'
    case 'auth/user-not-found':          return 'No account found with this email.'
    case 'auth/wrong-password':          return 'Incorrect password. Please try again.'
    case 'auth/email-already-in-use':    return 'An account with this email already exists.'
    case 'auth/weak-password':           return 'Password must be at least 6 characters.'
    case 'auth/too-many-requests':       return 'Too many attempts. Please try again later.'
    case 'auth/user-disabled':           return 'This account has been disabled. Contact support.'
    case 'auth/network-request-failed':  return 'Network error. Check your connection and try again.'
    case 'auth/popup-closed-by-user':    return 'Sign-in was cancelled.'
    case 'auth/popup-blocked':           return 'Pop-up was blocked. Please allow pop-ups and try again.'
    case 'auth/cancelled-popup-request': return 'Sign-in was cancelled.'
    case 'auth/invalid-credential':      return 'Invalid credentials. Please check your email and password.'
    default:                             return err?.message || 'Authentication failed. Please try again.'
  }
}

function validatePassword(password, email) {
  if (password.length < 8)
    return 'Password must be at least 8 characters.'
  if (/\s/.test(password))
    return 'Password must not contain spaces.'
  if (!/[A-Z]/.test(password))
    return 'Password must include at least one uppercase letter.'
  if (!/[a-z]/.test(password))
    return 'Password must include at least one lowercase letter.'
  if (!/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password))
    return 'Password must include at least one special character.'
  const localPart = email.split('@')[0].toLowerCase()
  if (localPart && password.toLowerCase() === localPart)
    return 'Password cannot be the same as your email username.'
  return null
}

export default function AuthPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  // Read ?mode=login or ?mode=register from URL (e.g. from Landing page buttons)
  const initialMode = searchParams.get('mode') === 'register' ? 'register' : 'login'

  const [mode,       setMode]       = useState(initialMode)
  const [form,       setForm]       = useState({ email: '', password: '' })
  const [showPwd,    setShowPwd]    = useState(false)
  const [error,      setError]      = useState('')
  const [busy,       setBusy]       = useState(false)
  const [googleBusy, setGoogleBusy] = useState(false)

  // Always land on /profile after auth — ProfilePage will redirect to / if profile already exists
  const handlePostAuth = async (userCredential) => {
    const uid = userCredential?.user?.uid
    if (!uid) { navigate('/'); return }
    const existing = await loadUserProfile(uid)
    navigate(existing ? '/dashboard' : '/profile')
  }

  const handleEmailAuth = async (e) => {
    e.preventDefault()
    setError('')
    const email    = form.email.trim()
    const password = form.password
    if (!email) { setError('Please enter a valid email address.'); return }
    if (mode === 'register') {
      const pwdError = validatePassword(password, email)
      if (pwdError) { setError(pwdError); return }
    } else if (password.length < 8) {
      setError('Enter a valid email and a password of at least 8 characters.')
      return
    }
    setBusy(true)
    try {
      const result = mode === 'login'
        ? await loginWithEmail(email, password)
        : await registerWithEmail(email, password)
      await handlePostAuth(result)
    } catch (err) {
      setError(friendlyAuthError(err))
    } finally {
      setBusy(false)
    }
  }

  const handleGoogle = async () => {
    setError('')
    setGoogleBusy(true)
    try {
      const result = await loginWithGoogle()
      await handlePostAuth(result)
    } catch (err) {
      setError(friendlyAuthError(err))
    } finally {
      setGoogleBusy(false)
    }
  }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Syne:wght@400;600;700;800&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg: #080c10; --surface: #0e1419;
          --border: rgba(255,255,255,0.07); --border-h: rgba(0,229,204,0.35);
          --teal: #00e5cc; --coral: #ff6b6b; --text: #e8edf2; --muted: #5a6878;
          --error: #ff6b6b; --font-display: 'Syne', sans-serif; --font-mono: 'DM Mono', monospace;
        }
        .auth-root {
          min-height: 100dvh; background: var(--bg);
          display: flex; align-items: center; justify-content: center;
          padding: 1.5rem; font-family: var(--font-mono); color: var(--text);
          position: relative; overflow: hidden;
        }
        .auth-orb { position: absolute; border-radius: 50%; filter: blur(100px); pointer-events: none; opacity: 0.18; }
        .auth-orb-1 { width: 600px; height: 600px; background: var(--teal);  top: -200px; left: -200px; }
        .auth-orb-2 { width: 500px; height: 500px; background: var(--coral); bottom: -180px; right: -150px; }
        .auth-grid {
          position: absolute; inset: 0;
          background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
          background-size: 48px 48px; pointer-events: none;
        }
        .auth-card {
          position: relative; width: 100%; max-width: 420px;
          background: var(--surface); border: 1px solid var(--border); border-radius: 20px;
          padding: 2.5rem 2.5rem 2rem; backdrop-filter: blur(20px);
          box-shadow: 0 24px 80px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.06); overflow: hidden;
        }
        .auth-card::before {
          content: ''; position: absolute; inset: 0; border-radius: inherit;
          background: linear-gradient(135deg, rgba(0,229,204,.06) 0%, transparent 60%); pointer-events: none;
        }
        .auth-logo { display: flex; align-items: center; gap: .65rem; margin-bottom: 2rem; }
        .auth-logo-name { font-family: var(--font-display); font-size: 1.05rem; font-weight: 700; letter-spacing: .5px; }
        .auth-heading { font-family: var(--font-display); font-size: 1.6rem; font-weight: 800; line-height: 1.15; margin-bottom: .4rem; }
        .auth-sub { font-size: .78rem; color: var(--muted); margin-bottom: 1.75rem; letter-spacing: .2px; }
        .btn-google {
          display: flex; align-items: center; justify-content: center; gap: .6rem;
          width: 100%; padding: .72rem 1rem;
          background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px;
          color: var(--text); font-family: var(--font-mono); font-size: .82rem; font-weight: 500;
          cursor: pointer; transition: border-color .2s, background .2s, transform .15s; margin-bottom: 1.25rem;
        }
        .btn-google:hover:not(:disabled) { border-color: var(--border-h); background: rgba(0,229,204,.06); transform: translateY(-1px); }
        .btn-google:disabled { opacity: .55; cursor: not-allowed; }
        .auth-divider {
          display: flex; align-items: center; gap: .75rem; margin-bottom: 1.25rem;
          font-size: .72rem; color: var(--muted); letter-spacing: .8px; text-transform: uppercase;
        }
        .auth-divider::before, .auth-divider::after { content: ''; flex: 1; height: 1px; background: var(--border); }
        .auth-field { margin-bottom: 1rem; }
        .auth-label { display: block; font-size: .72rem; letter-spacing: .8px; text-transform: uppercase; color: var(--muted); margin-bottom: .45rem; }
        .auth-input-wrap { position: relative; }
        .auth-input {
          width: 100%; padding: .72rem 1rem; background: rgba(255,255,255,.03);
          border: 1px solid var(--border); border-radius: 10px; color: var(--text);
          font-family: var(--font-mono); font-size: .85rem; outline: none;
          transition: border-color .2s, box-shadow .2s;
        }
        .auth-input:focus { border-color: var(--border-h); box-shadow: 0 0 0 3px rgba(0,229,204,.08); }
        .auth-input.has-toggle { padding-right: 2.8rem; }
        .pwd-toggle {
          position: absolute; right: .85rem; top: 50%; transform: translateY(-50%);
          background: none; border: none; color: var(--muted); cursor: pointer;
          display: flex; align-items: center; padding: .15rem; transition: color .2s;
        }
        .pwd-toggle:hover { color: var(--text); }
        .auth-error {
          font-size: .78rem; color: var(--error); background: rgba(255,107,107,.08);
          border: 1px solid rgba(255,107,107,.2); border-radius: 8px;
          padding: .55rem .85rem; margin-bottom: 1rem; line-height: 1.4;
        }
        .btn-submit {
          width: 100%; padding: .78rem 1rem; background: var(--teal); border: none; border-radius: 10px;
          color: #080c10; font-family: var(--font-display); font-size: .9rem; font-weight: 700;
          letter-spacing: .3px; cursor: pointer;
          transition: opacity .2s, transform .15s, box-shadow .2s;
          box-shadow: 0 4px 20px rgba(0,229,204,.25); margin-top: .25rem;
        }
        .btn-submit:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); box-shadow: 0 6px 28px rgba(0,229,204,.35); }
        .btn-submit:disabled { opacity: .55; cursor: not-allowed; }
        .auth-toggle { text-align: center; margin-top: 1.4rem; font-size: .78rem; color: var(--muted); }
        .auth-toggle button {
          background: none; border: none; color: var(--teal); cursor: pointer;
          font-family: var(--font-mono); font-size: .78rem; font-weight: 500;
          padding: 0; text-decoration: underline; text-underline-offset: 3px;
        }
        .auth-toggle button:hover { opacity: .8; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .spinner {
          display: inline-block; width: 14px; height: 14px;
          border: 2px solid rgba(8,12,16,.4); border-top-color: #080c10;
          border-radius: 50%; animation: spin .7s linear infinite;
          vertical-align: middle; margin-right: .4rem;
        }
      `}</style>

      <div className="auth-root">
        <div className="auth-grid" />
        <div className="auth-orb auth-orb-1" />
        <div className="auth-orb auth-orb-2" />

        <motion.div
          className="auth-card"
          initial={{ opacity: 0, y: 28, scale: 0.97 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <div className="auth-logo">
            <img src={logo} alt="Logo" style={{ height: '32px', width: '32px', objectFit: 'contain' }} />
            <span className="auth-logo-name">HeatSync</span>
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2 }}
            >
              <h1 className="auth-heading">{mode === 'login' ? 'Welcome back.' : 'Create account.'}</h1>
              <p className="auth-sub">
                {mode === 'login'
                  ? 'Sign in to access your vest dashboard.'
                  : 'Register to start monitoring your vest.'}
              </p>
            </motion.div>
          </AnimatePresence>

          <button className="btn-google" onClick={handleGoogle} disabled={googleBusy || busy} type="button">
            {googleBusy
              ? <><span className="spinner" style={{ borderTopColor: '#fff' }} /> Signing in…</>
              : <><GoogleIcon /> Continue with Google</>}
          </button>

          <div className="auth-divider">or</div>

          <form onSubmit={handleEmailAuth} noValidate>
            <div className="auth-field">
              <label className="auth-label" htmlFor="auth-email">Email</label>
              <div className="auth-input-wrap">
                <input
                  id="auth-email" className="auth-input" type="email" autoComplete="email"
                  placeholder="you@example.com" value={form.email}
                  onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))} required
                />
              </div>
            </div>
            <div className="auth-field">
              <label className="auth-label" htmlFor="auth-password">Password</label>
              <div className="auth-input-wrap">
                <input
                  id="auth-password" className={`auth-input has-toggle`}
                  type={showPwd ? 'text' : 'password'}
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  placeholder="Min. 8 chars, upper/lower, special"
                  value={form.password}
                  onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))} required
                />
                <button type="button" className="pwd-toggle" onClick={() => setShowPwd(v => !v)} aria-label={showPwd ? 'Hide password' : 'Show password'}>
                  <EyeIcon open={showPwd} />
                </button>
              </div>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div className="auth-error"
                  initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.2 }}>
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

            <button className="btn-submit" type="submit" disabled={busy || googleBusy}>
              {busy ? <><span className="spinner" />Please wait…</> : mode === 'login' ? 'Sign in' : 'Create account'}
            </button>
          </form>

          <div className="auth-toggle">
            {mode === 'login' ? (
              <>Don&apos;t have an account?{' '}
                <button type="button" onClick={() => { setMode('register'); setError('') }}>Register</button>
              </>
            ) : (
              <>Already have an account?{' '}
                <button type="button" onClick={() => { setMode('login'); setError('') }}>Sign in</button>
              </>
            )}
          </div>
        </motion.div>
      </div>
    </>
  )
}
