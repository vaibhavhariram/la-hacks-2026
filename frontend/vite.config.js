import { viteStaticCopy } from 'vite-plugin-static-copy';
import { defineConfig } from 'vite';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import sirv from 'sirv';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cesiumSource = resolve(__dirname, 'node_modules/cesium/Build/Cesium');

export default defineConfig({
  plugins: [
    viteStaticCopy({
      targets: [
        { src: `${cesiumSource}/ThirdParty`, dest: 'cesium' },
        { src: `${cesiumSource}/Workers`, dest: 'cesium' },
        { src: `${cesiumSource}/Assets`, dest: 'cesium' },
        { src: `${cesiumSource}/Widgets`, dest: 'cesium' },
      ],
    }),
    {
      // serve Cesium's built assets at /cesium/ during dev
      name: 'cesium-dev-server',
      configureServer(server) {
        server.middlewares.use('/cesium', sirv(cesiumSource, { dev: true }));
      },
    },
  ],
  define: {
    CESIUM_BASE_URL: JSON.stringify('/cesium'),
  },
  server: {
    port: 5173,
    host: true,
    https: false,
  },
  optimizeDeps: {
    // Cesium depends on a few CJS/UMD packages (e.g. `urijs`,
    // `grapheme-splitter`). If Cesium isn't pre-bundled, browsers can hit
    // "does not provide an export named 'default'" errors.
    include: ['cesium', 'mersenne-twister', 'urijs', 'grapheme-splitter'],
    needsInterop: ['urijs', 'grapheme-splitter'],
  },
  build: {
    chunkSizeWarningLimit: 10000,
  },
});
