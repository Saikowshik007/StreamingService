# Learning Platform - Udemy-like Course Streaming System

A full-stack learning management system (LMS) that automatically scans your local folder structure and serves videos/documents with progress tracking. Built with Python Flask backend and React frontend, integrated with Traefik for production deployment.

## 🚀 Key Features

- **Automatic Folder Scanning** - Point to your course folder and it automatically detects courses, lessons, and files
- **File-Level Progress Tracking** - Track progress for each video file individually
- **Course Progress Dashboard** - See completion percentage and files completed
- **Video Streaming** - Stream videos with seek support and auto-save position
- **Document Serving** - Serve PDFs and documents
- **Traefik Integration** - Works seamlessly with your existing Traefik setup
- **Vercel Deployment** - Frontend hosted on Vercel, backend on your PC

## 📁 Expected Folder Structure

```
CourseMedia/
├── Python Programming/
│   ├── Introduction/
│   │   ├── lesson1.mp4
│   │   ├── lesson2.mp4
│   │   └── notes.pdf
│   └── Advanced Topics/
│       ├── lesson3.mp4
│       └── exercises.pdf
├── Web Development/
│   ├── HTML Basics/
│   │   └── intro.mp4
│   └── CSS Styling/
│       └── styling.mp4
```

**Structure:**
- First level: Course folders (e.g., "Python Programming")
- Second level: Lesson/topic folders (e.g., "Introduction")
- Third level: Video and document files

## 🎬 Quick Start

### 1. Set Up Folder Structure

```bash
# Create your course media folder
mkdir -p C:/Users/anant/Desktop/CourseMedia

# Add your courses following the structure above
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set your media path
# MEDIA_PATH=C:/Users/anant/Desktop/CourseMedia
```

### 3. Deploy with Docker (Traefik)

```bash
# Build and start
docker-compose up -d

# Scan your courses
docker exec learning-platform-backend python folder_scanner.py

# Check status
docker logs learning-platform-backend
```

### 4. Test Backend

```bash
# Test through Traefik
curl https://jobtrackai.duckdns.org/learn/api/health

# Get courses
curl https://jobtrackai.duckdns.org/learn/api/courses
```

### 5. Deploy Frontend to Vercel

```bash
cd client
npm install
vercel --prod
```

Set environment variable in Vercel:
- `REACT_APP_API_URL` = `https://jobtrackai.duckdns.org/learn`

## 🎯 Supported File Types

**Videos:** .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v
**Documents:** .pdf, .doc, .docx, .txt, .ppt, .pptx, .xls, .xlsx, .zip, .rar

## 🏗️ Project Structure

```
StreamingService/
├── app_enhanced.py          # Enhanced Flask backend
├── database_enhanced.py     # Enhanced database schema
├── folder_scanner.py        # Automatic course importer
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container config
├── docker-compose.yml      # Traefik integration
├── .env                    # Environment variables
└── client/                 # React frontend
    ├── src/
    ├── package.json
    └── vercel.json
```

## 📚 Documentation

- **[QUICK_START.md](QUICK_START.md)** - 5-minute setup guide
- **[TRAEFIK_INTEGRATION.md](TRAEFIK_INTEGRATION.md)** - Detailed Traefik configuration
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[MIGRATION_CLEANUP.md](MIGRATION_CLEANUP.md)** - Cleanup old files guide

## 🔧 Common Tasks

### Adding New Courses

```bash
# 1. Add folders to CourseMedia/
# 2. Rescan
docker exec learning-platform-backend python folder_scanner.py --rescan
# 3. Refresh browser
```

### Viewing Logs

```bash
docker logs learning-platform-backend -f
```

### Restarting Service

```bash
docker-compose restart learning-platform-backend
```

### Database Reset

```bash
# WARNING: Deletes all progress data
rm -rf data/database.db
docker-compose restart learning-platform-backend
docker exec learning-platform-backend python folder_scanner.py
```

## 🌐 URLs

**Development:**
- Backend: `http://localhost:5000/api/*`
- Frontend: `http://localhost:3000`

**Production:**
- Backend: `https://jobtrackai.duckdns.org/learn/api/*`
- Frontend: `https://your-app.vercel.app`
- Traefik Dashboard: `http://localhost:8080`

## 🔍 API Endpoints

- `GET /api/courses` - List all courses with progress
- `GET /api/courses/:id` - Get course details with lessons
- `GET /api/lessons/:id` - Get lesson with files
- `GET /api/stream/:id` - Stream video file
- `GET /api/document/:id` - Download document
- `POST /api/progress` - Update watch progress
- `GET /api/stats` - Platform statistics
- `GET /api/health` - Health check

## 🐛 Troubleshooting

### Container won't start
```bash
docker logs learning-platform-backend
# Check media path exists
# Check permissions on data/ directory
```

### Videos won't play
- Use MP4 format for best compatibility
- Check file exists in CourseMedia folder
- Verify path in database matches actual file

### Can't access from internet
```bash
# Check Traefik routing
docker logs jobtrak-traefik

# Verify container is on correct network
docker network inspect jobtrak-network

# Test direct access
curl http://localhost:5000/api/health
```

### CORS errors
- Flask CORS is configured in `app_enhanced.py`
- Add your Vercel domain if needed
- Check browser console for specific errors

## 🔒 Security Notes

**For Production:**
- Add authentication system
- Use HTTPS (handled by Traefik)
- Implement rate limiting
- Set proper file permissions
- Regular backups of database

## 📦 Tech Stack

**Backend:**
- Python 3.11
- Flask
- SQLite
- Docker

**Frontend:**
- React 18
- React Router
- Axios
- Vercel

**Infrastructure:**
- Traefik (reverse proxy)
- DuckDNS (domain)
- Let's Encrypt (SSL)

## 🤝 Contributing

This is a personal project, but suggestions are welcome!

## 📄 License

MIT

## 🎓 Use Cases

- Personal course library
- Internal training materials
- Educational content streaming
- Video documentation hosting
- E-learning platform prototype

## ⚡ Performance Tips

1. **Use MP4 format** for best browser compatibility
2. **Compress videos** for faster streaming
3. **Keep database on SSD** for better performance
4. **Use path-based routing** to avoid subdomain complexity
5. **Regular database cleanup** for old progress data

## 🔮 Future Enhancements

- [ ] User authentication system
- [ ] Multiple user support
- [ ] Quiz/assessment system
- [ ] Course certificates
- [ ] Video quality selection
- [ ] Subtitles support
- [ ] Mobile app
- [ ] Admin dashboard

---

**Made with** ❤️ **for self-hosted learning**

For issues or questions, check the documentation files or create an issue.
