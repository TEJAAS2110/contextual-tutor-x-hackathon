# app/core/tools/decomposer_tool.py
"""
Decomposer tool - FIXED VERSION
"""
from typing import List
import json
import os

def decompose_concept_tool(concept: str, max_atoms: int = 5) -> List[str]:
    """Break concept into atomic sub-concepts"""
    if not concept or not concept.strip():
        return []
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        # Fallback: simple split
        return [s.strip() for s in concept.split(',')[:max_atoms] if s.strip()]
    
    prompt = f"""
You are a concise educational assistant.
Break the following concept into {max_atoms} short atomic sub-concepts (4-8 words each).
Return output as a valid JSON array of strings ONLY.

Concept:
\"\"\"{concept.strip()}\"\"\"
"""
    
    try:
        # Try new OpenAI SDK
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=300
            )
            out = response.choices[0].message.content
        except:
            # Try old SDK
            import openai
            openai.api_key = OPENAI_API_KEY
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=300
            )
            out = response.choices[0].message.content
        
        # Try parse JSON
        try:
            parsed = json.loads(out)
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()][:max_atoms]
        except:
            # Extract from text
            atoms = []
            for line in out.splitlines():
                line = line.strip()
                if not line:
                    continue
                # Remove numbering and bullets
                if line[0].isdigit():
                    parts = line.split(".", 1)
                    if len(parts) > 1:
                        atoms.append(parts[1].strip())
                        continue
                if line.startswith("-"):
                    atoms.append(line.lstrip("- ").strip())
                    continue
                atoms.append(line)
            return atoms[:max_atoms] if atoms else [concept]
    except Exception as e:
        # Final fallback
        return [s.strip() for s in concept.split(',')[:max_atoms] if s.strip()] or [concept]