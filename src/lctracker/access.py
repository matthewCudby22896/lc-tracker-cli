import sqlite3
import datetime
from pathlib import Path
from typing import Tuple, List, Any, Optional

# Resolve data directory
DATA_DIR = Path("~/.local/share/lc-track").expanduser()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Full path to database
DB_FILE = DATA_DIR / "database.db"

# Open SQLite connection
CON = sqlite3.connect(DB_FILE)

def insert_problem(number : int,
                   title : str,
                   difficulty : int,
                   url : str) -> None:    
    """Inserts / updates lc problem info.

    If the problem already exists, only the title, difficulty, and url are updated."""
    cur = CON.cursor()
    now_unix_ts = int(datetime.datetime.now().timestamp())    
    CON.execute("""
        INSERT INTO problems (number, title, difficulty, url, last_review_at, next_review_at)        
        VALUES (?, ?, ?, ?, NULL, ?)
        ON CONFLICT(number) DO UPDATE SET
            title = excluded.title,
            difficulty = excluded.difficulty,
            url = excluded.url
        """, 
        (number, title, difficulty, url, now_unix_ts)
    )
    CON.commit()

def del_problem(number : int) -> None:
    cur = CON.cursor()

    cur.execute("""
        DELETE FROM problems
        WHERE number = ?;
    """, (number,))
    
    CON.commit()

def problem_exists(number : int) -> bool:
    cur = CON.cursor()
    cur.execute("SELECT 1 FROM problems WHERE number = ? LIMIT 1", (number,))
    return cur.fetchone() is not None

def entry_exists(id : int) -> bool:
    cur = CON.cursor()
    cur.execute("SELECT 1 FROM records WHERE id = ? LIMIT 1", (number,))
    return cur.fetchone() is not None
 
def insert_record(number : int,
                  confidence : int,
                  time_taken : int,
                  ts : int) -> None:
    cur = CON.cursor()

    cur.execute(
        """
        INSERT INTO records (problem_num, confidence, time_taken, ts) 
        VALUES  (?, ?, ?, ?)
        """
    , (number, confidence, time_taken, ts))

    record_id = cur.lastrowid

    CON.commit()

    return record_id

def get_problem_state(number : int) -> Tuple[int, float, int]:
    """Get SM2 problem state.
    
    n : streak (number of times the question was completed succesfully)
    EF : easiness factor
    I : interval 
    """
    cur = CON.cursor()
    
    cur.execute("""
        SELECT n, EF, I  FROM problems
        WHERE number = ?
        LIMIT 1
    """, (number,))
    
    row = cur.fetchone()
    if row is None:
        raise Exception(f"No problem exists with number={number}")
    
    n, EF, I = row

    return n, EF, I

def update_problem_state(number : int, n : int, EF : float, I : int, last_review_at : int, next_review_at : int) -> None:
    cur = CON.cursor()

    cur.execute("""
        UPDATE problems
        SET n = ?,
            EF = ?,
            I = ?,
            last_review_at = ?,
            next_review_at = ?
        WHERE number = ?
    """, (n, EF, I, int(last_review_at), int(next_review_at), number))

    CON.commit()

def del_record(id : int) -> None:
    """Delete record by id."""
    cur = CON.cursor()
    
    cur.execute("DELETE FROM records WHERE id = ?", (id,))

    CON.commit()

def get_record(id: int) -> Optional[Tuple[int, int, int, int]]:
    cur = CON.cursor()
    
    cur.execute("""
        SELECT id, problem_num, confidence, ts  
        FROM records
        WHERE id = ?
    """, (id,))
    
    row : Optional[Tuple[int, int, int, int]] = cur.fetchone()
    
    return row

def get_all_records_by_problem(number : int) -> List[Tuple[int, int, int]]:
    cur = CON.cursor()
    
    cur.execute("""
        SELECT id, confidence, ts  
        FROM records
        WHERE problem_num = ?
    """, (number,))
    
    return cur.fetchall()

def init_problem_table() -> None:
    cur = CON.cursor()
    stmt = """
    CREATE TABLE IF NOT EXISTS problems (
        number INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        difficulty INTEGER NOT NULL,
        url TEXT NOT NULL,
        last_review_at INTEGER,
        next_review_at INTEGER NOT NULL,
        EF REAL NOT NULL DEFAULT 2.5,
        I REAL NOT NULL DEFAULT 0,
        n INTEGER NOT NULL DEFAULT 0
    );
    """
    cur.execute(stmt)
    CON.commit()

def init_record_table() -> None:
    cur = CON.cursor()

    stmt = """
    CREATE TABLE IF NOT EXISTS records(
        id INTEGER PRIMARY KEY,
        problem_num INTEGER NOT NULL,
        confidence INTEGER NOT NULL,
        ts INTEGER NOT NULL,
        time_taken INTEGER NOT NULL,
        FOREIGN KEY (problem_num) REFERENCES problems(number)
    );
    """
    cur.execute(stmt)
    CON.commit()

def init_database() -> None:
    cur = CON.cursor()
    # Enable foregin key constraint
    # cur.execute("PRAGMA foreign_keys = ON;")
    
    # Init tables (order matters)
    init_problem_table()
    init_record_table()

init_database()



    
    

    

