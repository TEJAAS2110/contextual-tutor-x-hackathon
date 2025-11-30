# app/core/llm_client.py
"""
Simple LLM client wrapper - FIXED for OpenAI SDK compatibility
"""
import os
from typing import List

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
DEFAULT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-3.5-turbo")

def _chat_complete(prompt: str, temperature: float = 0.2, max_tokens: int = 700) -> str:
    """Call OpenAI with compatibility for both old and new SDK"""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")
    
    try:
        # Try new OpenAI SDK (>=1.0)
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content.strip()
    except Exception as e1:
        try:
            # Fallback to old OpenAI SDK (<1.0)
            import openai
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model=DEFAULT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e2:
            raise RuntimeError(f"OpenAI call failed: {str(e1)[:100]} | {str(e2)[:100]}")

def get_llm(temperature: float = 0.2):
    """Return a callable LLM function"""
    def call(prompt_text: str):
        return _chat_complete(prompt_text, temperature=temperature)
    return call

def summarize_with_context(prompt: str, context_texts: List[str], temperature: float = 0.2) -> str:
    """
    Given a user prompt and context snippets from web search,
    call the LLM to produce an explain-by-analogy output.
    """
    MAX_CHARS = 4000
    joined = "\n\n".join(context_texts)
    if len(joined) > MAX_CHARS:
        joined = joined[:MAX_CHARS] + "\n\n...truncated..."
    
    instruction = f"""
You are an explain-by-analogy tutor. Use the web evidence provided to write a clear explanation.

Include:
- A 2-3 sentence summary
- 2-3 analogies (each 1-2 paragraphs)
- Key insights (3-5 bullet points)
- Short list of sources (URLs or titles)
- A confidence estimate (0-100)

User query:
{prompt}

Web evidence:
{joined}

Return the result as plain text. If evidence conflicts, note it briefly.
"""
    return _chat_complete(instruction, temperature=temperature, max_tokens=800)