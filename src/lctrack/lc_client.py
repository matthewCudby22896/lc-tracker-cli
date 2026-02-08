import requests
import logging
import typer
from rich.progress import track

from typing import Any, Dict, Tuple, List

ALL_PROBLEMS_URL = "https://leetcode.com/api/problems/all/"
GRAPHQL_ENDPOINT = "https://leetcode.com/graphql"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0...",
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com"
})

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

    typer.echo("Fetching leetcode problem set from leetcode.com...")

    try:
      # Make initial request (first 100 problems)
      payload['variables']['skip'] = skip
      res = session.post(url, json=payload)
      res.raise_for_status()

      data = res.json()
      total = data['data']['problemsetQuestionList']['totalNum'] # total no. problems to fetch

      question_batch = data['data']['problemsetQuestionList']['questions']
      all_questions.extend(question_batch)

      # Fetch the rest
      for skip in track(range(100, total, 100)):
          payload['variables']['skip'] = skip
          res = session.post(url, json=payload)
          res.raise_for_status()

          data = res.json()

          if total is None:
              total = data['data']['problemsetQuestionList']['totalNum'] # The total number of questions
          
          # Extract the problems in this batch
          question_batch = data['data']['problemsetQuestionList']['questions']
          all_questions.extend(question_batch)
        

    except Exception as exc:
      typer.echo(f"An unexpected exception occured whilst fetching problems from leetcode.com: {exc}")
      raise typer.Exit(1)
    
    typer.echo(f"All {len(all_questions)} problems succesfully fetched and stored from leetcode.com")

    return all_questions