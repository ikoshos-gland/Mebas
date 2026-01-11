# MEB RAG Frontend - React + Vite + TypeScript
# Multi-stage build for production

# ===== Stage 1: Build =====
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first (better caching)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .

# Set API URL for production build (can be overridden at runtime)
ARG VITE_API_URL=http://localhost:8001
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ===== Stage 2: Production =====
FROM nginx:alpine AS production

# Copy custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
