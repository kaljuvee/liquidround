"""
LiquidRound - Multi-Agent M&A and IPO Deal Flow System
Main Streamlit Application
"""
import streamlit as st
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workflow import workflow_instance
from utils.logging import get_logger
from utils.config import config

# Configure page
st.set_page_config(
    page_title="LiquidRound - Deal Flow System",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

logger = get_logger("streamlit_app")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    .company-name {
        color: #1f77b4;
        font-size: 1.2rem;
        font-weight: 600;
    }
    .suggested-query {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 0.75rem;
        margin: 0.5rem 0;
        cursor: pointer;
        transition: background-color 0.2s;
    }
    .suggested-query:hover {
        background-color: #e9ecef;
    }
    .agent-result {
        border: 1px solid #dee2e6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
    }
    .status-success {
        color: #28a745;
    }
    .status-error {
        color: #dc3545;
    }
    .status-progress {
        color: #ffc107;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application function."""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>💼 LiquidRound</h1>
        <p class="company-name">Lohusalu Capital Management</p>
        <p>Multi-Agent M&A and IPO Deal Flow System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "workflow_state" not in st.session_state:
        st.session_state.workflow_state = None
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Sidebar
    with st.sidebar:
        st.header("🎯 Deal Flow Assistant")
        
        # Mode selection (informational)
        st.subheader("Workflow Types")
        st.info("""
        **Buyer-Led M&A**: Find and analyze acquisition targets
        
        **Seller-Led M&A**: Prepare for sale and find buyers
        
        **IPO**: Assess readiness and plan public offering
        """)
        
        # Suggested queries
        st.subheader("💡 Suggested Queries")
        
        buyer_queries = [
            "Find fintech acquisition targets with $10-50M revenue",
            "Looking to acquire a SaaS company in healthcare",
            "Identify AI/ML startups for strategic acquisition",
            "Find manufacturing companies in the Midwest for acquisition"
        ]
        
        seller_queries = [
            "Preparing to sell our B2B software company",
            "Need help finding buyers for our logistics business",
            "Planning to divest our retail division",
            "Looking for strategic buyers in the energy sector"
        ]
        
        ipo_queries = [
            "Assessing IPO readiness for our tech company",
            "Planning to go public in the next 18 months",
            "Need help selecting underwriters for IPO",
            "Evaluating public market timing for our offering"
        ]
        
        st.markdown("**Buyer-Led M&A:**")
        for query in buyer_queries:
            if st.button(query, key=f"buyer_{hash(query)}", help="Click to use this query"):
                st.session_state.suggested_query = query
                st.rerun()
        
        st.markdown("**Seller-Led M&A:**")
        for query in seller_queries:
            if st.button(query, key=f"seller_{hash(query)}", help="Click to use this query"):
                st.session_state.suggested_query = query
                st.rerun()
        
        st.markdown("**IPO:**")
        for query in ipo_queries:
            if st.button(query, key=f"ipo_{hash(query)}", help="Click to use this query"):
                st.session_state.suggested_query = query
                st.rerun()
        
        # Clear conversation
        if st.button("🗑️ Clear Conversation"):
            st.session_state.messages = []
            st.session_state.workflow_state = None
            st.session_state.thread_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            st.rerun()
    
    # Main chat interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("💬 Deal Flow Chat")
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        query = st.chat_input("Describe your M&A or IPO requirements...")
        
        # Handle suggested query
        if "suggested_query" in st.session_state:
            query = st.session_state.suggested_query
            del st.session_state.suggested_query
        
        # Process user input
        if query:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": query})
            
            with st.chat_message("user"):
                st.markdown(query)
            
            # Process with workflow
            with st.chat_message("assistant"):
                with st.spinner("Analyzing your request and executing workflow..."):
                    try:
                        # Run the workflow
                        config = {"configurable": {"thread_id": st.session_state.thread_id}}
                        result_state = asyncio.run(workflow_instance.run(query, config))
                        
                        st.session_state.workflow_state = result_state
                        
                        # Display results
                        if result_state["workflow_status"] == "completed":
                            # Show workflow type
                            mode_names = {
                                "buyer_ma": "Buyer-Led M&A",
                                "seller_ma": "Seller-Led M&A", 
                                "ipo": "IPO"
                            }
                            mode_name = mode_names.get(result_state["mode"], result_state["mode"])
                            
                            st.success(f"✅ {mode_name} workflow completed successfully!")
                            
                            # Show agent results
                            for agent_name, agent_result in result_state["agent_results"].items():
                                if agent_result["status"] == "success":
                                    st.markdown(f"**{agent_name.replace('_', ' ').title()} Results:**")
                                    
                                    # Format results based on agent type
                                    if agent_name == "target_finder":
                                        display_target_finder_results(agent_result["result"])
                                    elif agent_name == "valuer":
                                        display_valuer_results(agent_result["result"])
                                    else:
                                        st.json(agent_result["result"])
                            
                            # Show final messages
                            for msg in result_state["messages"]:
                                if msg["role"] == "assistant":
                                    st.markdown(msg["content"])
                        
                        else:
                            st.error("❌ Workflow encountered an error. Please try again.")
                            if "error" in result_state:
                                st.error(f"Error: {result_state['error']}")
                    
                    except Exception as e:
                        st.error(f"❌ An error occurred: {str(e)}")
                        logger.log_error("streamlit_error", str(e), {"query": query})
            
            # Add assistant response to messages
            if st.session_state.workflow_state:
                response = f"Completed {st.session_state.workflow_state['mode']} workflow analysis."
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    with col2:
        st.subheader("📊 Workflow Status")
        
        if st.session_state.workflow_state:
            state = st.session_state.workflow_state
            
            # Show workflow info
            st.metric("Workflow Type", state["mode"].replace("_", " ").title())
            st.metric("Status", state["workflow_status"].title())
            st.metric("Deal ID", state["deal"]["deal_id"])
            
            # Show agent status
            st.subheader("🤖 Agent Status")
            for agent_name, result in state["agent_results"].items():
                status = result["status"]
                icon = "✅" if status == "success" else "❌" if status == "error" else "⏳"
                st.markdown(f"{icon} **{agent_name.replace('_', ' ').title()}**: {status}")
                
                if status == "error" and result.get("error_message"):
                    st.error(f"Error: {result['error_message']}")
        
        else:
            st.info("Start a conversation to see workflow status")


def display_target_finder_results(result: Dict[str, Any]):
    """Display target finder results in a formatted way."""
    if "targets" in result and result["targets"]:
        st.markdown(f"**Found {result['target_count']} potential targets:**")
        
        for i, target in enumerate(result["targets"][:5], 1):  # Show top 5
            with st.expander(f"{i}. {target['company_name']} - {target['location']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Revenue:** {target['estimated_revenue']}")
                    st.markdown(f"**EBITDA Margin:** {target['estimated_ebitda_margin']}")
                    st.markdown(f"**Strategic Fit:** {target['strategic_fit_score']}/5")
                
                with col2:
                    st.markdown(f"**Highlights:** {target['investment_highlights']}")
                    if 'ticker' in target:
                        st.markdown(f"**Ticker:** {target['ticker']}")
                    if 'industry' in target:
                        st.markdown(f"**Industry:** {target['industry']}")


def display_valuer_results(result: Dict[str, Any]):
    """Display valuation results in a formatted way."""
    if "key_metrics" in result:
        st.markdown("**Key Financial Metrics:**")
        metrics = result["key_metrics"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Revenue", f"${metrics.get('revenue', 0):,.0f}")
        with col2:
            st.metric("EBITDA", f"${metrics.get('ebitda', 0):,.0f}")
        with col3:
            st.metric("Market Cap", f"${metrics.get('market_cap', 0):,.0f}")
    
    if "valuation_range" in result:
        st.markdown("**Valuation Range:**")
        val_range = result["valuation_range"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Low", f"${val_range.get('low', 0):,.0f}")
        with col2:
            st.metric("Mid", f"${val_range.get('mid', 0):,.0f}")
        with col3:
            st.metric("High", f"${val_range.get('high', 0):,.0f}")


if __name__ == "__main__":
    main()
