# Cloud integration (Firebase) — step-by-step on the website

Module 2 talks to the vest (ESP32) and dashboard via **Firebase Realtime Database**. Follow these steps on the Firebase website.

---

## Step 1: Open Firebase and sign in

1. Open a browser and go to: **https://console.firebase.google.com/**
2. Sign in with your **Google account** (same one you use for Gmail, etc.).

---

## Step 2: Create a new project (or use an existing one)

1. On the Firebase welcome page, click **“Create a project”** (or **“Add project”** if you already have projects).
2. **Project name:** e.g. `smart-heating-vest` (or any name you like).  
   Click **Continue**.
3. **Google Analytics:** you can turn it **Off** for this project to keep it simple.  
   Click **Continue**, then **Create project**.
4. Wait until you see **“Your project is ready”**.  
   Click **Continue**.  
   You should now be on the **Project overview** page (dashboard).

---

## Step 3: Create the Realtime Database

1. In the **left sidebar**, click **“Build”** (or the **>** to expand it).
2. Click **“Realtime Database”**.
3. Click **“Create Database”**.
4. **Location:** choose a region close to you (e.g. `europe-west1` or `us-central1`).  
   Click **Next**.
5. **Security rules:** choose **“Start in test mode”** (we’ll lock it down later).  
   Click **Enable**.
6. After it’s created, you’ll see an empty database and a URL at the top, e.g.  
   `https://smart-heating-vest-default-rtdb.europe-west1.firebasedatabase.com`  
   **Copy this URL** — this is your **FIREBASE_DB_URL** (you’ll paste it in `.env` later).  
   - If your URL looks like `https://….firebaseio.com` (no region in the middle), that’s the older format; it’s still valid — use it as-is.

---

## Step 4: Get your Database URL (if you didn’t copy it)

1. In the left sidebar, click the **gear icon** next to **“Project overview”**.
2. Click **“Project settings”**.
3. Scroll down to **“Your apps”**.
4. If you see a **Realtime Database** section with a URL, **copy that URL**.  
   If you don’t see it, go back to **Build → Realtime Database** — the URL is shown at the top of the database view.

---

## Step 5: Create a service account key (for Python)

This key lets your Python script (Module 2) connect to Firebase.

1. Stay in **Project settings** (gear → Project settings).
2. Open the **“Service accounts”** tab at the top.
3. You’ll see “Firebase Admin SDK” and a list of service accounts.
4. Scroll down and click **“Generate new private key”** (or “Generate key”).  
   A dialog may say “Someone with access to this key can read/write your project.”  
   Click **“Generate key”**.
5. A **JSON file** will download (e.g. `smart-heating-vest-firebase-adminsdk-xxxxx.json`).
6. **Rename** this file to **`serviceAccountKey.json`**.
7. **Move** it into your **project folder** (the same folder where `run_firebase_listener.py` and `module2` are), e.g.:  
   `c:\Users\niku\.vscode\Desktop\smart heating prediction\serviceAccountKey.json`
8. **Important:** Never put this file in Git. Add to `.gitignore`:  
   `serviceAccountKey.json`  
   `.env`

---

## Step 6: Set up your `.env` file (in your project)

1. In your project folder, copy **`.env.example`** and rename the copy to **`.env`**.
2. Open **`.env`** in an editor and set:
   - **FIREBASE_CREDENTIALS** = path to the key file.  
     If the file is in the project root, use:  
     `FIREBASE_CREDENTIALS=serviceAccountKey.json`
   - **FIREBASE_DB_URL** = the Database URL you copied in Step 3 or 4, e.g.:  
     `FIREBASE_DB_URL=https://smart-heating-vest-default-rtdb.europe-west1.firebasedatabase.com`  
     (no slash at the end)
3. Save the file.

---

## Step 7: Run the cloud listener (on your PC)

1. Open a terminal in the **project folder**.
2. Install dependencies (if you haven’t):  
   `pip install firebase-admin python-dotenv`
3. Run:  
   `python run_firebase_listener.py`
4. You should see something like:  
   `Firebase listener attached: sensors/latest → heating/command`  
   and the script will keep running (listening for sensor data).
5. To stop: press **Ctrl+C**.

---

## Quick recap (what you did on the Firebase website)

| Step | Where on Firebase | What you did |
|------|-------------------|--------------|
| 1 | console.firebase.google.com | Signed in |
| 2 | Create project | Named project, created it |
| 3 | Build → Realtime Database | Created DB, chose region, test mode, **copied DB URL** |
| 4 | Project settings (optional) | Got DB URL if needed |
| 5 | Project settings → Service accounts | **Generated new private key**, saved as `serviceAccountKey.json` in project |

After that: you put the DB URL and key path in `.env` and ran `python run_firebase_listener.py`.

---

## Reference: Database structure

Module 2 expects this layout:

| Path | Who writes | Content |
|------|------------|--------|
| `sensors/latest` | ESP32 (Module 3) | Latest sensor reading: `body_temperature_C`, `pulse_bpm`, `motion_level_0_1`, `pad1_pwm_0_100`, `pad2_pwm_0_100` |
| `heating/command` | Module 2 (Python) | Command for ESP32: `pad1`, `pad2` (PWM 0–100) |

Example **sensors/latest** (ESP32 writes):

```json
{
  "body_temperature_C": 36.5,
  "pulse_bpm": 72,
  "motion_level_0_1": 0.2,
  "pad1_pwm_0_100": 25,
  "pad2_pwm_0_100": 30
}
```

Example **heating/command** (Module 2 writes):

```json
{
  "pad1": 28.0,
  "pad2": 32.0
}
```

You can change paths in `module2/config.py`: `FIREBASE_PATH_SENSORS`, `FIREBASE_PATH_COMMAND`.

---

## Reference: Security rules (Realtime Database)

For production, lock down rules and use auth. Example (adjust to your auth):

```json
{
  "rules": {
    "sensors": { ".read": true, ".write": "auth != null" },
    "heating": { ".read": "auth != null", ".write": true }
  }
}
```

Use Firebase Admin in Python with the service account; the ESP32 can use a token or restricted write rules.
