# app/core/analogy_agent_langchain.py
"""
Minimal LangChain agent integration with a web-search tool.
Requires: langchain, and either serpapi (SERPAPI_API_KEY) OR duckduckgo-search package.

This file provides `run_langchain_agent(prompt, profile)` -> str
"""

import os
def run_langchain_agent(prompt_text: str, profile=None) -> str:
    try:
        from langchain.agents import initialize_agent, Tool
        from langchain.llms import OpenAI
        use_serp = bool(os.environ.get("SERPAPI_API_KEY"))
        tools = []
        if use_serp:
            from langchain.tools import SerpAPIWrapper
            serp = SerpAPIWrapper()
            tools.append(Tool(name="Search", func=serp.run, description="Use for web search"))
        else:
            # fallback duckduckgo
            from langchain.utilities import DuckDuckGoSearchAPIWrapper
            ddg = DuckDuckGoSearchAPIWrapper()
            tools.append(Tool(name="Search", func=ddg.run, description="Use for web search (DuckDuckGo)"))
        # LLM for LangChain: use OpenAI (must have OPENAI_API_KEY)
        llm = OpenAI(temperature=0.2)
        agent = initialize_agent(tools, llm, agent="zero-shot-react-description", verbose=False)
        # build a task prompt including profile
        prof_text = ""
        if profile:
            prof_text = f"Profile: {profile}\n"
        query = f"{prof_text}Please provide an explain-by-analogy write-up for: {prompt_text}\nAlso return sources and a short confidence estimate."
        result = agent.run(query)
        return result
    except Exception as e:
        # fallback: return error so UI shows fallback
        return f"(LangChain agent error: {e})"
