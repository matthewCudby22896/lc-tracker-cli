"""

TODO:
- [ ] : Method for creating github repo
- [ ] : Method for pulling the remote event history
- [ ] : Method for pushing the up-to-date / merged event history

Authorisation will be done via a github PAT token that the user will have to provide.
"""

import git
from pathlib import Path
import typer

def clone_backup_repo(pat: str, username: str, repo_name: str, local_path: Path):
    auth_url = f"https://{pat}@github.com/{username}/{repo_name}.git"

    # 2. Ensure the target directory's parent exists, but the target itself should be empty/new
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        typer.echo(f"Action: Cloning {repo_name} to {local_path}...")
        
        # 3. Perform the clone
        repo = git.Repo.clone_from(auth_url, local_path)
        
        typer.echo("Success: Repository cloned successfully")
        return repo

    except git.GitCommandError as exc:
        typer.echo(f"Error: Failed to clone repository. {exc.summary}")
        raise typer.Exit(1)