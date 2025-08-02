from agent_base import BaseAgent
from typing import Dict, List, Any
import json
import os
import re

class EnhancedCollaborativeAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str = None):
        super().__init__(agent_id, session_id)
        # Tools are inherited from BaseAgent:
        # - execute_code(code, language)
        # - read_file(filepath) 
        # - write_file(filepath, content)
        # - web_search(query, max_results)
        # - execute_tool(tool_name, **kwargs)
    
    def extract_json_from_response(self, response: str) -> str:
        """Extract JSON from response that might contain thinking tags"""
        # Log the raw response for debugging
        self.log_activity("raw_llm_response", {
            "response_length": len(response),
            "response_preview": response[:500],
            "has_think_tags": "<think>" in response
        })
        
        # Remove thinking tags if present
        if "<think>" in response:
            # Try to find JSON after thinking tags
            json_match = re.search(r'</think>\s*({[\s\S]*})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try without whitespace requirement
                json_match = re.search(r'</think>({[\s\S]*})', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    json_str = response
        else:
            # Try to find JSON anywhere in the response
            # Use a more robust approach to find complete JSON objects
            json_match = re.search(r'({[\s\S]*})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                # Find the first opening brace and try to match the complete JSON object
                brace_count = 0
                start_idx = response.find('{')
                if start_idx != -1:
                    for i, char in enumerate(response[start_idx:], start_idx):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = response[start_idx:i+1]
                                break
            else:
                json_str = response
        
        # Strip any markdown code block markers
        json_str = json_str.strip()
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        if json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        json_str = json_str.strip()
        
        # Log extracted JSON for debugging
        self.log_activity("extracted_json", {
            "json_length": len(json_str),
            "json_preview": json_str[:200]
        })
        
        return json_str
    
    def validate_solution_fields(self, solution: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and ensure all required solution fields exist"""
        # Define required fields with defaults
        required_fields = {
            "solution_overview": "Solution generated",
            "research_phase": [],
            "development_phase": [],
            "files_created": [],
            "detailed_implementation": "Implementation details",
            "code_examples": [],
            "testing_approach": "Testing approach",
            "advantages": [],
            "limitations": [],
            "confidence": 0.5,
            "agent_id": self.agent_id,
            "phase": "solution"
        }
        
        # Add missing fields with defaults
        for field, default_value in required_fields.items():
            if field not in solution:
                solution[field] = default_value
                self.log_activity("solution_field_added", {
                    "field": field,
                    "default_value": default_value
                })
        
        # Validate confidence is between 0 and 1
        if "confidence" in solution:
            confidence = solution["confidence"]
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                solution["confidence"] = 0.5
                self.log_activity("solution_confidence_fixed", {
                    "original": confidence,
                    "fixed": 0.5
                })
        
        # Ensure lists are actually lists
        list_fields = ["research_phase", "development_phase", "files_created", 
                      "code_examples", "advantages", "limitations"]
        for field in list_fields:
            if field in solution and not isinstance(solution[field], list):
                solution[field] = []
                self.log_activity("solution_list_field_fixed", {"field": field})
        
        return solution
    
    def planning_phase(self, problem: str, temperature: float = 0.7) -> Dict[str, Any]:
        """Phase 1: Strategic planning"""
        system_prompt = f"""You are Agent {self.agent_id} creating a strategic plan.

Think through the problem and create a strategic plan.

RESPOND IN VALID JSON:
{{
  "analysis": "Brief problem analysis",
  "approach": "Chosen approach",
  "confidence": 0.8
}}

Problem: {problem}

"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Research and create a strategic plan for: {problem}"}
        ]
        
        response = self.call_llm(messages, temperature=temperature, max_tokens=6144)
        
        try:
            json_response = self.extract_json_from_response(response)
            result = json.loads(json_response)
            
            
            result["agent_id"] = self.agent_id
            result["phase"] = "planning"
            self.log_activity("planning_phase_with_tools", result)
            return result
            
        except json.JSONDecodeError as e:
            self.log_activity("planning_phase_json_error", {
                "error": str(e), 
                "response_preview": response[:1000],
                "json_attempt": json_response[:500]
            })
            return {
                "analysis": response[:300] + "..." if len(response) > 300 else response,
                "recommended_approach": "Failed to parse JSON response",
                "confidence": 0.3,
                "agent_id": self.agent_id,
                "phase": "planning",
                "error": f"JSON parse error: {str(e)}"
            }
    
    def deep_think_phase(self, problem: str, planning_context: Dict = None, temperature: float = 0.8) -> Dict[str, Any]:
        """Phase 2: Deep analysis with planning context"""
        context = f"Planning context: {json.dumps(planning_context, indent=2)[:500]}..." if planning_context else ""
        system_prompt = f"""You are Agent {self.agent_id} conducting deep analysis.

Conduct a comprehensive analysis of the problem.

RESPOND IN VALID JSON:
{{
  "deep_analysis": "Comprehensive analysis of the problem",
  "key_findings": ["finding 1", "finding 2"],
  "technical_considerations": ["technical factor 1", "technical factor 2"],
  "user_experience_factors": ["UX factor 1", "UX factor 2"],
  "implementation_challenges": ["challenge 1", "challenge 2"],
  "recommended_technologies": ["tech 1", "tech 2"],
  "performance_considerations": ["performance factor 1"],
  "accessibility_requirements": ["accessibility need 1"],
  "confidence": 0.85
}}

Problem: {problem}

"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Conduct deep analysis of: {problem}"}
        ]
        
        response = self.call_llm(messages, temperature=temperature, max_tokens=6144)
        
        try:
            json_response = self.extract_json_from_response(response)
            result = json.loads(json_response)
            
            
            result["agent_id"] = self.agent_id
            result["phase"] = "analysis"
            self.log_activity("deep_analysis_with_tools", result)
            return result
            
        except json.JSONDecodeError as e:
            self.log_activity("analysis_phase_json_error", {"error": str(e), "response_preview": response[:500]})
            return {
                "deep_analysis": response[:300] + "..." if len(response) > 300 else response,
                "confidence": 0.3,
                "agent_id": self.agent_id,
                "phase": "analysis",
                "error": f"JSON parse error: {str(e)}"
            }
    
    def solution_phase(self, problem: str, planning_context: Dict = None, temperature: float = 0.6) -> Dict[str, Any]:
        """Phase 3: Develop complete solution"""
        context = f"Planning context: {json.dumps(planning_context, indent=2)[:500]}..." if planning_context else ""
        
        system_prompt = f"""You are Agent {self.agent_id} developing a complete solution.

{context}

CRITICAL INSTRUCTIONS:
1. You MUST respond with ONLY the complete JSON structure shown below
2. Do NOT include any text before or after the JSON
3. Do NOT use markdown code blocks  
4. Do NOT respond with individual tool calls - include all information in the JSON
5. Even if you want to use tools, describe their usage in the JSON fields
6. For code in JSON: use \\n for newlines, \\" for quotes

Think through the problem and provide a complete solution.

RESPOND IN VALID JSON EXACTLY LIKE THIS EXAMPLE:
{{
  "solution_overview": "Created an interactive calculator with basic operations",
  "research_phase": [
    {{
      "topic": "JavaScript calculator patterns",
      "findings": "CSS Grid for layout, avoid eval() for security, use button event handlers"
    }}
  ],
  "development_phase": [
    {{
      "step": "Create calculator HTML structure",
      "description": "Built display and button grid"
    }}
  ],
  "files_created": [
    {{
      "filename": "calculator.html",
      "purpose": "Main calculator interface with HTML/CSS/JS",
      "content_preview": "<!DOCTYPE html>\\n<html>\\n<head>\\n<title>Calculator</title>..."
    }}
  ],
  "detailed_implementation": "Built calculator using HTML for structure, CSS Grid for button layout, and JavaScript for calculations. Avoided eval() for security.",
  "code_examples": [
    {{
      "language": "html",
      "purpose": "Complete calculator implementation",
      "code": "<!DOCTYPE html>\\n<html>\\n<head>\\n<title>Calculator</title>\\n<style>\\n.calculator {{ display: grid; }}\\n</style>\\n</head>\\n<body>\\n<div class=\\"calculator\\">\\n<input type=\\"text\\" id=\\"display\\">\\n<button onclick=\\"calculate()\\">Calculate</button>\\n</div>\\n<script>\\nfunction calculate() {{ /* logic */ }}\\n</script>\\n</body>\\n</html>",
      "tested": true,
      "test_results": "Calculator displays correctly and performs basic operations"
    }}
  ],
  "testing_approach": "Tested all basic operations (+-*/), edge cases like division by zero, and UI responsiveness",
  "advantages": ["Simple and intuitive UI", "No external dependencies", "Secure - no eval()"],
  "limitations": ["Basic operations only", "No scientific functions"],
  "implementation_time": "30 minutes",
  "confidence": 0.85
}}

IMPORTANT RULES FOR CODE IN JSON:
- Replace all newlines in code with \\n
- Replace all double quotes in code with \\"
- If you have no code yet, use empty arrays for research_phase, development_phase, etc.
- If a tool fails, still include it with result: "failed"
- Always include ALL required fields even if empty

Problem: {problem}

ONLY output the JSON structure above with your actual solution. NO other text!"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Output ONLY the JSON structure for your complete solution to: {problem}\n\nRemember: Output ONLY JSON, no other text!"}
        ]
        
        response = self.call_llm(messages, temperature=temperature, max_tokens=8192)
        
        try:
            json_response = self.extract_json_from_response(response)
            result = json.loads(json_response)
            
            # Validate and ensure all required fields exist
            result = self.validate_solution_fields(result)
            self.log_activity("solution_phase", result)
            return result
            
        except json.JSONDecodeError as e:
            self.log_activity("solution_phase_json_error", {
                "error": str(e),
                "response_preview": response[:500],
                "json_attempt": json_response[:500] if 'json_response' in locals() else "No JSON extracted",
                "error_position": f"line {e.lineno} column {e.colno} (char {e.pos})" if hasattr(e, 'lineno') else "Unknown"
            })
            
            # Extract any code that might be in the response even if JSON failed
            code_match = re.search(r'(<[^>]*>)|(```[\s\S]*?```)', response, re.DOTALL)
            extracted_code = code_match.group(0) if code_match else response[:1000]
            
            # Create fallback solution with extracted content
            fallback_solution = {
                "solution_overview": "Solution attempt with fallback due to JSON parsing error",
                "code_examples": [{
                    "language": "html",
                    "purpose": "Best effort extracted code from response",
                    "code": extracted_code,
                    "tested": False,
                    "test_results": "Not tested due to parsing error"
                }] if extracted_code else [],
                "detailed_implementation": "Used fallback extraction method due to JSON parsing errors",
                "error": f"JSON parse error: {str(e)}"
            }
            
            # Validate and ensure all required fields exist
            fallback_solution = self.validate_solution_fields(fallback_solution)
            return fallback_solution
    
    def enhanced_evaluate_solutions(self, all_solutions: Dict, temperature: float = 0.3) -> Dict[str, Any]:
        """Phase 4: Detailed evaluation of solutions"""
        # Prepare full solutions data for evaluation
        solutions_for_evaluation = {}
        for agent_id, solution in all_solutions.items():
            if isinstance(solution, dict) and "error" not in solution:
                solutions_for_evaluation[agent_id] = {
                    "overview": solution.get("solution_overview", "No overview"),
                    "confidence": solution.get("confidence", 0),
                    "code_examples": solution.get("code_examples", []),
                    "detailed_implementation": solution.get("detailed_implementation", ""),
                    "advantages": solution.get("advantages", []),
                    "limitations": solution.get("limitations", []),
                    "testing_approach": solution.get("testing_approach", ""),
                    "files_created": solution.get("files_created", [])
                }
        
        # Pass ALL solution data - agents need complete info to evaluate properly
        solutions_json = json.dumps(solutions_for_evaluation, indent=2)
        
        system_prompt = f"""You are Agent {self.agent_id} evaluating team solutions.

CRITICAL INSTRUCTIONS:
1. You MUST respond with ONLY valid JSON
2. Do NOT include any text before or after the JSON
3. Do NOT use markdown code blocks
4. If you cannot evaluate properly, still provide scores based on what you can see

Full Solutions Data:
{solutions_json}

You MUST evaluate ALL agents' solutions. Test their code and provide scores.

Evaluate each agent's solution based on the criteria below.

Evaluation Criteria (score each 0.0-1.0):
- technical_quality: Code quality, best practices, error handling
- completeness: Does it fully solve the problem?
- innovation: Creative or elegant approach?
- practicality: Easy to implement and maintain?
- verification_score: Does the code actually work when tested?

RESPOND IN VALID JSON:
{{
  "detailed_evaluations": [
    {{
      "agent_id": "agent_a",
      "technical_quality": 0.8,
      "completeness": 0.9,
      "innovation": 0.7,
      "practicality": 0.85,
      "verification_score": 0.9,
      "overall_score": 0.84,
      "strengths": ["strength 1", "strength 2"],
      "weaknesses": ["weakness 1"],
      "comments": "Detailed analysis including test results",
      "verified_working": true
    }},
    {{
      "agent_id": "agent_b",
      "technical_quality": 0.75,
      "completeness": 0.85,
      "innovation": 0.8,
      "practicality": 0.8,
      "verification_score": 0.85,
      "overall_score": 0.81,
      "strengths": ["different strengths"],
      "weaknesses": ["different weaknesses"],
      "comments": "Detailed analysis",
      "verified_working": true
    }},
    {{
      "agent_id": "agent_c",
      "technical_quality": 0.7,
      "completeness": 0.8,
      "innovation": 0.75,
      "practicality": 0.8,
      "verification_score": 0.8,
      "overall_score": 0.77,
      "strengths": ["strength for c"],
      "weaknesses": ["weakness for c"],
      "comments": "Analysis for agent_c",
      "verified_working": true
    }},
    {{
      "agent_id": "agent_d",
      "technical_quality": 0.65,
      "completeness": 0.75,
      "innovation": 0.7,
      "practicality": 0.75,
      "verification_score": 0.75,
      "overall_score": 0.72,
      "strengths": ["strength for d"],
      "weaknesses": ["weakness for d"],
      "comments": "Analysis for agent_d",
      "verified_working": true
    }}
  ],
  "ranking": ["agent_a", "agent_b", "agent_c", "agent_d"],
  "synthesis_recommendations": "How to combine best elements from different solutions",
  "confidence": 0.9
}}

IMPORTANT: You MUST include ALL FOUR agents (agent_a, agent_b, agent_c, agent_d) in detailed_evaluations!
ONLY output the JSON structure above with your actual evaluations. NO other text!"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": """OUTPUT ONLY JSON. Evaluate ALL 4 agents. Even if they have errors, score what exists. Include agent_a, agent_b, agent_c, and agent_d in detailed_evaluations."""}
        ]
        
        response = self.call_llm(messages, temperature=temperature, max_tokens=4096)
        
        # Check if response is an error or empty
        if not response or response.strip() == "" or response.startswith("Error:"):
            self.log_activity("evaluate_phase_empty_response", {
                "error": "Empty or error response from LLM",
                "response": response[:100] if response else "EMPTY"
            })
            # Return default evaluations so the system can continue
            return self.create_default_evaluations(all_solutions)
        
        try:
            json_response = self.extract_json_from_response(response)
            result = json.loads(json_response)
            
            
            # Ensure all evaluations have overall_score calculated
            if "detailed_evaluations" in result:
                for eval_item in result["detailed_evaluations"]:
                    if "overall_score" not in eval_item:
                        # Calculate overall_score as average of all scores
                        scores = []
                        for key in ["technical_quality", "completeness", "innovation", "practicality", "verification_score"]:
                            if key in eval_item:
                                scores.append(eval_item[key])
                        if scores:
                            eval_item["overall_score"] = sum(scores) / len(scores)
                        else:
                            eval_item["overall_score"] = 0.5
            
            result["agent_id"] = self.agent_id
            result["phase"] = "evaluation"
            self.log_activity("evaluation_phase_with_tools", result)
            return result
            
        except json.JSONDecodeError as e:
            # Provide default evaluations
            default_evaluations = []
            for agent_id in all_solutions.keys():
                if isinstance(all_solutions[agent_id], dict) and "error" not in all_solutions[agent_id]:
                    default_evaluations.append({
                        "agent_id": agent_id,
                        "technical_quality": 0.7,
                        "completeness": 0.7,
                        "innovation": 0.6,
                        "practicality": 0.7,
                        "verification_score": 0.6,
                        "overall_score": 0.66,
                        "strengths": ["Attempted solution"],
                        "weaknesses": ["Could not fully evaluate"],
                        "comments": "Default evaluation due to JSON parsing error",
                        "verified_working": False
                    })
            
            return {
                "verification_tests": [],
                "detailed_evaluations": default_evaluations,
                "ranking": list(all_solutions.keys()),
                "synthesis_recommendations": "Combine best practices from all solutions",
                "confidence": 0.5,
                "agent_id": self.agent_id,
                "phase": "evaluation",
                "error": f"JSON parse error: {str(e)}"
            }
    
    def create_default_evaluations(self, all_solutions: Dict) -> Dict[str, Any]:
        """Create default evaluations when LLM fails"""
        evaluations = []
        
        # Give each solution a basic score based on whether it has code
        for agent_id, solution in all_solutions.items():
            if isinstance(solution, dict) and "error" not in solution:
                # Base score on what's available
                has_code = bool(solution.get('code_examples') or solution.get('complete_code'))
                has_overview = bool(solution.get('solution_overview'))
                base_confidence = solution.get('confidence', 0.5)
                
                # Calculate scores - ensure minimum viable scores to prevent all zeros
                technical = max(0.5, 0.7 if has_code else 0.3)  # Min 0.5 to avoid all zeros
                completeness = max(0.5, 0.8 if has_code and has_overview else 0.4)
                practicality = max(0.5, 0.7 if has_code else 0.4)
                innovation = 0.5  # Default middle value
                verification = 0.5  # Default when not tested
                
                overall_score = (technical + completeness + innovation + practicality + verification) / 5
                overall_score = max(0.3, overall_score)  # Ensure minimum score to prevent all zeros
                
                evaluations.append({
                    "agent_id": agent_id,
                    "technical_quality": technical,
                    "completeness": completeness,
                    "innovation": innovation,
                    "practicality": practicality,
                    "verification_score": verification,
                    "overall_score": overall_score,
                    "strengths": ["Solution provided"] if has_code else ["Attempted solution"],
                    "weaknesses": ["Not fully evaluated due to LLM error"],
                    "comments": "Default evaluation due to LLM failure",
                    "verified_working": False
                })
        
        # Find best agent based on original confidences if available
        best_agent = "agent_a"
        source_confidences = {}
        for agent_id, solution in all_solutions.items():
            if isinstance(solution, dict) and "confidence" in solution:
                source_confidences[agent_id] = solution["confidence"]
        
        if source_confidences:
            best_agent = max(source_confidences.keys(), key=lambda x: source_confidences[x])
        
        return {
            "verification_tests": [],
            "detailed_evaluations": evaluations,
            "ranking": sorted([sol for sol in all_solutions.keys() if isinstance(all_solutions[sol], dict)], 
                            key=lambda x: all_solutions[x].get('confidence', 0), reverse=True),
            "synthesis_recommendations": "Unable to provide detailed synthesis due to evaluation error",
            "confidence": 0.6,  # Higher confidence for fallback
            "best_agent": best_agent,
            "agent_id": self.agent_id,
            "phase": "evaluation",
            "note": "Default evaluation due to LLM response issue"
        }
    
    def implement_consensus(self, consensus: Dict, best_solution: Dict = None, temperature: float = 0.5) -> Dict[str, Any]:
        """Phase 6: Final implementation with tools"""
        context = ""
        if best_solution:
            context = f"Best solution context: {json.dumps(best_solution, indent=2)[:500]}..."
        
        system_prompt = f"""You are Agent {self.agent_id} implementing the final solution.

Consensus: {json.dumps(consensus, indent=2)}
{context}

CRITICAL INSTRUCTIONS:
1. You MUST respond with ONLY valid JSON
2. Do NOT include any text before or after the JSON
3. For code in JSON: use \\n for newlines, \\" for quotes
4. If files contain multiple files, use a dict format for complete_code

Create the best possible implementation based on the consensus.

RESPOND IN VALID JSON EXACTLY LIKE THIS:
{{
  "optimization_notes": ["optimization 1", "optimization 2"],
  "final_implementation": "Complete final solution description",
  "implementation_steps": [
    {{
      "step": "Created main HTML file",
      "type": "file creation",
      "action": "wrote index.html with complete solution",
      "result": "file created successfully"
    }}
  ],
  "complete_code": "<!DOCTYPE html>\\n<html>\\n<head>\\n<title>Solution</title>\\n</head>\\n<body>\\n<h1>Hello</h1>\\n</body>\\n</html>",
  "files_created": [
    {{
      "filename": "final_solution.html",
      "purpose": "main solution file",
      "size": "2.5KB"
    }}
  ],
  "testing_results": [
    {{
      "test_name": "Basic functionality test",
      "test_code": "console.log('test');",
      "result": "test passed",
      "passed": true
    }}
  ],
  "improvements_made": ["Added error handling", "Improved performance"],
  "implementation_time": "30 minutes",
  "final_confidence": 0.95
}}

IMPORTANT:
- For multi-file solutions, complete_code can be a dict: {{"file1.html": "content", "file2.js": "content"}}
- Escape all quotes and newlines in code strings
- Keep arrays empty [] if no items to report
- ONLY output the JSON structure above. NO other text!"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Implement and test the final consensus solution"}
        ]
        
        response = self.call_llm(messages, temperature=temperature, max_tokens=6144)
        
        try:
            json_response = self.extract_json_from_response(response)
            result = json.loads(json_response)
            
            
            result["agent_id"] = self.agent_id
            result["phase"] = "implementation"
            result["confidence"] = result.get("final_confidence", 0.5)
            self.log_activity("implementation_phase_with_tools", result)
            return result
            
        except json.JSONDecodeError as e:
            self.log_activity("implementation_phase_json_error", {"error": str(e), "response_preview": response[:500]})
            return {
                "final_implementation": response[:300] + "..." if len(response) > 300 else response,
                "confidence": 0.3,
                "agent_id": self.agent_id,
                "phase": "implementation",
                "error": f"JSON parse error: {str(e)}"
            }
