# Nginx Service for DCIM Application

This directory contains a modular nginx configuration for serving the DCIM frontend and proxying requests to the FastAPI backend.

## Directory Structure

```
nginx/
├── nginx.conf              # Main nginx configuration file (production/Docker)
├── nginx-local.conf        # Nginx configuration for local development (SSL bypassed)
├── conf.d/                 # Modular configuration files
│   ├── upstreams.conf     # Upstream server definitions (production/Docker)
│   ├── upstreams-local.conf  # Upstream server definitions (local dev)
│   ├── backend.conf       # Backend API routing configuration
│   ├── frontend.conf      # Frontend routing configuration
│   ├── images.conf        # Image resize configuration
│   ├── security.conf      # Security headers configuration
│   └── ssl.conf           # SSL/HTTPS configuration
├── Dockerfile             # Docker image definition
├── .dockerignore          # Files to exclude from Docker build
├── docker-compose.example.yml  # Example docker-compose integration
└── README.md              # This file
```

## Features

- **Modular Configuration**: Separate config files for frontend, backend, security, and SSL
- **HTTPS Support**: SSL/TLS configuration with modern protocols and ciphers
- **Security Headers**: Comprehensive security headers including CSP, HSTS, XSS protection
- **Frontend Routing**: Support for Angular SPA routing with fallback to index.html
- **Backend Proxying**: Proxy pass to FastAPI backend with proper headers and timeouts
- **Image Resizing**: Real-time image resizing via URL patterns (returns original if no dimensions provided)
- **Docker Support**: Ready for containerization

## Configuration Files

### nginx.conf
Main configuration file for production/Docker that:
- Sets up basic nginx settings (logging, compression, etc.)
- Includes all modular configuration files
- Defines HTTP and HTTPS server blocks

### nginx-local.conf
Local development configuration file that:
- Bypasses SSL/HTTPS (HTTP only)
- Uses `upstreams-local.conf` for localhost backend connections
- Runs on port 8080 to avoid conflicts with system nginx
- Designed for local development workflow
- Used by `make nginx-local` command

### conf.d/upstreams.conf
Defines upstream servers for production/Docker:
- Backend API upstream (points to FastAPI service in Docker network)
- Optional frontend upstream (if using dev server)

### conf.d/upstreams-local.conf
Defines upstream servers for local development:
- Backend API upstream (points to `localhost:8000`)
- Used with `nginx-local.conf` configuration

### conf.d/backend.conf
Handles routing for backend APIs:
- Proxies `/api/` requests to FastAPI backend
- Sets proper proxy headers (X-Forwarded-For, X-Real-IP, etc.)
- Supports WebSocket connections
- Configures timeouts and buffering

### conf.d/frontend.conf
Handles frontend routing:
- Serves static files from `/usr/share/nginx/html`
- Supports Angular SPA routing with `try_files`
- Sets cache headers for static assets
- Proxies API documentation endpoints

### conf.d/images.conf
Image resize configuration:
- Real-time image resizing via URL pattern: `/images/{width}/{height}/{filename}`
- Returns original image if no width/height dimensions are provided
- Supports formats: jpg, jpeg, png, gif, webp
- Caches resized images for performance
- Maximum dimensions: 5000x5000 pixels
- Example: `/images/100/100/device_image.jpg` returns 100x100 resized image
- Example: `/images/device_image.jpg` returns original image

### conf.d/security.conf
Security headers configuration:
- X-Frame-Options (clickjacking protection)
- X-XSS-Protection
- X-Content-Type-Options
- Content-Security-Policy
- Referrer-Policy
- Permissions-Policy

### conf.d/ssl.conf
SSL/HTTPS configuration:
- TLS 1.2 and 1.3 protocols
- Modern cipher suites
- OCSP stapling
- HSTS headers
- SSL session caching

## Setup Instructions

### 1. Update Configuration

Before using this nginx configuration, update the following:

#### backend.conf
```nginx
upstream backend_api {
    server backend:8000;  # Update with your backend service name and port
}
```

#### nginx.conf
```nginx
server_name _;  # Replace with your domain name (e.g., example.com)
```

#### ssl.conf (when enabling HTTPS)
```nginx
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
```

### 2. Local Development (Recommended - Using Makefile)

The easiest way to run nginx for local development is using the Makefile commands:

#### Quick Start

1. **Install nginx** (one-time setup):
   ```bash
   make nginx-install
   ```

2. **Start backend** (in a separate terminal):
   ```bash
   make backend
   ```
   The backend should be running on `http://localhost:8000`

3. **Build frontend** (if not already built):
   ```bash
   cd ../dcim_frontend
   npm run build
   ```

4. **Start nginx for local development**:
   ```bash
   make nginx-local
   ```

   This will:
   - Use `nginx-local.conf` configuration (SSL bypassed)
   - Point to `localhost:8000` for backend API
   - Run nginx on port `8080` (to avoid conflicts with system nginx on port 80)
   - Serve frontend from `dcim_frontend/dist` directory
   - Access application at: `http://localhost:8080`

5. **Stop nginx**:
   ```bash
   make stop-nginx
   ```

#### Configuration Details

For local development:
- **SSL/HTTPS**: Bypassed (HTTP only)
- **Backend**: Points to `localhost:8000` (see `conf.d/upstreams-local.conf`)
- **Port**: Runs on `8080` to avoid conflicts
- **Frontend**: Served from `dcim_frontend/dist` directory

#### Available Makefile Commands

- `make nginx-install` - Install nginx on your system (Ubuntu/Debian/CentOS)
- `make nginx-local` - Start nginx for local development
- `make nginx-test` - Test nginx configuration
- `make stop-nginx` - Stop nginx server

### 3. Local Development (Manual Setup - Without Docker)

If you prefer to set up nginx manually:

1. Install nginx on your system:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install nginx
   
   # CentOS/RHEL
   sudo yum install nginx
   ```

2. Copy configuration files:
   ```bash
   sudo cp nginx.conf /etc/nginx/nginx.conf
   sudo cp -r conf.d/* /etc/nginx/conf.d/
   ```

3. Build your frontend (if serving static files):
   ```bash
   cd ../dcim_frontend
   npm run build
   sudo cp -r dist/* /usr/share/nginx/html/
   ```

4. Test configuration:
   ```bash
   sudo nginx -t
   ```

5. Start/restart nginx:
   ```bash
   sudo systemctl start nginx
   # or
   sudo systemctl restart nginx
   ```

### 4. Docker Setup

#### Build the Image

```bash
# Build nginx image
docker build -t dcim-nginx:latest .

# Or build with frontend included (update Dockerfile first)
docker build -t dcim-nginx:latest .
```

#### Run with Docker

```bash
# Run nginx container
docker run -d \
  --name dcim-nginx \
  -p 80:80 \
  -p 443:443 \
  -v $(pwd)/../dcim_frontend/dist:/usr/share/nginx/html:ro \
  -v $(pwd)/ssl:/etc/nginx/ssl:ro \
  --network dcim-network \
  dcim-nginx:latest
```

#### Docker Compose Example

Create a `docker-compose.yml` in the root directory:

```yaml
version: '3.8'

services:
  nginx:
    build:
      context: ./nginx
      dockerfile: Dockerfile
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./dcim_frontend/dist:/usr/share/nginx/html:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - backend
    networks:
      - dcim-network
    restart: unless-stopped

  backend:
    # Your FastAPI backend configuration
    build:
      context: ./dcim_backend_fastapi
    networks:
      - dcim-network
    # ... other backend configs

networks:
  dcim-network:
    driver: bridge
```

### 5. Enable HTTPS

1. Obtain SSL certificates (Let's Encrypt, self-signed, or commercial):
   ```bash
   # Using Let's Encrypt (recommended)
   certbot certonly --standalone -d yourdomain.com
   ```

2. Copy certificates to nginx ssl directory:
   ```bash
   sudo mkdir -p /etc/nginx/ssl
   sudo cp /path/to/cert.pem /etc/nginx/ssl/
   sudo cp /path/to/key.pem /etc/nginx/ssl/
   sudo chmod 600 /etc/nginx/ssl/*.pem
   ```

3. Update `nginx.conf`:
   - Uncomment the HTTPS server block
   - Uncomment the HTTP to HTTPS redirect in the HTTP server block
   - Update certificate paths in `conf.d/ssl.conf`

4. Test and reload:
   ```bash
   sudo nginx -t
   sudo nginx -s reload
   ```

## Customization

### Adjusting File Upload Size

If you need to handle larger file uploads, update `client_max_body_size` in `nginx.conf`:

```nginx
client_max_body_size 500M;  # Adjust as needed
```

### Adding Rate Limiting

Rate limiting zones are already defined in `nginx.conf`. To apply them, add to your location blocks:

```nginx
limit_req zone=api_limit burst=20 nodelay;
```

### Image Resizing

The nginx configuration supports real-time image resizing via URL patterns. This feature is configured in `conf.d/images.conf`.

**Usage:**

1. **Resize image**: `/images/{width}/{height}/{filename}`
   - Example: `http://localhost/images/100/100/device_image.jpg`
   - Returns the image resized to 100x100 pixels

2. **Original image**: `/images/{filename}`
   - Example: `http://localhost/images/device_image.jpg`
   - Returns the original image without resizing

3. **Alternative pattern**: `/images/resize/{width}/{height}/{filename}`
   - Automatically redirects to the standard pattern

4. **Direct original access**: `/images/original/{filename}`
   - Always returns original image without any processing

**Features:**
- Dimensions are validated (must be > 0, max 5000px)
- Resized images are cached for 1 hour
- Original images are cached for 30 days
- Supports jpg, jpeg, png, gif, webp formats
- If no dimensions provided, original image is returned

**Example URLs:**
```
# Resized image (100x100)
http://localhost/images/100/100/myimage.jpg

# Original image (no resize)
http://localhost/images/myimage.jpg

# Alternative resize URL
http://localhost/images/resize/200/150/myimage.jpg
```

**Note**: The image filter module requires nginx compiled with `--with-http_image_filter_module`. The configuration will proxy to the backend if images are not found locally.

### Custom Logging

Update log format in `nginx.conf`:

```nginx
log_format custom '$remote_addr - $remote_user [$time_local] "$request" '
                  '$status $body_bytes_sent "$http_referer" '
                  '"$http_user_agent"';
```

## Troubleshooting

### Check Nginx Configuration

```bash
sudo nginx -t
```

### View Nginx Logs

```bash
# Error logs
sudo tail -f /var/log/nginx/error.log

# Access logs
sudo tail -f /var/log/nginx/access.log
```

### Reload Configuration

```bash
sudo nginx -s reload
```

### Common Issues

1. **502 Bad Gateway**: Backend service is not running or not accessible
   - Check backend service status
   - Verify upstream server address in `backend.conf`

2. **404 for Frontend Routes**: Angular routing not working
   - Ensure `try_files $uri $uri/ /index.html;` is in `frontend.conf`

3. **SSL Certificate Errors**: Certificate path or permissions issue
   - Verify certificate paths in `ssl.conf`
   - Check file permissions (should be readable by nginx user)

## Security Notes

- Always use HTTPS in production
- Regularly update SSL certificates
- Review and adjust Content-Security-Policy based on your application needs
- Keep nginx updated to the latest version
- Use environment-specific configurations (dev/staging/prod)

## References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Nginx Security Headers](https://www.nginx.com/blog/http-strict-transport-security-hsts-and-nginx/)
- [Angular Deployment](https://angular.io/guide/deployment)

