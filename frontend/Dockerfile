# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:20-alpine AS builder

WORKDIR /app

# Install pnpm globally
RUN npm install -g pnpm@9

# Copy dependency files
COPY package.json pnpm-lock.yaml ./

# Install dependencies (allow lockfile update if needed)
RUN pnpm install --no-frozen-lockfile

# Copy source code
COPY . .

# Build for production
# API URL set to /api (nginx will proxy to backend)
ENV VITE_API_URL=/api
RUN pnpm run build

# ============================================
# Stage 2: Serve with Nginx
# ============================================
FROM nginx:1.25-alpine

# Copy built static files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check for docker-compose
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost/ || exit 1

# Start nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
