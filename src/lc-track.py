import re
import logging
import datetime
from enum import Enum
import typer
from click import IntRange

import access
from sm2 import SM2  # ensure this exists

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
def add_problem(number: int, title: str, difficulty: Difficulty) -> None:
    url = f"https://leetcode.com/problems/{slugify_title(title)}/description/"

    access.insert_problem(number, title, DIFF_TO_INT[difficulty.value], url)

    logging.info(f"LC {number}. {title} [{difficulty.value}] added/updated ")

@app.command(name="rm-problem")
def rm_problem(number: int) -> None:
    if not access.problem_exists(number):
        logging.error(f"LC {number} was not found.")
        raise typer.Exit(code=1)

    deleted = access.del_problem(number)  # make this return True/False

    logging.info(f"LC {number} removed.")

@app.command(name="add-record")
def add_record(
    number: int,
    confidence: int = typer.Option(..., help="Confidence rating (0–5)", click_type=IntRange(0, 5)),
    time_taken: int = typer.Option(..., help="Time spent in minutes"),
) -> None:
    now_unix_ts = int(datetime.datetime.now().timestamp())

    if not access.problem_exists(number):
        logging.error(f"LC {number} was not found.")
        raise typer.Exit(code=1)

    record_id = access.insert_record(number, confidence, time_taken, now_unix_ts)

    n, EF, I = access.get_problem_state(number)

    n_new, EF_new, I_new = SM2(confidence, n, EF, I)
    next_review_at = now_unix_ts + int(I_new * 86400)

    access.update_problem_state(number, n_new, EF_new, I_new, now_unix_ts, next_review_at)

    logging.info(
        f"New record added (ID {record_id}):\n"
        f"  LC Number       : {number}\n"
        f"  Confidence      : {confidence}\n"
        f"  Time Taken      : {time_taken}m\n"
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
        now = int(time())
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    app()

