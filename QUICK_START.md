# Quick Start Guide

## Setup (5 minutes)

### 1. Organize Your Course Files

Create your folder structure:
```
C:/Users/anant/Desktop/CourseMedia/
├── Python Basics/
│   ├── Lesson 1/
│   │   ├── intro.mp4
│   │   └── notes.pdf
│   └── Lesson 2/
│       └── variables.mp4
└── Web Development/
    └── HTML Basics/
        └── intro.mp4
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Edit `.env` file:
```env
MEDIA_PATH=C:/Users/anant/Desktop/CourseMedia
PORT=5000
```

### 4. Scan Your Courses

```bash
python folder_scanner.py
```

This will automatically:
- Find all courses
- Import videos and documents
- Create database entries

### 5. Start Backend

```bash
python app_enhanced.py
```

Backend runs at: http://localhost:5000

### 6. Start Frontend (Local Development)

```bash
cd client
npm install
npm start
```

Frontend runs at: http://localhost:3000

## Deploy to Vercel (10 minutes)

### 1. Ensure Backend is Internet-Accessible

Your PC backend must be accessible at: https://jobtrackai.duckdns.org

**Since you're using Traefik:** See `traefik_setup.md` for configuration.

Quick setup with Docker:
```bash
docker-compose up -d
```

**Test it:**
```bash
curl https://jobtrackai.duckdns.org/api/health
```

### 2. Deploy Frontend to Vercel

**Option A: Using Vercel CLI**
```bash
cd client
npm install -g vercel
vercel login
vercel --prod
```

**Option B: Using GitHub + Vercel Dashboard**
1. Push code to GitHub
2. Go to vercel.com/new
3. Import your repository
4. Set root directory to: `client`
5. Add environment variable:
   - Key: `REACT_APP_API_URL`
   - Value: `https://jobtrackai.duckdns.org`
6. Deploy!

### 3. Access Your App

- Frontend (Vercel): https://your-app.vercel.app
- Backend (Your PC): https://jobtrackai.duckdns.org

## Daily Usage

### Adding New Courses

1. Add folders to CourseMedia
2. Run: `python folder_scanner.py --rescan`
3. Refresh browser

### Keeping Backend Running

**Windows:** Create a batch file `start-backend.bat`:
```batch
@echo off
cd C:\Users\anant\Desktop\StreamingService
python app_enhanced.py
```

Add to Windows Task Scheduler to auto-start on boot.

## Common Commands

```bash
# Rescan courses after adding new files
python folder_scanner.py --rescan

# Check backend status
curl http://localhost:5000/api/health

# View statistics
curl http://localhost:5000/api/stats

# Deploy updated frontend
cd client && vercel --prod
```

## Troubleshooting

**Backend not accessible from internet:**
- Check port forwarding on router
- Allow port 5000 in Windows Firewall
- Verify DuckDNS is updating your IP

**Videos won't play:**
- Use MP4 format
- Ensure HTTPS is configured for backend
- Check browser console for errors

**Progress not saving:**
- Ensure database.db file is writable
- Check Flask server logs

## File Structure Reference

```
StreamingService/
├── app_enhanced.py          # Start this for backend
├── folder_scanner.py        # Run this to import courses
├── database_enhanced.py     # Database schema
├── .env                     # Configuration
├── requirements.txt         # Python dependencies
└── client/                  # React frontend
    ├── package.json
    ├── vercel.json          # Vercel config
    └── .env.production      # Production API URL
```

## Next Steps

- Read DEPLOYMENT_GUIDE.md for detailed Vercel deployment
- Read README_ENHANCED.md for all features
- Add authentication for security
- Set up HTTPS with SSL certificate
