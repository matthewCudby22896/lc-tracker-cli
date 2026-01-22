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

@app.callback()
def main():
    """
    LeetCode Track CLI: Spaced Repition for your coding practice.
    """
    if not access.db_exists():
        access.init_db()
        logging.info("lc-track database initialised.") 

    if access.get_state("initial_sync") != "complete":
        access.initial_sync()

def slugify_title(title: str) -> str:
    s = re.sub(r"[^a-z0-9\- ]", "", title.lower())
    return re.sub(r"\s+", "-", s.strip())

def fmt(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

@app.command(name="test")
def test():
    """
    For development purposes
    """
    print("test()")

@app.command(name="activate")
def activate(id: int) -> None:
    """ Add a problem to the active study set.
    """
    problem = access.get_problem(id)
    if not problem:
        print("No problem found with id: {id}")
        return

    if problem.active:
        print(f"LC {id}. {problem.title} [{problem.difficulty_txt}] is already in the active study set.")
        return

    access.set_active(id, True)

    print(f"LC {id}. {problem.title} [{problem.difficulty_txt}] added to active study set.")

@app.command(name="deactivate")
def deactivate(id: int) -> None:
    """ Remove a problem from the active study set.
    """
    problem = access.get_problem(id)
    if not problem:
        print("No problem found with id: {id}")
        return
    
    if not problem.active:
        print(f"LC {id}. {problem.title} [{problem.difficulty_txt}] is not in the active study set.")
        return

    access.set_active(id, False)

    print(f"LC {id}. {problem.title} [{problem.difficulty_txt}] removed from active study set.")

@app.command(name="details")
def details(id: int) -> None:
    problem = access.get_problem(id)
    if not problem: 
        print(f"No problem found with id: {id}")
        return

    def fmt_date(ts):
        return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "Never"

    print("\n" + "="*50)
    print(f" PROBLEM DETAILS: #{problem.id}")
    print("="*50)
    
    print(f"{'Title:':<15} {problem.title}")
    print(f"{'Slug:':<15} {problem.slug}")
    print(f"{'Difficulty:':<15} {problem.difficulty_txt} ({problem.difficulty})")
    print(f"{'Status:':<15} {'[ ACTIVE ]' if problem.active else '[ INACTIVE ]'}")
    
    print("-" * 50)
    print(" SPACED REPETITION (SM-2) STATS")
    print("-" * 50)
    
    print(f"{'Last Review:':<15} {fmt_date(problem.last_review_at)}")
    print(f"{'Next Review:':<15} {fmt_date(problem.next_review_at)}")
    print(f"{'Interval (I):':<15} {problem.i} days")
    print(f"{'Repetitions (n):':<15} {problem.n}")
    print(f"{'Easiness (EF):':<15} {problem.ef:.2f}")
    
    print("="*50 + "\n")


@app.command(name="add-entry")
def add_entry(
    id: int,
    confidence: int = typer.Option(..., help="Confidence rating (0–5)", click_type=IntRange(0, 5)),
) -> None:
    now_unix_ts = int(datetime.datetime.now().timestamp())

    problem = access.get_problem(id) 
    if not problem:
        print(f"No problem found with id: {id}")
        raise typer.Exit(code=1)

    # 1. Save the record
    record_id = access.insert_entry(id, confidence, now_unix_ts)

    # 2. Get the problems current SM-2 state 
    n, EF, I = problem.n, problem.ef, problem.i

    # 3. Calculate the new SM2 state
    n_new, EF_new, I_new = SM2(confidence, n, EF, I)
    next_review_at = now_unix_ts + int(I_new * 86400)

    access.update_SM2_state(id, n_new, EF_new, I_new, now_unix_ts, next_review_at)

    print(
        f"New record added (ID {record_id}):\n"
        f"  LC Number       : {id}\n"
        f"  Confidence      : {confidence}\n"
        f"  Last Review At  : {fmt(now_unix_ts)}\n"
        f"  Next Review At  : {fmt(next_review_at)}\n"
        f"  SM-2 State -> n: {n_new}, EF: {EF_new:.4f}, I: {I_new:.3f} days"
    )

@app.command(name="rm-entry")
def rm_entry(entry_id: int) -> None:
    rec = access.get_entry(entry_id)
    if rec is None:
        print(f"No record exists with id={entry_id}")
        raise typer.Exit(code=1)

    _, problem_id, *_ = rec

    access.del_entry(entry_id)

    recalc_and_set_problem_state(problem_id)

    logging.info(f"Record {entry_id} removed. LC {problem_id} state recalculated.")

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

if __name__ == "__main__":
    app()
