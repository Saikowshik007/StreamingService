# Learning Platform - Udemy Clone

A full-stack learning management system (LMS) that streams videos and serves documents from your local file system. Built with Python Flask backend and React frontend.

## Features

- Browse courses with beautiful UI
- Stream videos from local file system with seek support
- Serve PDF and document files
- Track learning progress
- Responsive design
- Course organization with lessons and resources

## Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

## Project Structure

```
StreamingService/
├── app.py              # Flask backend server
├── config.py           # Configuration settings
├── database.py         # Database initialization and helpers
├── add_courses.py      # Script to add courses to database
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create from .env.example)
├── client/            # React frontend
│   ├── public/
│   └── src/
│       ├── components/
│       ├── pages/
│       └── App.js
```

## Setup Instructions

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure your media path
# Edit .env file and set MEDIA_PATH to your video/document folder
# Example: MEDIA_PATH=C:/Users/anant/Desktop/CourseMedia

# Initialize the database
python database.py
```

### 2. Organize Your Media Files

Create a folder structure for your course media:

```
CourseMedia/
├── python/
│   ├── intro.mp4
│   ├── variables.mp4
│   └── cheatsheet.pdf
├── web/
│   ├── html-intro.mp4
│   └── css-basics.mp4
```

### 3. Add Courses to Database

Edit `add_courses.py` to add your own courses, then run:

```bash
python add_courses.py
```

Or use the Python functions directly:

```python
from database import init_db
from add_courses import add_course, add_lesson, add_resource

# Add a course
course_id = add_course(
    title='My Course',
    description='Course description',
    instructor='Your Name'
)

# Add a lesson with video
lesson_id = add_lesson(
    course_id=course_id,
    title='Lesson 1',
    description='Lesson description',
    video_path='folder/video.mp4',  # Relative to MEDIA_PATH
    duration=600,  # seconds
    order_index=1
)

# Add a resource (PDF, document, etc.)
add_resource(
    lesson_id=lesson_id,
    title='Course Notes',
    file_path='folder/notes.pdf',  # Relative to MEDIA_PATH
    file_type='pdf'
)
```

### 4. Frontend Setup

```bash
# Navigate to client folder
cd client

# Install dependencies
npm install

# Start the development server
npm start
```

The React app will open at http://localhost:3000

### 5. Start the Backend Server

In a new terminal:

```bash
# Make sure you're in the project root directory
python app.py
```

The Flask server will run at http://localhost:5000

## Making It Accessible Over the Internet

To access your learning platform from anywhere on the internet, you have several options:

### Option 1: Using ngrok (Recommended for Testing)

1. Download ngrok from https://ngrok.com/
2. Install and authenticate ngrok
3. Run your Flask server: `python app.py`
4. In another terminal, run: `ngrok http 5000`
5. ngrok will provide a public URL like `https://abc123.ngrok.io`
6. Update your React app's proxy or API calls to use this URL

### Option 2: Using Cloudflare Tunnel (Free)

1. Install Cloudflare Tunnel: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/
2. Run: `cloudflared tunnel --url http://localhost:5000`
3. You'll get a public URL that tunnels to your local server

### Option 3: Port Forwarding (Requires Router Access)

1. Find your local IP address
2. Access your router settings
3. Forward port 5000 to your computer's local IP
4. Use your public IP address to access the server
5. Consider using a dynamic DNS service for a consistent URL

### Option 4: Deploy to a Cloud Server

For production use, deploy to:
- AWS EC2
- Google Cloud Compute Engine
- DigitalOcean Droplet
- Heroku
- Azure VM

**Security Warning**: When exposing your server to the internet:
- Add authentication/login system
- Use HTTPS/SSL certificates
- Implement rate limiting
- Add firewall rules
- Keep your software updated
- Don't expose sensitive files

## Configuration

Edit `.env` file to configure:

```env
PORT=5000                                    # Backend server port
MEDIA_PATH=C:/Users/anant/Desktop/CourseMedia  # Path to your videos/documents
DB_PATH=database.db                          # SQLite database file
```

## API Endpoints

- `GET /api/courses` - Get all courses
- `GET /api/courses/:id` - Get course details with lessons
- `GET /api/lessons/:id` - Get lesson details with resources
- `GET /api/video/:lessonId` - Stream video (supports range requests)
- `GET /api/document/:resourceId` - Download/view document
- `POST /api/progress` - Update user progress
- `GET /api/progress/:lessonId` - Get user progress

## Supported File Types

### Videos
- MP4 (recommended)
- WebM
- OGG

### Documents
- PDF
- DOCX
- TXT
- XLSX
- PPTX
- ZIP

## Troubleshooting

### Videos won't play
- Ensure video files exist in the MEDIA_PATH directory
- Check file paths in database match actual file locations
- Verify video format is supported (MP4 recommended)
- Check browser console for errors

### Can't connect to backend
- Ensure Flask server is running on port 5000
- Check `.env` file configuration
- Verify no firewall is blocking the connection

### Database errors
- Run `python database.py` to reinitialize
- Check file permissions
- Ensure SQLite is installed

## Development

```bash
# Backend (with auto-reload)
pip install python-dotenv flask flask-cors
python app.py

# Frontend (with hot reload)
cd client
npm start
```

## Production Build

```bash
# Build React frontend
cd client
npm run build

# The build folder can be served by Flask or any web server
# You can modify app.py to serve the React build in production
```

## License

MIT

## Support

For issues and questions, refer to the code comments and Flask/React documentation.
