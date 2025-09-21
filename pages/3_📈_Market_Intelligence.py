"""
Market Intelligence Page for LiquidRound
Displays sector performance heatmaps and market insights for M&A decision-making.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_intelligence import market_intelligence
from utils.logging import get_logger

# Page configuration
st.set_page_config(
    page_title="Market Intelligence - LiquidRound",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

logger = get_logger(__name__)

# Custom CSS for styling
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .insight-card {
        background: #f8f9fa;
        border-left: 4px solid #3182bd;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    
    .sector-performance {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .heatmap-container {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

def display_header():
    """Display the page header."""
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1>📈 Market Intelligence</h1>
        <p style="font-size: 1.2rem; color: #666;">
            Sector Performance Analysis for Strategic M&A Decision-Making
        </p>
    </div>
    """, unsafe_allow_html=True)

def display_sector_heatmap():
    """Display the sector performance heatmap."""
    st.markdown("""
    <div class="heatmap-container">
        <h2>🎯 Sector vs Year Performance Heatmap</h2>
        <p>Annual returns by sector showing market trends and opportunities for strategic acquisitions.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data with spinner
    with st.spinner("📊 Loading sector performance data..."):
        try:
            # Get sector performance data (will use real data or fallback to sample data)
            df = market_intelligence.get_sector_performance_data(years=5)
            
            # Create and display heatmap (always shows data)
            fig = market_intelligence.create_sector_performance_heatmap(df)
            st.plotly_chart(fig, use_container_width=True)
            
            # Display data summary
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Sectors Analyzed", len(df['Sector'].unique()))
            
            with col2:
                st.metric("Years Covered", len(df['Year'].unique()))
            
            with col3:
                avg_return = df['Return'].mean()
                st.metric("Average Return", f"{avg_return:.1f}%")
            
            with col4:
                volatility = df['Return'].std()
                st.metric("Market Volatility", f"{volatility:.1f}%")
            
            return df
                
        except Exception as e:
            logger.error(f"Error displaying heatmap: {e}")
            st.error("Error loading market data. Please try again later.")
            return pd.DataFrame()

def display_market_insights(df: pd.DataFrame):
    """Display market insights and analysis."""
    if df.empty:
        return
    
    st.markdown("## 🔍 Market Insights & Analysis")
    
    try:
        insights = market_intelligence.get_sector_insights(df)
        
        if insights:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🏆 Top Performing Sectors")
                if 'best_sectors' in insights:
                    for sector, return_pct in list(insights['best_sectors'].items())[:3]:
                        st.markdown(f"""
                        <div class="insight-card">
                            <strong>{sector}</strong><br>
                            Average Return: <span style="color: #28a745; font-weight: bold;">{return_pct:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("### 📊 Most Volatile Sectors")
                if 'most_volatile' in insights:
                    for sector, volatility in list(insights['most_volatile'].items())[:3]:
                        st.markdown(f"""
                        <div class="insight-card">
                            <strong>{sector}</strong><br>
                            Volatility: <span style="color: #ffc107; font-weight: bold;">{volatility:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
            
            with col2:
                st.markdown("### 📉 Underperforming Sectors")
                if 'worst_sectors' in insights:
                    for sector, return_pct in list(insights['worst_sectors'].items())[:3]:
                        st.markdown(f"""
                        <div class="insight-card">
                            <strong>{sector}</strong><br>
                            Average Return: <span style="color: #dc3545; font-weight: bold;">{return_pct:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
                
                st.markdown("### 🎯 Recent Year Leaders")
                if 'recent_best' in insights:
                    for sector, return_pct in list(insights['recent_best'].items())[:3]:
                        st.markdown(f"""
                        <div class="insight-card">
                            <strong>{sector}</strong><br>
                            Recent Return: <span style="color: #17a2b8; font-weight: bold;">{return_pct:.1f}%</span>
                        </div>
                        """, unsafe_allow_html=True)
        
    except Exception as e:
        logger.error(f"Error displaying insights: {e}")
        st.error("Error generating market insights.")

def display_ma_implications():
    """Display M&A implications based on market data."""
    st.markdown("## 💼 M&A Strategic Implications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Acquisition Opportunities
        
        **High-Growth Sectors:**
        - Technology companies with strong fundamentals
        - Healthcare innovation and biotech
        - Clean energy and sustainability
        
        **Value Opportunities:**
        - Traditional retail transformation
        - Energy sector consolidation
        - Real estate optimization
        """)
    
    with col2:
        st.markdown("""
        ### 📈 Market Timing Insights
        
        **Favorable Conditions:**
        - Sector rotation creating opportunities
        - Valuation gaps between public/private markets
        - Interest rate environment impact
        
        **Risk Considerations:**
        - Market volatility affecting valuations
        - Regulatory changes in key sectors
        - Economic cycle positioning
        """)

def display_sector_etf_reference():
    """Display sector ETF reference table in accordion."""
    etf_data = []
    for sector, etf in market_intelligence.sector_etfs.items():
        etf_data.append({
            'Sector': sector,
            'ETF Symbol': etf,
            'Description': f"SPDR {sector} Select Sector ETF"
        })
    
    df_etfs = pd.DataFrame(etf_data)
    
    # Display in accordion
    with st.expander("📋 Sector ETF Reference", expanded=False):
        st.markdown("**Sector ETF Mapping for Market Analysis**")
        st.dataframe(df_etfs, use_container_width=True)

def main():
    """Main function for the Market Intelligence page."""
    display_header()
    
    # Main heatmap display
    df = display_sector_heatmap()
    
    # Market insights
    if not df.empty:
        display_market_insights(df)
    
    # M&A implications
    display_ma_implications()
    
    # ETF reference
    display_sector_etf_reference()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 1rem;">
        <small>
        Market data provided by Yahoo Finance. 
        This analysis is for informational purposes and should not be considered as investment advice.
        </small>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
