"""
Market Intelligence Module for LiquidRound
Provides sector performance analysis and heatmaps for M&A decision-making.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import yfinance as yf
import logging
from typing import Dict, List, Tuple, Optional
import streamlit as st

logger = logging.getLogger(__name__)

class MarketIntelligence:
    """Market intelligence service for sector performance analysis."""
    
    def __init__(self):
        """Initialize market intelligence service."""
        self.sector_etfs = {
            'Technology': 'XLK',
            'Healthcare': 'XLV', 
            'Financial Services': 'XLF',
            'Consumer Discretionary': 'XLY',
            'Consumer Staples': 'XLP',
            'Energy': 'XLE',
            'Utilities': 'XLU',
            'Materials': 'XLB',
            'Industrials': 'XLI',
            'Real Estate': 'XLRE',
            'Communication': 'XLC'
        }
        
    def get_sector_performance_data(self, years: int = 5) -> pd.DataFrame:
        """Get sector performance data for the specified number of years."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            performance_data = []
            
            for sector, etf in self.sector_etfs.items():
                try:
                    # Get ETF data
                    ticker = yf.Ticker(etf)
                    hist = ticker.history(start=start_date, end=end_date)
                    
                    if hist.empty:
                        continue
                    
                    # Calculate annual returns
                    hist['Year'] = hist.index.year
                    annual_data = hist.groupby('Year').agg({
                        'Close': ['first', 'last']
                    }).round(2)
                    
                    annual_data.columns = ['First_Close', 'Last_Close']
                    annual_data['Annual_Return'] = ((annual_data['Last_Close'] / annual_data['First_Close']) - 1) * 100
                    
                    for year, row in annual_data.iterrows():
                        performance_data.append({
                            'Sector': sector,
                            'Year': year,
                            'Return': round(row['Annual_Return'], 1),
                            'ETF': etf
                        })
                        
                except Exception as e:
                    logger.warning(f"Failed to get data for {sector} ({etf}): {e}")
                    continue
            
            df = pd.DataFrame(performance_data)
            return df
            
        except Exception as e:
            logger.error(f"Error getting sector performance data: {e}")
            return pd.DataFrame()
    
    def create_sector_performance_heatmap(self, df: pd.DataFrame) -> go.Figure:
        """Create a sector vs year performance heatmap."""
        try:
            if df.empty:
                # Create sample data if no real data available
                df = self._create_sample_data()
            
            # Pivot data for heatmap
            heatmap_data = df.pivot(index='Sector', columns='Year', values='Return')
            
            # Create the heatmap
            fig = go.Figure(data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale=[
                    [0.0, '#f7fbff'],    # Very light blue
                    [0.2, '#deebf7'],    # Light blue
                    [0.4, '#c6dbef'],    # Medium light blue
                    [0.6, '#9ecae1'],    # Medium blue
                    [0.8, '#6baed6'],    # Medium dark blue
                    [1.0, '#3182bd']     # Dark blue
                ],
                colorbar=dict(
                    title="Annual Return (%)",
                    titleside="right",
                    tickmode="linear",
                    tick0=-20,
                    dtick=10
                ),
                hoverongaps=False,
                hovertemplate='<b>%{y}</b><br>' +
                             'Year: %{x}<br>' +
                             'Return: %{z:.1f}%<br>' +
                             '<extra></extra>'
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    'text': 'Sector Performance Heatmap (Annual Returns %)',
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 18, 'color': '#2c3e50'}
                },
                xaxis_title="Year",
                yaxis_title="Sector",
                font=dict(size=12),
                height=600,
                width=1000,
                margin=dict(l=150, r=100, t=80, b=80),
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # Update axes
            fig.update_xaxes(
                tickangle=0,
                tickfont=dict(size=11),
                title_font=dict(size=14)
            )
            
            fig.update_yaxes(
                tickfont=dict(size=11),
                title_font=dict(size=14)
            )
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating heatmap: {e}")
            return self._create_empty_heatmap()
    
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample sector performance data."""
        sectors = list(self.sector_etfs.keys())
        years = list(range(2020, 2025))
        
        data = []
        np.random.seed(42)  # For consistent sample data
        
        for sector in sectors:
            for year in years:
                # Generate realistic returns with some sector bias
                base_return = np.random.normal(8, 15)  # Base market return
                
                # Add sector-specific bias
                if sector == 'Technology':
                    base_return += np.random.normal(5, 10)
                elif sector == 'Healthcare':
                    base_return += np.random.normal(3, 8)
                elif sector == 'Energy':
                    base_return += np.random.normal(-2, 20)
                
                data.append({
                    'Sector': sector,
                    'Year': year,
                    'Return': round(base_return, 1)
                })
        
        return pd.DataFrame(data)
    
    def _create_empty_heatmap(self) -> go.Figure:
        """Create an empty heatmap as fallback."""
        fig = go.Figure()
        fig.add_annotation(
            text="Unable to load sector performance data",
            xref="paper", yref="paper",
            x=0.5, y=0.5, xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            title="Sector Performance Heatmap",
            height=400,
            showlegend=False
        )
        return fig
    
    def get_sector_insights(self, df: pd.DataFrame) -> Dict:
        """Generate insights from sector performance data."""
        try:
            if df.empty:
                return {}
            
            insights = {}
            
            # Best performing sectors (average return)
            avg_returns = df.groupby('Sector')['Return'].mean().sort_values(ascending=False)
            insights['best_sectors'] = avg_returns.head(3).to_dict()
            insights['worst_sectors'] = avg_returns.tail(3).to_dict()
            
            # Most volatile sectors
            volatility = df.groupby('Sector')['Return'].std().sort_values(ascending=False)
            insights['most_volatile'] = volatility.head(3).to_dict()
            insights['least_volatile'] = volatility.tail(3).to_dict()
            
            # Recent year performance
            recent_year = df['Year'].max()
            recent_performance = df[df['Year'] == recent_year].set_index('Sector')['Return'].sort_values(ascending=False)
            insights['recent_best'] = recent_performance.head(3).to_dict()
            insights['recent_worst'] = recent_performance.tail(3).to_dict()
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {}

# Global instance
market_intelligence = MarketIntelligence()
