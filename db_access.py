import sys
import logging
import sqlite3
import datetime
from typing import Optional, Tuple, List

from sm2 import EASE_INIT, SM2


def db_con() -> sqlite3.Connection:
    conn  = sqlite3.connect('lc_tracker.db')
    return conn

def init_db(con : Optional[sqlite3.Connection] = None) -> sqlite3.Connection:
    con = db_con() if not con else con
    cur = con.cursor()

    # Enable foreign keys (in sqlite you need to enable foreign keys for some reason)
    logging.debug("Enabling foreign key constraint")
    cur.execute("""
        PRAGMA foreign_keys = ON;  
    """)
    
    # Create problem DB
    logging.debug("Creating problems table")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS problems(
            number INTEGER PRIMARY KEY,
            title  TEXT NOT NULL,
            difficulty INTEGER NOT NULL,
            url    TEXT NOT NULL,
            last_review_at INTEGER,
            next_review_at INTEGER NOT NULL,
            ease REAL NOT NULL DEFAULT 2.5,
            interval_days REAL NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0
        );
    """)

    logging.debug("Creating idx_problems_next index")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_problems_next ON problems(next_review_at);")
    
    logging.debug("Creating entries table")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entries(
            id INTEGER PRIMARY KEY,
            lc_num INTEGER NOT NULL,
            confidence INTEGER NOT NULL,
            ts INTEGER NOT NULL,
            time_taken INTEGER NOT NULL,
            FOREIGN KEY (lc_num ) REFERENCES problems(number)
        );
    """)

    con.commit()

    return con

def insert_problem(number : int,
                title : str,
                difficulty : int,
                url : str,
                con : Optional[sqlite3.Connection]=None,
                ) -> None:    
    con = db_con() if not con else con
    cur = con.cursor()

    now_unix_ts = int(datetime.datetime.now().timestamp())    
    cur.execute("""
        INSERT INTO problems (number, title, difficulty, url, last_review_at, next_review_at)        
        VALUES (?, ?, ?, ?, NULL, ?)
        ON CONFLICT(number) DO UPDATE SET
            title = excluded.title,
            difficulty = excluded.difficulty,
            url = excluded.url
        """, 
        (number, title, difficulty, url, now_unix_ts)
    )

    logging.info(f"LC {number}. has been added / updated")

    con.commit()

def problem_exists(con : sqlite3.Connection, number : int) -> bool:
    cur = con.cursor()
    cur.execute("SELECT 1 FROM problems WHERE number = ? LIMIT 1", (number,))
    return cur.fetchone() is not None

def del_problem(con : Optional[sqlite3.Connection], number : int) -> None:
    con = db_con if not con else con
    cur = con.cursor()

    if not problem_exists(con, number):
        logging.info("LC {number} not found within database.")
        return 

    # Delete the problem  
    cur.execute("""
        DELETE FROM problems
        WHERE number = ?;
    """, number) 
    
    con.commit()

    logging.info("LC {number}. removed from problem database.")
 
def add_entry(lc_num : int,
              confidence : int,
              time_taken : int,
              con : Optional[sqlite3.Connection] = None) -> None:
    con = db_con() if not con else con
    cur = con.cursor()

    now_unix_ts = int(datetime.datetime.now().timestamp())    

    if not problem_exists(con, lc_num):
        logging.error(f"Problem {lc_num} not found. Entry not added.")
        sys.exit(1)

    # Insert the entry
    cur.execute(
        """
        INSERT INTO entries (lc_num, confidence, ts, time_taken) 
        VALUES (?, ?, ?, ?)
        """,
        (lc_num, confidence, now_unix_ts, time_taken)
    )

    # Update the state of the problem
    cur.execute("""
        SELECT ease, interval_days, streak
        FROM problems
        WHERE number == ?
        LIMIT 1
    """, (lc_num,))

    EF, I, n = cur.fetchone()
    n, EF, I = SM2(confidence, n, EF, I)
    cur.execute("""
       UPDATE problems
       SET ease = ?,
           interval_days = ?,
           streak = ?
        WHERE number = ?
    """, EF, I, n, lc_num)

    entry_id = cur.lastrowid
    con.commit()

    logging.info(
        f"New entry added (ID {entry_id}):\n"
        f"  LC Number   : {lc_num}\n"
        f"  Confidence  : {confidence}\n"
        f"  Time Taken  : {time_taken}s\n"
        f"  Timestamp   : {now_unix_ts}"
    )
    
def basic_del_entry(entry_id: int,
                    con: Optional[sqlite3.Connection] = None) -> None:
    con = db_con() if not con else con
    cur = con.cursor()

    cur.execute("SELECT 1 FROM entries WHERE id = ? LIMIT 1", (entry_id,))
    if cur.fetchone() is None:
        logging.error(f"Entry {entry_id} not found. Nothing deleted.")
        sys.exit(1)

    cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    con.commit()

    logging.info(f"Entry {entry_id} removed from database.")


# TODO: Implement recalc problem state that uses the history of entries in 
# to calculate what the Leitner system variables should be.

def add_entry(lc_num: int,
              confidence: int,
              time_taken: int,
              solved: bool,
              con: Optional[sqlite3.Connection] = None) -> None:
    con = db_con() if not con else con
    cur = con.cursor()

    # validate inputs
    if not (0 <= confidence <= 5):
        logging.error(f"Invalid confidence {confidence}. Must be 0..5.")
        sys.exit(1)
    if time_taken < 0:
        logging.error(f"Invalid time_taken {time_taken}. Must be >= 0.")
        sys.exit(1)

    now_unix_ts = int(datetime.datetime.now().timestamp())

    if not problem_exists(con, lc_num):
        logging.error(f"Problem {lc_num} not found. Entry not added.")
        sys.exit(1)

    # insert entry
    cur.execute(
        """
        INSERT INTO entries (lc_num, confidence, ts, time_taken)
        VALUES (?, ?, ?, ?)
        """,
        (lc_num, confidence, now_unix_ts, time_taken)
    )
    entry_id = cur.lastrowid

    # fetch current scheduling state
    cur.execute(
        "SELECT ease, interval_days, streak FROM problems WHERE number = ? LIMIT 1",
        (lc_num,)
    )
    row = cur.fetchone()
    if row is None:
        logging.error(f"Inconsistent DB: problem {lc_num} disappeared.")
        sys.exit(1)
    EF, I, n = row

    # apply SM-2, compute next review time
    n, EF, I = SM2(confidence, n, EF, I)
    next_review_at = now_unix_ts + int(round(I * 86400))

    # update problem state
    cur.execute(
        """
        UPDATE problems
        SET last_review_at = ?,
            next_review_at = ?,
            ease = ?,
            interval_days = ?,
            streak = ?
        WHERE number = ?
        """,
        (now_unix_ts, next_review_at, float(EF), float(I), int(n), lc_num)
    )

    con.commit()

    logging.info(
        f"New entry added (ID {entry_id}):\n"
        f"  LC Number   : {lc_num}\n"
        f"  Confidence  : {confidence}\n"
        f"  Time Taken  : {time_taken}s\n"
        f"  Timestamp   : {now_unix_ts}\n"
        f"  Next Review : {next_review_at}\n"
        f"  Ease        : {EF:.4f}\n"
        f"  Interval    : {I:.3f} days\n"
        f"  Streak      : {n}"
    )


def get_due_problems(con: Optional[sqlite3.Connection] = None,
                     difficulty: Optional[int] = None) -> List[Tuple[int, str, str, str]]:
    """
    Return a list of problems that are due for review.
    If 'difficulty' is provided, only return problems of that difficulty.
    """
    con = db_con() if not con else con
    cur = con.cursor()

    now_unix_ts = int(datetime.datetime.now().timestamp())

    cur.execute(
        """
        SELECT number, title, difficulty
        FROM problems
        WHERE next_review_at <= :now_time
          AND (:diff IS NULL OR difficulty = :diff)
        ORDER BY next_review_at ASC
        """,
        {"diff": difficulty, "now_time": now_unix_ts}
    )

    results = cur.fetchall()

    logging.info(
        f"Retrieved {len(results)} due problems"
        + (f" (difficulty='{difficulty}')" if difficulty else "")
    )
    return results

def get_all_problems(con: Optional[sqlite3.Connection] = None) -> List[Tuple[int, str, int, str]]:
    con = db_con() if not con else con
    cur = con.cursor()
    
    cur.execute("""
        SELECT number, title, difficulty
        FROM problems 
    """)

    results = cur.fetchall()

    return results

