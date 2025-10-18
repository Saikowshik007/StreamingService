"""
Background worker to periodically sync progress from Redis to Firebase
"""
import time
import threading
import logging
from cache_service import get_cache
import firebase_service as db

logger = logging.getLogger(__name__)

class ProgressSyncWorker:
    """Background worker that syncs progress from Redis to Firebase periodically"""

    def __init__(self, sync_interval=30):
        """
        Initialize the progress sync worker

        Args:
            sync_interval: Interval in seconds between sync operations (default: 30)
        """
        self.sync_interval = sync_interval
        self.running = False
        self.thread = None
        self.cache = get_cache()

    def start(self):
        """Start the background sync worker"""
        if self.running:
            logger.warning("Progress sync worker is already running")
            return

        if not self.cache.enabled:
            logger.warning("Redis cache not available, progress sync worker disabled")
            return

        self.running = True
        self.thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.thread.start()
        logger.info(f"Progress sync worker started (interval: {self.sync_interval}s)")

    def stop(self):
        """Stop the background sync worker"""
        if not self.running:
            return

        logger.info("Stopping progress sync worker...")
        self.running = False

        # Perform one final sync before stopping
        self._sync_dirty_progress()

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("Progress sync worker stopped")

    def _sync_loop(self):
        """Main loop for syncing progress"""
        while self.running:
            try:
                self._sync_dirty_progress()
            except Exception as e:
                logger.error(f"Error in progress sync loop: {e}", exc_info=True)

            # Sleep in small intervals to allow quick shutdown
            for _ in range(self.sync_interval):
                if not self.running:
                    break
                time.sleep(1)

    def _sync_dirty_progress(self):
        """Sync all dirty progress entries from Redis to Firebase"""
        if not self.cache.enabled:
            return

        try:
            # Find all dirty progress entries
            dirty_keys = self.cache.redis_client.keys("progress:dirty:*")

            if not dirty_keys:
                logger.debug("No dirty progress entries to sync")
                return

            synced_count = 0
            failed_count = 0

            for dirty_key in dirty_keys:
                try:
                    # Extract user_id and file_id from the key
                    # Format: progress:dirty:user_id:file_id
                    parts = dirty_key.decode('utf-8').split(':', 3)
                    if len(parts) != 4:
                        logger.warning(f"Invalid dirty key format: {dirty_key}")
                        continue

                    user_id = parts[2]
                    file_id = parts[3]

                    # Get the progress data from Redis
                    progress_key = f"progress:{user_id}:{file_id}"
                    progress_data = self.cache.get(progress_key)

                    if not progress_data:
                        logger.warning(f"Progress data not found for {progress_key}")
                        # Clean up the dirty marker
                        self.cache.delete(dirty_key.decode('utf-8'))
                        continue

                    # Sync to Firebase
                    db.update_user_progress(
                        user_id=progress_data['user_id'],
                        file_id=progress_data['file_id'],
                        lesson_id=progress_data['lesson_id'],
                        course_id=progress_data['course_id'],
                        progress_seconds=progress_data['progress_seconds'],
                        progress_percentage=progress_data['progress_percentage'],
                        completed=progress_data['completed']
                    )

                    # Remove the dirty marker after successful sync
                    self.cache.delete(dirty_key.decode('utf-8'))

                    synced_count += 1
                    logger.debug(f"Synced progress for user {user_id}, file {file_id}")

                except Exception as e:
                    logger.error(f"Failed to sync progress entry {dirty_key}: {e}", exc_info=True)
                    failed_count += 1

            if synced_count > 0 or failed_count > 0:
                logger.info(f"Progress sync completed: {synced_count} synced, {failed_count} failed")

        except Exception as e:
            logger.error(f"Error in sync_dirty_progress: {e}", exc_info=True)


# Global worker instance
_worker = None

def start_progress_sync_worker(sync_interval=30):
    """Start the global progress sync worker"""
    global _worker
    if _worker is None:
        _worker = ProgressSyncWorker(sync_interval=sync_interval)
    _worker.start()
    return _worker

def stop_progress_sync_worker():
    """Stop the global progress sync worker"""
    global _worker
    if _worker:
        _worker.stop()

def get_progress_sync_worker():
    """Get the global progress sync worker instance"""
    return _worker
