import sqlite3
import os
import datetime
from pathlib import Path
from typing import Dict, Tuple, List, Any, Optional
import logging

from .lc_client import fetch_all_problems

def get_data_dir():
    # Priority: Environment variable -> Default XDF Path -> Home fallback
    xdg_data = os.environ.get("XDG_DATA_HOME")

    if xdg_data:
        data_path = Path(xdg_data) / "lc-track"
    else:
        data_path = Path.home() / ".local" / "share" / "lc-track"
    
    data_path.mkdir(parents=True, exist_ok=True)

    return data_path

DATA_DIR = get_data_dir()
DB_FILE = DATA_DIR / "database.db"

# def insert_problem(number : int,
#                    title : str,
#                    difficulty : int,
#                    url : str) -> None:    
#     """Inserts / updates lc problem info.

#     If the problem already exists, only the title, difficulty, and url are updated."""
#     cur = CON.cursor()
#     now_unix_ts = int(datetime.datetime.now().timestamp())    
#     CON.execute("""
#         INSERT INTO problems (number, title, difficulty, url, last_review_at, next_review_at)        
#         VALUES (?, ?, ?, ?, NULL, ?)
#         ON CONFLICT(number) DO UPDATE SET
#             title = excluded.title,
#             difficulty = excluded.difficulty,
#             url = excluded.url
#         """, 
#         (number, title, difficulty, url, now_unix_ts)
#     )
#     CON.commit()

# def del_problem(number : int) -> None:
#     cur = CON.cursor()

#     cur.execute("""
#         DELETE FROM problems
#         WHERE number = ?;
#     """, (number,))
    
#     CON.commit()

# def problem_exists(number : int) -> bool:
#     cur = CON.cursor()
#     cur.execute("SELECT 1 FROM problems WHERE number = ? LIMIT 1", (number,))
#     return cur.fetchone() is not None

# def entry_exists(id : int) -> bool:
#     cur = CON.cursor()
#     cur.execute("SELECT 1 FROM records WHERE id = ? LIMIT 1", (id,))
#     return cur.fetchone() is not None
 
# def insert_record(number : int,
#                   confidence : int,
#                   ts : int) -> None:
#     cur = CON.cursor()

#     cur.execute(
#         """
#         INSERT INTO records (problem_num, confidence, ts) 
#         VALUES  (?, ?, ?, ?)
#         """
#     , (number, confidence, ts))

#     record_id = cur.lastrowid

#     CON.commit()

#     return record_id

# def get_problem_state(number : int) -> Tuple[int, float, int]:
#     """Get SM2 problem state.
    
#     n : streak (number of times the question was completed succesfully)
#     EF : easiness factor
#     I : interval 
#     """
#     cur = CON.cursor()
    
#     cur.execute("""
#         SELECT n, EF, I  FROM problems
#         WHERE number = ?
#         LIMIT 1
#     """, (number,))
    
#     row = cur.fetchone()
#     if row is None:
#         raise Exception(f"No problem exists with number={number}")
    
#     n, EF, I = row

#     return n, EF, I

# def update_problem_state(number : int, n : int, EF : float, I : int, last_review_at : int, next_review_at : int) -> None:
#     cur = CON.cursor()

#     cur.execute("""
#         UPDATE problems
#         SET n = ?,
#             EF = ?,
#             I = ?,
#             last_review_at = ?,
#             next_review_at = ?
#         WHERE number = ?
#     """, (n, EF, I, int(last_review_at), int(next_review_at), number))

#     CON.commit()

# def del_record(id : int) -> None:
#     """Delete record by id."""
#     cur = CON.cursor()
    
#     cur.execute("DELETE FROM records WHERE id = ?", (id,))

#     CON.commit()

# def get_record(id: int) -> Optional[Tuple[int, int, int, int]]:
#     cur = CON.cursor()
    
#     cur.execute("""
#         SELECT id, problem_num, confidence, ts  
#         FROM records
#         WHERE id = ?
#     """, (id,))
    
#     row : Optional[Tuple[int, int, int, int]] = cur.fetchone()
    
#     return row

# def get_all_records_by_problem(number : int) -> List[Tuple[int, int, int]]:
#     cur = CON.cursor()
    
#     cur.execute("""
#         SELECT id, confidence, ts  
#         FROM records
#         WHERE problem_num = ?
#     """, (number,))
    
#     return cur.fetchall()

def get_title_slug_from_id(id : int) -> Optional[str]:
    con = get_db_connection()
    cur = con.cursor()
    cur.execute("select slug from problems where id = ?", (id, ))
    row : optional[tuple] = cur.fetchone()
    if row:
        return row[0]
    else:
        return none
    
def get_db_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    con.execute("PRAGMA foreign_keys = ON;")
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
        n INTEGER DEFAULT 0
    );


    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS problem_topic (
        problem_id INTEGER NOT NULL,
        topic_id INTEGER NOT NULL,
        PRIMARY KEY (problem_id, topic_id),
        FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
        FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS entries(
        id INTEGER PRIMARY KEY, 
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
    # Just execute the command. Do NOT commit or close here.
    con.execute("REPLACE INTO app_state (key, value) VALUES (?, ?)", (key, value))

# TODO: Move to suitable place
DIFF_TO_INT = {
    "Hard" : 2, 
    "Medium" : 1,
    "Easy" : 0
}

INT_TO_DIFF = {
    2 : "Hard",
    1 : "Medium",
    0 : "Easy"
}

def initial_sync() -> None:
    problems_raw = fetch_all_problems()
    
    try:
        problems = [
            (x['questionFrontendId'], x['titleSlug'], x['title'], DIFF_TO_INT[x['difficulty']])
            for x in problems_raw
        ]
    except Exception as e:
        logging.error(f"Failed to parse problem set fetched from leetcode.com: {e}")
        return

    con = get_db_connection()
    try:
        with con:
            cur = con.cursor()
            
            stmt = "INSERT INTO problems (id, slug, title, difficulty) VALUES (?, ?, ?, ?);"
            cur.executemany(stmt, problems)
            
            set_state(con, "initial_sync", "complete")
        
    except Exception as e:
        logging.error(f"Failed to sync problem set with leetcode.com: {e}")
    finally:
        con.close()

