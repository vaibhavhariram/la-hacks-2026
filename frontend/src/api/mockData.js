export const MOCK_ROUTE = {
  path: [
    { lat: 34.1897, lng: -118.1315 }, // Altadena Hospital area
    { lat: 34.1880, lng: -118.1340 },
    { lat: 34.1865, lng: -118.1370 },
    { lat: 34.1848, lng: -118.1395 },
    { lat: 34.1830, lng: -118.1415 },
    { lat: 34.1812, lng: -118.1430 },
    { lat: 34.1795, lng: -118.1445 },
    { lat: 34.1778, lng: -118.1460 },
    { lat: 34.1760, lng: -118.1480 },
    { lat: 34.1743, lng: -118.1500 },
    { lat: 34.1725, lng: -118.1515 },
    { lat: 34.1708, lng: -118.1530 },
    { lat: 34.1690, lng: -118.1548 },
    { lat: 34.1672, lng: -118.1562 },
    { lat: 34.1655, lng: -118.1578 },
    { lat: 34.1638, lng: -118.1592 },
    { lat: 34.1620, lng: -118.1608 },
    { lat: 34.1602, lng: -118.1622 },
    { lat: 34.1585, lng: -118.1638 },
    { lat: 34.1570, lng: -118.1650 }, // Lincoln Ave shelter area
  ],
  cost: 4200.0,
  rerouted: false,
};

export const MOCK_STATE = {
  hazards: [
    { id: 'h1', lat: 34.1920, lng: -118.1280, radius_m: 300, severity: 0.8 },
    { id: 'h2', lat: 34.1950, lng: -118.1230, radius_m: 250, severity: 0.9 },
    { id: 'h3', lat: 34.1900, lng: -118.1180, radius_m: 400, severity: 0.7 },
    { id: 'h4', lat: 34.1870, lng: -118.1150, radius_m: 200, severity: 0.6 },
    { id: 'h5', lat: 34.1840, lng: -118.1200, radius_m: 350, severity: 0.85 },
  ],
  routes: [
    {
      unit_id: 'unit-001',
      waypoints: MOCK_ROUTE.path,
      rerouted: false,
    },
  ],
};

export const MOCK_FIELD_REPORT = {
  lat: 34.181,
  lng: -118.127,
  status: 'blocked',
  confidence: 0.91,
};
