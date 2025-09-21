"""
LiquidRound - Multi-Agent M&A and IPO Deal Flow System
Main Streamlit Application
"""
import streamlit as st
import asyncio
import time
from datetime import datetime
from typing import Dict, Any

# Import only utils and database services
from utils.database import db_service
from utils.workflow_service import workflow_service
from utils.logging import get_logger
from utils.config import config

logger = get_logger("streamlit_app")

# Configure page
st.set_page_config(
    page_title="LiquidRound - AI M&A Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .workflow-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f4e79;
        margin: 0.5rem 0;
    }
    .status-pending { color: #ffa500; }
    .status-executing { color: #007bff; }
    .status-completed { color: #28a745; }
    .status-failed { color: #dc3545; }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables."""
    if "current_workflow_id" not in st.session_state:
        st.session_state.current_workflow_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "workflow_history" not in st.session_state:
        st.session_state.workflow_history = []

def display_header():
    """Display the main header."""
    st.markdown('<div class="main-header">🏢 LiquidRound</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-Powered M&A and IPO Deal Flow Platform</div>', unsafe_allow_html=True)
    st.markdown("---")

def display_sidebar():
    """Display sidebar with system status and recent workflows."""
    with st.sidebar:
        st.header("📈 System Status")
        
        # System metrics
        recent_workflows = workflow_service.get_recent_workflows(10)
        total_workflows = len(recent_workflows)
        
        if total_workflows > 0:
            completed = len([w for w in recent_workflows if w["status"] == "completed"])
            success_rate = (completed / total_workflows) * 100
            
            st.metric("Total Workflows", total_workflows)
            st.metric("Success Rate", f"{success_rate:.1f}%")
            
            # Status distribution
            status_counts = {}
            for workflow in recent_workflows:
                status = workflow["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            st.write("**Status Distribution:**")
            for status, count in status_counts.items():
                st.write(f"• {status.title()}: {count}")
        else:
            st.info("No workflows yet")
        
        st.markdown("---")
        
        # Configuration info
        st.subheader("⚙️ Configuration")
        try:
            st.write(f"**Model:** {config.default_model}")
            st.write(f"**Environment:** {'Production' if config.is_production else 'Development'}")
        except Exception as e:
            st.error(f"Configuration error: {e}")
        
        st.markdown("---")
        
        # Recent workflows
        st.subheader("📊 Recent Workflows")
        recent_workflows = workflow_service.get_recent_workflows(5)
        
        for workflow in recent_workflows:
            status_class = f"status-{workflow['status']}"
            st.markdown(f"""
            <div class="workflow-card">
                <strong>{workflow['workflow_type'].upper()}</strong><br>
                <small>{workflow['user_query'][:50]}...</small><br>
                <span class="{status_class}">● {workflow['status']}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"View", key=f"view_{workflow['id']}", use_container_width=True):
                st.session_state.current_workflow_id = workflow['id']
                st.rerun()
    
    return None

def display_sample_buttons():
    """Display sample query buttons in 2 rows, 3 columns above the chat."""
    st.subheader("🎯 Quick Start - Sample Queries")
    
    # Row 1
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Find Acquisition Targets", use_container_width=True):
            return "Find fintech companies to acquire with $20-100M revenue"
    
    with col2:
        if st.button("🏥 Healthcare SaaS Targets", use_container_width=True):
            return "Looking for SaaS acquisition targets in healthcare"
    
    with col3:
        if st.button("💼 Prepare Company for Sale", use_container_width=True):
            return "Preparing to sell our B2B software company"
    
    # Row 2
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Find Strategic Buyers", use_container_width=True):
            return "Need help finding buyers for our logistics business"
    
    with col2:
        if st.button("🏛️ IPO Readiness Assessment", use_container_width=True):
            return "Assessing IPO readiness for our tech company"
    
    with col3:
        if st.button("🔬 Tech Startup Valuation", use_container_width=True):
            return "Value our AI/ML startup for Series B funding"
    
    st.markdown("---")
    return None

async def start_new_workflow(user_query: str):
    """Start a new workflow."""
    try:
        workflow_id = await workflow_service.start_workflow(user_query)
        st.session_state.current_workflow_id = workflow_id
        st.session_state.messages = [{"role": "user", "content": user_query}]
        logger.info(f"Started new workflow: {workflow_id}")
        return workflow_id
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        st.error(f"Failed to start workflow: {str(e)}")
        return None

def display_workflow_status(workflow_id: str):
    """Display current workflow status and results."""
    if not workflow_id:
        return
    
    try:
        summary = workflow_service.get_workflow_status(workflow_id)
        
        if not summary:
            st.warning("Workflow not found")
            return
        
        workflow = summary.get("workflow", {})
        results = summary.get("results", [])
        messages = summary.get("messages", [])
        
        # Status header
        status = workflow.get("status", "unknown")
        status_class = f"status-{status}"
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**Workflow:** {workflow.get('workflow_type', 'unknown').upper()}")
        with col2:
            st.markdown(f"**Status:** <span class='{status_class}'>● {status}</span>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"**Agents:** {len(results)}")
        
        # Display messages
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "user":
                with st.chat_message("user"):
                    st.write(content)
            else:
                with st.chat_message("assistant"):
                    st.markdown(content)
        
        # Display detailed results if available
        if results:
            with st.expander("📊 Detailed Agent Results", expanded=False):
                for result in results:
                    agent_name = result["agent_name"]
                    result_data = result["result_data"]
                    execution_time = result.get("execution_time", 0)
                    
                    st.subheader(f"🤖 {agent_name.title()}")
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"Status: {result['status']}")
                    with col2:
                        st.write(f"Time: {execution_time:.2f}s")
                    
                    # Display specific result data based on agent type
                    if agent_name == "target_finder" and "targets" in result_data:
                        targets = result_data["targets"]
                        if targets:
                            st.write(f"**Found {len(targets)} targets:**")
                            for i, target in enumerate(targets[:3], 1):
                                st.write(f"{i}. **{target.get('company_name', 'Unknown')}**")
                                st.write(f"   - Revenue: {target.get('estimated_revenue', 'N/A')}")
                                st.write(f"   - Strategic Fit: {target.get('strategic_fit_score', 'N/A')}/5")
                    
                    elif agent_name == "valuer" and "key_metrics" in result_data:
                        metrics = result_data["key_metrics"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Revenue", f"${metrics.get('revenue', 0):,.0f}")
                        with col2:
                            st.metric("EBITDA", f"${metrics.get('ebitda', 0):,.0f}")
                        with col3:
                            st.metric("Market Cap", f"${metrics.get('market_cap', 0):,.0f}")
                    
                    elif agent_name == "orchestrator":
                        st.write(f"**Workflow Type:** {result_data.get('workflow_type', 'unknown')}")
                        st.write(f"**Rationale:** {result_data.get('rationale', 'N/A')}")
                    
                    st.markdown("---")
        
    except Exception as e:
        logger.error(f"Error displaying workflow status: {e}")
        st.error(f"Error loading workflow: {str(e)}")

def main():
    """Main application function."""
    init_session_state()
    display_header()
    
    # Sidebar with system status and recent workflows
    display_sidebar()
    
    # Main content area - full width
    # Sample buttons above chat
    suggested_query = display_sample_buttons()
    
    # Chat interface
    st.subheader("💬 Chat Interface")
    
    # Chat input
    if user_input := st.chat_input("Enter your M&A or IPO query..."):
        # Start new workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        workflow_id = loop.run_until_complete(start_new_workflow(user_input))
        loop.close()
        
        if workflow_id:
            st.rerun()
    
    # Handle suggested queries from buttons
    if suggested_query:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        workflow_id = loop.run_until_complete(start_new_workflow(suggested_query))
        loop.close()
        
        if workflow_id:
            st.rerun()
    
    # Display current workflow
    if st.session_state.current_workflow_id:
        display_workflow_status(st.session_state.current_workflow_id)
        
        # Auto-refresh for active workflows
        summary = workflow_service.get_workflow_status(st.session_state.current_workflow_id)
        if summary and summary.get("workflow", {}).get("status") in ["pending", "routing", "executing"]:
            time.sleep(2)
            st.rerun()
    else:
        st.info("👋 Welcome to LiquidRound! Start by selecting a sample query above or typing your own query below.")


if __name__ == "__main__":
    main()
