import argparse
from db_access import init_db
import logging

DIFFICULTY = ["easy", "med", "hard"] 

NEXT = "next"
ADD_PROBLEM = "add-problem"
LIST_ACTIVE = "ls-active"
LIST_ALL = "ls-all"
RECORD = "record"
COMMANDS = [NEXT, ADD_PROBLEM, LIST_ACTIVE, LIST_ALL, RECORD]

def add_problem() -> None:
    pass

def list_active() -> None:
    pass

def list_all() -> None:
    pass

def record() -> None:
    pass

def next() -> None:
    pass

def main(args : argparse.Namespace) -> None:
    init_db()

    command = args.command

    if command == LIST_ACTIVE: # Lists all 'active' problems that are up for studyu
        list_active()
    
    elif command == LIST_ALL: # List all problems
        list_all()
    
    elif command == NEXT: # Spits out a problem from the 'active' set for study
        diff = getattr(args, "diff", None)
    
    elif command == ADD_PROBLEM: # Add a s
        add_problem()

    elif command == RECORD: 
        record()
        

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="TBD", choices=COMMANDS)
    parser.add_argument("-d", "--diff", choices=DIFFICULTY)
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)


