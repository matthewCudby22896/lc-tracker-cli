
import requests
import logging
import os

from typing import Dict, Tuple, List
from pathlib import Path

from .access import get_db_con

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

ALL_PROBLEMS_URL = "https://leetcode.com/api/problems/all/"
GRAPHQL_ENDPOINT = "https://leetcode.com/graphql"
CACHED_ALL_PROBLEMS_LOC = ""

# Set up a global session
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0...",
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com"
})

def fetch_all_problems():
    """
    Makes a request to a public leetcode endpoint to retrieve all problem-slugs, and numbers.

    Returns dict that maps problem number -> title slug, which can in turn be used
    to request the details of a problem via a graphQL endpoint.
    """
    try:
        res = session.get(ALL_PROBLEMS_URL)
        res.raise_for_status()
        data = res.json()['stat_status_pairs']

        id_to_title_slug_map = {
            int(entry['stat']['question_id']) : entry['stat']['question__title_slug']
            for entry 
            in data
        }

    except Exception as e:
        # Adding context and rethrowing the original error
        raise RuntimeError(f"Failed to fetch up-to-date id->slug data LeetCode: {e}") from e

    return id_to_title_slug_map

def request_problem_details(slug : str):
    # The standard 'questionData' query used by the LeetCode frontend
    graphql_query = {
        "query": """
        query questionData($titleSlug: String!) {
            question(titleSlug: $titleSlug) {
                questionFrontendId
                title
                difficulty
                topicTags {
                    name
                    slug
                }
            }
        }
        """,
        "variables": {"titleSlug": slug}
    }

    try:
        res = session.post(GRAPHQL_ENDPOINT, json=graphql_query)
        res.raise_for_status()
        data = res.json().get('data', {}).get('question')
        title = data.get('title')
        diff = data.get('difficulty')
        topics : List[Tuple[str, str]]= [(x['name'], x['slug']) for x in data.get('topicTags')]

        print("-" * 30)
        print(f"TITLE:      {title}")
        print(f"DIFFICULTY: {diff}")
        print(f"TOPICS:     {', '.join([x[0] for x in topics])}")
        print("-" * 30)

    except Exception as e:
        pass



