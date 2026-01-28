
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

from .constants import TMP_EVENT_HISTORY, BACKUP_EVENT_HISTORY, LOCAL_EVENT_HISTORY
from .sm2 import SM2
from . import access

def merge_event_histories(hist1 : Path, hist2 : Path) -> List[Dict[str, Any]]:
    # Load both event histories into memory
    events_local : List[dict] = load_event_history(hist1)
    events_backup : List[dict] = load_event_history(hist2)

    # Merge the two into a single list of unique events, sorted by ts
    combined_events = list({event['id']: event for event in events_backup + events_local}.values())
    combined_events.sort(key=lambda x : x['ts'])

    return combined_events

def load_event_history(path : Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    
    events = []
    with open(path, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1): 
            line = line.strip() 
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise Exception(f"Failed to parse ln {ln} of {f}: {exc}") 

    return events            

def write_event_history(loc : Path, event_history : List[str, Any]) -> None:
    with open(loc, 'w', encoding="utf-8") as f:
        for event in event_history: 
            line = json.dumps(event)
            f.write(line + '\n')

def reset_local_state() -> None:
    events = load_event_history(LOCAL_EVENT_HISTORY)    
    sm2_states : Dict[int, Tuple[int, float, int]] = {} # problem_id -> SM2 state (n, EF, I, last_review_ts, next_review_ts)

    for e in events:
        problem_id, event, confidence, ts = (
            e['problem_id'], e['event'], e['confidence'], e['ts']
        )

        if event == "ADD_ENTRY":
            if problem_id not in sm2_states:
                n, EF, I = (0, 2.5, 0)

            n, EF, I = SM2(confidence, n, EF, I)
            last_review_at = ts
            next_review_at = last_review_at + int(I * 86400)

        elif event == "RM_ENTRY":
            pass

def update_state_from_local_event_history() -> None:
    """
    Steps:
    1. Clear the entries database table
    2. Run through the events stored under LOCAL_EVENT_HISTORY updating the entries database table
    3. Wipe the problem state for all problems
    4. Run through every entry within entries in chronological order to derive the correct state of each problem
    """
    
    access.clear_entries_table()

    # 1. Load all events from the local version of the event history
    events = load_event_history(LOCAL_EVENT_HISTORY)    

    # 2. Process all events in chronological order
    for event in events:
        access.process_event(event)
    
    # 3. Update the state of all problems based of the entries under the entries table
    entries = access.get_all_entries() 

    sm2_states : Dict[int, Tuple[int, float, int]] = {} # problem_id -> SM2 state (n, EF, I, last_review_ts, next_review_ts)

    for _, problem_id, confidence, ts in entries:    
        if problem_id not in sm2_states:
            n, EF, I = (0, 2.5, 0)
        n, EF, I = SM2(confidence, n, EF, I)
        last_review_at = ts
        next_review_at = last_review_at + int(I * 86400)

        sm2_states[problem_id] = (n, EF, I, last_review_at, next_review_at)

    new_states = [
        (v[0], v[1], v[2], v[3], v[4], k) 
        for k, v in sm2_states.items()
    ]

    access.bulk_update_SM2_state(new_states)


