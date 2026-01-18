import re
import sys
import logging
import datetime
from enum import Enum
import typer
from click import IntRange
import requests

from . import access
from .sm2 import SM2  # ensure this exists
from .lc_client import fetch_all_problems

from typing import Dict, Tuple, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
app = typer.Typer(add_completion=False)

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

DIFF_TO_INT = {"easy": 0, "medium": 1, "hard": 2}

def slugify_title(title: str) -> str:
    s = re.sub(r"[^a-z0-9\- ]", "", title.lower())
    return re.sub(r"\s+", "-", s.strip())

def fmt(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

@app.command(name="add-problem")
def add_problem(number: int) -> None:

    fetch_problem_by_number(number)
    return

    access.insert_problem(number, title, DIFF_TO_INT[difficulty.value], url)

    logging.info(f"LC {number}. {title} [{difficulty.value}] added/updated ")

def fetch_problem_by_number(number: int):
    url = "https://leetcode.com/graphql"
    
    # We use the exact structure from your search bar observation
    # 'searchKeyword' with the dot (e.g., "1.") is the trick for exact ID match
    payload = {
        "query": """
        query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionFilterInput, $searchKeyword: String, $sortBy: QuestionSortByInput) {
            problemsetQuestionListV2(
                categorySlug: $categorySlug
                limit: $limit
                skip: $skip
                filters: $filters
                searchKeyword: $searchKeyword
                sortBy: $sortBy
            ) {
                questions {
                    questionFrontendId
                    title
                    titleSlug
                    difficulty
                    topicTags {
                        name
                        slug
                    }
                }
            }
        }
        """,
        "variables": {
            "categorySlug": "all-code-essentials",
            "skip": 0,
            "limit": 20,
            "filters": {
                "filterCombineType": "ALL",
                "statusFilter": {"questionStatuses": [], "operator": "IS"},
                "difficultyFilter": {"difficulties": [], "operator": "IS"},
                "languageFilter": {"languageSlugs": [], "operator": "IS"},
                "topicFilter": {"topicSlugs": [], "operator": "IS"},
                "acceptanceFilter": {},
                "frequencyFilter": {},
                "frontendIdFilter": {},
                "lastSubmittedFilter": {},
                "publishedFilter": {},
                "companyFilter": {"companySlugs": [], "operator": "IS"},
                "positionFilter": {"positionSlugs": [], "operator": "IS"},
                "contestPointFilter": {"contestPoints": [], "operator": "IS"},
                "premiumFilter": {"premiumStatus": [], "operator": "IS"}
            },
            "searchKeyword": f"{number}.",
            "sortBy": {"sortField": "CUSTOM", "sortOrder": "ASCENDING"}
        },
        "operationName": "problemsetQuestionList"
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Referer": "https://leetcode.com/problemset/"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        print(data)
        return
        # Extract the list of questions
        results = data.get("data", {}).get("problemsetQuestionListV2", {}).get("questions", [])
        
        # Double-check the exact ID match among results
        problem = next((q for q in results if q["questionFrontendId"] == str(number)), None)
        
        if problem:
            return {
                "title": problem["title"],
                "difficulty": problem["difficulty"].lower(),
                "topics": [t["name"] for t in problem["topicTags"]],
                "slug": problem["titleSlug"]
            }
        return None

    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None

@app.command(name="rm-problem")
def rm_problem(number: int) -> None:
    if not access.problem_exists(number):
        logging.error(f"LC {number} was not found.")
        sys.exit(1)

    access.del_problem(number)

    logging.info(f"LC {number} removed.")

@app.command(name="add-record")
def add_record(
    number: int,
    confidence: int = typer.Option(..., help="Confidence rating (0–5)", click_type=IntRange(0, 5)),
) -> None:
    now_unix_ts = int(datetime.datetime.now().timestamp())

    if not access.problem_exists(number):
        logging.error(f"LC {number} was not found.")
        raise typer.Exit(code=1)

    record_id = access.insert_record(number, confidence, now_unix_ts)

    n, EF, I = access.get_problem_state(number)

    n_new, EF_new, I_new = SM2(confidence, n, EF, I)
    next_review_at = now_unix_ts + int(I_new * 86400)

    access.update_problem_state(number, n_new, EF_new, I_new, now_unix_ts, next_review_at)

    logging.info(
        f"New record added (ID {record_id}):\n"
        f"  LC Number       : {number}\n"
        f"  Confidence      : {confidence}\n"
        f"  Last Review At  : {fmt(now_unix_ts)}\n"
        f"  Next Review At  : {fmt(next_review_at)}\n"
        f"  SM-2 State -> n: {n_new}, EF: {EF_new:.4f}, I: {I_new:.3f} days"
    )

@app.command(name="rm-record")
def rm_record(record_id: int) -> None:
    rec = access.get_record(record_id)
    if rec is None:
        logging.error(f"No record exists with id={record_id}")
        raise typer.Exit(code=1)

    _, problem_num, *_ = rec

    access.del_record(record_id)

    recalc_and_set_problem_state(problem_num)

    logging.info(f"Record {record_id} removed. LC {problem_num} state recalculated.")

def recalc_and_set_problem_state(number: int) -> None:
    """Recompute SM-2 state, last/next review from this problem's records."""
    # [(id, confidence, ts)]
    records: List[Tuple[int, int, int]] = access.get_all_records_by_problem(number)

    if not records:
        now = int(datetime.datetime.now().timestamp())
        n, EF, I = 0, 2.5, 0.0
        last_review_at = None
        next_review_at = now
        access.update_problem_state(number, n, EF, I, last_review_at, next_review_at)
        return

    records.sort(key=lambda x: x[2])  # ts asc

    n, EF, I = 0, 2.5, 0.0
    last_ts = 0
    for _, conf, ts in records:
        n, EF, I = SM2(conf, n, EF, I)
        last_ts = ts

    last_review_at = last_ts
    next_review_at = last_ts + int(round(I * 86400))

    access.update_problem_state(number, n, EF, I, last_review_at, next_review_at)

@app.command(name="sync-problem-ids")
def sync_id_to_slug_table():
    con = access.get_db_con()
    cur = con.cursor()

    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS id_to_slug (
                id INTEGER PRIMARY KEY,
                slug TEXT NOT NULL
            )
        """) 

        id_to_slug_map : Dict[int, str] = fetch_all_problems()
        
        # If the above succeeds, proceed with the update
        cur.execute("DELETE FROM id_to_slug") 

        insert_data = [
            (prob_id, slug)
            for prob_id, slug in id_to_slug_map.items()
        ]

        # Bulk insert
        cur.executemany("INSERT INTO id_to_slug (id, slug) VALUES (?, ?)", insert_data)

        con.commit()
        logging.info(f"Sync of id_to_slug table complete. {len(insert_data)} problems saved.")

    except Exception as e:
        con.rollback()
        logging.error(f"Sync of id_to_slug table failed. For reason {e}")


if __name__ == "__main__":
    app()

