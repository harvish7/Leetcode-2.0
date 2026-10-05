"""
Daily LeetCode agent (free: uses Gemini API, no LeetCode login).
Picks a public Easy/Medium problem it hasn't given you before,
writes a solution + explanation. You submit it yourself.
Only secret needed: GEMINI_API_KEY  (free at aistudio.google.com)
"""
import os, re, json, random, datetime, pathlib
import requests

GQL = "https://leetcode.com/graphql"
MODEL = "gemini-2.5-flash"   # if it errors, try another Flash model name
OUT_DIR = pathlib.Path("daily")
HISTORY = OUT_DIR / "history.json"
H = {"Content-Type": "application/json", "Referer": "https://leetcode.com"}


def gql(query, variables=None):
    r = requests.post(GQL, json={"query": query, "variables": variables or {}},
                      headers=H, timeout=30)
    r.raise_for_status()
    return r.json()["data"]


def pick_problem(done):
    q = """
    query list($limit: Int, $filters: QuestionListFilterInput) {
      questionList(categorySlug: "", limit: $limit, skip: 0, filters: $filters) {
        data { titleSlug title difficulty paidOnly }
      }
    }"""
    pool = []
    for diff in ("EASY", "MEDIUM"):
        d = gql(q, {"limit": 500, "filters": {"difficulty": diff}})
        pool += [x for x in d["questionList"]["data"]
                 if not x["paidOnly"] and x["titleSlug"] not in done]
    if not pool:
        raise SystemExit("No new problems left.")
    return random.choice(pool)


def get_statement(slug):
    q = "query q($slug: String!) { question(titleSlug: $slug) { content } }"
    html = gql(q, {"slug": slug})["question"]["content"]
    return re.sub(r"<[^>]+>", "", html)


def solve(title, difficulty, statement):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent")
    prompt = (
        f"LeetCode problem: {title} ({difficulty})\n\n{statement}\n\n"
        "Give: 1) approach in plain English, 2) clean Python 3 solution "
        "in LeetCode `class Solution` format, 3) time/space complexity, "
        "4) two edge cases to test."
    )
    r = requests.post(
        url,
        headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
                 "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def main():
    OUT_DIR.mkdir(exist_ok=True)
    done = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    p = pick_problem(set(done))
    answer = solve(p["title"], p["difficulty"], get_statement(p["titleSlug"]))

    path = OUT_DIR / f"{datetime.date.today()}-{p['titleSlug']}.md"
    path.write_text(f"# {p['title']} ({p['difficulty']})\n"
                    f"https://leetcode.com/problems/{p['titleSlug']}/\n\n{answer}\n")
    HISTORY.write_text(json.dumps(done + [p["titleSlug"]]))
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
  
