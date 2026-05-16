import streamlit as st
import duckdb
import pandas as pd
import requests
import json
from datetime import datetime
import os
import random

# Configuration
OLLAMA_URL = "http://localhost:11434/api/generate"
AUDIT_LOG = "logs/audit.csv"
os.makedirs("logs", exist_ok=True)

# Page config
st.set_page_config(
    page_title="LoanIQ - AI Portfolio Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS (Modern Fintech) ---
st.markdown("""
<style>
    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global font */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8edf3 100%);
    }
    
    /* Header hero */
    .hero {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.2);
    }
    
    .hero h1 {
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin: 0;
    }
    
    .hero p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-top: 0.5rem;
    }
    
    /* Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border-left: 4px solid #667eea;
    }
    
    .metric-card h3 {
        color: #6b7280;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 0;
    }
    
    .metric-card .value {
        color: #1f2937;
        font-size: 2rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }
    
    /* Answer card */
    .answer-card {
        background: white;
        padding: 2rem;
        border-radius: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.08);
        border-left: 5px solid #10b981;
        margin: 1.5rem 0;
    }
    
    .answer-card h2 {
        color: #10b981;
        font-size: 1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin: 0 0 1rem 0;
    }
    
    .answer-card p {
        color: #1f2937;
        font-size: 1.15rem;
        line-height: 1.6;
        margin: 0;
    }
    
    /* Suggested questions */
    .question-chip {
        display: inline-block;
        background: white;
        padding: 0.75rem 1.25rem;
        border-radius: 25px;
        margin: 0.25rem;
        border: 2px solid #e5e7eb;
        color: #4b5563;
        font-size: 0.9rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .question-chip:hover {
        border-color: #667eea;
        background: #f3f4f6;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.6rem 1.5rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.2s;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Input field */
    .stTextInput > div > div > input {
        border-radius: 12px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem 1rem;
        font-size: 1rem;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: white;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Section headers */
    .section-header {
        color: #1f2937;
        font-size: 1.25rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        background: white;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# --- INIT SESSION STATE ---
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []
if "last_results" not in st.session_state:
    st.session_state.last_results = None
if "last_sql" not in st.session_state:
    st.session_state.last_sql = None
if "last_narration" not in st.session_state:
    st.session_state.last_narration = None
if "selected_question" not in st.session_state:
    st.session_state.selected_question = ""

# --- LOAD DATA ---
@st.cache_resource
def load_data():
    df = pd.read_csv("sample_data.csv")
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE loans AS SELECT * FROM df")
    return conn, df

try:
    conn, df = load_data()
except Exception as e:
    st.error(f"Data load error: {e}")
    st.stop()

# --- HERO SECTION ---
st.markdown("""
<div class="hero">
    <h1>💎 LoanIQ</h1>
    <p>AI-Powered Loan Portfolio Analytics — Ask anything in plain English</p>
</div>
""", unsafe_allow_html=True)

# --- KPI METRICS ROW ---
total_loans = len(df)
active_loans = len(df[df['status'] == 'Active'])
total_amount = df['loan_amount'].sum()
avg_rate = df['interest_rate'].mean()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>📊 Total Loans</h3>
        <div class="value">{total_loans}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h3>✅ Active</h3>
        <div class="value">{active_loans}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h3>💰 Total Value</h3>
        <div class="value">${total_amount/1e6:.1f}M</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h3>📈 Avg Rate</h3>
        <div class="value">{avg_rate:.2f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- GENERATE SQL ---
def generate_sql(question):
    schema = conn.execute("DESCRIBE loans").fetchall()
    columns = [f"{row[0]} ({row[1]})" for row in schema]
    schema_str = ", ".join(columns)
    
    prompt = f"""You are a SQL expert. Convert this question to DuckDB SQL.

Schema: loans table has columns: {schema_str}

IMPORTANT: Column values are case-sensitive. 
For the 'status' column, use 'Active', 'Paid Off', 'Defaulted' (with capital first letter).

Question: {question}

Return ONLY the SQL query, nothing else. No markdown, no explanation."""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": "mistral", "prompt": prompt, "stream": False, "temperature": 0.1},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- EXECUTE SQL ---
def execute_sql(sql):
    try:
        results = conn.execute(sql).fetchall()
        columns = [desc[0] for desc in conn.description]
        return pd.DataFrame(results, columns=columns)
    except Exception as e:
        return None

# --- NARRATE RESULTS ---
def narrate_results(question, results_df):
    csv_results = results_df.to_csv(index=False)
    
    prompt = f"""You are a finance expert. Explain these query results to a non-technical executive.
Be concise (2-3 sentences max). Don't use technical jargon.

Question: {question}
Results:
{csv_results}

Explanation:"""
    
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": "mistral", "prompt": prompt, "stream": False, "temperature": 0.3},
            timeout=60
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except Exception as e:
        return f"Could not narrate: {str(e)}"

# --- AUDIT LOG ---
def log_query(question, sql, success, error=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Success" if success else "Failed"
    error_msg = error if error else ""
    log_entry = f'{timestamp},"{question}","{sql}",{status},"{error_msg}"\n'
    
    if not os.path.exists(AUDIT_LOG):
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            f.write("timestamp,question,sql_generated,status,error\n")
    
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

# --- QUESTION INPUT ---
st.markdown('<div class="section-header">💬 Ask Your Question</div>', unsafe_allow_html=True)

# Suggested questions (clickable)

# Main input
question = st.text_input(
    "",
    value=st.session_state.selected_question,
    placeholder="e.g., Which borrowers have the highest loan amounts?",
    key="question_input_field"
)

# Update selected_question if user types
if question != st.session_state.selected_question:
    st.session_state.selected_question = question
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    ask_button = st.button("🚀 Analyze", use_container_width=True)
with col2:
    refresh_button = st.button("🔄 Refresh", use_container_width=True)
with col3:
    export_button = st.button("📥 Export", use_container_width=True)

# --- LOADING MESSAGES (Conversational) ---
LOADING_MESSAGES = [
    "🧠 Understanding your question...",
    "🔍 Analyzing the data...",
    "⚡ Crunching the numbers...",
    "📊 Preparing your insights...",
]

# --- LOGIC: ASK ---
if ask_button and question:
    loading_msg = random.choice(LOADING_MESSAGES)
    with st.spinner(loading_msg):
        sql = generate_sql(question)
        
        if "ERROR" in sql:
            st.error("❌ I couldn't understand your question. Please try rephrasing.")
            log_query(question, "FAILED", False, sql)
        else:
            results_df = execute_sql(sql)
            
            if results_df is None:
                st.error("❌ I couldn't find an answer. Try asking about loan amounts, lenders, status, or interest rates.")
                log_query(question, sql, False, "SQL execution error")
            else:
                narration = narrate_results(question, results_df)
                
                st.session_state.last_results = results_df
                st.session_state.last_sql = sql
                st.session_state.last_narration = narration
                st.session_state.conversation_history.append({
                    "question": question,
                    "sql": sql,
                    "results": results_df,
                    "narration": narration
                })
                
                log_query(question, sql, True)

# --- DISPLAY LAST ANSWER ---
if st.session_state.last_narration:
    st.markdown(f"""
    <div class="answer-card">
        <h2>💡 Answer</h2>
        <p>{st.session_state.last_narration}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show results table
    with st.expander("📊 View Detailed Results", expanded=True):
        st.dataframe(st.session_state.last_results, use_container_width=True, hide_index=True)
    
    # Show technical details
    with st.expander("🔬 How this was answered (technical details)"):
        st.markdown("**Generated SQL Query:**")
        st.code(st.session_state.last_sql, language="sql")
        st.markdown(f"**Rows returned:** {len(st.session_state.last_results)}")

# --- LOGIC: REFRESH ---
if refresh_button:
    st.cache_resource.clear()
    st.success("✅ Data refreshed!")
    st.rerun()

# --- LOGIC: EXPORT ---
if export_button and st.session_state.last_results is not None:
    csv = st.session_state.last_results.to_csv(index=False)
    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"loan_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
elif export_button:
    st.warning("⚠️ No results to export. Ask a question first.")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("### 📈 LoanIQ")
    st.markdown("*AI-Powered Portfolio Analytics*")
    st.divider()
    
    st.markdown("### 🕐 Recent Questions")
    if st.session_state.conversation_history:
        for i, item in enumerate(reversed(st.session_state.conversation_history[-3:])):
            with st.expander(f"Q: {item['question'][:35]}..."):
                st.markdown(f"**Answer:** {item['narration'][:150]}...")
    else:
        st.caption("No questions yet")
    
    st.divider()
    
    st.markdown("### 📋 Audit Log")
    if os.path.exists(AUDIT_LOG):
        try:
            audit_df = pd.read_csv(AUDIT_LOG)
            st.caption(f"📝 {len(audit_df)} queries logged")
            
            with open(AUDIT_LOG, "rb") as f:
                st.download_button(
                    label="⬇️ Download Audit Log",
                    data=f,
                    file_name="audit_log.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        except:
            st.caption("Log empty")
    else:
        st.caption("No queries logged yet")
    
    st.divider()
    st.caption("🔒 100% Offline · Powered by Mistral")