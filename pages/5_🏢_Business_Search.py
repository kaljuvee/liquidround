"""
Business Search Page for LiquidRound - UK Companies House Integration
Search and analyze UK companies for M&A opportunities and due diligence.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from utils.companies_house_api import CompaniesHouseAPI, CompanyProfile, Officer, PSC
except ImportError:
    st.error("Could not import Companies House API module. Please check the installation.")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="Business Search - LiquidRound",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f4e79;
        text-align: center;
        margin-bottom: 2rem;
    }
    .company-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f4e79;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: linear-gradient(135deg, #1f4e79 0%, #3182bd 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .officer-card {
        background: #e3f2fd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #2196f3;
        margin: 0.5rem 0;
    }
    .psc-card {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #4caf50;
        margin: 0.5rem 0;
    }
    .search-info {
        background: #fff3cd;
        padding: 1rem;
        border-radius: 8px;
        border-left: 3px solid #ffc107;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables"""
    if 'ch_search_results' not in st.session_state:
        st.session_state.ch_search_results = None
    if 'ch_company_details' not in st.session_state:
        st.session_state.ch_company_details = {}
    if 'ch_network_data' not in st.session_state:
        st.session_state.ch_network_data = None

def create_network_visualization(graph_data):
    """Create an interactive network visualization using Plotly"""
    if not graph_data or not graph_data['nodes']:
        return None
    
    import math
    nodes = graph_data['nodes']
    edges = graph_data['edges']
    
    # Simple circular layout for nodes
    n_nodes = len(nodes)
    node_positions = {}
    
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n_nodes
        radius = 100 if node['type'] == 'Company' else 80
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        node_positions[node['id']] = (x, y)
    
    # Create edge traces
    edge_x = []
    edge_y = []
    
    for edge in edges:
        source_pos = node_positions.get(edge['source'])
        target_pos = node_positions.get(edge['target'])
        
        if source_pos and target_pos:
            edge_x.extend([source_pos[0], target_pos[0], None])
            edge_y.extend([source_pos[1], target_pos[1], None])
    
    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='#888'),
        hoverinfo='none',
        mode='lines'
    )
    
    # Create node traces by type
    node_traces = []
    
    for node_type in ['Company', 'Person', 'PSC']:
        type_nodes = [n for n in nodes if n['type'] == node_type]
        if not type_nodes:
            continue
        
        node_x = [node_positions[n['id']][0] for n in type_nodes]
        node_y = [node_positions[n['id']][1] for n in type_nodes]
        
        # Create hover text
        hover_text = []
        for node in type_nodes:
            if node['type'] == 'Company':
                text = f"<b>{node['label']}</b><br>"
                text += f"Number: {node.get('company_number', 'N/A')}<br>"
                text += f"Status: {node.get('status', 'N/A')}<br>"
                text += f"Business: {node.get('business_activity', 'N/A')}"
            elif node['type'] == 'Person':
                text = f"<b>{node['label']}</b><br>"
                text += f"Role: {node.get('role', 'N/A')}<br>"
                text += f"Nationality: {node.get('nationality', 'N/A')}<br>"
                text += f"Occupation: {node.get('occupation', 'N/A')}"
            else:  # PSC
                text = f"<b>{node['label']}</b><br>"
                text += f"Type: {node.get('psc_type', 'N/A')}<br>"
                text += f"Country: {node.get('country_of_residence', 'N/A')}"
            hover_text.append(text)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            hovertext=hover_text,
            text=[n['label'] for n in type_nodes],
            textposition="middle center",
            name=node_type,
            marker=dict(
                size=[n.get('size', 15) for n in type_nodes],
                color=type_nodes[0]['color'],
                line=dict(width=2, color='white')
            )
        )
        node_traces.append(node_trace)
    
    # Create the figure
    fig = go.Figure(data=[edge_trace] + node_traces,
                    layout=go.Layout(
                        title=dict(
                            text="Business Network Graph",
                            font=dict(size=18, color='#1f4e79')
                        ),
                        showlegend=True,
                        hovermode='closest',
                        margin=dict(b=20,l=5,r=5,t=40),
                        annotations=[dict(
                            text="Hover over nodes for details",
                            showarrow=False,
                            xref="paper", yref="paper",
                            x=0.005, y=-0.002,
                            xanchor="left", yanchor="bottom",
                            font=dict(color="#888", size=12)
                        )],
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        plot_bgcolor='white'
                    ))
    
    return fig

def display_search_results(companies):
    """Display company search results"""
    if not companies:
        st.warning("No companies found matching your search criteria.")
        return
    
    st.subheader(f"🔍 Search Results ({len(companies)} companies found)")
    
    for i, company in enumerate(companies):
        with st.expander(f"🏢 {company.get('title', 'Unknown Company')} - {company.get('company_number', 'N/A')}", expanded=i==0):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Company Number:** {company.get('company_number', 'N/A')}")
                st.write(f"**Status:** {company.get('company_status', 'N/A')}")
                st.write(f"**Type:** {company.get('company_type', 'N/A')}")
                st.write(f"**Incorporation Date:** {company.get('date_of_creation', 'N/A')}")
            
            with col2:
                address = company.get('address', {})
                if address:
                    address_parts = [
                        address.get('address_line_1', ''),
                        address.get('address_line_2', ''),
                        address.get('locality', ''),
                        address.get('postal_code', '')
                    ]
                    full_address = ', '.join([part for part in address_parts if part])
                    st.write(f"**Address:** {full_address}")
                
                description = company.get('description', '')
                if description:
                    st.write(f"**Description:** {description}")
            
            # Button to get detailed information
            if st.button(f"📊 Get Detailed Info", key=f"detail_{company.get('company_number')}"):
                company_number = company.get('company_number')
                if company_number:
                    get_company_details(company_number)

def get_company_details(company_number):
    """Get detailed company information"""
    ch_api_key = st.session_state.get('ch_api_key', '')
    if not ch_api_key:
        st.error("Please enter your Companies House API key in the sidebar.")
        return
    
    with st.spinner("Fetching detailed company information..."):
        try:
            ch_api = CompaniesHouseAPI(ch_api_key, use_sandbox=False)
            
            # Get company profile
            profile = ch_api.get_company_profile(company_number)
            officers = ch_api.get_officers(company_number)
            pscs = ch_api.get_pscs(company_number)
            
            st.session_state.ch_company_details[company_number] = {
                'profile': profile,
                'officers': officers,
                'pscs': pscs
            }
            
            # Display detailed information
            display_company_details(company_number)
            
        except Exception as e:
            st.error(f"Error fetching company details: {str(e)}")

def display_company_details(company_number):
    """Display detailed company information"""
    details = st.session_state.ch_company_details.get(company_number)
    if not details:
        return
    
    profile = details['profile']
    officers = details['officers']
    pscs = details['pscs']
    
    if not profile:
        st.error("Could not retrieve company profile.")
        return
    
    st.markdown("---")
    st.subheader(f"📋 Detailed Information: {profile.company_name}")
    
    # Company overview
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{profile.company_status}</h3>
            <p>Company Status</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(officers)}</h3>
            <p>Officers</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(pscs)}</h3>
            <p>PSCs/UBOs</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{len(profile.sic_codes)}</h3>
            <p>SIC Codes</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Detailed information in accordions
    with st.expander("🏢 Company Profile", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Company Number:** {profile.company_number}")
            st.write(f"**Company Name:** {profile.company_name}")
            st.write(f"**Status:** {profile.company_status}")
            st.write(f"**Type:** {profile.company_type}")
            st.write(f"**Incorporation Date:** {profile.incorporation_date or 'N/A'}")
        
        with col2:
            if profile.registered_address:
                address_parts = [
                    profile.registered_address.get('address_line_1', ''),
                    profile.registered_address.get('address_line_2', ''),
                    profile.registered_address.get('locality', ''),
                    profile.registered_address.get('postal_code', '')
                ]
                full_address = ', '.join([part for part in address_parts if part])
                st.write(f"**Registered Address:** {full_address}")
            
            if profile.sic_codes:
                st.write(f"**SIC Codes:** {', '.join(profile.sic_codes)}")
            
            if profile.business_activity:
                st.write(f"**Business Activity:** {profile.business_activity}")
    
    # Officers information
    if officers:
        with st.expander(f"👥 Officers & Directors ({len(officers)})", expanded=False):
            for officer in officers:
                st.markdown(f"""
                <div class="officer-card">
                    <strong>{officer.name}</strong> - {officer.role}<br>
                    <small>
                    Appointed: {officer.appointed_on or 'N/A'} | 
                    Nationality: {officer.nationality or 'N/A'} | 
                    Occupation: {officer.occupation or 'N/A'}
                    </small>
                </div>
                """, unsafe_allow_html=True)
    
    # PSCs information
    if pscs:
        with st.expander(f"🎯 Persons with Significant Control ({len(pscs)})", expanded=False):
            for psc in pscs:
                control_nature = ', '.join(psc.nature_of_control) if psc.nature_of_control else 'N/A'
                st.markdown(f"""
                <div class="psc-card">
                    <strong>{psc.name}</strong> - {psc.psc_type}<br>
                    <small>
                    Control: {control_nature}<br>
                    Notified: {psc.notified_on or 'N/A'} | 
                    Country: {psc.country_of_residence or 'N/A'}
                    </small>
                </div>
                """, unsafe_allow_html=True)

def main():
    """Main function for the Business Search page"""
    init_session_state()
    
    st.markdown('<div class="main-header">🏢 Business Search</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <p style="font-size: 1.2rem; color: #666;">
            Search and analyze UK companies using official Companies House data for M&A opportunities and due diligence.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar configuration
    st.sidebar.header("🔧 Search Configuration")
    
    # API Key input
    api_key = st.sidebar.text_input(
        "Companies House API Key",
        type="password",
        value="ccd402e3-9dc9-4d47-b348-6decb7b18dea",  # Default provided key
        help="Your Companies House API key for accessing official UK company data"
    )
    
    if api_key:
        st.session_state.ch_api_key = api_key
    
    # Search input
    search_query = st.sidebar.text_input(
        "Company Name or Number",
        placeholder="e.g., Tesco PLC, BP PLC, Vodafone, or 00445790",
        help="Enter a UK company name to search for, or a company number for direct access"
    )
    
    # Search options
    max_results = st.sidebar.slider(
        "Maximum Results",
        min_value=5,
        max_value=50,
        value=20,
        help="Maximum number of search results to display"
    )
    
    # Search button
    if st.sidebar.button("🔍 Search Companies", type="primary"):
        if not api_key:
            st.sidebar.error("Please enter your Companies House API key")
        elif not search_query:
            st.sidebar.error("Please enter a company name or number")
        else:
            with st.spinner("Searching Companies House database..."):
                try:
                    ch_api = CompaniesHouseAPI(api_key, use_sandbox=False)
                    companies = ch_api.search_companies(search_query, items_per_page=max_results)
                    
                    if companies:
                        st.session_state.ch_search_results = companies
                        st.sidebar.success(f"✅ Found {len(companies)} companies!")
                    else:
                        st.sidebar.warning("No companies found matching your search.")
                        st.session_state.ch_search_results = None
                        
                except Exception as e:
                    st.sidebar.error(f"Search error: {str(e)}")
    
    # Network analysis button
    if st.sidebar.button("🕸️ Build Network Graph", help="Create a network graph showing company relationships"):
        if not api_key:
            st.sidebar.error("Please enter your Companies House API key")
        elif not search_query:
            st.sidebar.error("Please enter a company name")
        else:
            with st.spinner("Building company network graph..."):
                try:
                    ch_api = CompaniesHouseAPI(api_key, use_sandbox=False)
                    network_data = ch_api.get_company_network(search_query, max_companies=5)
                    
                    if network_data and network_data['nodes']:
                        st.session_state.ch_network_data = network_data
                        st.sidebar.success("✅ Network graph created!")
                    else:
                        st.sidebar.warning("Could not create network graph.")
                        
                except Exception as e:
                    st.sidebar.error(f"Network error: {str(e)}")
    
    # Display results
    if st.session_state.ch_search_results:
        display_search_results(st.session_state.ch_search_results)
    
    # Display network graph
    if st.session_state.ch_network_data:
        st.markdown("---")
        st.subheader("🕸️ Company Network Analysis")
        
        network_data = st.session_state.ch_network_data
        
        # Network summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            companies_count = len([n for n in network_data['nodes'] if n['type'] == 'Company'])
            st.metric("Companies", companies_count)
        
        with col2:
            people_count = len([n for n in network_data['nodes'] if n['type'] == 'Person'])
            st.metric("Directors/Officers", people_count)
        
        with col3:
            psc_count = len([n for n in network_data['nodes'] if n['type'] == 'PSC'])
            st.metric("PSCs/UBOs", psc_count)
        
        with col4:
            relationships_count = len(network_data['edges'])
            st.metric("Relationships", relationships_count)
        
        # Network visualization
        fig = create_network_visualization(network_data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        
        # Network data in accordion
        with st.expander("📊 Network Data Details", expanded=False):
            st.json(network_data['metadata'])
    
    # Help and information
    if not st.session_state.ch_search_results and not st.session_state.ch_network_data:
        st.markdown("---")
        st.info("👈 Use the sidebar to search for UK companies and analyze their business networks!")
        
        # Help information
        with st.expander("ℹ️ How to Use Business Search"):
            st.markdown("""
            ### Getting Started
            
            1. **API Key**: The Companies House API key is pre-configured for immediate use
            2. **Search**: Enter a UK company name (e.g., "Tesco PLC", "BP PLC") or company number
            3. **Results**: Browse search results and click "Get Detailed Info" for comprehensive analysis
            4. **Network**: Use "Build Network Graph" to visualize company relationships and ownership structures
            
            ### What You Can Discover
            
            - **Company Profiles**: Official registration details, status, and business activities
            - **Directors & Officers**: Current and former company leadership
            - **Ultimate Beneficial Owners**: Persons with Significant Control (PSCs) who own or control companies
            - **Business Networks**: Relationships between companies through shared directors and ownership
            - **Due Diligence**: Comprehensive information for M&A analysis and risk assessment
            
            ### Example Companies to Search
            
            - **Tesco PLC** - Major UK retailer
            - **BP PLC** - Energy company
            - **Vodafone Group PLC** - Telecommunications
            - **HSBC Holdings PLC** - Banking and financial services
            - **Rolls-Royce Holdings PLC** - Engineering and manufacturing
            
            ### M&A Applications
            
            - **Target Identification**: Find companies in specific sectors or regions
            - **Ownership Analysis**: Understand control structures and beneficial ownership
            - **Due Diligence**: Verify company status, directors, and business activities
            - **Network Mapping**: Identify related companies and potential conflicts of interest
            - **Risk Assessment**: Evaluate company status and regulatory compliance
            """)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9rem;">
        <p>Business Search powered by UK Companies House API | 
        Part of LiquidRound M&A Platform</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
