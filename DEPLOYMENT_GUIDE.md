# Deployment Guide - Vercel Frontend + Local PC Backend

This guide will help you deploy your frontend to Vercel while keeping the backend running on your local PC.

## Overview

- **Frontend**: Deployed on Vercel (accessible worldwide)
- **Backend**: Running on your PC at https://jobtrackai.duckdns.org:5000
- **Media Files**: Stored locally on your PC

## Prerequisites

- Vercel account (free at https://vercel.com)
- DuckDNS domain configured (you have: jobtrackai.duckdns.org)
- Port forwarding set up on your router
- SSL certificate for HTTPS (optional but recommended)

## Step 1: Set Up Your PC Backend for Internet Access

### Option A: Using Traefik (Your Current Setup - Recommended)

Since you already have Traefik running, this is the easiest option!

Your setup will work like this:
- External: `https://jobtrackai.duckdns.org` (port 443)
- Traefik forwards to: `http://localhost:5000` (Flask)

**See `traefik_setup.md` for complete setup instructions.**

Quick steps:
1. Add Traefik labels to docker-compose.yml
2. Run `docker-compose up -d`
3. Traefik automatically gets SSL certificate
4. Done!

### Option B: Using Nginx (Alternative)

**See `nginx_setup.md` for complete setup instructions.**

Quick steps:
1. Install Nginx
2. Get SSL certificate (certbot or Let's Encrypt)
3. Configure Nginx to forward port 443 → 5000
4. Update router to forward port 443 (not 5000)
5. Start both Nginx and Flask

### Option B: Using ngrok (Alternative - Easier for Testing)

```bash
# Install ngrok from https://ngrok.com
ngrok http 5000

# You'll get a URL like: https://abc123.ngrok-free.app
# Update .env.production with this URL
```

### Option C: Using Cloudflare Tunnel (Alternative - Free & Stable)

```bash
# Install Cloudflare Tunnel
cloudflared tunnel --url http://localhost:5000

# You'll get a trycloudflare.com URL
# Update .env.production with this URL
```

## Step 2: Update Flask Backend for CORS

Your Flask backend needs to accept requests from Vercel. Update `app_enhanced.py`:

```python
from flask_cors import CORS

app = Flask(__name__)

# Update CORS to allow Vercel domain
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "https://*.vercel.app",  # Allow all Vercel preview deployments
            "https://your-app.vercel.app"  # Your production Vercel domain
        ],
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})
```

## Step 3: Configure Environment Variables

You already have these files set up:

**`.env.local`** (for local development):
```env
REACT_APP_API_URL=http://localhost:5000
```

**`.env.production`** (for Vercel deployment):
```env
REACT_APP_API_URL=https://jobtrackai.duckdns.org:5000
```

## Step 4: Deploy Frontend to Vercel

### Method 1: Using Vercel CLI (Recommended)

```bash
# Install Vercel CLI
npm install -g vercel

# Navigate to client folder
cd client

# Login to Vercel
vercel login

# Deploy
vercel

# For production deployment
vercel --prod
```

### Method 2: Using Vercel Dashboard (Easier for First Time)

1. **Push Code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/learning-platform.git
   git push -u origin main
   ```

2. **Import to Vercel:**
   - Go to https://vercel.com/new
   - Click "Import Git Repository"
   - Select your GitHub repository
   - Configure project:
     - **Framework Preset**: Create React App
     - **Root Directory**: `client`
     - **Build Command**: `npm run build`
     - **Output Directory**: `build`

3. **Add Environment Variable:**
   - In Vercel project settings
   - Go to "Environment Variables"
   - Add: `REACT_APP_API_URL` = `https://jobtrackai.duckdns.org:5000`

4. **Deploy:**
   - Click "Deploy"
   - Wait for deployment to complete
   - You'll get a URL like: `https://your-app.vercel.app`

## Step 5: Start Your Backend

On your PC, start the Flask backend:

```bash
# Make sure you're in the project root
python app_enhanced.py

# The server should run on port 5000
# It should be accessible at https://jobtrackai.duckdns.org:5000
```

## Step 6: Test the Deployment

1. **Test Backend Accessibility:**
   ```bash
   # From any device, test:
   curl https://jobtrackai.duckdns.org:5000/api/health

   # Should return: {"status": "ok", ...}
   ```

2. **Test Frontend:**
   - Visit your Vercel URL: `https://your-app.vercel.app`
   - Check browser console for any CORS errors
   - Try browsing courses

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:

1. Update Flask CORS configuration to include your Vercel domain
2. Make sure Flask server is running
3. Check that HTTPS is properly configured

### Backend Not Accessible

1. **Check Port Forwarding:**
   ```bash
   # Test from outside your network using mobile data
   curl https://jobtrackai.duckdns.org:5000/api/health
   ```

2. **Check Firewall:**
   - Windows: Allow port 5000 in Windows Firewall
   - Add inbound rule for port 5000

3. **Check Router:**
   - Ensure port forwarding is saved and active
   - Some routers require reboot after configuration

### Videos Not Playing

1. **Mixed Content Error (HTTP/HTTPS):**
   - Ensure backend uses HTTPS
   - Browsers block HTTP content on HTTPS pages

2. **File Size Issues:**
   - Vercel has no involvement in video serving
   - Your PC's upload speed affects streaming quality

### Slow Performance

1. **Upload Speed:**
   - Your PC's upload speed limits video streaming
   - Consider compressing videos
   - Use lower bitrate for better streaming

2. **Keep PC Running:**
   - Backend must be running 24/7 for access
   - Consider using a VPS for production

## Production Considerations

### Security

1. **Add Authentication:**
   - Implement user login system
   - Protect API endpoints
   - Don't expose database directly

2. **Use HTTPS:**
   - Essential for security
   - Required for many browser features
   - Set up SSL certificate

3. **Rate Limiting:**
   - Protect against abuse
   - Limit API requests per IP

### Reliability

1. **Keep Backend Running:**
   - Use Windows Task Scheduler to auto-start
   - Set up monitoring/alerts
   - Consider UPS for power backup

2. **Dynamic IP Updates:**
   - Ensure DuckDNS updater runs automatically
   - Test after IP changes

3. **Backup:**
   - Regular database backups
   - Keep media files backed up

## Alternative: Full Cloud Deployment

For better reliability, consider deploying backend to cloud:

1. **AWS EC2 / DigitalOcean Droplet:**
   - Upload media files to cloud storage
   - Run Flask backend on server
   - No port forwarding needed

2. **Vercel + Cloud Storage:**
   - Backend on Vercel serverless functions
   - Videos on AWS S3 / Cloudflare R2
   - Database on MongoDB Atlas

## Useful Commands

```bash
# Local development
cd client
npm start  # Frontend on http://localhost:3000

# In another terminal
python app_enhanced.py  # Backend on http://localhost:5000

# Scan new courses
python folder_scanner.py --rescan

# Deploy to Vercel
cd client
vercel --prod

# Check backend status
curl https://jobtrackai.duckdns.org:5000/api/health
```

## Environment URLs

- **Local Development Frontend**: http://localhost:3000
- **Local Development Backend**: http://localhost:5000
- **Production Frontend (Vercel)**: https://your-app.vercel.app
- **Production Backend (Your PC)**: https://jobtrackai.duckdns.org (no port needed!)
- **Backend Internal**: http://localhost:5000 (Flask app)

## Quick Checklist

Before deploying:
- [ ] Port 5000 forwarded on router
- [ ] DuckDNS configured and updating
- [ ] Flask backend running with CORS enabled
- [ ] `.env.production` has correct API URL
- [ ] Backend accessible from external network
- [ ] Vercel account created
- [ ] Code pushed to GitHub (if using Git integration)

After deploying:
- [ ] Test from different device/network
- [ ] Check browser console for errors
- [ ] Verify videos stream properly
- [ ] Test document downloads
- [ ] Check progress tracking works

## Support

Common issues:
1. **Can't access backend** - Check port forwarding and firewall
2. **CORS errors** - Update Flask CORS configuration
3. **Videos won't play** - Ensure HTTPS is configured
4. **Vercel deployment fails** - Check build logs in Vercel dashboard

For Vercel-specific issues: https://vercel.com/docs
For Flask CORS issues: https://flask-cors.readthedocs.io/
