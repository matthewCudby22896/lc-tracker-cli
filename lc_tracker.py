import argparse
import sys
import random
import logging
import sqlite3
import lc_logging
import re
from typing import Tuple, List, Optional

from db_access import init_db, insert_problem, get_due_problems, get_all_problems, add_entry

DIFFICULTY = ["easy", "medium", "hard"] 
DIFF_TO_INT = {
    "easy" : 0,
    "medium" : 1,
    "hard" : 2
}
INT_TO_DIFF = {
   0 : "EASY" ,
   1 : "MEDIUM",
   2 : "HARD"
}

NEXT = "next"
ADD_PROBLEM = "add-problem"
LIST_ACTIVE = "ls-active"
LIST_ALL = "ls-all"
RECORD = "record"
COMMANDS = [NEXT, ADD_PROBLEM, LIST_ACTIVE, LIST_ALL, RECORD]

def add_problem(con : sqlite3.Connection,
                number : int,
                title : str,
                difficulty : str,
                ) -> None:
    dynamic_section = re.sub(r'[^a-z0-9\- ]', '', title.lower())  # keep letters, digits, spaces, and hyphens
    dynamic_section = re.sub(r'\s+', '-', dynamic_section.strip())  # collapse spaces into hyphens
    url = f"https://leetcode.com/problems/{dynamic_section}/description/"


    insert_problem(number, title, DIFF_TO_INT[difficulty], url, con)

def list_active(con : sqlite3.Connection) -> None:
    active : List[Tuple[int, str, int]] = get_due_problems(con)
    active.sort(key=lambda x:x[0])

    for num, title, diff in active:
        print(f"{num}. {title} [{INT_TO_DIFF[diff]}]")
    

def list_all(con : sqlite3.Connection) -> None:
    all : List[Tuple[int, str, int]] = get_all_problems(con)
    all.sort(key = lambda x : x[0])

    for num, title, diff in all:
        print(f"{num}. {title} [{INT_TO_DIFF[diff]}]")

def record(con : sqlite3.Connection,
           lc_num : int,
           conf : int,
           time_taken : int) -> None:
    add_entry(lc_num, conf, time_taken, con)


def next(con: sqlite3.Connection, diff: Optional[str]) -> None:
    # fetch due problems, optionally filtered by difficulty
    problems = get_due_problems(con, DIFF_TO_INT[diff] if diff else None)
    if not problems:
        print("No due problems.")
        return

    num, title, diff_int, _ = random.choice(problems)
    print(f"{num}. {title} [{INT_TO_DIFF[diff_int]}]")

    
def main(args : argparse.Namespace) -> None:
    con  = init_db()

    if args.command == LIST_ACTIVE: # Lists all 'active' problems that are up for studyu
        list_active(con)
    
    elif args.command == LIST_ALL: # List all problems
        list_all(con)
    
    elif args.command == NEXT: # Spits out a problem from the 'active' set for study
        next(con, args.diff)
    
    elif args.command == ADD_PROBLEM: 
        add_problem(con, args.number, args.title, args.difficulty)    

    elif args.command == RECORD: 
        record(con, args.lc_num, args.confidence, args.time_taken)
        
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="lc", description="LeetCode study helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_next = sub.add_parser(NEXT, help="Show next problem due")
    p_next.add_argument("-d", "--diff", choices=DIFFICULTY, help="Filter by difficulty")

    sub.add_parser(LIST_ACTIVE, help="List active (due) problems")
    sub.add_parser(LIST_ALL, help="List all problems")

    p_add = sub.add_parser(ADD_PROBLEM, help="Add a LeetCode problem")
    p_add.add_argument("number", type=int, help="LeetCode problem number")
    p_add.add_argument("title", help="Problem title (use quotes if it has spaces)")
    p_add.add_argument("difficulty", help="Problem difficulty i.e. [easy, medium, hard]", choices=DIFFICULTY)

    p_rec = sub.add_parser(RECORD, help="Record a study result")
    p_rec.add_argument("lc_num", type=int, help="LeetCode problem number")
    p_rec.add_argument("--confidence", type=int, required=True, help="0–5")
    p_rec.add_argument("--time-taken", type=int, required=True, help="Minutes")

    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)


