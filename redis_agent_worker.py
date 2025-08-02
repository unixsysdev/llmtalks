import json
import time
import redis
import sys
import os
from pathlib import Path
from typing import Dict, Any
from enhanced_agent import EnhancedCollaborativeAgent
from dotenv import load_dotenv

load_dotenv()

class RedisAgentWorker:
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host='host.docker.internal', 
            port=6379, 
            password=redis_password,
            decode_responses=True
        )
        # Agent will be created per task with session_id
        self.agent = None
        
        print(f"🤖 Redis Agent {agent_id} worker starting...")
        print(f"🔗 Connected to Redis at host.docker.internal:6379 with auth")
        
        # Test connection
        try:
            self.redis_client.ping()
            print(f"✅ {agent_id} Redis authentication successful")
        except Exception as e:
            print(f"❌ {agent_id} Redis connection failed: {e}")
            raise
    
    def run(self):
        """Main worker loop"""
        task_queue = f"agent_tasks:{self.agent_id}"
        
        while True:
            try:
                # Blocking pop from Redis queue (wait up to 1 second)
                task_data = self.redis_client.brpop(task_queue, timeout=1)
                
                if task_data:
                    _, task_json = task_data
                    task = json.loads(task_json)
                    
                    print(f"📨 {self.agent_id} processing {task['phase']} task")
                    
                    # Process the task
                    result = self.process_task(task)
                    
                    # Store result in Redis
                    result_key = f"result:{task['task_id']}"
                    self.redis_client.set(result_key, json.dumps(result), ex=3600)  # 1 hour expiry
                    
                    print(f"✅ {self.agent_id} completed {task['phase']}")
                    
            except Exception as e:
                print(f"❌ {self.agent_id} error: {e}")
                time.sleep(1)
    
    def process_task(self, task: Dict) -> Dict[str, Any]:
        """Process a task based on phase"""
        phase = task["phase"]
        data = task["data"]
        session_id = task.get("session_id", "default")
        
        # Create agent with session_id for this task
        self.agent = EnhancedCollaborativeAgent(self.agent_id, session_id)
        
        try:
            if phase == "plan":
                return self.agent.planning_phase(data["problem"])
            elif phase == "analyze":
                return self.agent.deep_think_phase(data["problem"], data.get("planning_context"))
            elif phase == "solve":
                return self.agent.solution_phase(data["problem"], data.get("planning_context"))
            elif phase == "evaluate":
                return self.agent.enhanced_evaluate_solutions(data["all_solutions"])
            elif phase == "implement":
                return self.agent.implement_consensus(data["consensus"], data.get("best_solution"))
            else:
                return {"error": f"Unknown phase: {phase}"}
        except Exception as e:
            return {"error": f"Task processing error: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python redis_agent_worker.py <agent_id>")
        sys.exit(1)
    
    agent_id = sys.argv[1]
    worker = RedisAgentWorker(agent_id)
    worker.run()
