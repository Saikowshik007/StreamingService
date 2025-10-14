# Setting Up Nginx Reverse Proxy for DuckDNS

Since you want to use `https://jobtrackai.duckdns.org` without a port number, you need to set up a reverse proxy that:
- Listens on port 443 (HTTPS)
- Forwards requests to your Flask app on port 5000
- Handles SSL/TLS certificates

## Option 1: Using Nginx (Recommended)

### Step 1: Install Nginx

**Windows:**
1. Download from: http://nginx.org/en/download.html
2. Extract to `C:\nginx`

**Linux/Mac:**
```bash
sudo apt install nginx  # Ubuntu/Debian
brew install nginx      # Mac
```

### Step 2: Get SSL Certificate

**Using Certbot (Free, Automated):**

```bash
# Install Certbot
# Windows: Download from https://certbot.eff.org/
# Linux:
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d jobtrackai.duckdns.org
```

Certificates will be saved at:
- Certificate: `/etc/letsencrypt/live/jobtrackai.duckdns.org/fullchain.pem`
- Private Key: `/etc/letsencrypt/live/jobtrackai.duckdns.org/privkey.pem`

### Step 3: Configure Nginx

Create/edit nginx configuration:

**Windows:** `C:\nginx\conf\nginx.conf`
**Linux:** `/etc/nginx/sites-available/learning-platform`

```nginx
http {
    upstream flask_backend {
        server 127.0.0.1:5000;
    }

    server {
        listen 80;
        server_name jobtrackai.duckdns.org;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name jobtrackai.duckdns.org;

        # SSL Certificate Configuration
        ssl_certificate /etc/letsencrypt/live/jobtrackai.duckdns.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/jobtrackai.duckdns.org/privkey.pem;

        # SSL Security Settings
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Increase upload size for video uploads (if needed)
        client_max_body_size 1000M;

        # Proxy all requests to Flask backend
        location / {
            proxy_pass http://flask_backend;
            proxy_http_version 1.1;

            # Headers
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support (if needed)
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";

            # Timeouts for video streaming
            proxy_read_timeout 300;
            proxy_connect_timeout 300;
            proxy_send_timeout 300;
        }

        # Optional: Cache static content
        location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
            proxy_pass http://flask_backend;
            proxy_cache_valid 200 1d;
            expires 1d;
        }
    }
}

events {
    worker_connections 1024;
}
```

### Step 4: Enable Configuration (Linux)

```bash
sudo ln -s /etc/nginx/sites-available/learning-platform /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl restart nginx
```

### Step 5: Update Router Port Forwarding

**Change from:**
- External Port 5000 → Internal Port 5000

**To:**
- External Port 443 → Internal Port 443 (HTTPS)
- External Port 80 → Internal Port 80 (HTTP, for redirect)

### Step 6: Start Services

```bash
# Start Flask backend (keep running on port 5000)
python app.py

# Start Nginx (Windows)
cd C:\nginx
start nginx

# Start Nginx (Linux)
sudo systemctl start nginx
```

## Option 2: Using Cloudflare Tunnel (No Port Forwarding Needed!)

This is actually easier and doesn't require SSL certificates or port forwarding!

### Step 1: Install Cloudflare Tunnel

**Windows:**
```powershell
# Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

**Linux/Mac:**
```bash
# Install
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
sudo mv cloudflared /usr/local/bin/
sudo chmod +x /usr/local/bin/cloudflared
```

### Step 2: Authenticate

```bash
cloudflared tunnel login
```

### Step 3: Create Tunnel

```bash
cloudflared tunnel create learning-platform
```

### Step 4: Configure Tunnel

Create `config.yml`:
```yaml
url: http://localhost:5000
tunnel: <tunnel-id-from-step-3>
credentials-file: /path/to/credentials.json
```

### Step 5: Route Your Domain

```bash
cloudflared tunnel route dns learning-platform jobtrackai.duckdns.org
```

### Step 6: Run Tunnel

```bash
cloudflared tunnel run learning-platform
```

This gives you HTTPS automatically without certificates or port forwarding!

## Option 3: Simple Port Forwarding (Not Recommended for Production)

If you just want to test without HTTPS:

1. Forward port 5000 on your router
2. Use: `http://jobtrackai.duckdns.org:5000`
3. Update `.env.production`: `REACT_APP_API_URL=http://jobtrackai.duckdns.org:5000`

**Warning:** Browsers may block mixed content (HTTP API on HTTPS Vercel site)

## Testing Your Setup

### Test Backend Directly

```bash
# Test local
curl http://localhost:5000/api/health

# Test through nginx/tunnel
curl https://jobtrackai.duckdns.org/api/health
```

Should return:
```json
{"status": "ok", "media_path": "...", "db_path": "..."}
```

### Test CORS

```bash
curl -H "Origin: https://your-app.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     https://jobtrackai.duckdns.org/api/courses
```

Should return CORS headers allowing your Vercel domain.

## Recommended Setup

**For Production:** Use **Cloudflare Tunnel** (Option 2)
- No port forwarding needed
- Automatic HTTPS
- Free
- Easy to set up
- Reliable

**For Learning:** Use **Nginx** (Option 1)
- Full control
- Learn about reverse proxies
- Standard production setup

## Troubleshooting

### Nginx won't start
```bash
# Check configuration
nginx -t

# Check what's using port 443
netstat -ano | findstr :443  # Windows
sudo lsof -i :443            # Linux/Mac
```

### Certificate renewal (Certbot)
```bash
# Auto-renew (add to cron)
sudo certbot renew
```

### Check Nginx logs
```bash
# Windows
C:\nginx\logs\error.log

# Linux
/var/log/nginx/error.log
/var/log/nginx/access.log
```

## Windows Service Setup

To run Nginx as a Windows service:

1. Download NSSM: https://nssm.cc/download
2. Install service:
```cmd
nssm install nginx "C:\nginx\nginx.exe"
nssm set nginx AppDirectory "C:\nginx"
nssm start nginx
```

## Summary

After setup, your URLs will be:
- **Frontend (Vercel):** `https://your-app.vercel.app`
- **Backend (Your PC):** `https://jobtrackai.duckdns.org` (port 443)
- **Backend Internal:** `http://localhost:5000`

Nginx/Cloudflare forwards: `https://jobtrackai.duckdns.org` → `http://localhost:5000`
