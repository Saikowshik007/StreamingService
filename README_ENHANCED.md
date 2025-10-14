# Learning Platform - Enhanced with Automatic Folder Scanning

A full-stack learning management system (LMS) that automatically scans your local folder structure and serves videos/documents. Built with Python Flask backend and React frontend.

## Key Features

- **Automatic Folder Scanning** - Point to your course folder and it automatically detects courses, lessons, and files
- **File-Level Progress Tracking** - Track progress for each video file individually
- **Course Progress Dashboard** - See completion percentage and files completed
- **Video Streaming** - Stream videos with seek support and auto-save position
- **Document Serving** - Serve PDFs and documents
- **Responsive Design** - Works on desktop and mobile
- **Internet Accessible** - Instructions to expose over the internet

## Expected Folder Structure

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

## Supported File Types

**Videos:** .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm, .m4v
**Documents:** .pdf, .doc, .docx, .txt, .ppt, .pptx, .xls, .xlsx, .zip, .rar

## Quick Start

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure your media path in .env file
# Set MEDIA_PATH to your course folder location
```

Edit `.env` file:
```env
MEDIA_PATH=C:/Users/anant/Desktop/CourseMedia
PORT=5000
```

### 2. Scan Your Folders

Run the automatic folder scanner:

```bash
# Scan and import all courses
python folder_scanner.py

# Or specify a custom path
python folder_scanner.py "D:/MyCourses"

# To rescan and update existing courses
python folder_scanner.py --rescan
```

The scanner will:
- Detect all courses and lessons from your folder structure
- Import video and document files
- Create database entries automatically
- Show a summary of what was imported

### 3. Start the Backend Server

```bash
# Using the enhanced version
python app.py

# Or use the original if you want manual course management
python app.py
```

Server runs at http://localhost:5000

### 4. Frontend Setup

```bash
# Install dependencies
cd client
npm install

# Start the development server
npm start
```

Frontend runs at http://localhost:3000

## Database Schema

The enhanced system uses these tables:

- **courses** - Course information with folder paths
- **lessons** - Lesson/topic information
- **files** - Individual video and document files
- **user_progress** - Progress tracking for each file
- **course_progress** - Overall course completion statistics
- **scan_history** - History of folder scans

## API Endpoints (Enhanced)

### Courses
- `GET /api/courses` - Get all courses with progress
- `GET /api/courses/:id` - Get course with lessons and files
- `GET /api/courses/:id/progress` - Get course progress

### Lessons
- `GET /api/lessons/:id` - Get lesson with files and progress

### Files
- `GET /api/file/:id` - Get file information
- `GET /api/stream/:id` - Stream video file
- `GET /api/document/:id` - Get document file

### Progress
- `POST /api/progress` - Update file progress
- `GET /api/progress/course/:id` - Get course progress

### Admin
- `POST /api/scan` - Trigger folder scan
- `GET /api/scan/history` - Get scan history
- `GET /api/stats` - Get platform statistics

## Features in Detail

### File-Level Progress Tracking

Each video file tracks:
- Current position (in seconds)
- Completion percentage
- Completed status
- Last watched timestamp

Progress is auto-saved every 5 seconds while watching.

### Course Progress

Courses show:
- Overall completion percentage
- Number of files completed vs total
- Total duration watched
- Visual progress bars

### Automatic Resume

When you return to a video:
- It automatically resumes from where you left off
- Progress is maintained across sessions

### Auto-Play Next

After finishing a video:
- Automatically plays the next video in the lesson
- Skips to next incomplete video

## Folder Management

### Adding New Courses

1. Add new folders to your MEDIA_PATH directory
2. Run: `python folder_scanner.py --rescan`
3. Refresh your browser

### Updating Existing Courses

1. Add/remove files in your course folders
2. Run: `python folder_scanner.py --rescan`
3. Database will be updated automatically

### File Organization Tips

- Use clear, descriptive folder names (they become course/lesson titles)
- Number files to control order (e.g., "01_intro.mp4", "02_basics.mp4")
- Keep related files together in lesson folders
- Use consistent naming conventions

## Making It Internet Accessible

### Option 1: ngrok (Easiest)

```bash
# Start your Flask server
python app.py

# In another terminal
ngrok http 5000

# ngrok will give you a public URL like: https://abc123.ngrok.io
```

### Option 2: Cloudflare Tunnel (Free & Stable)

```bash
# Install Cloudflare Tunnel
# Download from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/

# Run tunnel
cloudflared tunnel --url http://localhost:5000
```

### Option 3: Port Forwarding

1. Find your local IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)
2. Access router admin panel
3. Forward port 5000 to your local IP
4. Access via your public IP address

### Option 4: Cloud Deployment

Deploy to:
- **AWS EC2** - Full control, pay per use
- **DigitalOcean** - Simple droplets
- **Google Cloud** - Compute Engine
- **Azure** - Virtual Machines

**Security Warning:** When exposing to internet:
- Add authentication/login system
- Use HTTPS with SSL certificate
- Implement rate limiting
- Use firewall rules
- Don't expose sensitive files

## Troubleshooting

### Scanner Issues

**"Path does not exist"**
- Check MEDIA_PATH in .env file
- Ensure path uses forward slashes or double backslashes
- Example: `C:/Users/anant/Desktop/CourseMedia`

**"No courses found"**
- Verify folder structure (Course/Lesson/Files)
- Check file extensions are supported
- Ensure folders aren't empty

### Video Issues

**Videos won't play**
- Use MP4 format for best compatibility
- Check file isn't corrupted
- Verify MEDIA_PATH is correct
- Check browser console for errors

**Progress not saving**
- Ensure database is writable
- Check browser console for errors
- Verify API endpoint is reachable

### Database Issues

**"Database locked"**
- Close all connections to database
- Restart Flask server
- Check file permissions

**Want to reset everything?**
```bash
# Delete database file
rm database.db  # or del database.db on Windows

# Run scanner again
python folder_scanner.py
```

## Advanced Configuration

### Custom Scan Location

```python
from folder_scanner import scan_and_import

# Scan specific path
scan_and_import('D:/MyCourses')

# Rescan existing
scan_and_import('D:/MyCourses', rescan=True)
```

### Programmatic Course Management

```python
from database_enhanced import get_db, update_course_progress

# Get all courses
conn = get_db()
cursor = conn.cursor()
cursor.execute('SELECT * FROM courses')
courses = cursor.fetchall()

# Update progress for a user
update_course_progress(course_id=1, user_id='user123')
```

## Project Structure

```
StreamingService/
├── app_enhanced.py          # Enhanced Flask server
├── database_enhanced.py     # Enhanced database schema
├── folder_scanner.py        # Automatic folder scanner
├── config.py               # Configuration
├── requirements.txt        # Python dependencies
├── .env                    # Environment variables
├── client/                 # React frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Home.js              # Course listing with progress
│   │   │   ├── CoursePage.js        # Course details
│   │   │   └── LessonPlayerEnhanced.js  # Video player with file list
│   │   └── components/
│   └── package.json
```

## Development

```bash
# Backend with auto-reload
python app.py

# Frontend with hot reload
cd client
npm start

# Rescan folders after adding content
python folder_scanner.py --rescan
```

## Statistics & Monitoring

Access statistics:
```bash
# Via API
curl http://localhost:5000/api/stats

# Shows:
# - Total courses
# - Total lessons
# - Total files
# - Videos count
# - Documents count
```

View scan history:
```bash
curl http://localhost:5000/api/scan/history
```

## Tips for Best Experience

1. **Organize folders logically** - Clear structure = better course organization
2. **Use MP4 format** - Best browser compatibility
3. **Rescan after changes** - Always rescan when adding new content
4. **Check scan history** - Monitor successful imports
5. **Keep files local** - For fast streaming access

## Common Workflows

### Adding a New Course

```bash
# 1. Create folder structure
mkdir "CourseMedia/New Course/Lesson 1"

# 2. Add video files
cp videos/*.mp4 "CourseMedia/New Course/Lesson 1/"

# 3. Scan
python folder_scanner.py --rescan

# 4. Refresh browser
```

### Monitoring Progress

```python
from database_enhanced import get_course_stats

# Get stats for a course
stats = get_course_stats(course_id=1, user_id='default_user')
print(f"Completed: {stats['completed_files']}/{stats['total_files']}")
```

## License

MIT

## Support

For issues, check:
1. Console logs (browser & terminal)
2. Database file exists and is writable
3. MEDIA_PATH is correct
4. File permissions are proper
5. Folder structure matches expected format
