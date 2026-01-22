## LC-Track CLI Command Reference

### Records Keeping
- `lc-track add-record [number] [rating] --language [lang]`
  Adds a timestamped SM2 entry for the specified problem.
- `lc-track rm-record [record-id]`
  Removes the specified record, then recalculates the SM2 state for that specific problem.
- `lc-track ls-records -n [no. displayed]`
  Displays recent entries with their unique IDs.

### Managing the Active Set
- `lc-track add-problem [number]`
  Add a problem to the studied set. It can be chosen via `study` if its review date is before or equal to the current date.
- `lc-track rm-problem [number]`
  Remove a problem from the studied set. Note: Does not remove entries for this problem.
- `lc-track ls-problems`
  Displays all problems currently in the active study set, along with their titles and next review dates.

### Other
- `lc-track study`
  Picks a random problem from the active study set that is scheduled for review.

### Settings
- `lc-track auto-sync`
  Toggle auto-sync on/off. When on, the DB is synced to the GitHub backup whenever a record is added or deleted.
- `lc-track default-language [language]`
  Sets the default language assumed when using `add-record` without specifying via `--language`.


### v.0.1.2 Progres

- [ ] : Remove time-taken
- [ ] : Github back-up functionality, records + settings
- [ ] : Language + Default Language
- [ ] : Improved add-problem that requires only the problem number, and then proceeds to fetch the details, which are then stored locally.

### DB Design

-- 1. Main Problems Table
CREATE TABLE problems (
    id INTEGER PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT,
    difficulty INTEGER NOT NULL CHECK,
    last_review_at INTEGER,
    next_review_at INTEGER NOT NULL,

    -- Spaced Repetition Fields (SuperMemAo-2 logic)
    EF REAL NOT NULL DEFAULT 2.5,
    I INTEGER NOT NULL DEFAULT 0,
    n INTEGER NOT NULL DEFAULT 0
);

-- 2. Topics Lookup Table
CREATE TABLE topics (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- 3. Junction Table
CREATE TABLE problem_topic (
    problem_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    PRIMARY KEY (problem_id, topic_id),
    FOREIGN KEY (problem_id) REFERENCES problems(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);