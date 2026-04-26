import {
  Ion,
  Viewer,
  Cartesian3,
  Cartographic,
  Color,
  Math as CesiumMath,
  createWorldTerrainAsync,
  createWorldImageryAsync,
  IonWorldImageryStyle,
  ImageryLayer,
  PolylineGlowMaterialProperty,
  HeightReference,
  VerticalOrigin,
  ScreenSpaceEventType,
  ConstantProperty,
} from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';

const CESIUM_ION_TOKEN = import.meta.env.VITE_CESIUM_ION_TOKEN;
Ion.defaultAccessToken = CESIUM_ION_TOKEN ?? '';

// Eaton Fire origin — Altadena, CA
const HOME_LAT = 34.1897;
const HOME_LNG = -118.1315;
const HOME_HEIGHT = 18000; // meters above terrain — close enough to see streets

// California bounds — camera snaps back if you wander too far
const CA_BOUNDS = {
  minLat: 32.0,
  maxLat: 42.5,
  minLng: -124.8,
  maxLng: -113.5,
};
const SNAP_MARGIN = 3.0; // degrees outside CA before snap triggers

function routeKey(route) {
  return route.unit_id ?? route.route_id ?? 'route';
}

export class CesiumViewer {
  constructor(containerId) {
    this.viewer = null;
    this.container = null;
    this.routeEntities = new Map();   // unitId → Entity
    this.hazardEntities = new Map();  // hazardId → Entity
    this.startMarker = null;
    this.endMarker = null;
    this._boundsCheckInterval = null;
    this.ready = this._init(containerId);
  }

  async _init(containerId) {
    // Cesium needs a real DOM container, not a canvas
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error('[CesiumViewer] container not found:', containerId);
      return;
    }

    if (!CESIUM_ION_TOKEN) {
      const message = 'Cesium Ion token missing. Set VITE_CESIUM_ION_TOKEN in frontend/.env to load the real globe imagery and terrain.';
      console.error(`[CesiumViewer] ${message}`);
      this._renderFatalError(message);
      return;
    }

    // Remove Three.js canvas if present — we own the viewport now
    const oldCanvas = document.querySelector('canvas');
    if (oldCanvas) oldCanvas.remove();

    try {
      const terrainProvider = await createWorldTerrainAsync({
        requestWaterMask: true,
        requestVertexNormals: true,
      });

      this.viewer = new Viewer(this.container, {
        terrainProvider,
        baseLayer: false,
        baseLayerPicker: false,
        geocoder: false,
        homeButton: false,
        sceneModePicker: false,
        navigationHelpButton: false,
        animation: false,
        timeline: false,
        fullscreenButton: false,
        infoBox: false,
        selectionIndicator: false,
        shadows: false,
        shouldAnimate: true,
      });

      // Bing aerial via createWorldImagery — served through Ion CDN, always CORS-safe
      this.viewer.imageryLayers.removeAll();
      this.viewer.imageryLayers.add(
        new ImageryLayer(
          await createWorldImageryAsync({
            style: IonWorldImageryStyle.AERIAL_WITH_LABELS,
          })
        )
      );

      // Maximize terrain detail
      this.viewer.scene.globe.maximumScreenSpaceError = 1.5;
      this.viewer.scene.globe.tileCacheSize = 1000;

      // Atmosphere, lighting, fog for depth
      this.viewer.scene.globe.enableLighting = true;
      this.viewer.scene.atmosphere.show = true;
      this.viewer.scene.fog.enabled = true;
      this.viewer.scene.fog.density = 0.0002;

      // Anti-alias
      this.viewer.scene.postProcessStages.fxaa.enabled = true;

      // Fly home to Altadena on load
      this.flyHome();

      // Enforce CA bounds
      this._startBoundsEnforcement();

      console.log('[CesiumViewer] Globe initialized — Altadena, CA');
    } catch (error) {
      const reason = error instanceof Error ? error.message : String(error);
      console.error('[CesiumViewer] Failed to initialize terrain/imagery:', error);
      this._renderFatalError(`Cesium globe failed to load terrain or imagery: ${reason}`);
    }
  }

  _renderFatalError(message) {
    if (!this.container) return;
    this.container.innerHTML = `
      <div style="
        position:absolute;
        inset:0;
        display:flex;
        align-items:center;
        justify-content:center;
        padding:24px;
        background:radial-gradient(circle at top, #16233d 0%, #09111f 45%, #05080f 100%);
        color:#f4f7fb;
        font-family:'Courier New', monospace;
        text-align:center;
      ">
        <div style="max-width:720px; border:1px solid rgba(255, 91, 91, 0.55); background:rgba(0, 0, 0, 0.45); padding:24px;">
          <div style="font-size:18px; letter-spacing:2px; color:#ff8f8f; margin-bottom:12px;">GLOBE INITIALIZATION FAILED</div>
          <div style="font-size:13px; line-height:1.7; color:#d7e0ee;">${message}</div>
        </div>
      </div>
    `;
  }

  flyHome() {
    if (!this.viewer) return;
    this.viewer.camera.flyTo({
      destination: Cartesian3.fromDegrees(HOME_LNG, HOME_LAT, HOME_HEIGHT),
      orientation: {
        heading: CesiumMath.toRadians(0),
        pitch: CesiumMath.toRadians(-45), // 45° tilt — Google Earth style
        roll: 0,
      },
      duration: 2.0,
    });
  }

  _startBoundsEnforcement() {
    this._boundsCheckInterval = setInterval(() => {
      if (!this.viewer) return;
      const pos = this.viewer.camera.positionCartographic;
      if (!pos) return;

      const lat = CesiumMath.toDegrees(pos.latitude);
      const lng = CesiumMath.toDegrees(pos.longitude);

      const outside =
        lat < CA_BOUNDS.minLat - SNAP_MARGIN ||
        lat > CA_BOUNDS.maxLat + SNAP_MARGIN ||
        lng < CA_BOUNDS.minLng - SNAP_MARGIN ||
        lng > CA_BOUNDS.maxLng + SNAP_MARGIN;

      if (outside) {
        this.viewer.camera.flyTo({
          destination: Cartesian3.fromDegrees(HOME_LNG, HOME_LAT, HOME_HEIGHT),
          orientation: {
            heading: 0,
            pitch: CesiumMath.toRadians(-45),
            roll: 0,
          },
          duration: 1.5,
        });
      }
    }, 1500);
  }

  // --- Routes ---

  syncRoutes(routesArray) {
    const seen = new Set();
    for (const r of routesArray) {
      const key = routeKey(r);
      seen.add(key);
      if (this.routeEntities.has(key)) {
        this._updateRoute(r);
      } else {
        this._addRoute(r);
      }
    }
    for (const [id] of this.routeEntities) {
      if (!seen.has(id)) this._removeRoute(id);
    }
  }

  _waypointsToCartesian(waypoints) {
    return waypoints.flatMap((wp) => [wp.lng, wp.lat, 20]); // 20m above ground
  }

  _addRoute(r) {
    if (!this.viewer || !r.waypoints?.length) return;
    const positions = Cartesian3.fromDegreesArrayHeights(
      this._waypointsToCartesian(r.waypoints)
    );
    const entity = this.viewer.entities.add({
      id: `route-${routeKey(r)}`,
      polyline: {
        positions,
        width: 6,
        material: new PolylineGlowMaterialProperty({
          glowPower: 0.3,
          color: Color.fromCssColorString('#0088ff'),
        }),
        clampToGround: true,
      },
    });
    this.routeEntities.set(routeKey(r), entity);
  }

  _updateRoute(r) {
    const entity = this.routeEntities.get(routeKey(r));
    if (!entity || !r.waypoints?.length) return;
    entity.polyline.positions = new ConstantProperty(
      Cartesian3.fromDegreesArrayHeights(this._waypointsToCartesian(r.waypoints))
    );
    if (r.rerouted) this._flashReroute(entity);
  }

  _flashReroute(entity) {
    entity.polyline.material = new PolylineGlowMaterialProperty({
      glowPower: 0.5,
      color: Color.fromCssColorString('#ffaa00'),
    });
    setTimeout(() => {
      if (entity.polyline) {
        entity.polyline.material = new PolylineGlowMaterialProperty({
          glowPower: 0.3,
          color: Color.fromCssColorString('#0088ff'),
        });
      }
    }, 800);
  }

  _removeRoute(unitId) {
    const entity = this.routeEntities.get(unitId);
    if (entity && this.viewer) this.viewer.entities.remove(entity);
    this.routeEntities.delete(unitId);
  }

  addSingleRoute(waypoints, unitId = 'dispatched') {
    const r = { unit_id: unitId, waypoints, rerouted: false };
    if (this.routeEntities.has(unitId)) {
      this._updateRoute(r);
    } else {
      this._addRoute(r);
    }
  }

  highlightReroute(unitId) {
    const entity = this.routeEntities.get(unitId);
    if (entity) this._flashReroute(entity);
  }

  // --- Hazards (fire circles) ---

  syncHazards(hazards) {
    const seen = new Set();
    for (const h of hazards) {
      const id = h.id ?? `${h.lat},${h.lng}`;
      seen.add(id);
      if (!this.hazardEntities.has(id)) this._addHazard(id, h);
    }
    for (const [id] of this.hazardEntities) {
      if (!seen.has(id)) this._removeHazard(id);
    }
  }

  _addHazard(id, h) {
    if (!this.viewer) return;
    const entity = this.viewer.entities.add({
      id: `hazard-${id}`,
      position: Cartesian3.fromDegrees(h.lng, h.lat),
      ellipse: {
        semiMajorAxis: h.radius_m,
        semiMinorAxis: h.radius_m,
        material: Color.fromCssColorString('#ff4400').withAlpha(0.45),
        outline: true,
        outlineColor: Color.fromCssColorString('#ff6600'),
        outlineWidth: 2,
        heightReference: HeightReference.CLAMP_TO_GROUND,
      },
    });
    this.hazardEntities.set(id, entity);
  }

  _removeHazard(id) {
    const entity = this.hazardEntities.get(id);
    if (entity && this.viewer) this.viewer.entities.remove(entity);
    this.hazardEntities.delete(id);
  }

  // --- Markers ---

  setStartMarker(lat, lng) {
    if (!this.viewer) return;
    if (this.startMarker) this.viewer.entities.remove(this.startMarker);
    this.startMarker = this.viewer.entities.add({
      id: 'marker-start',
      position: Cartesian3.fromDegrees(lng, lat, 10),
      point: {
        pixelSize: 18,
        color: Color.fromCssColorString('#00ff88'),
        outlineColor: Color.WHITE,
        outlineWidth: 2,
        heightReference: HeightReference.CLAMP_TO_GROUND,
      },
      label: {
        text: 'START',
        font: '13px monospace',
        fillColor: Color.fromCssColorString('#00ff88'),
        outlineColor: Color.BLACK,
        outlineWidth: 2,
        verticalOrigin: VerticalOrigin.BOTTOM,
        pixelOffset: { x: 0, y: -14 },
      },
    });
  }

  setEndMarker(lat, lng) {
    if (!this.viewer) return;
    if (this.endMarker) this.viewer.entities.remove(this.endMarker);
    this.endMarker = this.viewer.entities.add({
      id: 'marker-end',
      position: Cartesian3.fromDegrees(lng, lat, 10),
      point: {
        pixelSize: 18,
        color: Color.fromCssColorString('#ff4444'),
        outlineColor: Color.WHITE,
        outlineWidth: 2,
        heightReference: HeightReference.CLAMP_TO_GROUND,
      },
      label: {
        text: 'END',
        font: '13px monospace',
        fillColor: Color.fromCssColorString('#ff4444'),
        outlineColor: Color.BLACK,
        outlineWidth: 2,
        verticalOrigin: VerticalOrigin.BOTTOM,
        pixelOffset: { x: 0, y: -14 },
      },
    });
  }

  clearMarkers() {
    if (!this.viewer) return;
    if (this.startMarker) { this.viewer.entities.remove(this.startMarker); this.startMarker = null; }
    if (this.endMarker) { this.viewer.entities.remove(this.endMarker); this.endMarker = null; }
  }

  getStartLatLng() {
    if (!this.startMarker) return null;
    const pos = this.startMarker.position.getValue();
    const carto = Cartographic.fromCartesian(pos);
    return { lat: CesiumMath.toDegrees(carto.latitude), lng: CesiumMath.toDegrees(carto.longitude) };
  }

  getEndLatLng() {
    if (!this.endMarker) return null;
    const pos = this.endMarker.position.getValue();
    const carto = Cartographic.fromCartesian(pos);
    return { lat: CesiumMath.toDegrees(carto.latitude), lng: CesiumMath.toDegrees(carto.longitude) };
  }

  // --- Click handling for desktop dispatch ---

  onLeftClick(callback) {
    if (!this.viewer) return;
    this.viewer.screenSpaceEventHandler.setInputAction((click) => {
      const ray = this.viewer.camera.getPickRay(click.position);
      const pos = this.viewer.scene.globe.pick(ray, this.viewer.scene);
      if (!pos) return;
      const carto = Cartographic.fromCartesian(pos);
      callback({
        lat: CesiumMath.toDegrees(carto.latitude),
        lng: CesiumMath.toDegrees(carto.longitude),
      });
    }, ScreenSpaceEventType.LEFT_CLICK);
  }

  destroy() {
    clearInterval(this._boundsCheckInterval);
    if (this.viewer) this.viewer.destroy();
  }
}
