@echo off
REM Cleanup script for Windows to remove old files

echo ==========================================
echo Learning Platform - Cleanup Script
echo ==========================================
echo.

REM Check if we're in the right directory
if not exist "app_enhanced.py" (
    echo Error: app_enhanced.py not found
    echo Please run this script from the StreamingService directory
    exit /b 1
)

echo Creating backup directory...
if not exist "old_files_backup" mkdir old_files_backup

echo.
echo Backing up old files...

REM Backup old files if they exist
if exist "app.py" (
    move app.py old_files_backup\
    echo - Backed up app.py
) else (
    echo - app.py not found (already removed?)
)

if exist "database.py" (
    move database.py old_files_backup\
    echo - Backed up database.py
) else (
    echo - database.py not found (already removed?)
)

if exist "add_courses.py" (
    move add_courses.py old_files_backup\
    echo - Backed up add_courses.py
) else (
    echo - add_courses.py not found (already removed?)
)

echo.
echo Cleanup complete!
echo.
echo Old files backed up to: old_files_backup\
echo.
echo Active files:
echo   - app_enhanced.py
echo   - database_enhanced.py
echo   - folder_scanner.py
echo   - config.py
echo.
echo To restore old files if needed:
echo   move old_files_backup\* .
echo.
echo To permanently delete backup:
echo   rmdir /s /q old_files_backup
echo.
pause
