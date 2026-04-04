# Smart Heating Vest — Dashboard

Fitbit-style React dashboard for real-time monitoring of the smart heating vest.

## Setup

1. **Install dependencies**
   ```bash
   cd dashboard
   npm install
   ```

2. **Configure Firebase** — see **[DASHBOARD_FIREBASE_SETUP.md](../DASHBOARD_FIREBASE_SETUP.md)** for step-by-step instructions.
   - Firebase Console → Project settings → Your apps → Web app (</>)
   - Copy `apiKey`, `messagingSenderId`, `appId` into `dashboard/.env`

3. **Run**
   ```bash
   npm run dev
   ```
   Open http://localhost:3000

## Features

- **Live metrics**: Body temperature, heart rate, motion
- **Heating gauges**: Pad 1 & 2 PWM levels (circular progress)
- **Status**: Cloud connection, safety thresholds
- **Analysis (click-to-expand)**: Real-time trend graphs + training plot gallery
- **Fitbit-inspired**: Dark theme, teal/coral accents, clean cards

## Training plots in the dashboard

If you generated PNG plots in the project root `plots/` folder, copy them into:

- `dashboard/public/plots/`

Or run (PowerShell):

```powershell
cd dashboard
.\scripts\sync_plots.ps1
```
