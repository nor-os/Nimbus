# Overview: Multi-stage Dockerfile for the Nimbus frontend (Angular 17).
# Architecture: Builds Angular app, serves via nginx with reverse proxy to backend.
# Dependencies: Node 20, Angular CLI, nginx
# Concepts: Multi-stage build, static asset serving, API reverse proxy

# ── Build stage ──────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (layer cache)
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

# Copy source and build
COPY . .
RUN npx ng build --configuration=production

# ── Runtime stage ────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY docker/nginx.conf /etc/nginx/conf.d/nimbus.conf
COPY --from=builder /app/dist/nimbus/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
