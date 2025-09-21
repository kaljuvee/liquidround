"""
Database service layer for LiquidRound workflow management.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .logging import get_logger

logger = get_logger("database")


class DatabaseService:
    """Database service for managing workflows and results."""
    
    def __init__(self, db_path: str = "liquidround.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Workflows table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    user_query TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT DEFAULT '{}'
                )
            """)
            
            # Workflow results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    result_data TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'success',
                    execution_time REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
                )
            """)
            
            # Messages table for chat history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (workflow_id) REFERENCES workflows (id)
                )
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    def create_workflow(self, user_query: str, workflow_type: str = "unknown") -> str:
        """Create a new workflow and return its ID."""
        workflow_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflows (id, user_query, workflow_type, status)
                VALUES (?, ?, ?, 'pending')
            """, (workflow_id, user_query, workflow_type))
            conn.commit()
        
        logger.info(f"Created workflow {workflow_id} for query: {user_query[:50]}...")
        return workflow_id
    
    def update_workflow_status(self, workflow_id: str, status: str, workflow_type: str = None):
        """Update workflow status and optionally workflow type."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if workflow_type:
                cursor.execute("""
                    UPDATE workflows 
                    SET status = ?, workflow_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, workflow_type, workflow_id))
            else:
                cursor.execute("""
                    UPDATE workflows 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, workflow_id))
            
            conn.commit()
        
        logger.info(f"Updated workflow {workflow_id} status to {status}")
    
    def save_agent_result(self, workflow_id: str, agent_name: str, result_data: Dict[Any, Any], 
                         status: str = "success", execution_time: float = None):
        """Save agent execution result."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_results (workflow_id, agent_name, result_data, status, execution_time)
                VALUES (?, ?, ?, ?, ?)
            """, (workflow_id, agent_name, json.dumps(result_data, default=str), status, execution_time))
            conn.commit()
        
        logger.info(f"Saved {agent_name} result for workflow {workflow_id}")
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow details by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_query, workflow_type, status, created_at, updated_at, metadata
                FROM workflows WHERE id = ?
            """, (workflow_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "user_query": row[1],
                    "workflow_type": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "metadata": json.loads(row[6])
                }
        return None
    
    def get_workflow_results(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get all agent results for a workflow."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT agent_name, result_data, status, execution_time, created_at
                FROM workflow_results 
                WHERE workflow_id = ?
                ORDER BY created_at ASC
            """, (workflow_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "agent_name": row[0],
                    "result_data": json.loads(row[1]),
                    "status": row[2],
                    "execution_time": row[3],
                    "created_at": row[4]
                })
            
            return results
    
    def add_message(self, workflow_id: str, role: str, content: str):
        """Add a message to the workflow chat history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO messages (workflow_id, role, content)
                VALUES (?, ?, ?)
            """, (workflow_id, role, content))
            conn.commit()
        
        logger.debug(f"Added {role} message to workflow {workflow_id}")
    
    def get_messages(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a workflow."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, timestamp
                FROM messages 
                WHERE workflow_id = ?
                ORDER BY timestamp ASC
            """, (workflow_id,))
            
            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "timestamp": row[2]
                })
            
            return messages
    
    def get_recent_workflows(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent workflows for the dashboard."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_query, workflow_type, status, created_at, updated_at
                FROM workflows 
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            
            workflows = []
            for row in cursor.fetchall():
                workflows.append({
                    "id": row[0],
                    "user_query": row[1],
                    "workflow_type": row[2],
                    "status": row[3],
                    "created_at": row[4],
                    "updated_at": row[5]
                })
            
            return workflows
    
    def get_workflow_summary(self, workflow_id: str) -> Dict[str, Any]:
        """Get a complete summary of a workflow including results and messages."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return {}
        
        results = self.get_workflow_results(workflow_id)
        messages = self.get_messages(workflow_id)
        
        return {
            "workflow": workflow,
            "results": results,
            "messages": messages,
            "agent_count": len(results),
            "message_count": len(messages)
        }


# Global database instance
db_service = DatabaseService()
