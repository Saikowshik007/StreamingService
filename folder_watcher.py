"""
Automatic folder watcher that monitors the media directory for changes
and triggers scans when new courses or files are added.
"""

import time
import logging
from pathlib import Path
from threading import Thread, Lock
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from folder_scanner import scan_and_import
from config import Config

logger = logging.getLogger(__name__)

class CoursesFolderEventHandler(FileSystemEventHandler):
    """Handler for file system events in the courses folder"""

    def __init__(self, scan_callback, debounce_seconds=5):
        super().__init__()
        self.scan_callback = scan_callback
        self.debounce_seconds = debounce_seconds
        self.last_scan_time = 0
        self.scan_lock = Lock()
        self.pending_scan = False

    def should_trigger_scan(self, event):
        """Check if event should trigger a scan"""
        # Ignore temporary files and hidden files
        if event.src_path.startswith('.') or '~' in event.src_path:
            return False

        # Only trigger on directory creation/deletion or video/document files
        if event.is_directory:
            return True

        path = Path(event.src_path)
        ext = path.suffix.lower()

        # Video extensions
        if ext in {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}:
            return True

        # Document extensions
        if ext in {'.pdf', '.doc', '.docx', '.txt', '.ppt', '.pptx', '.xls', '.xlsx'}:
            return True

        return False

    def trigger_scan_debounced(self):
        """Trigger a scan with debouncing to avoid multiple rapid scans"""
        current_time = time.time()

        with self.scan_lock:
            # Check if enough time has passed since last scan
            if current_time - self.last_scan_time < self.debounce_seconds:
                # Mark that a scan is pending
                self.pending_scan = True
                return

            # Perform scan
            self.pending_scan = False
            self.last_scan_time = current_time

        logger.info("File system change detected, triggering automatic scan...")
        self.scan_callback()

    def on_created(self, event):
        """Called when a file or folder is created"""
        if self.should_trigger_scan(event):
            logger.info(f"New item detected: {event.src_path}")
            self.trigger_scan_debounced()

    def on_deleted(self, event):
        """Called when a file or folder is deleted"""
        if self.should_trigger_scan(event):
            logger.info(f"Item deleted: {event.src_path}")
            self.trigger_scan_debounced()

    def on_moved(self, event):
        """Called when a file or folder is moved"""
        if self.should_trigger_scan(event):
            logger.info(f"Item moved: {event.src_path} -> {event.dest_path}")
            self.trigger_scan_debounced()

class FolderWatcher:
    """Watches the media folder for changes and triggers automatic scans"""

    def __init__(self, watch_path=None, auto_scan_on_start=True):
        self.watch_path = watch_path or Config.MEDIA_PATH
        self.auto_scan_on_start = auto_scan_on_start
        self.observer = None
        self.is_running = False

    def scan_callback(self):
        """Callback function to trigger a scan"""
        try:
            scan_and_import(self.watch_path, rescan=True)
            logger.info("Automatic scan completed successfully")
        except Exception as e:
            logger.error(f"Automatic scan failed: {e}")

    def start(self):
        """Start watching the folder"""
        if self.is_running:
            logger.warning("Folder watcher is already running")
            return

        # Verify path exists
        watch_path_obj = Path(self.watch_path)
        if not watch_path_obj.exists():
            logger.warning(f"Watch path does not exist: {self.watch_path}")
            logger.info(f"Creating directory: {self.watch_path}")
            watch_path_obj.mkdir(parents=True, exist_ok=True)

        # Perform initial scan if enabled
        if self.auto_scan_on_start:
            logger.info("Performing initial scan on startup...")
            try:
                scan_and_import(self.watch_path, rescan=False)
                logger.info("Initial scan completed")
            except Exception as e:
                logger.error(f"Initial scan failed: {e}")

        # Set up file system observer
        event_handler = CoursesFolderEventHandler(self.scan_callback)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.watch_path, recursive=True)

        # Start observer in a separate thread
        self.observer.start()
        self.is_running = True

        logger.info(f"Folder watcher started - monitoring: {self.watch_path}")
        logger.info("Automatic scans will trigger when new courses or files are added")

    def stop(self):
        """Stop watching the folder"""
        if not self.is_running or not self.observer:
            return

        logger.info("Stopping folder watcher...")
        self.observer.stop()
        self.observer.join(timeout=5)
        self.is_running = False
        logger.info("Folder watcher stopped")

    def is_active(self):
        """Check if watcher is active"""
        return self.is_running and self.observer and self.observer.is_alive()

# Global watcher instance
_watcher_instance = None

def get_watcher():
    """Get the global watcher instance"""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = FolderWatcher()
    return _watcher_instance

def start_watcher():
    """Start the global folder watcher"""
    watcher = get_watcher()
    if not watcher.is_active():
        watcher.start()
    return watcher

def stop_watcher():
    """Stop the global folder watcher"""
    watcher = get_watcher()
    watcher.stop()
