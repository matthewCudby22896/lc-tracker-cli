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

from .constants import BACKUP_REPO_DIR

def clone_backup_repo(pat: str, username: str, repo_name: str) -> Optional[git.Repo]:
    auth_url = f"https://{pat}@github.com/{username}/{repo_name}.git"

        
    # 3. Perform the clone
    repo = git.Repo.clone_from(auth_url, BACKUP_REPO_DIR)
        