import argparse
from db_access import init_db
import logging

def add_problem() -> None:
    pass

def list_active() -> None:
    pass

def log() -> None:
    pass

def study() -> None:
    pass

def main(args : argparse.Namespace) -> None:
    print(args)
    
    init_db()
    pass

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", help="TBD")
    
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)


