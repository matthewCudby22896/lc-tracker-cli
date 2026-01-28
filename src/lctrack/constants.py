from platformdirs import PlatformDirs
from pathlib import Path

dirs = PlatformDirs('lc-track','lc-track')

def get_data_dir() -> Path:
    data_dir = Path(dirs.user_data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_backup_repo_dir() -> Path:
    data_dir = get_data_dir()
    backup_repo = data_dir / "backup"
    backup_repo.mkdir(parents=True, exist_ok=True)
    return backup_repo

DATA_DIR = get_data_dir()
DB_FILE = DATA_DIR / "database.db" # Where the current state of lc-track is stored

# A local copy of the event log, to which new events are appended to
LOCAL_EVENT_HISTORY = DATA_DIR / "event_history_local.jsonl" 

# The directory to which the backup / sync github repo is cloned in to
BACKUP_REPO_DIR = get_backup_repo_dir()
BACKUP_EVENT_HISTORY = BACKUP_REPO_DIR / "event_history_backup.jsonl"

TMP_EVENT_HISTORY = DATA_DIR / "tmp" / "tmp_event_history"


