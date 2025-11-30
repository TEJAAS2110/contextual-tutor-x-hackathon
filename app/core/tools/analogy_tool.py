# app/core/tools/analogy_tool.py
"""
Analogy generator tool - FIXED VERSION
"""
from typing import Optional, List
import textwrap

def analogy_generator_tool(concept: str, atoms: Optional[List[str]] = None, profile: Optional[dict] = None) -> str:
    """Generate analogies using simple OpenAI call"""
    if not concept:
        return "No concept provided."
    
    import os
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    if not OPENAI_API_KEY:
        return "⚠️ OPENAI_API_KEY not set"
    
    atoms_text = "\n".join(f"- {a}" for a in (atoms or [])) if atoms else "(no atoms)"
    profile_text = ""
    if profile:
        pf = {k: v for k, v in profile.items() if k in ("name", "age_group", "role", "interests")}
        profile_text = f"User profile: {pf}"
    
    prompt = textwrap.dedent(f"""
    You are a friendly tutor that explains difficult topics using relatable analogies.
    {profile_text}
    
    Concept: {concept.strip()}
    
    Key atoms:
    {atoms_text}
    
    Produce EXACTLY three analogies with short mappings:
    
    Analogy 1 (Story): <2-4 sentences>
    Mapping 1: <one line mapping>
    
    Analogy 2 (Visual): <2-4 sentences>
    Mapping 2: <one line mapping>
    
    Analogy 3 (Practical): <2-4 sentences>
    Mapping 3: <one line mapping>
    
    Keep overall length concise and easy to read.
    """)
    
    try:
        # Try new OpenAI SDK (>=1.0)
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600
            )
            return response.choices[0].message.content
        except:
            # Try old OpenAI SDK (<1.0)
            import openai
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=600
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"❌ Analogy generation failed: {str(e)[:200]}"