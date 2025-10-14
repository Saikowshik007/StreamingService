# Integrating Learning Platform with Your Existing Traefik Setup

## Your Current Setup

You have Traefik running with:
- **Main domain**: `jobtrackai.duckdns.org` (JobTrak API)
- **3 API instances** with load balancing
- **SSL/TLS** via Let's Encrypt
- **Network**: `jobtrak-network`

## Integration Options

### Option 1: Path-Based Routing (Recommended)

Use the same domain with different paths:
- JobTrak API: `https://jobtrackai.duckdns.org/`
- Learning Platform: `https://jobtrackai.duckdns.org/learn`

**Pros:**
- Single domain/certificate
- No additional DNS configuration
- Simpler setup

**Cons:**
- Need to handle path prefixes in frontend

### Option 2: Subdomain Routing

Use a subdomain:
- JobTrak API: `https://jobtrackai.duckdns.org/`
- Learning Platform: `https://learn.jobtrackai.duckdns.org/`

**Pros:**
- Clean separation
- No path prefix handling needed
- Each app has its own URL space

**Cons:**
- Need to configure subdomain in DuckDNS
- Slightly more complex DNS

## Quick Start (Path-Based Routing)

### 1. Update docker-compose.yml

The provided `docker-compose.yml` is already configured for path-based routing.

**Key configuration:**
```yaml
labels:
  # Routes jobtrackai.duckdns.org/learn/* to learning platform
  - "traefik.http.routers.learning.rule=Host(`jobtrackai.duckdns.org`) && PathPrefix(`/learn`)"

  # Strips /learn prefix before forwarding to Flask
  - "traefik.http.middlewares.learning-stripprefix.stripprefix.prefixes=/learn"
  - "traefik.http.routers.learning.middlewares=learning-stripprefix"
```

### 2. Update Frontend Configuration

Update `client/.env.production`:
```env
REACT_APP_API_URL=https://jobtrackai.duckdns.org/learn
```

### 3. Deploy

```bash
# Build and start the learning platform
docker-compose up -d

# Check if it's running
docker ps | grep learning-platform

# Check logs
docker logs learning-platform-backend

# Test endpoint
curl https://jobtrackai.duckdns.org/learn/api/health
```

### 4. Deploy Frontend to Vercel

```bash
cd client
vercel --prod
```

In Vercel environment variables:
- `REACT_APP_API_URL` = `https://jobtrackai.duckdns.org/learn`

## Alternative: Subdomain Routing

### 1. Configure DuckDNS Subdomain

DuckDNS doesn't support traditional subdomains, but you can:

**Option A: Use a different DuckDNS domain**
- Register: `learning.duckdns.org` (separate domain)
- Point to same IP

**Option B: Use Traefik's Host matching with multiple domains**
- Keep using `jobtrackai.duckdns.org`
- Use local DNS/hosts file for `learn.jobtrackai.duckdns.org`

### 2. Update docker-compose.yml Labels

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.learning.rule=Host(`learn.jobtrackai.duckdns.org`)"
  - "traefik.http.routers.learning.entrypoints=websecure"
  - "traefik.http.routers.learning.tls.certresolver=letsencrypt"
  - "traefik.http.services.learning.loadbalancer.server.port=5000"
```

### 3. Update Frontend

```env
REACT_APP_API_URL=https://learn.jobtrackai.duckdns.org
```

## Testing Your Setup

### 1. Check Container is Running

```bash
docker ps | grep learning-platform
```

### 2. Test Direct Container Access

```bash
# Get container IP or use name
curl http://learning-platform-backend:5000/api/health
```

### 3. Test Through Traefik

**Path-based:**
```bash
curl https://jobtrackai.duckdns.org/learn/api/health
```

**Subdomain:**
```bash
curl https://learn.jobtrackai.duckdns.org/api/health
```

Expected response:
```json
{
  "status": "ok",
  "media_path": "/media",
  "db_path": "/app/data/database.db"
}
```

### 4. Check Traefik Dashboard

Visit: http://localhost:8080 (or your Traefik dashboard URL)

Look for:
- Router: `learning@docker`
- Service: `learning@docker`
- Should show as "healthy"

### 5. Test Full Flow

```bash
# Get courses
curl https://jobtrackai.duckdns.org/learn/api/courses

# Get stats
curl https://jobtrackai.duckdns.org/learn/api/stats

# Stream video (should handle range requests)
curl -I https://jobtrackai.duckdns.org/learn/api/stream/1
```

## Scanning and Managing Courses

### Initial Scan

```bash
# Enter the container
docker exec -it learning-platform-backend bash

# Run scanner
python folder_scanner.py

# Exit
exit
```

### Add New Courses

1. Add files to `C:/Users/anant/Desktop/CourseMedia/`
2. Rescan:
```bash
docker exec learning-platform-backend python folder_scanner.py --rescan
```

### View Logs

```bash
docker logs learning-platform-backend -f
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs learning-platform-backend

# Common issues:
# - Media path doesn't exist
# - Database directory not writable
# - Port 5000 already in use
```

### Traefik Not Routing

```bash
# Check Traefik logs
docker logs jobtrak-traefik

# Verify network connection
docker network inspect jobtrak-network

# Should show learning-platform-backend in the containers list
```

### 404 Errors

**Path-based routing:**
- Make sure you're accessing `/learn/api/...` not `/api/...`
- Check `stripprefix` middleware is applied

**Subdomain routing:**
- Verify DNS is resolving correctly
- Check certificate is issued for subdomain

### CORS Errors

Flask app already has CORS configured in `app_enhanced.py`:
```python
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "https://*.vercel.app",
            "https://jobtrackai.duckdns.org"
        ],
        ...
    }
})
```

If still having issues, add your Vercel URL explicitly.

### Database Issues

```bash
# Check database file exists
docker exec learning-platform-backend ls -la /app/data/

# Check permissions
docker exec learning-platform-backend ls -la /app/data/database.db

# Reset database (WARNING: deletes all data)
rm -rf data/database.db
docker restart learning-platform-backend
```

## Advanced Configuration

### Adding to Existing docker-compose.yml

If you want to add the learning platform to your existing JobTrak `docker-compose.yml`:

```yaml
# Add to your existing file
services:
  # ... your existing services (traefik, jobtrak-api-*, postgres, etc.) ...

  learning-platform:
    build:
      context: ./learning-platform
      dockerfile: Dockerfile
    container_name: learning-platform-backend
    restart: unless-stopped
    environment:
      - FLASK_APP=app_enhanced.py
      - FLASK_ENV=production
      - MEDIA_PATH=/media
      - PORT=5000
      - DB_PATH=/app/data/database.db
    volumes:
      - C:/Users/anant/Desktop/CourseMedia:/media:ro
      - ./learning-platform/data:/app/data
    networks:
      - jobtrak-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:5000/api/health')"]
      interval: 30s
      timeout: 10s
      start_period: 10s
      retries: 3
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.learning.rule=Host(`jobtrackai.duckdns.org`) && PathPrefix(`/learn`)"
      - "traefik.http.routers.learning.entrypoints=websecure"
      - "traefik.http.routers.learning.tls.certresolver=letsencrypt"
      - "traefik.http.services.learning.loadbalancer.server.port=5000"
      - "traefik.http.middlewares.learning-stripprefix.stripprefix.prefixes=/learn"
      - "traefik.http.routers.learning.middlewares=learning-stripprefix"
```

### Shared Resources

You can optionally share resources with JobTrak:

**Shared Logging:**
```yaml
volumes:
  - ./logs:/app/logs
```

**Shared Redis (for caching):**
```yaml
environment:
  - REDIS_URL=redis://redis:6379/1  # Different DB than JobTrak
```

**Shared PostgreSQL (instead of SQLite):**
You could migrate to PostgreSQL if needed, but SQLite is fine for this use case.

## Monitoring

### Add to Grafana

Your existing Grafana can monitor the learning platform:

1. **Check container logs in Grafana**
2. **Add health check dashboard**
3. **Monitor API response times**

The learning platform logs to `/app/logs` which your Promtail can pick up.

## Production Checklist

- [ ] Container is running: `docker ps | grep learning`
- [ ] Health check passing: `curl https://jobtrackai.duckdns.org/learn/api/health`
- [ ] SSL certificate valid (Traefik auto-renews)
- [ ] Can access courses: `curl https://jobtrackai.duckdns.org/learn/api/courses`
- [ ] Can stream video: Test in browser
- [ ] Vercel frontend deployed with correct API URL
- [ ] CORS working (test from Vercel URL)
- [ ] Database persists after restart
- [ ] Media files accessible to container

## URLs Reference

**Path-based routing:**
- API: `https://jobtrackai.duckdns.org/learn/api/*`
- Health: `https://jobtrackai.duckdns.org/learn/api/health`
- Courses: `https://jobtrackai.duckdns.org/learn/api/courses`
- Stream: `https://jobtrackai.duckdns.org/learn/api/stream/:id`

**Local development:**
- Backend: `http://localhost:5000/api/*`
- Frontend: `http://localhost:3000`

**Vercel frontend:**
- Production: `https://your-app.vercel.app`
- Calls: `https://jobtrackai.duckdns.org/learn/api/*`

## Summary

With your existing Traefik setup, integration is straightforward:

1. **Use same network**: `jobtrak-network`
2. **Use path-based routing**: `/learn` prefix
3. **Let Traefik handle SSL**: Uses same Let's Encrypt cert
4. **Deploy with**: `docker-compose up -d`
5. **Test with**: `curl https://jobtrackai.duckdns.org/learn/api/health`

Done! Your learning platform is now integrated with your existing infrastructure.
