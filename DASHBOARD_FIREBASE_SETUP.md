# Dashboard → Firebase setup

The dashboard uses the **Firebase Web SDK** (different from the Admin SDK used by Python). Follow these steps to connect the dashboard to your Firebase project.

---

## Step 1: Open Firebase Console

1. Go to **https://console.firebase.google.com/**
2. Sign in and open your project **smart-heater-b8aca**

---

## Step 2: Add a Web app (if you haven’t)

1. Click the **gear icon** next to **Project overview** → **Project settings**
2. Scroll to **Your apps**
3. If you see a **Web** app (</> icon), click it and copy the config
4. If you don’t see one, click **Add app** → choose **Web** (</>)
5. Enter an app nickname (e.g. `dashboard`) → **Register app**
6. You’ll see a `firebaseConfig` object

---

## Step 3: Copy the config values

Copy these values from the `firebaseConfig` object:

| Config value | What you’ll see |
|--------------|----------------|
| `apiKey` | `"AIza..."` (long string) |
| `authDomain` | `smart-heater-b8aca.firebaseapp.com` |
| `databaseURL` | `https://smart-heater-b8aca-default-rtdb.XXXX.firebaseio.com` or `...firebasedatabase.app` |
| `projectId` | `smart-heater-b8aca` |
| `storageBucket` | `smart-heater-b8aca.appspot.com` |
| `messagingSenderId` | Numbers like `123456789` |
| `appId` | `"1:123456:web:abc123"` |

---

## Step 4: Create `dashboard/.env`

1. Create a file named `.env` in the **dashboard** folder (same folder as `package.json`)
2. Paste this and fill in the values you copied:

```env
VITE_FIREBASE_API_KEY=AIza...your_api_key
VITE_FIREBASE_AUTH_DOMAIN=smart-heater-b8aca.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://smart-heater-b8aca-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=smart-heater-b8aca
VITE_FIREBASE_STORAGE_BUCKET=smart-heater-b8aca.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your_sender_id
VITE_FIREBASE_APP_ID=1:123456:web:abc123
```

---

## Step 5: Realtime Database rules

Make sure the dashboard can read the database:

1. Firebase Console → **Build** → **Realtime Database** → **Rules**
2. For testing, you can use:

```json
{
  "rules": {
    ".read": true,
    ".write": "auth != null"
  }
}
```

For production, tighten rules so only authenticated users can read.

---

## Step 6: Run the dashboard

```bash
cd dashboard
npm install
npm run dev
```

Open **http://localhost:3000**. The dashboard should connect to Firebase and show live data when the Python listener sends updates to `sensors/latest` and `heating/command`.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Banner says "Add Firebase Web config" | Check that `.env` is in the `dashboard` folder and all env vars start with `VITE_` |
| "Permission denied" | Update Realtime Database rules (see Step 5) |
| No data showing | Ensure the Python listener is running and writing to Firebase |
| Database URL wrong | Use the exact URL from Firebase Console → Realtime Database (top of page) |
