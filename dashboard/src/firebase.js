import { initializeApp } from 'firebase/app'
import { getDatabase, ref, onValue } from 'firebase/database'

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

const hasConfig = firebaseConfig.apiKey && firebaseConfig.databaseURL

let db = null
if (hasConfig) {
  const app = initializeApp(firebaseConfig)
  db = getDatabase(app)
}

export function subscribeToSensors(callback) {
  if (!db) return () => {}
  const sensorsRef = ref(db, 'sensors/latest')
  return onValue(sensorsRef, (snapshot) => callback(snapshot.val()))
}

export function subscribeToCommand(callback) {
  if (!db) return () => {}
  const cmdRef = ref(db, 'heating/command')
  return onValue(cmdRef, (snapshot) => callback(snapshot.val()))
}

export const isFirebaseConfigured = !!hasConfig
