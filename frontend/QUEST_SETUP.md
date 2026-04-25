# Quest 2 Setup — Aegis-Route VR

## Prerequisites
- Dev machine and Quest 2 on the **same WiFi network**
- Node 18+ installed

## Steps

1. Install dependencies (first time only):
   ```
   cd frontend
   npm install
   ```

2. Configure tokens (recommended):
   ```
   cp .env.example .env
   ```
   Then set `VITE_DEV_HTTPS=true`, `VITE_CESIUM_ION_TOKEN` (required for terrain/imagery), and optionally `VITE_MAPBOX_TOKEN` (for the Three.js terrain tiles).

2. Start dev server:
   ```
   npm run dev
   ```

3. Note the **network URL** shown by Vite, e.g.:
   ```
   https://192.168.1.X:5173
   ```

4. On Quest 2: open **Oculus Browser**, navigate to that URL.

5. Accept the self-signed certificate warning:
   - Tap **Advanced** → **Proceed to site**

6. Tap the **ENTER VR** button at the bottom of the screen.

7. Controller mapping:
   - **Left trigger** — set start point (green ring)
   - **Right trigger** — set end point (red ring)
   - **Right grip** — dispatch route

## Backend access from Quest 2

The backend (FastAPI on port 8000) must be reachable from the headset.

**Option A (same machine, local network):**
Set `VITE_BACKEND_URL` in `.env` to your machine's LAN IP:
```bash
VITE_BACKEND_URL=http://192.168.1.X:8000
```

**Option B (deployed backend):**
Set `VITE_BACKEND_URL` to the public deployment URL.

## ElevenLabs voice alerts

Pass your API key via URL param (no code change needed):
```
https://192.168.1.X:5173?apikey=YOUR_KEY_HERE
```

## Offline / mock mode

If the backend is unreachable, the app falls back to mock data automatically.
The Eaton Fire replay button always works (uses hardcoded data, no API needed).
