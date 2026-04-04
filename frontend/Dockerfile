# Build stage
FROM node:20-alpine3.21 AS builder

WORKDIR /app

# Install dependencies (lockfile pour builds reproductibles)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:1.27-alpine3.21

# Create non-root user
RUN adduser -D -H -u 1001 -s /sbin/nologin nginx-user && \
    chown -R nginx-user:nginx-user /var/cache/nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx-user:nginx-user /var/run/nginx.pid

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config and entrypoint
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && \
    chown -R nginx-user:nginx-user /usr/share/nginx/html

EXPOSE 8080

USER nginx-user

ENTRYPOINT ["/docker-entrypoint.sh"]
