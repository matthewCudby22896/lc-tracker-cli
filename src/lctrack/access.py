import os
import json
import uuid
import datetime
import sqlite3
import logging
import git    
from pathlib import Path
from typing import Dict, Tuple, List, Any, Optional

from .sm2 import SM2
from .ds import Problem
from .constants import DB_FILE, LOCAL_EVENT_HISTORY, BACKUP_EVENT_HISTORY, TMP_EVENT_HISTORY

def get_for_review_problems() -> List[Problem]:
    now = int(datetime.datetime.now().timestamp())

    con = get_db_connection()
    try:
        cur = con.cursor()

        cur.execute("""
            SELECT * FROM problems
            WHERE next_review_at <= ? 
            AND active = 1
        """, (now, ))
        
        for_review = [Problem.from_row(x) for x in  cur.fetchall()]

        return for_review

    except Exception as e:
        logging.error(f"Error occured whilst attempting to fetch all 'for review' problems : {e}")
        
    finally:
        con.close()

def get_active() -> List[Problem]:
    con = get_db_connection()
    try:
        cur = con.cursor()

        cur.execute("SELECT * FROM problems WHERE active = 1")

        active = [Problem.from_row(x) for x in cur.fetchall()]

        return active
    except Exception as e:
        logging.error(f"Error occured whilst attempting to fetch all 'active' problems : {e}")
    finally:
        con.close()

def update_SM2_state(id : int, n : int, EF : float, I : int, last_review_at : int, next_review_at : int) -> None:
    con = get_db_connection()

    try:
        with con:
            cur = con.cursor()

            cur.execute("""
                UPDATE problems
                SET n = ?,
                    ef = ?,
                    i = ?,
                    last_review_at = ?,
                    next_review_at = ?
                WHERE id = ?
            """, (n, EF, I, int(last_review_at), int(next_review_at), id))
    finally:
        con.close()


def append_event(event: Dict[str, Any]) -> None:
    with open(LOCAL_EVENT_HISTORY, "a", encoding="utf-8") as f:
        json_event = json.dumps(event)
        f.write(json_event + '\n')

def create_add_entry_event(entry_uuid : str, problem_id: int, confidence: int, ts: int) -> Dict[str, Any]:
    """Returns a dictionary representing an ADD_ENTRY event with a unique ID."""
    return {
        "id": entry_uuid, # Uniquely identifies the event
        "event": "ADD_ENTRY",
        "problem_id": problem_id,
        "confidence": confidence,
        "ts": ts # For ordered replay
    }

def create_rm_entry_event(entry_uuid : int, ts : int) -> Dict[str, Any]:
    return {
        "id" : str(uuid.uuid4()), # Uniquely identify the event
        "entry_uuid" : entry_uuid, # The uuid of the entry that was removed
        "ts" : ts # For ordered replay
    }

def insert_entry(problem_id: int, confidence: int, ts: int) -> int:
    entry_uuid = str(uuid.uuid4())

    con = get_db_connection()

    try:
        with con:
            cur = con.cursor()

            cur.execute(
                """
                INSERT INTO entries (id, problem_id, confidence, ts) 
                VALUES (?, ?, ?, ?)
                """,
                (entry_uuid, problem_id, confidence, ts)
            )

            # If the above succeeds, append a ADD_ENTRY
            append_event(
                create_add_entry_event(entry_uuid, problem_id, confidence, ts)
            )
            
            return entry_uuid
    finally:
        con.close()

def rm_entry(entry_uuid : str) -> int:
    """ Removes a specific entry from the local database, then recalculates
    the SM2 state for the corresponding problem using the remaining entries.
    
    Returns the problem_id of the problem corresponding to the specified event.
    """
    rec = get_entry(entry_uuid)
    if rec is None:
        raise RuntimeError(f"No entry exists with uuid: {entry_uuid}")

    _, problem_id, *_ = rec
    con = get_db_connection()
    try:
        with con:
            # Delete the entry
            cur = con.cursor()
            cur.execute("DELETE FROM entries WHERE id = ?", (entry_uuid,))

            # Get all of the entries for the problem_id
            cur.execute("SELECT id, confidence, ts FROM entries WHERE problem_id = ?", (problem_id,))
            entries = cur.fetchall()

            n, EF, I = 0, 2.5, 0.0
            if not entries:     
                last_review_at = 0
                next_review_at = 0
            else:
                entries.sort(key=lambda x: x[2])  # ts asc
                last_ts = 0
                for _, conf, ts in entries:
                    n, EF, I = SM2(conf, n, EF, I)
                    last_ts = ts
                last_review_at = last_ts
                next_review_at = last_ts + int(round(I * 86400))
            
            cur.execute("""
                UPDATE problems
                SET n = ?,
                    ef = ?,
                    i = ?,
                    last_review_at = ?,
                    next_review_at = ?
                WHERE id = ?
            """, (n, EF, I, int(last_review_at), int(next_review_at), problem_id))

            # If the above succeeds, append a RM_ENTRY event
            now_unix_ts = int(datetime.datetime.now().timestamp())

            append_event(
                create_rm_entry_event(entry_uuid, now_unix_ts)
            )

            return problem_id
    finally:
        con.close()

def get_entry(entry_uuid : str) -> Optional[Tuple[int, int, int, int]]:
    con = get_db_connection()
    
    try:
        with con:
            cur = con.cursor()

            cur.execute("""
                SELECT id, problem_id, confidence, ts  
                FROM entries
                WHERE id = ?
            """, (entry_uuid,))

            row : Optional[Tuple[int, int, int, int]] = cur.fetchone()

        return row

    finally:
        con.close()

def get_all_entries_by_problem_id(problem_id : int) -> List[Tuple[int, int, int]]:
    con = get_db_connection()
    
    try:
        cur = con.cursor()
        
        cur.execute("""
            SELECT id, confidence, ts  
            FROM entries
            WHERE problem_id = ?
        """, (problem_id,))

        return cur.fetchall()

    finally:
        con.close()

def get_problem(id: int) -> Optional[Problem]:
    con = get_db_connection()
    try:
        cur = con.cursor()
        cur.execute("SELECT * FROM problems WHERE id = ?", (id,))
        row = cur.fetchone()
        
        if row is None:
            return None
            
        return Problem.from_row(row)
        
    finally:
        con.close()

def get_problem_topics(problem_id : int) -> List[str]:
    con = get_db_connection()
    try:
        cur = con.cursor()
        cur.execute("""
            SELECT t.topic_title
            FROM problem_topic pt
            JOIN topics t ON pt.topic_slug = t.topic_slug
            WHERE pt.problem_id = ?
        """, (problem_id,))

        return [x[0] for  x in cur.fetchall()]
    except Exception as e:
        logging.error(f"Error fetching topics for problem {problem_id}: {e}")
    finally:
        con.close()
    
def set_active(id: int, active: bool) -> None:  
    con = get_db_connection()
    try:
        with con:
            cur = con.cursor()
            cur.execute(
                "UPDATE problems SET active = ? WHERE id = ?", 
                (active, id)
            )
    finally:
        con.close()

def get_db_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON;")
    con.isolation_level = ""
    return con

def db_exists() -> bool:
    return os.path.exists(DB_FILE)

def init_db() -> None:
    con = get_db_connection()    
    cur = con.cursor()

    # 2. Define the schema
    stmt = """
    CREATE TABLE IF NOT EXISTS problems (
        id INTEGER PRIMARY KEY,
        slug TEXT NOT NULL UNIQUE, 
        title TEXT,
        difficulty INTEGER CHECK (difficulty BETWEEN 0 AND 2),
        last_review_at INTEGER,
        next_review_at INTEGER DEFAULT 0,
        EF REAL DEFAULT 2.5,
        I INTEGER DEFAULT 0,
        n INTEGER DEFAULT 0,
        active BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS topics (
        topic_slug TEXT PRIMARY KEY,
        topic_title TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS problem_topic (
        problem_id INTEGER NOT NULL,
        topic_slug TEXT NOT NULL,
        PRIMARY KEY (problem_id, topic_slug),
        FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
        FOREIGN KEY (topic_slug) REFERENCES topics(topic_slug) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS entries(
        id TEXT PRIMARY KEY, 
        problem_id INTEGER NOT NULL,
        confidence INTEGER NOT NULL CHECK (confidence BETWEEN 0 and 5),
        ts INTEGER NOT NULL,
        FOREIGN KEY (problem_id) references problems(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY, 
        value TEXT
    );
    """

    cur.executescript(stmt)
    con.commit()

def get_state(key : str) -> Optional[str]:
    con = get_db_connection()
    try:
        cur = con.execute("SELECT value FROM app_state WHERE key = ?", (key, ))
        row = cur.fetchone()
    
        return row[0] if row else None

    finally:
        con.close()

def set_state(con, key: str, value: str) -> None:
    con.execute("REPLACE INTO app_state (key, value) VALUES (?, ?)", (key, value))

def insert_problems(con : sqlite3.Connection, problems : List[Tuple[int, str]]):
    """ Batch inserts the lc problems (id, slug) into the problems table.
    """
    cur = con.cursor()
    stmt = """
    INSERT OR IGNORE INTO problems (id, slug)
    VALUES (?, ?)
    """
    cur.executemany(stmt, problems)

def set_state(con, key: str, value: str) -> None:
    con.execute("REPLACE INTO app_state (key, value) VALUES (?, ?)", (key, value))

def check_repo(path : Path) -> bool:
    try:
        git.Repo(path)
        # If this succeeds, this is a valid repo
        return True
    except git.InvalidGitRepositoryError as exc:
        # The folder exists, but it's not a git repo
        return False
    except git.NoSuchPathError as exc:
        # The folder doesn't even exist
        return False

def merge_event_histories() -> None:
    # Load both event histories into memory
    events_local : List[dict] = load_event_history(LOCAL_EVENT_HISTORY)
    events_backup : List[dict] = load_event_history(BACKUP_EVENT_HISTORY)

    # Merge the two into a single list
    combined_events = list({event['id']: event for event in events_backup + events_local}.values())
    combined_events.sort(key=lambda x : x['ts'])

    return combined_events

def load_event_history(path : Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1): 
            line = line.strip() 
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise Exception(f"Failed to parse ln {ln} of {f}: {exc}") 

    return events            

def update_event_history_backup(event_history : List[str, Any]) -> None:
    with open(TMP_EVENT_HISTORY, 'w', encoding="utf-8") as f:
        for event in event_history: 
            line = json.dumps(event)
            f.write(line + '\n')

    # Atomic swap: Replace the backup file with the tmp file
    TMP_EVENT_HISTORY.replace(BACKUP_EVENT_HISTORY) 


