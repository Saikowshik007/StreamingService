# Firebase Migration Guide

This guide will help you migrate your streaming service from local SQLite database to Firebase Firestore with base64-encoded thumbnails.

## What Changed

### Database
- **Before**: Local SQLite database (`streaming.db`)
- **After**: Firebase Firestore (cloud database)

### Thumbnails
- **Before**: Stored as image files in `Media/thumbnails/`
- **After**: Stored as base64 strings directly in Firestore

### Benefits
- ✅ No more local database file management
- ✅ Cloud-based, accessible from anywhere
- ✅ Automatic backups and scaling
- ✅ No thumbnail files to manage
- ✅ Faster thumbnail loading (embedded in API responses)

## Prerequisites

1. **Python packages** - Install new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. **ffmpeg** - Required for thumbnail generation:
   - **Windows**: `choco install ffmpeg` or download from ffmpeg.org
   - **Linux**: `sudo apt install ffmpeg`
   - **Mac**: `brew install ffmpeg`

## Firebase Setup

### Step 1: Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click "Add Project"
3. Enter project name (e.g., "streaming-service")
4. Disable Google Analytics (optional)
5. Click "Create Project"

### Step 2: Enable Firestore Database

1. In Firebase Console, click "Firestore Database" in the left menu
2. Click "Create database"
3. Choose "Start in production mode"
4. Select a location (choose closest to your users)
5. Click "Enable"

### Step 3: Set Up Firestore Security Rules

In the Firestore console, go to the "Rules" tab and update with:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow read/write access to all documents
    // IMPORTANT: Update these rules for production!
    match /{document=**} {
      allow read, write: if true;
    }
  }
}
```

**Note**: For production, implement proper authentication and security rules!

### Step 4: Get Firebase Credentials

1. In Firebase Console, click the gear icon ⚙️ (Settings)
2. Go to "Project settings"
3. Click on the "Service accounts" tab
4. Click "Generate new private key"
5. Save the JSON file as `firebase-credentials.json` in your project root

### Step 5: Configure Environment Variables

You have two options for providing Firebase credentials:

**Option 1: Credentials File** (Recommended for development)
```bash
# Place firebase-credentials.json in project root
# The app will automatically find it
```

**Option 2: Environment Variable** (Recommended for production)
```bash
# Set the JSON content as an environment variable
export FIREBASE_CREDENTIALS='<paste-json-content-here>'
```

Or set the file path:
```bash
export FIREBASE_CREDENTIALS_PATH='/path/to/firebase-credentials.json'
```

## Migration Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Firebase

Place your `firebase-credentials.json` file in the project root directory.

### 3. Test Firebase Connection

```bash
python firebase_service.py
```

You should see: "Firebase service initialized successfully!"

### 4. Scan Your Media Files

This will import all your courses, lessons, and files into Firebase and generate thumbnails:

```bash
python folder_scanner.py
```

Or scan a specific directory:

```bash
python folder_scanner.py /path/to/media --rescan
```

### 5. Generate Thumbnails for Existing Videos

Start the Flask server:

```bash
python app.py
```

Then make a POST request to generate thumbnails:

```bash
curl -X POST http://localhost:5000/learn/api/thumbnails/generate
```

### 6. Start the Application

Backend:
```bash
python app.py
```

Frontend:
```bash
cd client
npm start
```

## Firestore Collections Structure

Your data is organized in the following collections:

### `courses`
```javascript
{
  id: "auto-generated",
  title: "Course Name",
  description: "Course description",
  instructor: "Instructor name",
  thumbnail: null,
  folder_path: "relative/path",
  total_files: 10,
  created_at: timestamp,
  updated_at: timestamp
}
```

### `lessons`
```javascript
{
  id: "auto-generated",
  course_id: "course-id",
  title: "Lesson Name",
  description: null,
  folder_path: "relative/path",
  order_index: 1,
  created_at: timestamp
}
```

### `files`
```javascript
{
  id: "auto-generated",
  lesson_id: "lesson-id",
  course_id: "course-id",
  filename: "video.mp4",
  file_path: "relative/path/video.mp4",
  file_type: ".mp4",
  file_size: 1234567,
  duration: null,
  order_index: 1,
  is_video: true,
  is_document: false,
  thumbnail_base64: "data:image/jpeg;base64,...",
  created_at: timestamp,
  last_scanned: timestamp
}
```

### `user_progress`
```javascript
{
  id: "auto-generated",
  user_id: "default_user",
  file_id: "file-id",
  lesson_id: "lesson-id",
  course_id: "course-id",
  progress_seconds: 120,
  progress_percentage: 45.5,
  completed: false,
  last_watched: timestamp
}
```

### `course_progress`
```javascript
{
  id: "auto-generated",
  user_id: "default_user",
  course_id: "course-id",
  total_files: 10,
  completed_files: 5,
  total_duration: 3600,
  watched_duration: 1800,
  progress_percentage: 50,
  last_updated: timestamp
}
```

### `scan_history`
```javascript
{
  id: "auto-generated",
  scan_path: "/path/to/media",
  files_found: 100,
  courses_added: 5,
  lessons_added: 20,
  scan_duration: 45.5,
  scan_timestamp: timestamp,
  status: "success"
}
```

## API Changes

### Thumbnail Endpoint

**Before**:
```
GET /api/thumbnail/<file_id>
Returns: Image file (JPEG)
```

**After**:
```
GET /api/thumbnail/<file_id>
Returns: JSON with base64 string
{
  "thumbnail": "data:image/jpeg;base64,/9j/4AAQ..."
}
```

**Frontend Usage**:
```javascript
// Thumbnail is now included in file data
<img src={file.thumbnail_base64} alt={file.filename} />
```

## Troubleshooting

### Firebase Connection Issues

**Error**: "Failed to initialize Firebase"
- Check that `firebase-credentials.json` exists and is valid JSON
- Verify environment variables are set correctly
- Ensure Firebase project has Firestore enabled

### Thumbnail Generation Issues

**Error**: "ffmpeg not found"
- Install ffmpeg: `choco install ffmpeg` (Windows) or `brew install ffmpeg` (Mac)
- Verify ffmpeg is in PATH: `ffmpeg -version`

**Error**: "Thumbnail generation timed out"
- Large video files may take time
- Check that video files are accessible
- Verify ffmpeg can read the video format

### Import Issues

**Error**: "File not found"
- Check that `Config.MEDIA_PATH` points to the correct directory
- Verify file permissions

**Slow imports**:
- Thumbnail generation can be slow for many videos
- Consider running import in batches
- You can skip thumbnail generation initially and run `/api/thumbnails/generate` later

## Production Considerations

1. **Security Rules**: Update Firestore security rules to implement proper authentication
2. **Environment Variables**: Use environment variables for credentials in production
3. **Backup**: Set up automated backups in Firebase Console
4. **Indexes**: Create composite indexes if you need complex queries
5. **Monitoring**: Enable Firebase monitoring and logging

## Reverting to SQLite (If Needed)

If you need to revert to the old SQLite database:

1. Restore `database_enhanced.py` imports in `app.py`
2. Change `import firebase_service as db` back to `from database_enhanced import *`
3. Update all function calls to match SQLite patterns
4. Restore `init_enhanced_db()` call
5. Update frontend to fetch thumbnails as images

## Support

For issues or questions:
- Check Firebase Console for error logs
- Review application logs for detailed error messages
- Verify all dependencies are installed correctly

## Next Steps

1. ✅ Set up Firebase project
2. ✅ Configure credentials
3. ✅ Import media files
4. ✅ Generate thumbnails
5. ✅ Test the application
6. 🔒 Update security rules for production
7. 🚀 Deploy!
