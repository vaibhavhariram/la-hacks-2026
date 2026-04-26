import { CesiumViewer } from './scene/CesiumViewer.js';
import { ReplayController } from './scene/ReplayController.js';
import { fetchState, fetchRoute, postHazard } from './api/client.js';
import { speak } from './audio/VoiceAlerts.js';

// Cesium owns the full viewport — mount it to #cesium-container
const cesium = new CesiumViewer('cesium-container');
const replay = new ReplayController();

// --- State polling (every 2s) ---
let latestHazards = [];

async function poll() {
  const state = await fetchState();

  const dot = document.getElementById('status-dot');
  const txt = document.getElementById('status-text');

  if (state) {
    dot?.classList.add('connected');
    if (txt) txt.textContent = 'CONNECTED';

    if (state.routes) cesium.syncRoutes(state.routes);

    if (state.hazards) {
      latestHazards = state.hazards;
      cesium.syncHazards(latestHazards);
    }
  } else {
    dot?.classList.remove('connected');
    if (txt) txt.textContent = 'OFFLINE';
  }
}

poll();
setInterval(poll, 2000);

// --- Click-to-dispatch (desktop) ---
let clickState = 0; // 0=set start, 1=set end, 2=dispatch
let dispatching = false;

cesium.onLeftClick(async ({ lat, lng }) => {

  if (clickState === 0) {
    cesium.setStartMarker(lat, lng);
    clickState = 1;
    updateInstructions('Right trigger / next click: Set END point');
  } else if (clickState === 1) {
    cesium.setEndMarker(lat, lng);
    clickState = 2;
    updateInstructions('Click again to dispatch route');
  } else {
    if (dispatching) return;
    dispatching = true;
    const start = cesium.getStartLatLng();
    const end = cesium.getEndLatLng();
    console.log('[dispatch] start:', start, 'end:', end);
    if (!start || !end) { dispatching = false; return; }

    updateInstructions('Calculating route...');
    try {
      const result = await fetchRoute(start.lat, start.lng, end.lat, end.lng);
      console.log('[dispatch] result:', result);
      const waypoints = result.waypoints ?? [];
      if (waypoints.length === 0) {
        updateInstructions('No route found — try points closer to Altadena streets');
        dispatching = false;
        clickState = 0;
        return;
      }
      cesium.addSingleRoute(waypoints, 'dispatched');
      if (result.rerouted) {
        speak('Warning. Route rerouted due to hazard. New path calculated.');
        cesium.highlightReroute('dispatched');
      } else {
        speak('Route calculated. Dispatching unit to destination.');
      }
      updateInstructions('Click to set START point');
    } catch (e) {
      console.error('[dispatch] error:', e);
      updateInstructions('Route error: ' + e.message);
    } finally {
      dispatching = false;
      clickState = 0;
    }
  }
});

function updateInstructions(text) {
  const el = document.getElementById('instructions');
  if (el) el.innerHTML = text;
}

// --- Replay ---
const replayHazards = [];

document.getElementById('replay-btn')?.addEventListener('click', () => {
  if (replay.isPlaying) {
    replay.stopReplay();
    document.getElementById('replay-btn').textContent = 'REPLAY EATON FIRE';
    return;
  }

  replayHazards.length = 0;
  replay.startReplay(async (event) => {
    const id = `replay-${event.timestamp_ms}`;
    replayHazards.push({ id, ...event });
    cesium.syncHazards([...latestHazards, ...replayHazards]);
    await postHazard(event.lat, event.lng, event.radius_m, 0.9, 'fire');
  });

  document.getElementById('replay-btn').textContent = 'STOP REPLAY';
  speak('Eaton Fire replay initiated. January eighth, twenty twenty five.');
});

// --- Demo route button ---
// Pre-set: Lake Ave (west Altadena) → Eaton Ave (east Altadena), right through the fire path
const DEMO_START = { lat: 34.1897, lng: -118.1480 };
const DEMO_END   = { lat: 34.1895, lng: -118.0920 };

document.getElementById('demo-route-btn')?.addEventListener('click', async () => {
  cesium.setStartMarker(DEMO_START.lat, DEMO_START.lng);
  cesium.setEndMarker(DEMO_END.lat, DEMO_END.lng);
  updateInstructions('Calculating demo route...');
  const result = await fetchRoute(DEMO_START.lat, DEMO_START.lng, DEMO_END.lat, DEMO_END.lng);
  const waypoints = result.waypoints ?? [];
  if (waypoints.length) {
    cesium.addSingleRoute(waypoints, 'dispatched');
    speak('Route calculated. Dispatching unit to destination.');
    updateInstructions('Click REPLAY EATON FIRE to watch rerouting');
  } else {
    updateInstructions('No route found for demo coordinates');
  }
  clickState = 0;
});

// --- Home button ---
document.getElementById('home-btn')?.addEventListener('click', () => {
  cesium.flyHome();
});

// --- VR button ---
document.getElementById('enter-vr-btn')?.addEventListener('click', () => {
  alert('Open this URL on the Quest 2 browser, then use the Cesium globe in fullscreen mode.');
});

// --- Replay controller update (needs a RAF loop for the clock overlay) ---
function rafLoop() {
  replay.update(16); // ~60fps tick for the clock display
  requestAnimationFrame(rafLoop);
}
rafLoop();
