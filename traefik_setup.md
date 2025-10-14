# Using Traefik with Your Learning Platform

Since you already have Traefik running, you just need to configure it to route requests from `jobtrackai.duckdns.org` to your Flask backend.

## Architecture

```
Internet → https://jobtrackai.duckdns.org
         → Traefik (port 443)
         → Flask Backend (http://localhost:5000)
         → Vercel Frontend calls this API
```

## Option 1: Docker Setup (Recommended)

### 1. Create docker-compose.yml for your Learning Platform

```yaml
version: '3.8'

services:
  learning-platform-backend:
    build: .
    container_name: learning-platform-backend
    restart: unless-stopped
    environment:
      - FLASK_APP=app_enhanced.py
      - FLASK_ENV=production
      - MEDIA_PATH=/media
      - PORT=5000
    volumes:
      - C:/Users/anant/Desktop/CourseMedia:/media:ro
      - ./database.db:/app/database.db
    networks:
      - traefik
    labels:
      # Enable Traefik
      - "traefik.enable=true"

      # HTTP Router
      - "traefik.http.routers.learning-platform.rule=Host(`jobtrackai.duckdns.org`)"
      - "traefik.http.routers.learning-platform.entrypoints=websecure"
      - "traefik.http.routers.learning-platform.tls=true"
      - "traefik.http.routers.learning-platform.tls.certresolver=letsencrypt"

      # Service
      - "traefik.http.services.learning-platform.loadbalancer.server.port=5000"

      # Optional: Middleware for CORS headers
      - "traefik.http.routers.learning-platform.middlewares=learning-platform-cors"
      - "traefik.http.middlewares.learning-platform-cors.headers.accesscontrolallowmethods=GET,POST,PUT,DELETE,OPTIONS"
      - "traefik.http.middlewares.learning-platform-cors.headers.accesscontrolalloworiginlist=https://*.vercel.app,http://localhost:3000"
      - "traefik.http.middlewares.learning-platform-cors.headers.accesscontrolallowheaders=Content-Type,Authorization"
      - "traefik.http.middlewares.learning-platform-cors.headers.accesscontrolmaxage=100"
      - "traefik.http.middlewares.learning-platform-cors.headers.addvaryheader=true"

networks:
  traefik:
    external: true
```

### 2. Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app_enhanced.py"]
```

### 3. Start the Service

```bash
docker-compose up -d
```

## Option 2: Non-Docker Setup

If you're not using Docker, add Traefik configuration for your Flask app running directly on the host.

### Dynamic Configuration File

Create `traefik/dynamic/learning-platform.yml`:

```yaml
http:
  routers:
    learning-platform:
      rule: "Host(`jobtrackai.duckdns.org`)"
      entryPoints:
        - websecure
      service: learning-platform-service
      tls:
        certResolver: letsencrypt
      middlewares:
        - learning-platform-cors

  services:
    learning-platform-service:
      loadBalancer:
        servers:
          - url: "http://localhost:5000"

  middlewares:
    learning-platform-cors:
      headers:
        accessControlAllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
        accessControlAllowOriginList:
          - "https://*.vercel.app"
          - "http://localhost:3000"
        accessControlAllowHeaders:
          - "Content-Type"
          - "Authorization"
        accessControlMaxAge: 100
        addVaryHeader: true
```

### Apply Configuration

```bash
# Reload Traefik configuration
# If using Docker:
docker restart traefik

# If using systemd:
sudo systemctl reload traefik
```

## Option 3: Traefik Static Configuration

If you're managing Traefik via static config file (`traefik.yml` or `traefik.toml`):

### traefik.yml

```yaml
entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https

  websecure:
    address: ":443"

certificatesResolvers:
  letsencrypt:
    acme:
      email: your-email@example.com
      storage: /letsencrypt/acme.json
      httpChallenge:
        entryPoint: web

providers:
  file:
    directory: /etc/traefik/dynamic
    watch: true
```

## Verifying Traefik Configuration

### Check Traefik Dashboard

If you have Traefik dashboard enabled, check:
- `http://your-traefik-dashboard:8080`
- Look for `learning-platform` router
- Verify it's routing to port 5000

### Test Routing

```bash
# Test locally
curl http://localhost:5000/api/health

# Test through Traefik
curl https://jobtrackai.duckdns.org/api/health
```

Should return:
```json
{"status": "ok", "media_path": "...", "db_path": "..."}
```

### Check Traefik Logs

```bash
# Docker
docker logs traefik

# Systemd
journalctl -u traefik -f
```

## Troubleshooting

### 404 Not Found

**Problem:** Traefik returns 404

**Solutions:**
1. Check router rule matches domain exactly
2. Verify service is running on port 5000
3. Check Traefik can reach localhost:5000
4. Look at Traefik logs for routing errors

```bash
# Test if Flask is reachable
curl http://localhost:5000/api/health
```

### Certificate Issues

**Problem:** SSL/TLS errors

**Solutions:**
1. Check Let's Encrypt rate limits
2. Verify DNS is pointing to your public IP
3. Check port 80 and 443 are forwarded
4. Verify `acme.json` has correct permissions (600)

```bash
# Check certificate
curl -vI https://jobtrackai.duckdns.org
```

### CORS Errors

**Problem:** Browser shows CORS errors

**Solutions:**
1. Flask already has CORS configured in `app_enhanced.py`
2. Traefik middleware is optional but can add extra layer
3. Check browser console for specific error
4. Verify Vercel domain is in CORS origins

### Connection Refused

**Problem:** Traefik can't connect to Flask

**Solutions:**
1. Ensure Flask is running: `python app_enhanced.py`
2. Check Flask is listening on 0.0.0.0, not 127.0.0.1
3. Check firewall isn't blocking localhost connections
4. If using Docker, ensure networks are correct

## Flask Configuration for Traefik

Your `app_enhanced.py` is already configured correctly:

```python
# Listens on all interfaces
app.run(host='0.0.0.0', port=5000)

# CORS is already configured for Vercel
CORS(app, resources={...})
```

## Complete Setup Checklist

- [ ] Traefik is running and accessible
- [ ] Port 80 and 443 forwarded to Traefik machine
- [ ] DuckDNS pointing to your public IP
- [ ] Flask backend running on port 5000
- [ ] Traefik configuration added (Docker labels or file)
- [ ] SSL certificate obtained (Let's Encrypt)
- [ ] Test: `curl https://jobtrackai.duckdns.org/api/health`
- [ ] CORS working for Vercel domain
- [ ] Videos streaming properly

## Example: Adding to Existing Traefik Setup

If you already have services running with Traefik, just add the learning platform to the same network:

```yaml
# Your existing docker-compose.yml
services:
  # ... your other services ...

  learning-platform:
    image: learning-platform:latest
    networks:
      - traefik  # Same network as your other services
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.learning.rule=Host(`jobtrackai.duckdns.org`)"
      - "traefik.http.routers.learning.entrypoints=websecure"
      - "traefik.http.routers.learning.tls.certresolver=letsencrypt"

networks:
  traefik:
    external: true
```

## Monitor and Maintain

### Check Service Health

```bash
# Traefik API (if enabled)
curl http://localhost:8080/api/http/routers

# Direct backend check
curl http://localhost:5000/api/stats
```

### Auto-restart on Failure

**Docker:**
```yaml
restart: unless-stopped
```

**Systemd:**
Create `/etc/systemd/system/learning-platform.service`:
```ini
[Unit]
Description=Learning Platform Backend
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/StreamingService
ExecStart=/usr/bin/python3 app_enhanced.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable learning-platform
sudo systemctl start learning-platform
```

## Summary

With Traefik already running, you just need to:

1. **Add Traefik labels/config** to route `jobtrackai.duckdns.org` → `localhost:5000`
2. **Start Flask backend** with `python app_enhanced.py`
3. **Deploy to Vercel** with `REACT_APP_API_URL=https://jobtrackai.duckdns.org`

That's it! Traefik handles SSL, routing, and certificates automatically.
