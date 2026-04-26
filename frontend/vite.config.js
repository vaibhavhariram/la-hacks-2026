import basicSsl from '@vitejs/plugin-basic-ssl';
import { viteStaticCopy } from 'vite-plugin-static-copy';
import { defineConfig, loadEnv } from 'vite';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import sirv from 'sirv';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cesiumSource = resolve(__dirname, 'node_modules/cesium/Build/Cesium');

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '');
  const useHttps = env.VITE_DEV_HTTPS === 'true';

  return {
    plugins: [
      useHttps ? basicSsl() : null,
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
    ].filter(Boolean),
    define: {
      CESIUM_BASE_URL: JSON.stringify('/cesium'),
    },
    server: {
      port: 5173,
      host: true,
      https: useHttps,
    },
    build: {
      chunkSizeWarningLimit: 10000,
    },
  };
});
