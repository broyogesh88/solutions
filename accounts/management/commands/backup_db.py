# accounts/backup.py
import sqlite3
import gzip
import shutil
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def perform_backup(base_dir: Path, outdir: Path | None = None, retention: int = 168) -> Path | None:
    """
    Create a safe sqlite backup and gzip it.

    - base_dir: Path to project BASE_DIR (settings.BASE_DIR)
    - outdir: optional output directory; default: base_dir / "db_backups"
    - retention: number of backups to keep (default 168 = 7 days hourly)
    Returns path to created gzipped backup or None on failure.
    """
    if outdir is None:
        outdir = base_dir / "db_backups"

    outdir.mkdir(parents=True, exist_ok=True)

    db_path = base_dir / "db.sqlite3"
    if not db_path.exists():
        logger.error("Source DB not found: %s", db_path)
        return None

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    tmp_dest = outdir / f"db_backup_{ts}.sqlite3"
    gz_dest = outdir / f"db_backup_{ts}.sqlite3.gz"

    try:
        # Use sqlite3 backup API for an atomic, consistent copy
        src_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        dest_conn = sqlite3.connect(str(tmp_dest))
        with dest_conn:
            src_conn.backup(dest_conn, pages=0, progress=None)
        dest_conn.close()
        src_conn.close()

        # Gzip the sqlite file
        with open(tmp_dest, "rb") as f_in, gzip.open(gz_dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # Remove the temporary sqlite
        tmp_dest.unlink(missing_ok=True)

        logger.info("Backup created: %s", gz_dest)

        # Rotation: keep newest `retention` files
        backups = sorted(outdir.glob("db_backup_*.sqlite3.gz"), reverse=True)
        if len(backups) > retention:
            to_remove = backups[retention:]
            for p in to_remove:
                try:
                    p.unlink()
                    logger.info("Removed old backup: %s", p)
                except Exception as exc:
                    logger.exception("Failed to remove old backup %s: %s", p, exc)

        return gz_dest

    except Exception as exc:
        logger.exception("Error creating backup: %s", exc)
        # Clean up temporary file on error
        try:
            tmp_dest.unlink(missing_ok=True)
        except Exception:
            pass
        return None