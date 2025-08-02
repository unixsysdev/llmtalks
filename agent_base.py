import json
import os
import requests
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class BaseAgent:
    def __init__(self, agent_id: str, session_id: str = None):
        self.agent_id = agent_id
        self.session_id = session_id
        
        # Use absolute paths for container compatibility
        base_path = Path("/app")  # Base path in Docker container
        
        # Create session-specific workspace if session_id provided
        if session_id:
            self.workspace = base_path / agent_id / "workspace" / session_id
        else:
            # Fallback to default workspace
            self.workspace = base_path / agent_id / "workspace"
            
        self.logs_dir = base_path / agent_id / "logs"
        self.api_token = os.getenv("CHUTES_API_TOKEN")
        self.api_url = os.getenv("CHUTES_API_URL")
        self.model_name = os.getenv("MODEL_NAME")
        
        # Ensure directories exist
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
    def call_llm(self, messages: List[Dict], temperature: float = 0.7, max_tokens: int = 4096, 
                 top_k: int = -1, top_p: float = 1.0, max_retries: int = 5) -> str:
        """Call GLM-4.5 via Chutes API with retry logic"""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        # Only add optional parameters if they're not default values
        if top_k != -1:
            data["top_k"] = top_k
        if top_p != 1.0:
            data["top_p"] = top_p
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = min(10, 2 ** (attempt - 1))
                    print(f"🔄 Retry {attempt + 1}/{max_retries} after {wait_time}s...")
                    time.sleep(wait_time)
                
                response = requests.post(self.api_url, headers=headers, json=data, timeout=120)
                response.raise_for_status()
                response_json = response.json()
                result = response_json["choices"][0]["message"]["content"]
                
                # Log the raw response for debugging
                self.log_activity("llm_response", {
                    "model": self.model_name,
                    "response_length": len(result) if result else 0,
                    "response_preview": result[:200] if result else "EMPTY",
                    "attempt": attempt + 1
                })
                
                if not result or result.strip() == "":
                    if attempt == max_retries - 1:
                        self.log_activity("llm_empty_response", {
                            "model": self.model_name,
                            "attempts": max_retries,
                            "messages": messages
                        })
                        return "Error: Empty response from API"
                    continue
                    
                return result
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    return f"Error calling LLM after {max_retries} retries: {str(e)}"
                print(f"⚠️ API call failed (attempt {attempt + 1}): {str(e)}")
                continue
            except Exception as e:
                return f"Unexpected error calling LLM: {str(e)}"
    
    def execute_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Execute code in sandboxed environment"""
        try:
            if language == "python":
                with tempfile.NamedTemporaryFile(mode='w', suffix='.py', 
                                               dir=self.workspace, delete=False) as f:
                    f.write(code)
                    temp_file = f.name
                
                result = subprocess.run(
                    ["python", temp_file], 
                    capture_output=True, 
                    text=True, 
                    timeout=30,
                    cwd=self.workspace
                )
                
                os.unlink(temp_file)
                
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "success": result.returncode == 0
                }
            else:
                return {"error": f"Language {language} not supported"}
        except subprocess.TimeoutExpired:
            return {"error": "Code execution timed out"}
        except Exception as e:
            return {"error": f"Execution error: {str(e)}"}
    
    def read_file(self, filepath: str) -> str:
        """Read file from workspace"""
        try:
            full_path = self.workspace / filepath
            return full_path.read_text()
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def write_file(self, filepath: str, content: str) -> bool:
        """Write file to workspace"""
        try:
            full_path = self.workspace / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return True
        except Exception as e:
            print(f"Error writing file: {str(e)}")
            return False
    
    def web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search the web using DuckDuckGo"""
        try:
            import requests
            from urllib.parse import quote_plus
            
            encoded_query = quote_plus(query)
            url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            if data.get("Abstract"):
                results.append({
                    "title": data.get("Heading", "Instant Answer"),
                    "snippet": data.get("Abstract", ""),
                    "url": data.get("AbstractURL", ""),
                    "source": data.get("AbstractSource", "")
                })
            
            for topic in data.get("RelatedTopics", [])[:max_results-1]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append({
                        "title": topic.get("Text", "")[:100] + "...",
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo"
                    })
            
            return {
                "query": query,
                "results": results,
                "count": len(results),
                "success": True
            }
            
        except Exception as e:
            return {
                "query": query,
                "results": [],
                "error": f"Search failed: {str(e)}",
                "success": False
            }
    
    def execute_bash(self, command: str) -> Dict[str, Any]:
        """Execute bash command in workspace"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.workspace
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
                "command": command
            }
        except subprocess.TimeoutExpired:
            return {"error": "Command timed out", "success": False, "command": command}
        except Exception as e:
            return {"error": f"Bash execution error: {str(e)}", "success": False, "command": command}
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool and return structured results"""
        try:
            if tool_name == "execute_code":
                return self.execute_code(kwargs.get("code", ""), kwargs.get("language", "python"))
            elif tool_name == "read_file":
                content = self.read_file(kwargs.get("filepath", ""))
                return {"content": content, "success": "Error" not in content}
            elif tool_name == "write_file":
                success = self.write_file(kwargs.get("filepath", ""), kwargs.get("content", ""))
                return {"success": success}
            elif tool_name == "web_search":
                return self.web_search(kwargs.get("query", ""), kwargs.get("max_results", 5))
            elif tool_name == "bash":
                return self.execute_bash(kwargs.get("command", ""))
            else:
                return {"error": f"Unknown tool: {tool_name}", "success": False}
        except Exception as e:
            return {"error": f"Tool execution failed: {str(e)}", "success": False}
    
    def log_activity(self, activity: str, data: Any = None):
        """Log agent activity"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent_id,
            "activity": activity,
            "data": data
        }
        
        log_file = self.logs_dir / f"{self.agent_id}_log.jsonl"
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
