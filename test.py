import requests

def fetch_by_slug(slug: str):
    url = "https://leetcode.com/graphql"
    
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

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.post(url, json=graphql_query, headers=headers)
        response.raise_for_status()
        data = response.json().get('data', {}).get('question')

        if not data:
            print(f"Error: Problem with slug '{slug}' not found.")
            return

        # Formatting for display
        print(f"--- Metadata for: {slug} ---")
        print(f"ID:         {data['questionFrontendId']}")
        print(f"Title:      {data['title']}")
        print(f"Difficulty: {data['difficulty']}")
        print(f"Topics:     {', '.join([tag['name'] for tag in data['topicTags']])}")
        
    except requests.exceptions.RequestException as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    # Example usage: python script.py reverse-linked-list
    import sys
    target_slug = sys.argv[1] if len(sys.argv) > 1 else "two-sum"
    fetch_by_slug(target_slug)
