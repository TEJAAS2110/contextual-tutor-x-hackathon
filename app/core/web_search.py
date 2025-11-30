# app/core/web_search.py
"""
Small web search helper. Returns a list of short snippets (text + source).
Uses SerpAPI if SERPAPI_API_KEY present, else uses duckduckgo-search package.
"""

import os
from typing import List, Dict

SERP_KEY = os.environ.get("SERPAPI_API_KEY")

def serpapi_search(query: str, num_results: int = 5) -> List[Dict]:
    from serpapi import GoogleSearch
    params = {"q": query, "api_key": SERP_KEY, "engine": "google", "num": num_results}
    search = GoogleSearch(params)
    res = search.get_dict()
    snippets = []
    # parse organic results
    for r in res.get("organic_results", [])[:num_results]:
        title = r.get("title")
        snippet = r.get("snippet") or r.get("rich_snippet", {}).get("top", "")
        link = r.get("link") or r.get("source")
        snippets.append({"title": title, "snippet": snippet, "link": link})
    return snippets

def duckduckgo_search(query: str, num_results: int = 5) -> List[Dict]:
    from duckduckgo_search import ddg
    results = ddg(query, max_results=num_results)
    snippets = []
    if results:
        for r in results:
            snippets.append({"title": r.get("title"), "snippet": r.get("body") or r.get("snippet"), "link": r.get("href")})
    return snippets

def web_search_snippets(query: str, num_results: int = 5):
    if SERP_KEY:
        try:
            return serpapi_search(query, num_results=num_results)
        except Exception as e:
            # fallback to duckduckgo if serpapi call fails
            print("SerpAPI error:", e)
    # fallback
    try:
        return duckduckgo_search(query, num_results=num_results)
    except Exception as e:
        print("DuckDuckGo error:", e)
        return []
