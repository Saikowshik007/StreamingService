# Migration to Enhanced Version - Cleanup Guide

## Files to Remove (Old Versions)

These files are replaced by enhanced versions:

1. **`app.py`** → Replaced by `app_enhanced.py`
2. **`database.py`** → Replaced by `database_enhanced.py`
3. **`add_courses.py`** → Replaced by `folder_scanner.py`

## Safe Cleanup Steps

### Option 1: Archive First (Recommended)

```bash
# Create archive folder
mkdir old_files_backup

# Move old files to archive
mv app.py old_files_backup/
mv database.py old_files_backup/
mv add_courses.py old_files_backup/

# If everything works fine after a week, delete the backup
# rm -rf old_files_backup/
```

### Option 2: Direct Deletion

If you're confident everything works:

```bash
# Remove old files
rm app.py
rm database.py
rm add_courses.py
```

### Windows Commands

```cmd
# Archive
mkdir old_files_backup
move app.py old_files_backup\
move database.py old_files_backup\
move add_courses.py old_files_backup\

# Or delete directly
del app.py
del database.py
del add_courses.py
```

## What's Different?

### app.py → app_enhanced.py

**Old (app.py):**
- Basic file serving
- Simple progress tracking by lesson
- Manual course creation required

**New (app_enhanced.py):**
- File-level progress tracking
- Automatic folder scanning
- Course progress calculation
- More robust CORS configuration
- Health check endpoints
- Statistics API

### database.py → database_enhanced.py

**Old (database.py):**
- Basic schema: courses, lessons, resources, user_progress
- Manual data insertion

**New (database_enhanced.py):**
- Enhanced schema with file tracking
- Course progress aggregation
- Scan history tracking
- Better indexing for performance
- Helper functions for stats

### add_courses.py → folder_scanner.py

**Old (add_courses.py):**
- Manual script to add courses
- Had to edit the file for each course
- No automatic detection

**New (folder_scanner.py):**
- Automatic folder scanning
- Detects course structure automatically
- Supports rescan with `--rescan` flag
- Tracks scan history
- Much more user-friendly

## Updated References

All documentation now points to enhanced versions:

- ✅ `docker-compose.yml` uses `app_enhanced.py`
- ✅ `Dockerfile` uses `app_enhanced.py`
- ✅ `QUICK_START.md` references enhanced files
- ✅ `DEPLOYMENT_GUIDE.md` references enhanced files
- ✅ `README_ENHANCED.md` uses new system

## Files to Keep

Keep these files (they're used by both old and new):

- ✅ `config.py` - Configuration (used by enhanced version)
- ✅ `requirements.txt` - Python dependencies
- ✅ `.env` - Environment variables
- ✅ `folder_scanner.py` - NEW: Auto-import system
- ✅ `app_enhanced.py` - NEW: Enhanced backend
- ✅ `database_enhanced.py` - NEW: Enhanced database

## Verification

After cleanup, verify:

1. **Check imports work:**
```bash
python -c "from app_enhanced import app; print('✓ app_enhanced loads')"
python -c "from database_enhanced import init_enhanced_db; print('✓ database_enhanced loads')"
python -c "from folder_scanner import scan_and_import; print('✓ folder_scanner loads')"
```

2. **Test Docker build:**
```bash
docker-compose build
```

3. **Start services:**
```bash
docker-compose up -d
```

4. **Test endpoints:**
```bash
curl http://localhost:5000/api/health
curl http://localhost:5000/api/stats
```

## If Something Breaks

If you run into issues after cleanup:

1. **Restore from backup:**
```bash
cp old_files_backup/* .
```

2. **Check what's using old files:**
```bash
# Search for imports of old files
grep -r "from app import" .
grep -r "import database" .
grep -r "add_courses" .
```

3. **File an issue with error details**

## Summary

**Remove these (old versions):**
- ❌ `app.py`
- ❌ `database.py`
- ❌ `add_courses.py`

**Keep these (current/active):**
- ✅ `app_enhanced.py`
- ✅ `database_enhanced.py`
- ✅ `folder_scanner.py`
- ✅ `config.py`
- ✅ All other files

After cleanup, your project will be cleaner and easier to maintain!
