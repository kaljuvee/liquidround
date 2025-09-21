"""
Deals Management Page - View and Manage M&A and IPO Deals
"""
import streamlit as st
import sqlite3
import pandas as pd
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from utils.database import db_service
from utils.logging import get_logger

logger = get_logger("deals_page")

st.set_page_config(
    page_title="Deals - LiquidRound",
    page_icon="💼",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .deal-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .deal-card.buyer_ma {
        border-left-color: #007bff;
    }
    .deal-card.seller_ma {
        border-left-color: #ffc107;
    }
    .deal-card.ipo {
        border-left-color: #6f42c1;
    }
    .status-active { color: #28a745; font-weight: bold; }
    .status-pending { color: #ffc107; font-weight: bold; }
    .status-completed { color: #6c757d; font-weight: bold; }
    .status-failed { color: #dc3545; font-weight: bold; }
    .metric-card {
        background: #e9ecef;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def get_deals_data() -> pd.DataFrame:
    """Get all deals from the database."""
    db_path = Path("db/liquidround.db")
    
    if not db_path.exists():
        return pd.DataFrame()
    
    try:
        with sqlite3.connect(db_path) as conn:
            query = """
            SELECT 
                d.*,
                COUNT(DISTINCT dt.company_id) as target_count,
                COUNT(DISTINCT v.id) as valuation_count,
                AVG(dt.strategic_fit_score) as avg_strategic_fit,
                MAX(v.valuation_amount) as max_valuation
            FROM deals d
            LEFT JOIN deal_targets dt ON d.id = dt.deal_id
            LEFT JOIN valuations v ON d.id = v.deal_id
            GROUP BY d.id
            ORDER BY d.created_at DESC
            """
            df = pd.read_sql_query(query, conn)
            return df
    
    except Exception as e:
        logger.error(f"Error getting deals data: {e}")
        st.error(f"Error loading deals: {e}")
        return pd.DataFrame()

def get_deal_details(deal_id: str) -> Dict[str, Any]:
    """Get detailed information for a specific deal."""
    db_path = Path("db/liquidround.db")
    
    if not db_path.exists():
        return {}
    
    try:
        with sqlite3.connect(db_path) as conn:
            # Get deal info
            deal_query = "SELECT * FROM deals WHERE id = ?"
            deal_df = pd.read_sql_query(deal_query, conn, params=[deal_id])
            
            if deal_df.empty:
                return {}
            
            deal = deal_df.iloc[0].to_dict()
            
            # Get targets
            targets_query = """
            SELECT c.*, dt.strategic_fit_score, dt.valuation_low, dt.valuation_high, dt.notes
            FROM companies c
            JOIN deal_targets dt ON c.id = dt.company_id
            WHERE dt.deal_id = ?
            """
            targets_df = pd.read_sql_query(targets_query, conn, params=[deal_id])
            
            # Get valuations
            valuations_query = """
            SELECT v.*, c.name as company_name
            FROM valuations v
            LEFT JOIN companies c ON v.company_id = c.id
            WHERE v.deal_id = ?
            """
            valuations_df = pd.read_sql_query(valuations_query, conn, params=[deal_id])
            
            # Get workflows
            workflows_query = """
            SELECT w.*, COUNT(wr.id) as result_count
            FROM workflows w
            LEFT JOIN workflow_results wr ON w.id = wr.workflow_id
            WHERE w.deal_id = ?
            GROUP BY w.id
            ORDER BY w.created_at DESC
            """
            workflows_df = pd.read_sql_query(workflows_query, conn, params=[deal_id])
            
            return {
                "deal": deal,
                "targets": targets_df,
                "valuations": valuations_df,
                "workflows": workflows_df
            }
    
    except Exception as e:
        logger.error(f"Error getting deal details: {e}")
        return {}

def create_new_deal(deal_data: Dict[str, Any]) -> str:
    """Create a new deal in the database."""
    db_path = Path("db/liquidround.db")
    
    if not db_path.exists():
        st.error("Database not found")
        return ""
    
    try:
        import uuid
        deal_id = str(uuid.uuid4())
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT INTO deals (
                id, deal_type, company_name, industry, sector,
                deal_size_min, deal_size_max, deal_size_currency,
                status, priority, created_at, updated_at, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                deal_id,
                deal_data["deal_type"],
                deal_data.get("company_name"),
                deal_data.get("industry"),
                deal_data.get("sector"),
                deal_data.get("deal_size_min"),
                deal_data.get("deal_size_max"),
                deal_data.get("deal_size_currency", "USD"),
                "pending",
                deal_data.get("priority", "medium"),
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                json.dumps(deal_data.get("metadata", {}))
            ))
            
            conn.commit()
            return deal_id
    
    except Exception as e:
        logger.error(f"Error creating deal: {e}")
        st.error(f"Error creating deal: {e}")
        return ""

def display_deal_card(deal: Dict[str, Any]):
    """Display a deal as a card."""
    deal_type = deal.get("deal_type", "unknown")
    status = deal.get("status", "unknown")
    
    st.markdown(f"""
    <div class="deal-card {deal_type}">
        <h4>{deal.get('company_name', 'Unnamed Deal')} ({deal_type.upper()})</h4>
        <p><strong>Industry:</strong> {deal.get('industry', 'N/A')} | 
           <strong>Status:</strong> <span class="status-{status}">{status.upper()}</span></p>
        <p><strong>Deal Size:</strong> ${deal.get('deal_size_min', 0):,.0f} - ${deal.get('deal_size_max', 0):,.0f} {deal.get('deal_size_currency', 'USD')}</p>
        <p><strong>Created:</strong> {deal.get('created_at', '')[:10]} | 
           <strong>Targets:</strong> {deal.get('target_count', 0)} | 
           <strong>Valuations:</strong> {deal.get('valuation_count', 0)}</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main function for Deals page."""
    
    st.title("💼 Deals Management")
    st.markdown("View and manage M&A and IPO deals")
    
    # Get deals data
    deals_df = get_deals_data()
    
    # Sidebar filters
    with st.sidebar:
        st.header("🔍 Filters")
        
        # Deal type filter
        deal_types = ["All"] + list(deals_df["deal_type"].unique()) if not deals_df.empty else ["All"]
        selected_deal_type = st.selectbox("Deal Type", deal_types)
        
        # Status filter
        statuses = ["All"] + list(deals_df["status"].unique()) if not deals_df.empty else ["All"]
        selected_status = st.selectbox("Status", statuses)
        
        # Industry filter
        industries = ["All"] + list(deals_df["industry"].dropna().unique()) if not deals_df.empty else ["All"]
        selected_industry = st.selectbox("Industry", industries)
        
        # Date range filter
        st.subheader("Date Range")
        date_filter = st.selectbox("Period", ["All Time", "Last 7 days", "Last 30 days", "Last 90 days"])
        
        st.markdown("---")
        
        # Create new deal button
        if st.button("➕ Create New Deal", use_container_width=True):
            st.session_state.show_create_form = True
    
    # Apply filters
    filtered_df = deals_df.copy() if not deals_df.empty else pd.DataFrame()
    
    if not filtered_df.empty:
        if selected_deal_type != "All":
            filtered_df = filtered_df[filtered_df["deal_type"] == selected_deal_type]
        
        if selected_status != "All":
            filtered_df = filtered_df[filtered_df["status"] == selected_status]
        
        if selected_industry != "All":
            filtered_df = filtered_df[filtered_df["industry"] == selected_industry]
        
        # Date filtering
        if date_filter != "All Time":
            days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}
            cutoff_date = (datetime.now() - timedelta(days=days_map[date_filter])).isoformat()
            filtered_df = filtered_df[filtered_df["created_at"] >= cutoff_date]
    
    # Main content
    if deals_df.empty:
        st.info("No deals found. Create your first deal or run some workflows to generate deal data.")
        
        # Show create form
        if st.session_state.get("show_create_form", False):
            with st.form("create_deal_form"):
                st.subheader("Create New Deal")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    deal_type = st.selectbox("Deal Type", ["buyer_ma", "seller_ma", "ipo"])
                    company_name = st.text_input("Company Name")
                    industry = st.text_input("Industry")
                    sector = st.text_input("Sector")
                
                with col2:
                    deal_size_min = st.number_input("Min Deal Size ($)", min_value=0, value=1000000)
                    deal_size_max = st.number_input("Max Deal Size ($)", min_value=0, value=10000000)
                    priority = st.selectbox("Priority", ["low", "medium", "high", "urgent"])
                
                submitted = st.form_submit_button("Create Deal")
                
                if submitted:
                    deal_data = {
                        "deal_type": deal_type,
                        "company_name": company_name,
                        "industry": industry,
                        "sector": sector,
                        "deal_size_min": deal_size_min,
                        "deal_size_max": deal_size_max,
                        "priority": priority
                    }
                    
                    deal_id = create_new_deal(deal_data)
                    if deal_id:
                        st.success(f"Deal created successfully! ID: {deal_id}")
                        st.session_state.show_create_form = False
                        st.rerun()
        
        return
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(filtered_df)}</h3>
            <p>Total Deals</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        active_deals = len(filtered_df[filtered_df["status"].isin(["pending", "active"])])
        st.markdown(f"""
        <div class="metric-card">
            <h3>{active_deals}</h3>
            <p>Active Deals</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        total_targets = filtered_df["target_count"].sum() if not filtered_df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>{total_targets:.0f}</h3>
            <p>Total Targets</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_valuation = filtered_df["max_valuation"].mean() if not filtered_df.empty else 0
        st.markdown(f"""
        <div class="metric-card">
            <h3>${avg_valuation/1000000:.1f}M</h3>
            <p>Avg Valuation</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Display deals
    if not filtered_df.empty:
        # View toggle
        view_mode = st.radio("View Mode", ["Cards", "Table"], horizontal=True)
        
        if view_mode == "Cards":
            # Card view
            for _, deal in filtered_df.iterrows():
                display_deal_card(deal.to_dict())
                
                col1, col2, col3 = st.columns([1, 1, 3])
                with col1:
                    if st.button("View Details", key=f"view_{deal['id']}"):
                        st.session_state.selected_deal_id = deal['id']
                        st.session_state.show_deal_details = True
                
                with col2:
                    if st.button("Edit", key=f"edit_{deal['id']}"):
                        st.session_state.edit_deal_id = deal['id']
                        st.session_state.show_edit_form = True
        
        else:
            # Table view
            display_columns = [
                "company_name", "deal_type", "industry", "status", 
                "deal_size_min", "deal_size_max", "target_count", 
                "valuation_count", "created_at"
            ]
            
            with st.expander(f"📊 Deals Table View ({len(filtered_df)} deals)", expanded=True):
                st.dataframe(
                    filtered_df[display_columns],
                    use_container_width=True,
                    column_config={
                        "deal_size_min": st.column_config.NumberColumn("Min Size", format="$%.0f"),
                        "deal_size_max": st.column_config.NumberColumn("Max Size", format="$%.0f"),
                        "created_at": st.column_config.DatetimeColumn("Created"),
                    }
                )
    
    else:
        st.info("No deals match the current filters.")
    
    # Deal details modal
    if st.session_state.get("show_deal_details", False):
        deal_id = st.session_state.get("selected_deal_id")
        
        if deal_id:
            deal_details = get_deal_details(deal_id)
            
            if deal_details:
                st.subheader(f"Deal Details: {deal_details['deal'].get('company_name', 'Unknown')}")
                
                # Deal info
                deal = deal_details["deal"]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Type:** {deal.get('deal_type', 'N/A').upper()}")
                    st.write(f"**Industry:** {deal.get('industry', 'N/A')}")
                    st.write(f"**Status:** {deal.get('status', 'N/A')}")
                    st.write(f"**Priority:** {deal.get('priority', 'N/A')}")
                
                with col2:
                    st.write(f"**Deal Size:** ${deal.get('deal_size_min', 0):,.0f} - ${deal.get('deal_size_max', 0):,.0f}")
                    st.write(f"**Created:** {deal.get('created_at', '')[:10]}")
                    st.write(f"**Updated:** {deal.get('updated_at', '')[:10]}")
                
                # Targets
                if not deal_details["targets"].empty:
                    with st.expander(f"🎯 Target Companies ({len(deal_details['targets'])} targets)", expanded=False):
                        st.dataframe(deal_details["targets"], use_container_width=True)
                
                # Valuations
                if not deal_details["valuations"].empty:
                    with st.expander(f"💰 Valuations ({len(deal_details['valuations'])} valuations)", expanded=False):
                        st.dataframe(deal_details["valuations"], use_container_width=True)
                
                # Workflows
                if not deal_details["workflows"].empty:
                    with st.expander(f"🔄 Related Workflows ({len(deal_details['workflows'])} workflows)", expanded=False):
                        st.dataframe(deal_details["workflows"], use_container_width=True)
                
                if st.button("Close Details"):
                    st.session_state.show_deal_details = False
                    st.rerun()

if __name__ == "__main__":
    main()
