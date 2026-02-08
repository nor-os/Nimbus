/**
 * Proxy configuration for Angular dev-server (Vite).
 * Routes /api/* and /graphql to the backend.
 */
export default {
  '/api': {
    target: 'http://127.0.0.1:8000',
    secure: false,
    changeOrigin: true,
    configure: (proxy, _options) => {
      proxy.on('proxyReq', (_proxyReq, req) => {
        console.log(`[proxy] ${req.method} ${req.url} -> http://127.0.0.1:8000`);
      });
      proxy.on('error', (err, req) => {
        console.error(`[proxy] ERROR ${req.url}: ${err.message}`);
      });
    },
  },
  '/graphql': {
    target: 'http://127.0.0.1:8000',
    secure: false,
    changeOrigin: true,
  },
};
