# lc-track

A CLI tool for tracking LeetCode completions using the SuperMemo-2 (SM-2) algorithm. It automatically schedules your next study date based on past performance and a user-provided confidence rating (0–5).

## Synchronization Specification: Git-Backed Event Ledger

### 1. Core Architecture: Event Sourcing
The application utilizes an **Event Sourcing** model where the "Source of Truth" is an immutable, append-only **Action Log** (`actions.jsonl`). The local SQLite database is a **Projection**—a calculated state derived by replaying the history of events.

### 2. Event Schema
Every state-modifying transaction is captured as a discrete JSON object.
- `ADD_ENTRY`: Records a study session (Problem ID, Confidence, Timestamp).
- `RM_ENTRY`: Nullifies a specific study session.
- `ACTIVATE`: Flags a problem for the active study queue.
- `DEACTIVATE`: Removes a problem from the active study queue.

### 3. Automated Persistence Layer
- **Local Capture:** Every modification appends a new line to `actions.jsonl` in the local data directory.
- **Background Sync:** Each modification triggers an automated `git commit` and `git push` to the remote repository.
- **Deterministic Replay:** On-demand or upon "Pull," the local SQLite tables (`problems`, `entries`) are cleared and reconstructed by iterating through the log from Line 1.

### 4. Conflict Resolution & Parity
When the local ledger diverges from the remote repository, the system provides two recovery paths:

1. **Remote-First (Reset/Rebase):** Discards local unsynced actions and aligns perfectly with the remote ledger. 
   *Equivalent to: `git fetch && git reset --hard origin/main`*
   
2. **Local-First (Force Push):** Overwrites the remote history with the current local ledger.
   *Equivalent to: `git push --force`*


**25/01/2026**

- [ ] : Implement local storage of events i.e. ADD RECORD, RM RECORD using (jsonl)