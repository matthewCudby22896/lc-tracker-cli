
import requests
import logging

from typing import Any, Dict, Tuple, List

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

# def fetch_all_problems() -> List[Tuple[int, str]]:
#     """
#     Makes a request to a public leetcode endpoint to retrieve all problem-slugs, and numbers.

#     Returns dict that maps problem number -> title slug, which can in turn be used
#     to request the details of a problem via a graphQL endpoint.
#     """
#     try:
#         res = session.get(ALL_PROBLEMS_URL)
#         res.raise_for_status()
#         data = res.json()['stat_status_pairs']

#         id_to_title_slug_map = [
#             (int(entry['stat']['frontend_question_id']), entry['stat']['question__title_slug'])
#             for entry 
#             in data
#         ]

#     except Exception as e:
#         # Adding context and rethrowing the original error
#         raise RuntimeError(f"Failed to fetch up-to-date id->slug data LeetCode: {e}") from e

#     return id_to_title_slug_map


def fetch_all_problems() -> List[Dict[str, Any]]: 
    url = "https://leetcode.com/graphql/"
    limit = 100
    skip = 0
    
    query = """
    query problemsetQuestionList($categorySlug: String, $limit: Int, $skip: Int, $filters: QuestionListFilterInput) {
      problemsetQuestionList: questionList(
        categorySlug: $categorySlug
        limit: $limit
        skip: $skip
        filters: $filters
      ) {
        totalNum
        questions: data {
          questionFrontendId
          title
          titleSlug
          difficulty
          topicTags {
            name
            slug
          }
        }
      }
    }
    """

    all_questions = []
    payload = {
        "query" : query,
        "variables" : {"categorySlug": "", "skip": skip, "limit": limit, "filters": {}}
    }
    total = None

    logging.info("Fetching complete problem set from leetcode.com ...")
    try:
        while True:
            payload['variables']['skip'] = skip
            res = session.post(url, json=payload)
            res.raise_for_status()

            data = res.json()

            if total is None:
                total = data['data']['problemsetQuestionList']['totalNum'] # The total number of questions
            
            # Extract the problems in this batch
            question_batch = data['data']['problemsetQuestionList']['questions']
            all_questions.extend(question_batch)

            pct_complete = min(skip + limit, total) / total
            logging.info(f"Progress: {min(skip + limit, total)}/{total} problems fetched ({pct_complete:.1%})")

            if skip + limit > total:
                break
                
            skip += limit

    except Exception as e:
        logging.error(f"Failed to fetch problem set from leetcode.com: {e}")
        return None
    
    logging.info(f"{len(all_questions)} problems fetched.")

    return all_questions





