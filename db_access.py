import sys
import logging
import sqlite3
import datetime

from typing import Optional

def db_con() -> sqlite3.Connection:
    conn  = sqlite3.connect('lc-track-db')
    return conn

def init_db(con : Optional[sqlite3.Connection] = None) -> None:
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
            topic TEXT NOT NULL,
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
            solved INTEGER NOT NULL,
            FOREIGN KEY (lc_num ) REFERENCES problems(number)
        );
    """)

    con.commit()

def add_problem(number : int,
                title : str,
                topic : str,
                url : str,
                con : Optional[sqlite3.Connection]=None,
                ) -> None:    
    con = db_con() if not con else con
    cur = con.cursor()
    
    now_unix_ts = int(datetime.datetime.now().timestamp())    
    cur.execute("""
        INSERT INTO problems (number, title, topic, url, last_review_at, next_review_at)        
        VALUES (?, ?, ?, ?, NULL, ?)
        ON CONFLICT(number) DO UPDATE SET
            title = excluded.title
            topic = excluded.topic
            url = excluded.url
        """, 
        (number, title, topic, url, now_unix_ts)
    )

    # TODO: Log that probelm has been added / updated
    logging.info("LC {number}. has been added / updated")

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
              solved : bool,
              con : Optional[sqlite3.Connection] = None) -> None:
    con = db_con() if not con else con
    cur = con.cursor()

    now_unix_ts = int(datetime.datetime.now().timestamp())    

    if not problem_exists(con, lc_num):
        logging.error("Problem {lc_num} not found. Entry not added.")
        sys.exit(1)

    cur.execute(
        """
        INSERT INTO entries (lc_num, confidence, ts, time_taken, solved) 
        VALUES (?, ?, ?, ?, ?)
        """,
        (lc_num, confidence, now_unix_ts, time_taken, 1 if solved else 0)
    )
    entry_id = cur.lastrowid
    con.commit()

    logging.info(
        f"New entry added (ID {entry_id}):\n"
        f"  LC Number   : {lc_num}\n"
        f"  Confidence  : {confidence}\n"
        f"  Time Taken  : {time_taken}s\n"
        f"  Solved      : {solved}\n"
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