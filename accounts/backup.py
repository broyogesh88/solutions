# accounts/backup.py
import sqlite3
import gzip
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def perform_backup(base_dir: Path, outdir: Optional[Path] = None, retention: int = 168) -> Optional[Path]:
    """
    Create a consistent sqlite3 backup and store gzipped copy in backups folder.

    - base_dir: Path to project BASE_DIR (settings.BASE_DIR)
    - outdir: optional output directory; default: base_dir / "db_backups"
    - retention: number of backups to keep (default: 168)
    Returns path to created gzipped backup or None on failure.
    """
    if outdir is None:
        outdir = base_dir / "db_backups"

    try:
        outdir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.exception("Could not create backup directory %s: %s", outdir, e)
        return None

    db_path = base_dir / "db.sqlite3"
    if not db_path.exists():
        logger.error("Source DB not found: %s", db_path)
        return None

    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    tmp_dest = outdir / f"db_backup_{ts}.sqlite3"
    gz_dest = outdir / f"db_backup_{ts}.sqlite3.gz"

    try:
        # Use sqlite backup API for an atomic, consistent copy
        src_conn = sqlite3.connect(str(db_path), check_same_thread=False)
        dest_conn = sqlite3.connect(str(tmp_dest))
        with dest_conn:
            src_conn.backup(dest_conn, pages=0, progress=None)
        dest_conn.close()
        src_conn.close()

        # Gzip the resulting sqlite file
        with open(tmp_dest, "rb") as f_in, gzip.open(gz_dest, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # Remove the uncompressed temporary file
        try:
            tmp_dest.unlink()
        except Exception:
            # missing_ok not available on older Pythons; ignore errors
            pass

        logger.info("Backup created: %s", gz_dest)

        # Rotation: keep only the newest `retention` backups
        backups = sorted(outdir.glob("db_backup_*.sqlite3.gz"), reverse=True)
        if len(backups) > retention:
            old = backups[retention:]
            for p in old:
                try:
                    p.unlink()
                    logger.info("Removed old backup: %s", p)
                except Exception:
                    logger.exception("Failed to remove old backup %s", p)

        return gz_dest

    except Exception as exc:
        logger.exception("Error creating backup: %s", exc)
        # Cleanup temp file if present
        try:
            if tmp_dest.exists():
                tmp_dest.unlink()
        except Exception:
            pass
        return None