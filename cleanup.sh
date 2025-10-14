#!/bin/bash
# Cleanup script to remove old files and keep only enhanced versions

set -e

echo "=========================================="
echo "Learning Platform - Cleanup Script"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "app_enhanced.py" ]; then
    echo "❌ Error: app_enhanced.py not found"
    echo "Please run this script from the StreamingService directory"
    exit 1
fi

echo "📁 Creating backup directory..."
mkdir -p old_files_backup

echo ""
echo "📦 Backing up old files..."

# Backup old files if they exist
if [ -f "app.py" ]; then
    mv app.py old_files_backup/
    echo "✓ Backed up app.py"
else
    echo "⊘ app.py not found (already removed?)"
fi

if [ -f "database.py" ]; then
    mv database.py old_files_backup/
    echo "✓ Backed up database.py"
else
    echo "⊘ database.py not found (already removed?)"
fi

if [ -f "add_courses.py" ]; then
    mv add_courses.py old_files_backup/
    echo "✓ Backed up add_courses.py"
else
    echo "⊘ add_courses.py not found (already removed?)"
fi

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Old files backed up to: old_files_backup/"
echo ""
echo "Active files:"
echo "  ✓ app_enhanced.py"
echo "  ✓ database_enhanced.py"
echo "  ✓ folder_scanner.py"
echo "  ✓ config.py"
echo ""
echo "To restore old files if needed:"
echo "  mv old_files_backup/* ."
echo ""
echo "To permanently delete backup:"
echo "  rm -rf old_files_backup/"
echo ""
