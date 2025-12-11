# accounts/apps.py
from django.apps import AppConfig
import threading
import time
import atexit
import sys
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    _backup_thread = None
    _stop_event = None

    def ready(self):
        # Import signal handlers so they register
        try:
            import accounts.signals  # noqa: F401
        except Exception:
            logger.exception("Failed to import accounts.signals")

        # Only start scheduler in server processes, not when running manage.py commands like migrations.
        # Common check: start when RUN_MAIN env is set (development runserver child process),
        # or when 'runserver' in sys.argv, or when DEBUG/production servers might be running.
        should_start = False
        try:
            cmd = sys.argv[1] if len(sys.argv) > 1 else ""
        except Exception:
            cmd = ""

        if os.environ.get("RUN_MAIN") == "true" or "runserver" in cmd or ("gunicorn" in sys.argv[0]) or ("uwsgi" in sys.argv[0]):
            should_start = True

        # If you want it always on, set should_start = True (be careful in multi-worker setups)
        if not should_start:
            return

        # Avoid starting multiple times
        if AccountsConfig._backup_thread is not None and AccountsConfig._backup_thread.is_alive():
            return

        from django.conf import settings
        from accounts.backup import perform_backup

        stop_event = threading.Event()
        AccountsConfig._stop_event = stop_event

        def backup_loop():
            base_dir = Path(settings.BASE_DIR)
            outdir = base_dir / "db_backups"
            retention = 168  # keep last 168 backups (7 days hourly)
            interval_seconds = 60 * 60  # 1 hour

            # First run immediately
            try:
                logger.info("Starting in-app DB backup loop, first backup running now.")
                perform_backup(base_dir, outdir=outdir, retention=retention)
            except Exception:
                logger.exception("Initial backup failed.")

            while not stop_event.wait(interval_seconds):
                try:
                    logger.info("Performing scheduled backup.")
                    perform_backup(base_dir, outdir=outdir, retention=retention)
                except Exception:
                    logger.exception("Scheduled backup failed.")

            logger.info("Backup loop stopped.")

        t = threading.Thread(target=backup_loop, name="accounts-db-backup", daemon=True)
        AccountsConfig._backup_thread = t
        t.start()

        # Ensure thread stops at process exit
        def _stop():
            try:
                if AccountsConfig._stop_event:
                    AccountsConfig._stop_event.set()
                if AccountsConfig._backup_thread:
                    AccountsConfig._backup_thread.join(timeout=5)
            except Exception:
                logger.exception("Error shutting down backup thread.")

        atexit.register(_stop)