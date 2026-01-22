import re
import logging
import datetime
import typer
import click
import random

from .ds import Problem
from .utility import recalc_and_set_problem_state
from .sm2 import SM2 
from . import access

from typing import Dict, Tuple, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
app = typer.Typer(add_completion=False)

colors = {
    "Easy": "92",
    "Medium": "93",
    "Hard": "91"
}

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
    For development purposes.
    """
    print("test()")

@app.command(name="study")
def study():
    problems : List[Problem] = access.get_for_review_problems()

    chosen = random.choice(problems)

    print(f"\033[1mLC{chosen.id}. {chosen.title} [{chosen.difficulty_txt}]\033[0m")

@app.command(name="study")
def study():
    problems = access.get_for_review_problems()

    if not problems:
        print("No problems due for review.")
        return

    chosen = random.choice(problems)

    
    color_code = colors.get(chosen.difficulty_txt, "37")

    # \033[94m: Blue label | \033[0m: Reset | \033[{color_code}m: Difficulty color
    print(f"\033[1;94mTo study:\033[0m LC{chosen.id}. {chosen.title} [\033[{color_code}m{chosen.difficulty_txt}\033[0m]")

@app.command(name="show-active")
def show_active():
    """ List all problems currently in the active study set. """
    active_problems = access.get_active()

    if not active_problems:
        print("Your active study set is empty. Use 'lc-track activate <id>' to add some!")
        return


    print(f"\033[1mActive Study Set ({len(active_problems)} problems)\033[0m")
    
    for p in active_problems:
        color_code = colors.get(p.difficulty_txt, "37")

        # Using :<4 to align IDs so the titles start at the same spot
        print(f"LC{p.id:<4}. {p.title:<35} [\033[{color_code}m{p.difficulty_txt}\033[0m] \033[1m\033[0m")

@app.command(name="activate")
def activate(id: int) -> None:
    """ Add a problem (by it's id) to the 'active' study set.
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
    """ Remove a problem (by it's id) from the 'active' study set.
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
    """ Show the details of a LC problem.
    """
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
    confidence: int = typer.Option(..., help="Confidence rating (0–5)", click_type=click.IntRange(0, 5)),
) -> None:
    """ Log a completion and update the SM-2 state.
    """
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

    print("-" * 30)
    print(f"Record Saved [ID: {record_id}]")
    print("-" * 30)
    print(f"{'Problem ID':<15}: {id}")
    print(f"{'Confidence':<15}: {confidence}/5")
    print(f"{'Next Review':<15}: {fmt(next_review_at)} (in {I_new:.1f} days)")
    print(f"{'New EF':<15}: {EF_new:.2f}")
    print("-" * 30)

# TODO: Rework this using with con, s.t. all db changes are handled in a single transaction and thus rolled back if failed.
@app.command(name="rm-entry")
def rm_entry(entry_id: int) -> None:
    """ Remove an entry and update the SM2 state.
    """
    rec = access.get_entry(entry_id)
    if rec is None:
        print(f"No record exists with id={entry_id}")
        raise typer.Exit(code=1)

    _, problem_id, *_ = rec

    con = access.get_db_connection()
    try:
        with con:
            # Delete the entry
            cur = con.cursor()
            cur.execute("DELETE FROM entries WHERE id = ?", (entry_id,))

            # Get all of the entries for the problem_id
            cur.execute("SELECT (id, confidence, ts) FROM entries WHERE problem_id = ?", (problem_id,))
            entries = cur.fetchall()

            if not entries:     
                now = int(datetime.datetime.now().timestamp())
                n, EF, I = 0, 2.5, 0.0
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
            """, (n, EF, I, int(last_review_at), int(next_review_at), ts))
    finally:
        con.close()

    logging.info(f"Record {entry_id} removed. LC {problem_id} state recalculated.")


if __name__ == "__main__":
    app()
