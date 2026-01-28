import re
import logging
import datetime
import typer
import click
import random
import github
import git

from .utility import recalc_and_set_problem_state
from .sm2 import SM2 
from . import access
from . import utility

from typing import Any, Dict, Tuple, List

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
app = typer.Typer(add_completion=False)

colours = {
    "Easy": "92",
    "Medium": "93",
    "Hard": "91"
}

def fmt_date(ts):
    return datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M') if ts else "Never"

@app.callback()
def main():
    """
    LeetCode Track CLI: Spaced Repition for your coding practice.
    """
    if not access.db_exists():
        access.init_db()
        logging.info("lc-track database initialised.") 

    if access.get_state("initial_sync") != "complete":
        utility.initial_sync()

@app.command(name="study")
def study():
    """Picks a random problem those scheduled for review."""

    problems = access.get_for_review_problems()

    if not problems:
        typer.echo("No problems due for review.")
        return

    chosen = random.choice(problems)
    
    color_code = colours.get(chosen.difficulty_txt, "37")

    # \033[94m: Blue label | \033[0m: Reset | \033[{color_code}m: Difficulty color
    typer.echo(f"\033[1;94mTo study:\033[0m LC{chosen.id}. {chosen.title} [\033[{color_code}m{chosen.difficulty_txt}\033[0m]")
@app.command(name="set-pat")
def set_pat():
    PAT = input("Enter github PAT token:").strip()

    with access.get_db_connection() as con:
        access.set_state('PAT')

import typer

@app.command(name="ls-active")
def ls_active():
    """ List all problems currently in the active study set. """
    active_problems = access.get_active()

    if not active_problems:
        typer.echo("Your active study set is empty. Use 'lc-track activate <id>' to add some!")
        return

    typer.echo(f"\033[1mActive Study Set ({len(active_problems)} problems)\033[0m")
    
    for p in active_problems:
        color_code = colours.get(p.difficulty_txt, "37")

        # Using :<4 to align IDs so the titles start at the same spot
        typer.echo(f"LC{p.id:<4}. {p.title:<35} [\033[{color_code}m{p.difficulty_txt}\033[0m] \033[1m\033[0m")

@app.command(name="ls-review")
def ls_for_review():
    """ List all problems currently due for an SM-2 review. """
    due_problems = access.get_for_review_problems()

    if not due_problems:
        typer.echo("No problems due for review. You're all caught up!")
        return

    # Using your bold blue style for the header
    typer.echo(f"\033[1;94mTo review:\033[0m {len(due_problems)} problems pending")
    
    for p in due_problems:
        color_code = colours.get(p.difficulty_txt, "37")
        # Kept the padding and removed the trailing blue bracket bug
        typer.echo(f"LC{p.id:<4}. {p.title:<35} [\033[{color_code}m{p.difficulty_txt}\033[0m]")


@app.command(name="activate")
def activate(id: int) -> None:
    """ Add a problem (by its id) to the 'active' study set. """
    problem = access.get_problem(id)
    
    if not problem:
        typer.echo(f"No problem found with id: {id}")
        return

    color_code = colours.get(problem.difficulty_txt, "37")

    if problem.active:
        typer.echo(f"LC{id}. {problem.title} [\033[{color_code}m{problem.difficulty_txt}\033[0m] is already in the active study set.")
        return

    access.set_active(id, True)

    # Bold blue label followed by the colored problem info
    typer.echo(f"\033[1;94mAdded to active set:\033[0m LC{problem.id}. {problem.title} [\033[{color_code}m{problem.difficulty_txt}\033[0m]")

@app.command(name="deactivate")
def deactivate(id: int) -> None:
    """ Remove a problem (by its id) from the 'active' study set. """
    problem = access.get_problem(id)
    
    if not problem:
        typer.echo(f"No problem found with id: {id}")
        return

    color_code = colours.get(problem.difficulty_txt, "37")
    
    if not problem.active:
        typer.echo(f"LC{id}. {problem.title} [\033[{color_code}m{problem.difficulty_txt}\033[0m] is not in the active study set.")
        return

    access.set_active(id, False)

    typer.echo(f"\033[1;94mRemoved from active set:\033[0m LC{problem.id}. {problem.title} [\033[{color_code}m{problem.difficulty_txt}\033[0m]")


@app.command(name="details")
def details(id: int) -> None:
    """ Show the details of a LC problem. """
    problem = access.get_problem(id)
    # topics is already a list of strings: ["Array", "Hash Table"]
    topics = access.get_problem_topics(id)
    
    if not problem: 
        typer.echo(f"No problem found with id: {id}")
        return

    BW = "\033[1;37m"        # Bold White
    RESET = "\033[0m"        # Full Reset
    color_code = colours.get(problem.difficulty_txt, "37")
    diff_color = f"\033[{color_code}m"

    typer.echo(f"{BW}LC{problem.id}. {problem.title} [{RESET}{diff_color}{problem.difficulty_txt}{RESET}{BW}]{RESET}")

    if topics:
        typer.echo(f"Topics: {', '.join(topics)}")
    typer.echo("")
    typer.echo(f"Last Review: {fmt_date(problem.last_review_at)}")
    typer.echo(f"Next Review: {fmt_date(problem.next_review_at)}")
    typer.echo(f"Interval:    {problem.i:.0f} days")
    typer.echo(f"Repetitions: {problem.n}")
    typer.echo(f"Easiness:    {problem.ef:.2f}\n")

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
        typer.echo(f"No problem found with id: {id}")
        raise typer.Exit(code=1)

    # 1. Save the record
    try:
        record_id = access.insert_entry(id, confidence, now_unix_ts)
    except Exception as exc: 
        logging.error(f"Failed to insert entry into local database: {exc}")
        raise typer.Exit(1)

    # 2. Get the problems current SM-2 state 
    n, EF, I = problem.n, problem.ef, problem.i

    # 3. Calculate the new SM2 state
    n_new, EF_new, I_new = SM2(confidence, n, EF, I)
    next_review_at = now_unix_ts + int(I_new * 86400)

    # 4. Update the state of the problem
    try:
        access.update_SM2_state(id, n_new, EF_new, I_new, now_unix_ts, next_review_at)
    except Exception as exc:
        logging.error(f"Failed to update SM2 state of problem: {exc}")
        raise typer.Exit(1)

    typer.echo("-" * 30)
    typer.echo(f"Record Saved [ID: {record_id}]")
    typer.echo("-" * 30)
    typer.echo(f"{'Problem ID':<15}: {id}")
    typer.echo(f"{'Confidence':<15}: {confidence}/5")
    typer.echo(f"{'Next Review':<15}: {fmt_date(next_review_at)} (in {I_new:.1f} days)")
    typer.echo(f"{'New EF':<15}: {EF_new:.2f}")
    typer.echo("-" * 30)

@app.command(name="rm-entry")
def rm_entry(entry_uuid : str) -> None:
    """ Remove an entry and update the SM2 state.
    """
    try:
        problem_id = access.rm_entry(entry_uuid)
    except Exception as exc:
        logging.error(f"Failed to remove entry: {exc}")
        raise typer.Exit(1)

    logging.info(f"Record {entry_uuid} removed. LC {problem_id} state recalculated.")


@app.command(name="set-pat")
def set_pat(pat: str = typer.Argument(..., help="Your GitHub Personal Access Token")):
    """
    Store your GitHub Personal Access Token in the local database.
    Usage: lc-track set-pat <YOUR_PAT_HERE>
    """
    try:
        with access.get_db_connection() as con:
            access.set_state(con, 'PAT', pat)

    except Exception as exc:
        typer.echo("An unexpected exception has occurred: {exc}")
        raise typer.Exit(1)
    
    typer.echo("Success: GitHub PAT has been saved.")

@app.command(name="setup-backup")
def setup_backup():
    typer.echo(
        """
        [ LC-TRACK SYNC SETUP ]

        Prerequisites:
        1. A GitHub repository (e.g., 'lc-track-backup')
        2. A Fine-Grained PAT with 'Contents: Read & Write' permissions
        """
    )

    # 1. Inputs
    repo_name = typer.prompt("Backup repository name")
    pat = typer.prompt("GitHub Personal Access Token", hide_input=True)

    g = github.Github(pat)

    # 3. Connection & Authentication
    try: 
        user = g.get_user()
        username = user.login
        typer.echo(f"Connected: Authenticated as {username}")
    except github.BadCredentialsException:
        typer.echo("Error: Invalid PAT. Please verify your token and try again.")
        access.set_state(con, 'SYNC_SETUP', 'FAILURE')
        raise typer.Exit(1)

    # 4. Repository Verification
    try:
        repo = user.get_repo(repo_name)
        typer.echo(f"Connected: Found {repo_name} repository")
    except github.UnknownObjectException:
        typer.echo(f"Error: Repository '{repo_name}' not found. Check name and PAT scopes.")
        access.set_state(con, 'SYNC_SETUP', 'FAILURE')
        raise typer.Exit(1) 
    
    # 5. Permission Verification
    permissions = repo.permissions
    if not (permissions.push and permissions.pull):
        typer.echo("Error: PAT has insufficient permissions (Read/Write required)")
        access.set_state(con, 'SYNC_SETUP', 'FAILURE')
        raise typer.Exit(1)
    
    typer.echo("Connected: Read and Write access confirmed")

    # 6. Finalize
    with access.get_db_connection() as con:
        access.set_state(con, 'PAT', pat)
        access.set_state(con, 'BACKUP_REPO_NAME', repo_name)
        access.set_state(con, 'USERNAME', username)
        access.set_state(con, 'SYNC_SETUP', 'SUCCESS')
    
    typer.echo("Success: Sync configuration saved")

@app.command(name="sync")
def sync():
    if access.get_state('SYNC_SETUP') != "SUCCESS":
        typer.echo("You have not yet setup syncing / backups. See `lc-track setup-backup`.") 
        raise typer.Exit(1)
    
    # Based of the SUCCESS, we can assumed we have a PAT & repo name
    PAT = access.get_state('PAT') 
    BACKUP_REPO_NAME = access.get_state('PAT')

    if not access.check_repo(access.BACKUP_REPO_DIR):
        typer.echo(f"Cloning {BACKUP_REPO_NAME} to {access.BACKUP_REPO_DIR}")
    
    

@app.command(name="sync")
def sync():
    # 1. Check if a github PAT has been provided. Where to store?
    PAT = access.get_state('PAT')

    if not PAT:
        PAT = input("No github PAT set. Please enter:")

        # TODO: Basic validation

        # Make some sort of request to verify it
        with access.get_db_connection() as con:
            access.set_state(con, 'PAT', PAT)
    
    g = github.Github(PAT)

    user = g.get_user()

    # TODO: Move this to a constants file (among with some other vars)
    repo_name = "lc-track-remote-backup"

    try:
        remote_repo = user.get_repo(repo_name)

    # Exception raised when a non-existing object is requested 
    # (when Github API replies with a 404 HTML status)
    except github.UnknownObjectException as e: #
        # Create the repository        
        remote_repo = user.create_repo(
            name=repo_name,
            description="A repository for maintaining a backup of lc-track's state.",
            private=False,
            auto_init=True,
        )

    # 2. Check if the local of the remote backup repo is initialised
    if not access.check_repo(access.BACKUP_REPO_DIR):
        typer.echo(f"Cloning {repo_name} to {access.BACKUP_REPO_DIR}")
        try: 
            # Create an authenticated URL: https://<PAT>@github.com/user/repo.git
            auth_url = remote_repo.clone_url.replace("https://", f"https://{PAT}@")

            local_backup_repo = git.Repo.clone_from(auth_url, access.BACKUP_REPO_DIR)
        
        # TODO: More informative exception handling
        except Exception as exc:
            typer.echo(f"An unexpected exception has occurred: {exc}")
            raise typer.Exit(1)
        
        typer.echo(f"Local backup directory initialised.")
    else:
        local_backup_repo = git.Repo(access.BACKUP_REPO_DIR)
        origin = local_backup_repo.remotes.origin
        
        # Update the remote URL to include the PAT for this session
        auth_url = remote_repo.clone_url.replace("https://", f"https://{PAT}@")
        origin.set_url(auth_url)

    # 3. See if the local version of the remote backup is up-to-date
    origin = local_backup_repo.remotes.origin

    origin.fetch()
    origin.pull()

    # 4. Perform an event history merge
    merged_history : List[Dict[str, Any]] = access.merge_event_histories()

    # 5. Push the updated event history
    access.update_event_history_backup(merged_history)

    local_backup_repo.index.add([access.BACKUP_EVENT_LOG_FILE])
    new_commit = local_backup_repo.index.commit("Synced & and updated event log.")

    local_backup_repo.remote(name="origin")

    push_info = origin.push()

    # Optional: Check if the push was successful
    if push_info[0].flags & push_info[0].ERROR:
        print(f"Push failed: {push_info[0].summary}")
    else:
        print("Push successful!")

    # 6. Report success
    typer.echo("Sync complete.")

if __name__ == "__main__":
    app()
