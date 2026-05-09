# Multi-stage build for React frontend (Vite)
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* yarn.lock* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build arguments for environment variables
ARG VITE_API_BASE_URL=http://localhost:8000
ARG NODE_ENV=production
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV NODE_ENV=$NODE_ENV

# Build the app (Create React App outputs to build/)
RUN npm run build

# Verify build succeeded
RUN test -d /app/build || (echo "ERROR: Build failed - build directory not found" && exit 1)
RUN ls -la /app/build

# ============================================
# Production stage with nginx
# ============================================
FROM nginx:stable-alpine

# Install curl for healthchecks
RUN apk add --no-cache curl

# Copy built files from builder (Create React App build folder)
COPY --from=builder /app/build /usr/share/nginx/html

# Verify files copied correctly
RUN ls -la /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]