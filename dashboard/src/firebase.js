import { initializeApp } from 'firebase/app'
import { getDatabase, ref, onValue, set, get } from 'firebase/database'
import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  GoogleAuthProvider,
  signInWithPopup,
} from 'firebase/auth'

const firebaseConfig = {
  apiKey:            import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain:        import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  databaseURL:       import.meta.env.VITE_FIREBASE_DATABASE_URL,
  projectId:         import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket:     import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId:             import.meta.env.VITE_FIREBASE_APP_ID,
}

const hasConfig = firebaseConfig.apiKey && firebaseConfig.databaseURL

let db = null
let auth = null
let googleProvider = null

if (hasConfig) {
  const app = initializeApp(firebaseConfig)
  db = getDatabase(app)
  auth = getAuth(app)
  googleProvider = new GoogleAuthProvider()
}

// ─── CURRENT USER ─────────────────────────

export async function setCurrentUser(uid) {
  if (!db || !uid) return false
  await set(ref(db, 'meta/current_user'), { uid, updated_at: Date.now() })
  return true
}

export async function getCurrentUser() {
  if (!db) return null
  const snap = await get(ref(db, 'meta/current_user'))
  return snap.exists() ? snap.val().uid : null
}

// 🔥 REALTIME LISTENER (NEW)

export function listenToCurrentUser(callback) {
  if (!db) return () => {}

  const metaRef = ref(db, 'meta/current_user')

  return onValue(metaRef, (snap) => {
    const uid = snap.val()?.uid || null
    console.log("🧠 META UID UPDATE:", uid)
    callback(uid)
  })
}

// ─── DEVICE STATUS ─────────────────────────

export async function setDeviceStatus(uid, status) {
  if (!db || !uid) return false
  await set(ref(db, `users/${uid}/status`), {
    state: status,
    updated_at: Date.now(),
  })
  return true
}

// ─── SENSORS ─────────────────────────

export function subscribeToSensors(uid, callback) {
  if (!db) return () => {}

  console.log("🔌 Subscribing UID:", uid)

  const unsubs = []
  let primaryReceived = false

  if (uid) {
    unsubs.push(
      onValue(ref(db, `users/${uid}/sensor`), (snap) => {
        if (snap.exists()) {
          primaryReceived = true
          console.log("✅ USER DATA:", snap.val())
          callback(snap.val())
        }
      })
    )
  }

  // fallback (optional)
  unsubs.push(
    onValue(ref(db, 'sensor'), (snap) => {
      if (!primaryReceived && snap.exists()) {
        console.log("⚠️ FALLBACK sensor")
        callback(snap.val())
      }
    })
  )

  return () => unsubs.forEach((u) => u())
}

// ─── HEATING ─────────────────────────

export function subscribeToCommand(callback) {
  if (!db) return () => {}
  return onValue(ref(db, 'heating/pad_level'), (snap) => callback(snap.val()))
}

// ─── AUTH ─────────────────────────

export function subscribeToAuth(callback) {
  if (!auth) return () => {}
  return onAuthStateChanged(auth, async (user) => {
    if (user?.uid) {
      await setCurrentUser(user.uid)
    }
    callback(user)
  })
}

export function loginWithEmail(email, password) {
  return signInWithEmailAndPassword(auth, email, password)
}

export function registerWithEmail(email, password) {
  return createUserWithEmailAndPassword(auth, email, password)
}

export function loginWithGoogle() {
  return signInWithPopup(auth, googleProvider)
}

export function logout() {
  return signOut(auth)
}

// ─── PROFILE ─────────────────────────

export async function loadUserProfile(uid) {
  if (!db || !uid) return null
  const snap = await get(ref(db, `users/${uid}/profile`))
  return snap.exists() ? snap.val() : null
}

export async function saveUserProfile(uid, profile) {
  if (!db || !uid) return false
  const payload = { ...profile, updated_at: Date.now() }
  await set(ref(db, `users/${uid}/profile`), payload)
  return true
}

export const isFirebaseConfigured = !!hasConfig
