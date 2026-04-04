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

let db           = null
let auth         = null
let googleProvider = null

if (hasConfig) {
  const app    = initializeApp(firebaseConfig)
  db           = getDatabase(app)
  auth         = getAuth(app)
  googleProvider = new GoogleAuthProvider()
}

export function subscribeToSensors(callback) {
  if (!db) return () => {}
  const sensorsLatestRef = ref(db, 'sensors/latest')
  const sensorRootRef    = ref(db, 'sensor')
  const unsub1 = onValue(sensorsLatestRef, (snapshot) => callback(snapshot.val()))
  const unsub2 = onValue(sensorRootRef,    (snapshot) => callback(snapshot.val()))
  return () => { unsub1(); unsub2() }
}

export function subscribeToCommand(callback) {
  if (!db) return () => {}
  return onValue(ref(db, 'heating/command'), (snapshot) => callback(snapshot.val()))
}

export function subscribeToAuth(callback) {
  if (!auth) return () => {}
  return onAuthStateChanged(auth, (user) => callback(user))
}

export function loginWithEmail(email, password) {
  if (!auth) return Promise.reject(new Error('Firebase auth not configured'))
  return signInWithEmailAndPassword(auth, email, password)
}

export function registerWithEmail(email, password) {
  if (!auth) return Promise.reject(new Error('Firebase auth not configured'))
  return createUserWithEmailAndPassword(auth, email, password)
}

export function loginWithGoogle() {
  if (!auth || !googleProvider) return Promise.reject(new Error('Firebase auth not configured'))
  return signInWithPopup(auth, googleProvider)
}

export function logout() {
  if (!auth) return Promise.resolve()
  return signOut(auth)
}

export async function loadUserProfile(uid) {
  if (!db || !uid) return null
  const snap = await get(ref(db, `users/${uid}/profile`))
  return snap.exists() ? snap.val() : null
}

export async function saveUserProfile(uid, profile) {
  if (!db || !uid) return false
  const payload = { ...profile, updated_at: Date.now() }
  await set(ref(db, `users/${uid}/profile`), payload)
  await set(ref(db, 'user/profile'), payload)
  return true
}

export const isFirebaseConfigured = !!hasConfig