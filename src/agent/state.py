"""Agent state definitions for LangGraph workflow"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """State maintained throughout the agent workflow"""
    
    # Input
    user_input: str
    db_name: str
    show_query_details: Optional[bool]  # Flag to show actual query details in output
    
    # Investigation results
    slow_queries: List[Dict[str, Any]]
    explain_results: List[Dict[str, Any]]
    index_analysis: List[Dict[str, Any]]
    
    # Analysis and recommendations
    analysis_summary: str
    recommendations: List[Dict[str, Any]]
    
    # Output
    final_output: str
    
    # Metadata
    investigation_start_time: float
    investigation_end_time: Optional[float]
    errors: List[str]