"""
Deal History Page - Natural Language Query Interface for Deal Analysis
"""
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import json
from typing import Dict, Any, List

from utils.config import config
from utils.logging import get_logger
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

logger = get_logger("deal_history_page")

st.set_page_config(
    page_title="Deal History - LiquidRound",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .query-result {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
        font-family: 'Courier New', monospace;
    }
    .result-table {
        margin-top: 1rem;
    }
    .data-info {
        background-color: #e9ecef;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def get_database_schema() -> Dict[str, List[str]]:
    """Get the database schema information."""
    db_path = Path("db/liquidround.db")
    
    if not db_path.exists():
        return {}
    
    schema = {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for table in tables:
                table_name = table[0]
                
                # Get column information for each table
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                
                schema[table_name] = [
                    f"{col[1]} ({col[2]})" + (" PRIMARY KEY" if col[5] else "") + (" NOT NULL" if col[3] else "")
                    for col in columns
                ]
    
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        st.error(f"Error accessing database: {e}")
    
    return schema

def execute_sql_query(query: str) -> pd.DataFrame:
    """Execute SQL query and return results as DataFrame."""
    db_path = Path("db/liquidround.db")
    
    if not db_path.exists():
        st.error("Database not found. Please run some workflows first to create data.")
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query(query, conn)
            return df
    
    except Exception as e:
        logger.error(f"SQL execution error: {e}")
        st.error(f"SQL Error: {e}")
        return pd.DataFrame()

def generate_sql_from_text(user_question: str, schema: Dict[str, List[str]]) -> str:
    """Generate SQL query from natural language using LLM."""
    
    # Create schema description
    schema_description = ""
    for table, columns in schema.items():
        schema_description += f"\nTable: {table}\n"
        for column in columns:
            schema_description += f"  - {column}\n"
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", """You are a SQL expert. Generate SQLite queries based on user questions about M&A and IPO deal data.

Database Schema:
{schema}

Important Notes:
- Use SQLite syntax
- Always use proper table and column names from the schema
- For date comparisons, use string comparisons with ISO format dates
- Use LIKE for text searches with % wildcards
- Return only the SQL query, no explanations
- Use appropriate JOINs when querying multiple tables
- For aggregations, use GROUP BY appropriately

Common Query Patterns:
- Active deals: WHERE status IN ('pending', 'active')
- Recent deals: WHERE created_at >= date('now', '-30 days')
- Deal value ranges: WHERE deal_size_min <= X AND deal_size_max >= Y
- Industry filtering: WHERE industry = 'Technology'
"""),
        ("user", "{question}")
    ])
    
    try:
        llm = ChatOpenAI(
            model=config.default_model,
            temperature=0.1,
            api_key=config.openai_api_key
        )
        
        chain = prompt_template | llm
        
        response = chain.invoke({
            "schema": schema_description,
            "question": user_question
        })
        
        # Extract SQL from response
        sql_query = response.content.strip()
        
        # Remove markdown formatting if present
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        
        return sql_query.strip()
    
    except Exception as e:
        logger.error(f"Error processing search: {e}")
        st.error(f"Error processing search: {e}")
        return ""

def main():
    """Main function for Deal History page."""
    
    st.title("📈 Deal History & Analytics")
    st.markdown("Search and analyze deal data using natural language questions")
    
    # Get database schema
    schema = get_database_schema()
    
    if not schema:
        st.warning("No database found or database is empty. Run some workflows first to generate data.")
        return
    
    # Display data structure information
    with st.expander("📋 Available Data", expanded=False):
        st.markdown('<div class="data-info">', unsafe_allow_html=True)
        
        for table, columns in schema.items():
            st.subheader(f"Table: {table}")
            for column in columns:
                st.text(f"  • {column}")
            st.markdown("---")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Query interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔍 Search & Analytics")
        
        # Suggested questions
        st.markdown("**Suggested Questions:**")
        suggested_questions = [
            "Show all active deals",
            "What are the top 5 deals by maximum valuation?",
            "Show deals in the technology industry",
            "List all companies with market cap over $1 billion",
            "Show recent workflows from the last 7 days",
            "What's the average strategic fit score for acquisition targets?",
            "Show deals with their target companies and valuations"
        ]
        
        for i, question in enumerate(suggested_questions):
            if st.button(question, key=f"suggested_{i}"):
                st.session_state.user_question = question
        
        # Text input for custom questions
        user_question = st.text_area(
            "Ask a question about the deal data:",
            value=st.session_state.get("user_question", ""),
            height=100,
            placeholder="e.g., Show me all deals in healthcare with valuations over $100M"
        )
        
        if st.button("🔍 Search Deal Data", type="primary"):
            if user_question:
                with st.spinner("Searching deal data..."):
                    sql_query = generate_sql_from_text(user_question, schema)
                    
                    if sql_query:
                        st.session_state.generated_sql = sql_query
                        st.session_state.user_question = user_question
                        st.rerun()
    
    with col2:
        st.subheader("⚙️ Search Options")
        
        # Query execution options
        limit_results = st.checkbox("Limit results", value=True)
        result_limit = st.number_input("Max rows", min_value=1, max_value=1000, value=100) if limit_results else None
        
        show_query = st.checkbox("Show technical details", value=False)
        
        # Export options
        st.markdown("**Export Options:**")
        export_format = st.selectbox("Format", ["CSV", "JSON", "Excel"])
    
    # Display and execute search
    if "generated_sql" in st.session_state:
        st.subheader("📊 Search Results")
        
        sql_query = st.session_state.generated_sql
        
        if show_query:
            st.markdown("**Technical Query Details:**")
            st.markdown(f'<div class="query-result">{sql_query}</div>', unsafe_allow_html=True)
        
        # Allow manual editing for advanced users
        if show_query:
            edited_sql = st.text_area(
                "Advanced: Edit query if needed:",
                value=sql_query,
                height=150,
                key="sql_editor"
            )
        else:
            edited_sql = sql_query
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("▶️ Get Results", type="primary"):
                final_sql = edited_sql
                
                # Add LIMIT if requested
                if limit_results and result_limit and "LIMIT" not in final_sql.upper():
                    final_sql += f" LIMIT {result_limit}"
                
                with st.spinner("Retrieving data..."):
                    df = execute_sql_query(final_sql)
                    
                    if not df.empty:
                        st.session_state.query_results = df
                        st.session_state.last_sql = final_sql
                        st.success(f"Search completed! Found {len(df)} results.")
                    else:
                        st.info("Search completed but no matching deals found.")
        
        with col2:
            if st.button("🗑️ Clear"):
                for key in ["generated_sql", "query_results", "user_question", "last_sql"]:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    # Display results
    if "query_results" in st.session_state:
        st.subheader("📊 Query Results")
        
        df = st.session_state.query_results
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            if "last_sql" in st.session_state:
                st.metric("Query Length", len(st.session_state.last_sql))
        
        # Display data
        st.dataframe(df, use_container_width=True)
        
        # Export functionality
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if export_format == "CSV":
                    csv = df.to_csv(index=False)
                    st.download_button(
                        "📥 Download CSV",
                        csv,
                        "query_results.csv",
                        "text/csv"
                    )
            
            with col2:
                if export_format == "JSON":
                    json_str = df.to_json(orient="records", indent=2)
                    st.download_button(
                        "📥 Download JSON",
                        json_str,
                        "query_results.json",
                        "application/json"
                    )
            
            with col3:
                if export_format == "Excel":
                    # Note: This would require openpyxl
                    st.info("Excel export requires openpyxl package")
    
    # Sample searches section
    with st.expander("💡 Sample Searches", expanded=False):
        sample_queries = {
            "Active Deals Overview": """
SELECT 
    id,
    deal_type,
    company_name,
    industry,
    status,
    created_at
FROM deals 
WHERE status IN ('pending', 'active')
ORDER BY created_at DESC;
            """,
            
            "Deal Valuations Summary": """
SELECT 
    d.company_name,
    d.deal_type,
    v.valuation_method,
    v.valuation_amount,
    v.confidence_level
FROM deals d
JOIN valuations v ON d.id = v.deal_id
ORDER BY v.valuation_amount DESC;
            """,
            
            "Top Strategic Targets": """
SELECT 
    c.name as company_name,
    c.industry,
    c.market_cap,
    dt.strategic_fit_score,
    dt.valuation_high
FROM companies c
JOIN deal_targets dt ON c.id = dt.company_id
WHERE dt.target_type = 'acquisition_target'
ORDER BY dt.strategic_fit_score DESC, dt.valuation_high DESC;
            """,
            
            "Workflow Performance": """
SELECT 
    workflow_type,
    status,
    COUNT(*) as count,
    AVG(julianday('now') - julianday(created_at)) as avg_age_days
FROM workflows
GROUP BY workflow_type, status
ORDER BY workflow_type, status;
            """
        }
        
        for title, query in sample_queries.items():
            st.subheader(title)
            if show_query:
                st.code(query, language="sql")
            
            if st.button(f"Run {title}", key=f"sample_{title}"):
                with st.spinner(f"Getting {title.lower()}..."):
                    df = execute_sql_query(query)
                    if not df.empty:
                        st.dataframe(df)
                    else:
                        st.info("No results found")

if __name__ == "__main__":
    main()
