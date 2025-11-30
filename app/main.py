# app/main.py - Contextual Tutor X (Complete with Multilingual + PDF/Image)
import os
import io
import json
import time
import base64
import traceback
from pathlib import Path
from datetime import datetime
from PIL import Image
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SERPAPI_KEY = os.getenv("SERPAPI_API_KEY")

# Import your existing modules
from core.llm_client import get_llm, summarize_with_context
from core.web_search import web_search_snippets
from core.storage import memory_store
from core.tools.decomposer_tool import decompose_concept_tool
from core.tools.analogy_tool import analogy_generator_tool
from core.tools.image_tool import generate_image_bytes

# Storage paths
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "storage"
DATA_DIR.mkdir(exist_ok=True)
PROFILES_DIR = APP_DIR / "core" / "data"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_FILE = PROFILES_DIR / "sample_profiles.json"

# NEW: PDF/Image extraction
def extract_text_from_pdf(pdf_bytes):
    """Extract text from PDF bytes"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_chunks = []
        for page_num in range(min(5, doc.page_count)):  # First 5 pages
            page = doc.load_page(page_num)
            text_chunks.append(page.get_text())
        return "\n\n".join(text_chunks)
    except Exception as e:
        return f"PDF extraction failed: {str(e)[:100]}"

def extract_text_from_image(img_bytes):
    """Extract text from image using OCR"""
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img)
        return text if text.strip() else "No text found in image"
    except Exception as e:
        return f"OCR failed (install pytesseract): {str(e)[:100]}"

# NEW: Translation function
def translate_text(text: str, target_lang: str) -> str:
    """Translate text to target language"""
    if target_lang == "English" or not OPENAI_API_KEY:
        return text
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": f"Translate the following text to {target_lang}. Maintain formatting:\n\n{text}"
            }],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except:
        return text  # Fallback

# Profile management
def load_profiles():
    if PROFILES_FILE.exists():
        try:
            return json.loads(PROFILES_FILE.read_text())
        except:
            return []
    return []

def save_profile(profile):
    profiles = load_profiles()
    existing = [p for p in profiles if p.get('name') != profile.get('name')]
    existing.append(profile)
    PROFILES_FILE.write_text(json.dumps(existing, indent=2))

# Web scraping utility
def scrape_url(url: str, max_length: int = 3000) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            text = soup.get_text(separator='\n', strip=True)
            return text[:max_length]
        return ""
    except Exception as e:
        return f"Scraping error: {str(e)[:100]}"

# Main AI Agent class
class ContextualTutorAgent:
    """AI Agent with document context support"""
    
    def __init__(self):
        self.llm = get_llm(temperature=0.7)
        
    def explain_concept(self, concept: str, profile: dict = None, use_web: bool = True, 
                       doc_context: str = None, target_lang: str = "English"):
        """
        Main explanation pipeline with optional document context
        """
        result = {
            "concept": concept,
            "profile": profile,
            "timestamp": datetime.now().isoformat(),
            "steps": [],
            "language": target_lang
        }
        
        try:
            # Step 1: Web Search (if no document context)
            web_results = []
            web_context = ""
            
            if use_web and not doc_context:
                try:
                    web_results = web_search_snippets(concept, num_results=5)
                    if web_results:
                        web_context = "\n\n".join([
                            f"[{i+1}] {r['title']}\n{r['snippet']}\nSource: {r['link']}"
                            for i, r in enumerate(web_results[:3])
                        ])
                        result["steps"].append({"step": "web_search", "status": "success", "count": len(web_results)})
                    else:
                        result["steps"].append({"step": "web_search", "status": "no_results"})
                except Exception as e:
                    result["steps"].append({"step": "web_search", "status": "error", "error": str(e)[:100]})
            
            # Step 2: Use document context if provided
            if doc_context:
                web_context = f"Document Context:\n{doc_context[:3000]}"
                result["steps"].append({"step": "document_context", "status": "success"})
            
            # Step 3: Decompose concept
            atoms = []
            try:
                atoms = decompose_concept_tool(concept, max_atoms=5)
                result["atoms"] = atoms
                result["steps"].append({"step": "decomposition", "status": "success", "count": len(atoms)})
            except Exception as e:
                result["steps"].append({"step": "decomposition", "status": "error", "error": str(e)[:100]})
            
            # Step 4: Generate analogies
            analogies_text = ""
            try:
                analogies_text = analogy_generator_tool(concept, atoms, profile)
                result["analogies"] = analogies_text
                result["steps"].append({"step": "analogies", "status": "success"})
            except Exception as e:
                result["steps"].append({"step": "analogies", "status": "error", "error": str(e)[:100]})
            
            # Step 5: Synthesize final explanation
            try:
                if web_context or doc_context:
                    context_texts = [web_context, f"Atomic concepts: {', '.join(atoms)}"]
                    final_explanation = summarize_with_context(
                        prompt=f"Explain '{concept}' for a {profile.get('role', 'student')} using analogies",
                        context_texts=context_texts,
                        temperature=0.7
                    )
                else:
                    prompt = f"""Explain the concept: {concept}

Atomic concepts: {', '.join(atoms)}

User profile: {json.dumps(profile) if profile else 'General audience'}

Provide:
1. Clear summary (2-3 sentences)
2. Key insights (3-4 points)
3. Practical applications
4. Learning roadmap (4 steps)
5. Confidence score (0-100)

Keep it educational and engaging."""
                    
                    final_explanation = self.llm(prompt)
                
                # NEW: Translate if needed
                if target_lang != "English":
                    final_explanation = translate_text(final_explanation, target_lang)
                    analogies_text = translate_text(analogies_text, target_lang)
                    result["steps"].append({"step": "translation", "status": "success", "language": target_lang})
                
                result["explanation"] = final_explanation
                result["analogies"] = analogies_text
                result["steps"].append({"step": "synthesis", "status": "success"})
                
            except Exception as e:
                result["explanation"] = f"Synthesis error: {str(e)[:200]}"
                result["steps"].append({"step": "synthesis", "status": "error", "error": str(e)[:100]})
            
            # Add sources
            if web_results:
                result["sources"] = [{"title": r['title'], "url": r['link']} for r in web_results[:5]]
            
            result["confidence"] = self._calculate_confidence(result)
            
            return result
            
        except Exception as e:
            result["error"] = str(e)
            result["traceback"] = traceback.format_exc()
            return result
    
    def _calculate_confidence(self, result: dict) -> int:
        total_steps = len(result.get("steps", []))
        successful = len([s for s in result.get("steps", []) if s.get("status") == "success"])
        
        if total_steps == 0:
            return 30
        
        base_score = (successful / total_steps) * 70
        
        if result.get("sources"):
            base_score += 15
        
        if result.get("analogies"):
            base_score += 15
        
        return min(100, int(base_score))

# Image generation
def generate_diagram(concept: str, size: str = "1024x1024"):
    try:
        if not OPENAI_API_KEY:
            return None, "No API key"
        
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        prompt = f"Educational infographic explaining '{concept}'. Modern, clean design with diagrams, labels, and icons. Professional style."
        
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1
        )
        
        return response.data[0].url, "success"
        
    except Exception as e:
        return None, str(e)[:200]

# Enhanced CSS (same as before)
ENHANCED_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
:root {
    --bg-primary: #0a0e27;
    --bg-secondary: #131937;
    --accent-cyan: #00f5ff;
    --accent-purple: #b857ff;
    --text-primary: #e0e6f0;
    --text-secondary: #9ca3af;
}
* { font-family: 'Inter', sans-serif; }
body { background: var(--bg-primary) !important; color: var(--text-primary) !important; }
.stApp { background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0a0e27 100%); }
h1 { font-weight: 800; font-size: 3em; background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; margin: 20px 0;
    text-shadow: 0 0 40px rgba(0, 245, 255, 0.3); animation: glow 2s ease-in-out infinite alternate; }
@keyframes glow {
    from { filter: drop-shadow(0 0 20px rgba(0, 245, 255, 0.4)); }
    to { filter: drop-shadow(0 0 30px rgba(184, 87, 255, 0.4)); }
}
.glass-panel { background: rgba(19, 25, 55, 0.7); backdrop-filter: blur(20px); border: 1px solid rgba(0, 245, 255, 0.2);
    border-radius: 20px; padding: 25px; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.1);
    margin: 15px 0; }
.tool-badge { display: inline-block; padding: 8px 16px; margin: 5px; border-radius: 25px; font-size: 13px; font-weight: 600;
    background: linear-gradient(135deg, rgba(0, 245, 255, 0.15), rgba(184, 87, 255, 0.15));
    border: 1px solid rgba(0, 245, 255, 0.3); transition: all 0.3s ease; }
.tool-badge:hover { transform: translateY(-2px); box-shadow: 0 5px 20px rgba(0, 245, 255, 0.4); }
.status-success { color: #00ff88; font-weight: 700; }
.status-error { color: #ff4466; font-weight: 700; }
.stButton > button { background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple)) !important;
    color: white !important; border: none !important; border-radius: 12px !important; padding: 12px 28px !important;
    font-weight: 700 !important; font-size: 15px !important; transition: all 0.3s ease !important;
    box-shadow: 0 4px 20px rgba(0, 245, 255, 0.3) !important; }
.stButton > button:hover { transform: translateY(-3px) !important; box-shadow: 0 8px 30px rgba(0, 245, 255, 0.5) !important; }
.output-card { background: rgba(19, 25, 55, 0.5); border-left: 3px solid var(--accent-cyan); padding: 20px;
    margin: 15px 0; border-radius: 12px; animation: slideIn 0.5s ease-out; }
@keyframes slideIn { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
.citation { color: var(--accent-cyan); font-size: 12px; font-style: italic; opacity: 0.8; }
.metric-card { background: linear-gradient(135deg, rgba(0, 245, 255, 0.1), rgba(184, 87, 255, 0.1));
    padding: 15px; border-radius: 12px; text-align: center; border: 1px solid rgba(0, 245, 255, 0.2); }
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: rgba(19, 25, 55, 0.6) !important; border: 1px solid rgba(0, 245, 255, 0.3) !important;
    color: var(--text-primary) !important; border-radius: 10px !important; }
.stSelectbox > div > div { background: rgba(19, 25, 55, 0.6) !important; border: 1px solid rgba(0, 245, 255, 0.3) !important;
    border-radius: 10px !important; }
.upload-notice { background: rgba(0, 245, 255, 0.1); padding: 10px; border-radius: 8px; border: 1px solid rgba(0, 245, 255, 0.3);
    margin: 10px 0; }
</style>
"""

def main():
    st.set_page_config(
        page_title="Contextual Tutor X - AI Agent",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.markdown(ENHANCED_CSS, unsafe_allow_html=True)
    
    # Initialize session state
    if "agent" not in st.session_state:
        st.session_state.agent = ContextualTutorAgent()
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_profile" not in st.session_state:
        st.session_state.current_profile = {}
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "uploaded_doc_text" not in st.session_state:
        st.session_state.uploaded_doc_text = None
    if "uploaded_filename" not in st.session_state:
        st.session_state.uploaded_filename = None
    
    # Header
    st.markdown("""
    <div class='glass-panel'>
        <h1>⚡ Contextual Tutor X</h1>
        <p style='text-align:center; font-size:1.3em; color:#00f5ff; font-weight:600;'>
            LangChain AI Agent • Multilingual • Document Chat • Learn with Context • Web-Enhanced Ans.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🛠️ Agent Tools Status")
        
        tools_status = {
            "🌐 Web Search": bool(web_search_snippets),
            "🤖 OpenAI GPT": bool(OPENAI_API_KEY),
            "🎨 DALL-E": bool(OPENAI_API_KEY),
            "🧠 Decomposer": True,
            "💡 Analogy Gen": True,
            "📄 PDF/Image": True,
            "🌍 Multilingual": bool(OPENAI_API_KEY),
        }
        
        for tool, available in tools_status.items():
            status_class = "status-success" if available else "status-error"
            icon = "✅" if available else "❌"
            st.markdown(f"<div class='tool-badge'>{tool} <span class='{status_class}'>{icon}</span></div>", unsafe_allow_html=True)
        
        st.markdown("---")
        
        # NEW: Language Selection
        st.markdown("### 🌍 Language")
        languages = ["English", "Hindi", "Spanish", "French", "German", "Japanese", "Chinese", "Arabic", "Russian", "Portuguese"]
        selected_lang = st.selectbox("Response Language", languages, key="language_selector")
        
        st.markdown("---")
        
        # NEW: Document Upload
        st.markdown("### 📄 Upload Document")
        uploaded_file = st.file_uploader("PDF or Image", type=["pdf", "png", "jpg", "jpeg"], key="doc_uploader")
        
        if uploaded_file:
            file_bytes = uploaded_file.read()
            file_type = uploaded_file.type
            
            with st.spinner("Extracting text..."):
                if "pdf" in file_type:
                    extracted_text = extract_text_from_pdf(file_bytes)
                else:
                    extracted_text = extract_text_from_image(file_bytes)
                
                st.session_state.uploaded_doc_text = extracted_text
                st.session_state.uploaded_filename = uploaded_file.name
                
                st.success(f"✅ Loaded: {uploaded_file.name}")
                with st.expander("Preview Text"):
                    st.text(extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text)
        
        if st.session_state.uploaded_doc_text:
            st.markdown(f"<div class='upload-notice'>📄 Document active: {st.session_state.uploaded_filename}</div>", unsafe_allow_html=True)
            if st.button("🗑️ Clear Document"):
                st.session_state.uploaded_doc_text = None
                st.session_state.uploaded_filename = None
                st.rerun()
        
        st.markdown("---")
        
        # Profile Management
        st.markdown("### 👤 User Profile")
        with st.expander("📝 Manage Profile", expanded=False):
            profiles = load_profiles()
            
            if profiles:
                profile_names = ["Create New"] + [p.get('name', 'Unnamed') for p in profiles]
                selected_profile_name = st.selectbox("Select Profile", profile_names, key="profile_selector")
                
                if selected_profile_name != "Create New":
                    idx = profile_names.index(selected_profile_name) - 1
                    st.session_state.current_profile = profiles[idx]
                    st.success(f"✅ Loaded: {selected_profile_name}")
            
            name = st.text_input("Name", value=st.session_state.current_profile.get('name', ''))
            age_group = st.selectbox("Age Group", ["10-15", "16-22", "23-30", "30+"])
            role = st.selectbox("Role", ["Student", "Engineer", "Teacher", "Researcher", "Professional"])
            interests = st.text_input("Interests", value=st.session_state.current_profile.get('interests', 'technology'))
            
            if st.button("💾 Save Profile", use_container_width=True):
                new_profile = {
                    "name": name,
                    "age_group": age_group,
                    "role": role,
                    "interests": interests,
                    "created_at": datetime.now().isoformat()
                }
                save_profile(new_profile)
                st.session_state.current_profile = new_profile
                st.success("✅ Profile saved!")
                st.rerun()
        
        st.markdown("---")
        
        # Session History
        st.markdown("### 📚 Recent Sessions")
        sessions = memory_store.list_sessions()[:5]
        
        if sessions:
            for i, session in enumerate(sessions):
                with st.expander(f"📝 {session.get('concept_preview', 'Session')[:35]}..."):
                    st.caption(f"🕐 {session.get('ts', 'N/A')}")
                    if st.button(f"Load", key=f"load_session_{i}"):
                        st.session_state.last_result = session
                        st.rerun()
        else:
            st.info("No sessions yet")
        
        if st.button("🗑️ Clear All History", use_container_width=True):
            memory_store.clear_sessions()
            st.session_state.chat_history = []
            st.success("✅ History cleared!")
            st.rerun()
    
    # Main Content
    col_main, col_actions = st.columns([2, 1])
    
    with col_main:
        st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
        st.markdown("### 💬 Chat with AI Agent")
        
        # Show document context notice
        if st.session_state.uploaded_doc_text:
            st.info(f"📄 Chatting with document: **{st.session_state.uploaded_filename}**")
        
        # Display chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Chat input
        if user_input := st.chat_input("Ask me anything..."):
            if not OPENAI_API_KEY:
                st.error("⚠️ Set OPENAI_API_KEY in .env")
                st.stop()
            
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            with st.chat_message("user"):
                st.markdown(user_input)
            
            # Process with agent
            with st.chat_message("assistant"):
                with st.spinner("🔍 Processing..."):
                    try:
                        result = st.session_state.agent.explain_concept(
                            concept=user_input,
                            profile=st.session_state.current_profile,
                            use_web=not st.session_state.uploaded_doc_text,
                            doc_context=st.session_state.uploaded_doc_text,
                            target_lang=selected_lang
                        )
                        
                        # Format response
                        response_md = f"""
**Concept:** {result.get('concept', 'N/A')}
**Language:** {result.get('language', 'English')}

**Summary:**
{result.get('explanation', 'No explanation')}

**Atomic Concepts:**
{chr(10).join(['• ' + atom for atom in result.get('atoms', [])])}

**Analogies:**
{result.get('analogies', 'No analogies')}

**Sources:**
{chr(10).join([f"• [{s['title']}]({s['url']})" for s in result.get('sources', [])])}

**Confidence:** {result.get('confidence', 0)}%
"""
                        
                        st.markdown(response_md)
                        
                        st.session_state.chat_history.append({"role": "assistant", "content": response_md})
                        st.session_state.last_result = result
                        
                        memory_store.add_session({
                            "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "concept_preview": user_input[:100],
                            "result": response_md,
                            "confidence": result.get('confidence', 0)
                        })
                        
                    except Exception as e:
                        error_msg = f"❌ Error: {str(e)}\n\n{traceback.format_exc()}"
                        st.error(error_msg)
                        st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col_actions:
        st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
        st.markdown("### 🎯 Quick Actions")
        
        quick_concept = st.text_area("Enter Concept", height=100, placeholder="e.g., quantum physics...")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("⚡ Explain", use_container_width=True):
                if quick_concept.strip():
                    with st.spinner("Analyzing..."):
                        result = st.session_state.agent.explain_concept(
                            quick_concept, 
                            st.session_state.current_profile,
                            doc_context=st.session_state.uploaded_doc_text,
                            target_lang=selected_lang
                        )
                        st.session_state.last_result = result
                        st.rerun()
        
        with col_btn2:
            if st.button("🌐 Search", use_container_width=True):
                if quick_concept.strip():
                    with st.spinner("Searching..."):
                        results = web_search_snippets(quick_concept, 5)
                        for r in results:
                            st.markdown(f"**{r['title']}**")
                            st.caption(r['snippet'][:120] + "...")
                            st.markdown(f"[🔗]({r['link']})")
        
        if st.button("🧠 Decompose", use_container_width=True):
            if quick_concept.strip():
                atoms = decompose_concept_tool(quick_concept, 5)
                st.markdown("**Atomic Ideas:**")
                for atom in atoms:
                    st.markdown(f"• {atom}")
        
        if st.button("💡 Analogies", use_container_width=True):
            if quick_concept.strip():
                analogies = analogy_generator_tool(quick_concept, None, st.session_state.current_profile)
                translated = translate_text(analogies, selected_lang) if selected_lang != "English" else analogies
                st.markdown(translated)
        
        if st.button("🎨 Generate Diagram", use_container_width=True):
            if quick_concept.strip() and OPENAI_API_KEY:
                with st.spinner("Creating..."):
                    img_url, status = generate_diagram(quick_concept)
                    if img_url:
                        st.image(img_url, caption=f"Diagram: {quick_concept}")
                        st.markdown(f"[📥 Download]({img_url})")
                    else:
                        st.error(f"Failed: {status}")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Metrics
        if st.session_state.last_result:
            st.markdown("<div class='glass-panel'>", unsafe_allow_html=True)
            st.markdown("### 📊 Last Result")
            
            result = st.session_state.last_result
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                <div class='metric-card'>
                    <h2 style='color: #00f5ff;'>{result.get('confidence', 0)}%</h2>
                    <p>Confidence</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                sources_count = len(result.get('sources', []))
                st.markdown(f"""
                <div class='metric-card'>
                    <h2 style='color: #b857ff;'>{sources_count}</h2>
                    <p>Sources</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()