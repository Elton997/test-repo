# Nginx Dockerfile for DCIM Application
# Uses standard nginx with image filter module
FROM nginx:1.25-alpine

# Install nginx image filter module dependencies
RUN apk add --no-cache \
    libgd \
    gd-dev

# Note: The nginx:alpine image should already have image_filter_module compiled in
# If not, you may need to use a custom build or different base image

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy modular configuration files
COPY conf.d/ /etc/nginx/conf.d/

# Copy frontend build files (if building frontend separately)
# Uncomment the following lines and adjust path if you want to include frontend in nginx image
# COPY ../dcim_frontend/dist/ /usr/share/nginx/html/

# Create directories for SSL certificates (if using HTTPS)
RUN mkdir -p /etc/nginx/ssl

# Create log directories
RUN mkdir -p /var/log/nginx

# Create cache directories
RUN mkdir -p /tmp/nginx_image_cache

# Expose ports
EXPOSE 80 443

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
