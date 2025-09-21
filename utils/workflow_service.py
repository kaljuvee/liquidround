"""
Workflow service layer for managing agent execution.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor

from .database import db_service
from .logging import get_logger

logger = get_logger("workflow_service")


class WorkflowService:
    """Service for managing workflow execution without direct agent imports."""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._agent_registry = {}
    
    def register_agent(self, name: str, agent_class):
        """Register an agent class for lazy loading."""
        self._agent_registry[name] = agent_class
        logger.info(f"Registered agent: {name}")
    
    def _get_agent(self, name: str):
        """Get an agent instance by name."""
        if name not in self._agent_registry:
            # Lazy import agents only when needed
            try:
                if name == "orchestrator":
                    from ..agents.orchestrator import OrchestratorAgent
                    self._agent_registry[name] = OrchestratorAgent
                elif name == "target_finder":
                    from ..agents.target_finder import TargetFinderAgent
                    self._agent_registry[name] = TargetFinderAgent
                elif name == "valuer":
                    from ..agents.valuer import ValuerAgent
                    self._agent_registry[name] = ValuerAgent
                else:
                    logger.error(f"Unknown agent: {name}")
                    return None
            except ImportError as e:
                logger.error(f"Failed to import agent {name}: {e}")
                return None
        
        agent_class = self._agent_registry[name]
        return agent_class()
    
    async def start_workflow(self, user_query: str) -> str:
        """Start a new workflow and return the workflow ID."""
        workflow_id = db_service.create_workflow(user_query)
        
        # Add user message
        db_service.add_message(workflow_id, "user", user_query)
        
        # Start workflow execution in background
        asyncio.create_task(self._execute_workflow(workflow_id, user_query))
        
        return workflow_id
    
    async def _execute_workflow(self, workflow_id: str, user_query: str):
        """Execute the workflow asynchronously."""
        try:
            logger.info(f"Starting workflow execution for {workflow_id}")
            
            # Step 1: Orchestrator determines workflow type
            db_service.update_workflow_status(workflow_id, "routing")
            orchestrator = self._get_agent("orchestrator")
            
            if not orchestrator:
                db_service.update_workflow_status(workflow_id, "failed")
                return
            
            start_time = time.time()
            
            # Create a simple state object for the orchestrator
            state = {"user_query": user_query, "messages": []}
            
            try:
                orchestrator_result = await asyncio.get_event_loop().run_in_executor(
                    self.executor, orchestrator.execute, state
                )
                
                execution_time = time.time() - start_time
                db_service.save_agent_result(
                    workflow_id, "orchestrator", orchestrator_result, 
                    "success", execution_time
                )
                
                workflow_type = orchestrator_result.get("workflow_type", "unknown")
                db_service.update_workflow_status(workflow_id, "executing", workflow_type)
                
                # Add orchestrator response
                rationale = orchestrator_result.get("rationale", "Workflow routing completed")
                db_service.add_message(workflow_id, "assistant", f"🎯 **Workflow Routing**: {workflow_type.upper()}\n\n{rationale}")
                
            except Exception as e:
                logger.error(f"Orchestrator failed for {workflow_id}: {e}")
                db_service.save_agent_result(workflow_id, "orchestrator", {"error": str(e)}, "failed")
                db_service.update_workflow_status(workflow_id, "failed")
                return
            
            # Step 2: Execute workflow-specific agents
            if workflow_type in ["buyer_ma", "seller_ma"]:
                await self._execute_ma_workflow(workflow_id, user_query, workflow_type)
            elif workflow_type == "ipo":
                await self._execute_ipo_workflow(workflow_id, user_query)
            else:
                logger.warning(f"Unknown workflow type: {workflow_type}")
                db_service.update_workflow_status(workflow_id, "completed")
            
        except Exception as e:
            logger.error(f"Workflow execution failed for {workflow_id}: {e}")
            db_service.update_workflow_status(workflow_id, "failed")
            db_service.add_message(workflow_id, "assistant", f"❌ **Error**: Workflow execution failed: {str(e)}")
    
    async def _execute_ma_workflow(self, workflow_id: str, user_query: str, workflow_type: str):
        """Execute M&A workflow with target finder and valuer."""
        try:
            state = {"user_query": user_query, "workflow_type": workflow_type, "messages": []}
            
            # Step 1: Target Finder
            db_service.add_message(workflow_id, "assistant", "🔍 **Finding acquisition targets...**")
            
            target_finder = self._get_agent("target_finder")
            if target_finder:
                start_time = time.time()
                
                try:
                    target_result = await asyncio.get_event_loop().run_in_executor(
                        self.executor, target_finder.execute, state
                    )
                    
                    execution_time = time.time() - start_time
                    db_service.save_agent_result(
                        workflow_id, "target_finder", target_result,
                        "success", execution_time
                    )
                    
                    # Add target finder response
                    targets = target_result.get("targets", [])
                    if targets:
                        response = f"📊 **Found {len(targets)} potential targets:**\n\n"
                        for i, target in enumerate(targets[:5], 1):  # Show top 5
                            response += f"{i}. **{target.get('company_name', 'Unknown')}**\n"
                            response += f"   - Revenue: {target.get('estimated_revenue', 'N/A')}\n"
                            response += f"   - Strategic Fit: {target.get('strategic_fit_score', 'N/A')}/5\n"
                            response += f"   - Highlights: {target.get('investment_highlights', 'N/A')}\n\n"
                        
                        db_service.add_message(workflow_id, "assistant", response)
                    else:
                        db_service.add_message(workflow_id, "assistant", "🔍 **Target search completed** but no specific targets were identified.")
                
                except Exception as e:
                    logger.error(f"Target finder failed for {workflow_id}: {e}")
                    db_service.save_agent_result(workflow_id, "target_finder", {"error": str(e)}, "failed")
                    db_service.add_message(workflow_id, "assistant", f"❌ **Target Finder Error**: {str(e)}")
            
            # Step 2: Valuer
            db_service.add_message(workflow_id, "assistant", "💰 **Performing valuation analysis...**")
            
            valuer = self._get_agent("valuer")
            if valuer:
                start_time = time.time()
                
                try:
                    valuation_result = await asyncio.get_event_loop().run_in_executor(
                        self.executor, valuer.execute, state
                    )
                    
                    execution_time = time.time() - start_time
                    db_service.save_agent_result(
                        workflow_id, "valuer", valuation_result,
                        "success", execution_time
                    )
                    
                    # Add valuation response
                    if "valuation_analysis" in valuation_result:
                        analysis = valuation_result["valuation_analysis"]
                        response = f"💰 **Valuation Analysis Complete**\n\n{analysis[:500]}..."
                        if len(analysis) > 500:
                            response += "\n\n*Full analysis available in detailed results.*"
                        db_service.add_message(workflow_id, "assistant", response)
                    else:
                        db_service.add_message(workflow_id, "assistant", "💰 **Valuation analysis completed** - detailed metrics captured.")
                
                except Exception as e:
                    logger.error(f"Valuer failed for {workflow_id}: {e}")
                    db_service.save_agent_result(workflow_id, "valuer", {"error": str(e)}, "failed")
                    db_service.add_message(workflow_id, "assistant", f"❌ **Valuation Error**: {str(e)}")
            
            db_service.update_workflow_status(workflow_id, "completed")
            db_service.add_message(workflow_id, "assistant", "✅ **M&A Analysis Complete** - All results are available in the detailed view.")
            
        except Exception as e:
            logger.error(f"M&A workflow failed for {workflow_id}: {e}")
            db_service.update_workflow_status(workflow_id, "failed")
    
    async def _execute_ipo_workflow(self, workflow_id: str, user_query: str):
        """Execute IPO workflow (placeholder for future implementation)."""
        try:
            db_service.add_message(workflow_id, "assistant", "🏛️ **IPO Analysis** - Coming soon! Currently focusing on M&A workflows.")
            db_service.update_workflow_status(workflow_id, "completed")
        except Exception as e:
            logger.error(f"IPO workflow failed for {workflow_id}: {e}")
            db_service.update_workflow_status(workflow_id, "failed")
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current workflow status and results."""
        return db_service.get_workflow_summary(workflow_id)
    
    def get_recent_workflows(self, limit: int = 10) -> list:
        """Get recent workflows for dashboard."""
        return db_service.get_recent_workflows(limit)


# Global workflow service instance
workflow_service = WorkflowService()
