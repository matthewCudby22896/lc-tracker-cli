import datetime
import sqlite3
import os
from pathlib import Path
from typing import Dict, Tuple, List, Any, Optional
import logging
from dataclasses import dataclass

from .ds import Problem
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

def insert_entry(problem_id: int, confidence: int, ts: int) -> int:
    con = get_db_connection()
    try:
        with con:
            cur = con.cursor()

            # Here we omit 'id' from the columns so SQLite auto-generates it
            cur.execute(
                """
                INSERT INTO entries (problem_id, confidence, ts) 
                VALUES (?, ?, ?)
                """,
                (problem_id, confidence, ts)
            )

            # Fetch the ID of the record just created
            record_id = cur.lastrowid
            return record_id

    finally:
        con.close()

def del_entry(entry_id : int) -> None:
    """Delete entry by id."""
    con = get_db_connection()
    try:
        with con:
            cur = con.cursor()
            cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    finally:
        con.close()

def get_entry(entry_id: int) -> Optional[Tuple[int, int, int, int]]:
    con = get_db_connection()
    
    try:
        with con:
            cur = con.cursor()

            cur.execute("""
                SELECT id, problem_id, confidence, ts  
                FROM entries
                WHERE id = ?
            """, (entry_id,))

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
    cur = con.cursor()
    
    try:
        cur.execute("SELECT * FROM problems WHERE id = ?", (id,))
        row = cur.fetchone()
        
        if row is None:
            return None
            
        return Problem.from_row(row)
        
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
    con.execute("REPLACE INTO app_state (key, value) VALUES (?, ?)", (key, value))

