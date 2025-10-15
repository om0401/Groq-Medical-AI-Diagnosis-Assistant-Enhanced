# Groq-Medical-AI-Enhanced

Local project to run a multi-agent, multimodal medical assistant using Groq models.

## Setup (Windows / macOS / Linux)

1. Create and activate a virtual environment:
   - python -m venv .venv
   - Windows: .\.venv\Scripts\Activate.ps1
   - macOS/Linux: source .venv/bin/activate

2. Install dependencies:
pip install -r requirements.txt


3. Copy `.env.example` to `.env` and put your Groq key:


GROQ_API_KEY=gsk_...
GROQ_API_BASE=https://api.groq.com/openai/v1


4. Run the app from the **project root**:


streamlit run webapp/app.py


## Notes
- If you don't have a GROQ key, the app runs in **simulated mode** for development.
- To test real Groq calls, ensure your key is active and your account has access to the models you try.

Final checks & tips

Run from project root (very important):

cd path/to/Groq-Medical-AI-Enhanced
streamlit run webapp/app.py


If you hit ModuleNotFoundError for agents or utils, ensure the top-of-file sys.path insertion is present in webapp/app.py (I included it).

If Groq returns 401 Invalid API Key:

Verify .env contains the correct key and the process is loading it (I used dotenv.load_dotenv()).

Test with the one-line PowerShell or the debug_groq.py test (previous messages included those).

If Groq returns model_not_found, list models available to your key:

# create a script that hits GET https://api.groq.com/openai/v1/models with Authorization header


To implement live partial streaming (per-agent partial results), say "partial streaming" and I'll provide the background-thread/session_state implementation for Streamlit.
