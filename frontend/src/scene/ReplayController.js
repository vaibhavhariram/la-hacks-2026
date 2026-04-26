// Eaton Fire replay — real fire spread direction: east/northeast driven by Santa Ana winds
const EATON_FIRE_REPLAY = [
  { timestamp_ms: 0,     lat: 34.1900, lng: -118.1310, radius_m: 200 },
  { timestamp_ms: 2000,  lat: 34.1905, lng: -118.1280, radius_m: 250 },
  { timestamp_ms: 4000,  lat: 34.1912, lng: -118.1250, radius_m: 300 },
  { timestamp_ms: 6000,  lat: 34.1920, lng: -118.1220, radius_m: 350 },
  { timestamp_ms: 7000,  lat: 34.1895, lng: -118.1290, radius_m: 280 },
  { timestamp_ms: 8000,  lat: 34.1930, lng: -118.1190, radius_m: 400 },
  { timestamp_ms: 10000, lat: 34.1940, lng: -118.1160, radius_m: 450 },
  { timestamp_ms: 11000, lat: 34.1918, lng: -118.1240, radius_m: 320 },
  { timestamp_ms: 12000, lat: 34.1952, lng: -118.1130, radius_m: 500 },
  { timestamp_ms: 14000, lat: 34.1965, lng: -118.1100, radius_m: 550 },
  { timestamp_ms: 15000, lat: 34.1935, lng: -118.1180, radius_m: 420 },
  { timestamp_ms: 16000, lat: 34.1978, lng: -118.1070, radius_m: 600 },
  { timestamp_ms: 18000, lat: 34.1990, lng: -118.1040, radius_m: 650 },
  { timestamp_ms: 19000, lat: 34.1960, lng: -118.1120, radius_m: 480 },
  { timestamp_ms: 20000, lat: 34.2002, lng: -118.1010, radius_m: 700 },
  { timestamp_ms: 22000, lat: 34.2015, lng: -118.0980, radius_m: 800 },
  { timestamp_ms: 23000, lat: 34.1985, lng: -118.1060, radius_m: 560 },
  { timestamp_ms: 24000, lat: 34.2028, lng: -118.0950, radius_m: 900 },
  { timestamp_ms: 26000, lat: 34.2040, lng: -118.0920, radius_m: 1000 },
  { timestamp_ms: 27000, lat: 34.2010, lng: -118.1000, radius_m: 650 },
  { timestamp_ms: 28000, lat: 34.2052, lng: -118.0890, radius_m: 1100 },
  { timestamp_ms: 30000, lat: 34.2065, lng: -118.0860, radius_m: 1200 },
  { timestamp_ms: 32000, lat: 34.2078, lng: -118.0830, radius_m: 1350 },
  { timestamp_ms: 34000, lat: 34.2090, lng: -118.0800, radius_m: 1500 },
  { timestamp_ms: 36000, lat: 34.2035, lng: -118.0910, radius_m: 1100 },
  { timestamp_ms: 38000, lat: 34.2102, lng: -118.0770, radius_m: 1650 },
  { timestamp_ms: 42000, lat: 34.2115, lng: -118.0740, radius_m: 1800 },
  { timestamp_ms: 48000, lat: 34.2128, lng: -118.0710, radius_m: 1900 },
  { timestamp_ms: 54000, lat: 34.2140, lng: -118.0680, radius_m: 2000 },
  { timestamp_ms: 60000, lat: 34.2150, lng: -118.0650, radius_m: 2000 },
];

// Replay starts at 11:47 PM Jan 8, 2025 — 60 seconds covers ~60 minutes of real fire
const BASE_DISPLAY_MINUTES = 23 * 60 + 47; // 11:47 PM in minutes from midnight

export class ReplayController {
  constructor() {
    this.isPlaying = false;
    this._elapsed = 0;
    this._eventIndex = 0;
    this._onHazard = null;

    this._overlay = document.getElementById('replay-overlay');
    this._timeEl = document.getElementById('replay-time');
  }

  startReplay(onHazardCallback) {
    if (this.isPlaying) return;
    this.isPlaying = true;
    this._elapsed = 0;
    this._eventIndex = 0;
    this._onHazard = onHazardCallback;
    this._overlay.classList.add('active');
  }

  stopReplay() {
    this.isPlaying = false;
    this._overlay.classList.remove('active');
  }

  update(deltaMs) {
    if (!this.isPlaying) return;

    this._elapsed += deltaMs;

    // fire events whose timestamp has been passed
    while (
      this._eventIndex < EATON_FIRE_REPLAY.length &&
      EATON_FIRE_REPLAY[this._eventIndex].timestamp_ms <= this._elapsed
    ) {
      const event = EATON_FIRE_REPLAY[this._eventIndex];
      if (this._onHazard) this._onHazard(event);
      this._eventIndex++;
    }

    // update display clock: 1 second elapsed = 1 minute of fire time
    const minutesElapsed = Math.floor(this._elapsed / 1000);
    const totalMinutes = BASE_DISPLAY_MINUTES + minutesElapsed;
    const hours = Math.floor(totalMinutes / 60) % 24;
    const mins = totalMinutes % 60;
    const ampm = hours >= 12 ? 'AM' : 'PM';
    const displayHour = hours % 12 === 0 ? 12 : hours % 12;
    const displayMin = String(mins).padStart(2, '0');
    if (this._timeEl) {
      this._timeEl.textContent = `Jan 8, 2025 — ${displayHour}:${displayMin} ${ampm}`;
    }

    if (this._eventIndex >= EATON_FIRE_REPLAY.length) {
      // end of replay — leave fire visible, stop updating
      this.isPlaying = false;
    }
  }
}
