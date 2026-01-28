"""

TODO:
- [ ] : Method for creating github repo
- [ ] : Method for pulling the remote event history
- [ ] : Method for pushing the up-to-date / merged event history

Authorisation will be done via a github PAT token that the user will have to provide.
"""

import git
import typer
from pathlib import Path
from typing import Optional

def clone_backup_repo(pat: str, username: str, repo_name: str, local_path: Path) -> Optional[git.Repo]:
    auth_url = f"https://{pat}@github.com/{username}/{repo_name}.git"

    # 2. Ensure the target directory's parent exists, but the target itself should be empty/new
    local_path.mkdir(parents=True, exist_ok=True)

    try:
        
        # 3. Perform the clone
        repo = git.Repo.clone_from(auth_url, local_path)
        
        return repo

    except git.GitCommandError as exc:
        typer.echo(f"Error: Failed to clone repository. {exc.summary}")
        return None