import datetime
import logging
from typing import List, Tuple

from . import access
from .sm2 import SM2
from .lc_client import fetch_all_problems

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

def recalc_and_set_problem_state(problem_id: int) -> None:
    """Recompute SM-2 state, last/next review from this problem's records."""
    # [(id, confidence, ts)]
    records: List[Tuple[int, int, int]] = access.get_all_entries_by_problem_id(problem_id)

    if not records: # Reset to default state
        now = int(datetime.datetime.now().timestamp())
        n, EF, I = 0, 2.5, 0.0
        last_review_at = 0
        next_review_at = now
        access.update_SM2_state(problem_id, n, EF, I, last_review_at, next_review_at)
        return

    records.sort(key=lambda x: x[2])  # ts asc

    n, EF, I = 0, 2.5, 0.0
    last_ts = 0
    for _, conf, ts in records:
        n, EF, I = SM2(conf, n, EF, I)
        last_ts = ts

    last_review_at = last_ts
    next_review_at = last_ts + int(round(I * 86400))

    access.update_SM2_state(problem_id, n, EF, I, last_review_at, next_review_at)

def initial_sync() -> None:
    problems_raw = fetch_all_problems()
    
    try:
        problems = [
            (x['questionFrontendId'], x['titleSlug'], x['title'], DIFF_TO_INT[x['difficulty']])
            for x in problems_raw
        ]

        topics = {(t['slug'], t['name']) for p in problems_raw for t in p['topicTags']}

        problem_topics = [(p['questionFrontendId'], t['slug']) for p in problems_raw for t in p['topicTags']]

    except Exception as e:
        logging.error(f"Failed to parse problem set fetched from leetcode.com: {e}")
        return

    con = access.get_db_connection()
    try:
        with con:
            cur = con.cursor()
            
            stmt = "INSERT INTO problems (id, slug, title, difficulty) VALUES (?, ?, ?, ?);"
            cur.executemany(stmt, problems)

            stmt = "INSERT INTO topics (topic_slug, topic_title) VALUES (?, ?);"
            cur.executemany(stmt, topics)

            stmt = "INSERT INTO problem_topic (problem_id, topic_slug) VALUES (?, ?);"
            cur.executemany(stmt, problem_topics)
            
            access.set_state(con, "initial_sync", "complete")
        
    except Exception as e:
        logging.error(f"Failed to sync problem set with leetcode.com: {e}")
    finally:
        con.close()