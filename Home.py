"""
LiquidRound - Multi-Agent M&A and IPO Deal Flow System
Main Streamlit Application Entry Point
"""
import sys
import os

# Add the agents directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agents'))

# Import the main function from the agents directory
from agents.Home import main

if __name__ == "__main__":
    main()
else:
    # For streamlit run command
    main()
