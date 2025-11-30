# app/core/analogy_agent.py
"""
Self-contained analogy agent runner.

This file intentionally does NOT rely on langchain's initialize_agent,
so it should work regardless of langchain version.

It uses the get_llm() wrapper in core/llm_client.py and provides:
- decompose_concept(concept) -> list[str]
- generate_analogies(concept, atoms, profile) -> str (human-friendly output)
- run_agent(concept, profile=None) -> str

The functions try several common call styles (invoke, __call__, generate)
to be robust across langchain/openai wrappers.
"""
from typing import List, Optional
from core.llm_client import get_llm
import json
import textwrap

# Helper to call the LLM in a few possible ways (robust wrapper)
def _call_llm(llm, prompt: str, max_retries: int = 2) -> str:
    """
    Call the llm with different APIs depending on what's available.
    Returns plain text result.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            # preferred: llm.invoke(prompt)
            if hasattr(llm, "invoke"):
                out = llm.invoke(prompt)
                # some wrappers return object with .content
                return getattr(out, "content", str(out)).strip()
        except Exception as e:
            last_exc = e
        try:
            # next: llm(prompt)
            out = llm(prompt)
            return getattr(out, "content", str(out)).strip()
        except Exception as e:
            last_exc = e
        try:
            # final: llm.generate([prompt])
            gen = llm.generate([prompt])
            # try to pick text safely
            if hasattr(gen, "generations") and gen.generations:
                cand = gen.generations[0][0]
                # cand may have .text or .content
                return getattr(cand, "text", getattr(cand, "content", str(cand))).strip()
            return str(gen)
        except Exception as e:
            last_exc = e
    # if all failed, raise the last exception so caller can inspect
    raise last_exc if last_exc else RuntimeError("LLM call failed without exception.")


def decompose_concept(concept: str, max_atoms: int = 5) -> List[str]:
    """
    Use the LLM to return a short list of atomic sub-concepts (strings).
    Returns a python list of strings.
    """
    llm = get_llm(temperature=0.0)
    prompt = f"""You are a helpful tutor. Break this concept into {max_atoms} short, atomic ideas
(bulleted, each 4-8 words). Return only a JSON array of strings.

Concept:
\"\"\"{concept.strip()}\"\"\"
"""
    out = _call_llm(llm, prompt)
    # try to parse JSON from the output, else heuristically split bullets
    atoms = []
    try:
        # accept outputs that are like: ["a","b",...]
        parsed = json.loads(out)
        if isinstance(parsed, list):
            atoms = [str(x).strip() for x in parsed if str(x).strip()]
            return atoms
    except Exception:
        pass

    # fallback: extract lines starting with - or numbers or split by newline
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # remove leading bullet characters
        if line.startswith("-") or line[0].isdigit():
            # remove leading "- " or "1. "
            parts = line.lstrip("- ").split(".", 1)
            candidate = parts[-1].strip()
            if candidate:
                atoms.append(candidate)
        else:
            atoms.append(line)
    # if still empty, split concept into comma chunks
    if not atoms:
        atoms = [s.strip() for s in concept.split(",") if s.strip()]
    # truncate to max_atoms
    return atoms[:max_atoms]


def generate_analogies(concept: str, atoms: List[str], profile: Optional[dict] = None) -> str:
    """
    Generate a set of analogies tailored to the profile.
    Returns human-readable multi-paragraph string.
    """
    llm = get_llm(temperature=0.6)
    profile_text = ""
    if profile:
        # keep profile short
        profile_text = json.dumps(profile, ensure_ascii=False)
    atom_list_text = "\n".join(f"- {a}" for a in atoms) if atoms else "N/A"

    prompt = textwrap.dedent(
        f"""
        You are a creative tutor. Produce 3 analogies for the following concept.
        Use the user's profile to tailor tone and examples.

        Profile: {profile_text}
        Concept: {concept.strip()}
        Key idea atoms:
        {atom_list_text}

        Produce EXACTLY three labeled analogies: 1) Story analogy (2-4 sentences),
        2) Visual analogy (2-4 sentences), 3) Hobby analogy (2-4 sentences).
        After each analogy, include a one-line "mapping" that explains which part of the concept
        maps to which element of the analogy.

        Output format (plain text):
        Analogy 1: ...
        Mapping 1: ...
        Analogy 2: ...
        Mapping 2: ...
        Analogy 3: ...
        Mapping 3: ...
        """
    ).strip()

    out = _call_llm(llm, prompt)
    return out


def run_agent(concept: str, profile: Optional[dict] = None) -> str:
    """
    High-level runner: decompose -> generate analogies -> assemble pretty result.
    Returns a string suitable for display.
    """
    # input validation
    if not concept or not concept.strip():
        return "No concept provided."

    # Step 1: decompose
    try:
        atoms = decompose_concept(concept)
    except Exception as e:
        atoms = []
        # we will continue but include the error info
        decomp_err = f" (decompose failed: {e})"
    else:
        decomp_err = ""

    # Step 2: generate analogies
    try:
        analogies_text = generate_analogies(concept, atoms, profile=profile)
    except Exception as e:
        analogies_text = f"Analogy generation failed: {e}"

    # Assemble a clean, readable result
    atoms_block = "\n".join(f"- {a}" for a in atoms) if atoms else "- (no decomposition available)"
    header = f"Concept: {concept.strip()}\n\nAtomic ideas:\n{atoms_block}{decomp_err}\n\n"
    result = header + "Analogies & mappings:\n\n" + analogies_text
    return result
