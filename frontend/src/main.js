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
  if (replay.isPlaying) return;

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
    if (!start || !end) { dispatching = false; return; }

    speak('Route calculated. Dispatching unit to destination.');
    const result = await fetchRoute(start.lat, start.lng, end.lat, end.lng);
    const waypoints = result.path ?? result.waypoints ?? [];
    cesium.addSingleRoute(waypoints, 'dispatched');
    if (result.rerouted) {
      speak('Warning. Route rerouted due to hazard. New path calculated.');
      cesium.highlightReroute('dispatched');
    }

    clickState = 0;
    dispatching = false;
    updateInstructions('Click to set START point');
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
