import json
import time
import redis
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class RedisMultiAgentOrchestrator:
    def __init__(self):
        # Connect to existing Redis instance with password
        redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.Redis(
            host='host.docker.internal', 
            port=6379, 
            password=redis_password,
            decode_responses=True
        )
        
        self.agents = ["agent_a", "agent_b", "agent_c", "agent_d"]
        self.session_id = str(uuid.uuid4())[:8]
        self.debug = False  # Debug mode flag
        
        # Redis channels
        self.task_queue = "agent_tasks"
        self.result_queue = "agent_results"
        self.status_channel = "agent_status"
        
        print(f"🔗 Connected to Redis at host.docker.internal:6379 with auth")
        print(f"🆔 Session ID: {self.session_id}")
        print(f"🤖 Managing agents: {', '.join(self.agents)}")
        
        # Test connection
        try:
            self.redis_client.ping()
            print("✅ Redis authentication successful")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            raise
    
    def send_task_to_agent(self, agent_id: str, phase: str, data: Dict) -> str:
        """Send task to agent via Redis"""
        task_id = f"{self.session_id}_{phase}_{agent_id}_{int(time.time())}"
        
        task = {
            "task_id": task_id,
            "session_id": self.session_id,
            "agent_id": agent_id,
            "phase": phase,
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "status": "pending"
        }
        
        # Push task to Redis queue
        queue_name = f"{self.task_queue}:{agent_id}"
        self.redis_client.lpush(queue_name, json.dumps(task))
        
        print(f"📬 Sent {phase} task to {agent_id}")
        print(f"   📋 Task ID: {task_id}")
        print(f"   📊 Queue: {queue_name}")
        print(f"   📝 Data size: {len(str(data))} chars")
        
        return task_id
    
    def wait_for_result(self, task_id: str, timeout: int = 300) -> Dict:
        """Wait for agent result via Redis with progress updates"""
        start_time = time.time()
        last_update = 0
        
        print(f"⏳ Waiting for result: {task_id}")
        
        while time.time() - start_time < timeout:
            # Check for result
            result_json = self.redis_client.get(f"result:{task_id}")
            if result_json:
                elapsed = time.time() - start_time
                result = json.loads(result_json)
                
                print(f"✅ Got result for {task_id} after {elapsed:.1f}s")
                if isinstance(result, dict):
                    if "confidence" in result:
                        print(f"   🎯 Confidence: {result['confidence']}")
                    if "tools_used" in result:
                        print(f"   🛠️ Tools used: {result['tools_used']}")
                    if "error" in result:
                        print(f"   ❌ Error: {result['error']}")
                
                # Clean up
                self.redis_client.delete(f"result:{task_id}")
                return result
            
            # Progress updates every 10 seconds
            if time.time() - start_time > last_update + 10:
                elapsed = time.time() - start_time
                print(f"   ⏳ Still waiting for {task_id} ({elapsed:.0f}s elapsed)")
                last_update = elapsed
            
            time.sleep(0.5)
        
        print(f"⏰ Timeout waiting for {task_id} after {timeout}s")
        return {"error": f"Timeout waiting for {task_id}"}
    
    def run_parallel_phase(self, phase: str, phase_data: Dict, timeout: int = 300) -> Dict[str, Any]:
        """Run phase with all agents in parallel via Redis"""
        print(f"\n🚀 Starting parallel {phase} phase...")
        print(f"📊 Phase data size: {len(str(phase_data))} chars")
        print(f"⏱️ Timeout: {timeout}s")
        
        # Send tasks to all agents
        task_ids = {}
        for agent_id in self.agents:
            task_id = self.send_task_to_agent(agent_id, phase, phase_data)
            task_ids[agent_id] = task_id
        
        print(f"📬 Sent {len(task_ids)} tasks to Redis queues")
        print("🔄 Starting parallel execution...")
        
        # Wait for all results in parallel
        results = {}
        completed_count = 0
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_agent = {
                executor.submit(self.wait_for_result, task_id, timeout): agent_id 
                for agent_id, task_id in task_ids.items()
            }
            
            for future in as_completed(future_to_agent):
                agent_id = future_to_agent[future]
                completed_count += 1
                
                try:
                    result = future.result()
                    results[agent_id] = result
                    
                    print(f"✅ {agent_id} completed {phase} ({completed_count}/{len(self.agents)})")
                    
                    if "error" not in result:
                        if "confidence" in result:
                            confidence = result["confidence"]
                            print(f"   🎯 Confidence: {confidence}")
                        if "tools_used" in result:
                            tools = result["tools_used"]
                            print(f"   🛠️ Tools: {tools}")
                        if isinstance(result, dict):
                            # Show content sizes
                            if "analysis" in result:
                                print(f"   📊 Analysis: {len(result['analysis'])} chars")
                            if "solution_overview" in result:
                                print(f"   💡 Solution: {len(result['solution_overview'])} chars")
                            if "detailed_evaluations" in result:
                                print(f"   🔍 Evaluations: {len(result['detailed_evaluations'])} items")
                    else:
                        print(f"   ❌ Error: {result['error']}")
                        
                except Exception as e:
                    print(f"💥 {agent_id} exception: {e}")
                    results[agent_id] = {"error": str(e)}
        
        print(f"🎉 Phase {phase} completed! {completed_count} agents finished")
        success_count = len([r for r in results.values() if "error" not in r])
        print(f"📊 Success rate: {success_count}/{len(self.agents)} agents")
        
        # Show phase-specific debug info if debug mode is enabled
        if self.debug:
            self.show_phase_debug(phase, results)
        
        return results
    
    def build_consensus(self, evaluation_results: Dict, solution_results: Dict = None) -> Dict[str, Any]:
        """Build consensus from evaluation results"""
        print("\n" + "="*60)
        print("🤝 BUILDING CONSENSUS FROM EVALUATIONS")
        print("="*60)
        
        all_scores = {}
        confidence_scores = []
        evaluation_details = []
        
        for evaluator_id, evaluation in evaluation_results.items():
            if isinstance(evaluation, dict) and "error" not in evaluation:
                print(f"\n📊 Evaluator: {evaluator_id}")
                print(f"   Confidence: {evaluation.get('confidence', 'N/A')}")
                
                if "detailed_evaluations" in evaluation:
                    print(f"   Evaluations given:")
                    for eval_item in evaluation["detailed_evaluations"]:
                        eval_agent = eval_item.get("agent_id")
                        score = eval_item.get("overall_score", 0)
                        
                        # Show detailed scores
                        print(f"\n      🎯 {eval_agent}:")
                        print(f"         Overall Score: {score}")
                        print(f"         Technical Quality: {eval_item.get('technical_quality', 'N/A')}")
                        print(f"         Completeness: {eval_item.get('completeness', 'N/A')}")
                        print(f"         Innovation: {eval_item.get('innovation', 'N/A')}")
                        print(f"         Practicality: {eval_item.get('practicality', 'N/A')}")
                        print(f"         Verification: {eval_item.get('verification_score', 'N/A')}")
                        print(f"         Comments: {eval_item.get('comments', 'None')[:100]}...")
                        
                        if eval_agent:
                            if eval_agent not in all_scores:
                                all_scores[eval_agent] = []
                            all_scores[eval_agent].append(score)
                            
                        evaluation_details.append({
                            "evaluator": evaluator_id,
                            "evaluated": eval_agent,
                            "score": score,
                            "details": eval_item
                        })
                
                if "confidence" in evaluation:
                    confidence_scores.append(evaluation["confidence"])
            else:
                print(f"\n❌ Evaluator {evaluator_id} had error: {evaluation.get('error', 'Unknown error')}")
        
        # Calculate consensus
        consensus_scores = {}
        print(f"\n📈 CONSENSUS CALCULATION:")
        for agent_id, scores in all_scores.items():
            if scores:
                avg_score = sum(scores) / len(scores)
                consensus_scores[agent_id] = avg_score
                print(f"   {agent_id}: {avg_score:.3f} (from {len(scores)} evaluations: {[f'{s:.2f}' for s in scores]})")
        
        # Handle case where all consensus scores are 0 or invalid
        if not consensus_scores or all(score == 0 for score in consensus_scores.values()):
            print("❌ ALL AGENTS RETURNED CONFIDENCE = 0 - FALLING BACK TO HIGHEST SOURCE CONFIDENCE")
            # Fallback to original solution confidences if available
            source_confidences = {}
            if solution_results:
                for agent_id, solution in solution_results.items():
                    if isinstance(solution, dict) and "confidence" in solution:
                        source_confidences[agent_id] = solution["confidence"]
            
            if source_confidences:
                best_agent = max(source_confidences.keys(), key=lambda x: source_confidences[x])
                print(f"   🎯 Fallback best agent: {best_agent} (confidence: {source_confidences[best_agent]:.3f})")
            else:
                best_agent = "agent_a"
                print("   ⚠️  No valid source confidences found, using agent_a")
        else:
            best_agent = max(consensus_scores.keys(), key=lambda x: consensus_scores[x]) if consensus_scores else "agent_a"
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        
        print(f"\n🏆 FINAL RANKINGS:")
        for i, (agent_id, score) in enumerate(sorted(consensus_scores.items(), key=lambda x: x[1], reverse=True), 1):
            print(f"   {i}. {agent_id}: {score:.3f}")
        
        print(f"\n🏆 Best solution: {best_agent} (score: {consensus_scores.get(best_agent, 0):.3f})")
        print(f"🎯 Average evaluator confidence: {avg_confidence:.3f}")
        print("="*60)
        
        return {
            "best_agent": best_agent,
            "consensus_scores": consensus_scores,
            "confidence": avg_confidence,
            "total_evaluators": len([r for r in evaluation_results.values() if "error" not in r]),
            "evaluation_details": evaluation_details
        }
    
    def show_phase_debug(self, phase: str, results: Dict[str, Any]):
        """Show detailed debug info after each phase"""
        print("\n" + "="*60)
        print(f"🔍 PHASE DEBUG: {phase.upper()}")
        print("="*60)
        
        # Rank agents by confidence
        rankings = []
        for agent_id, result in results.items():
            if isinstance(result, dict):
                confidence = result.get('confidence', 0)
                error = result.get('error', None)
                rankings.append((agent_id, confidence, error, result))
        
        rankings.sort(key=lambda x: x[1], reverse=True)
        
        print("\n📊 AGENT RANKINGS BY CONFIDENCE:")
        for i, (agent_id, confidence, error, result) in enumerate(rankings, 1):
            status = "❌ ERROR" if error else "✅ SUCCESS"
            print(f"   {i}. {agent_id}: {confidence:.2f} {status}")
            if error:
                print(f"      Error: {error[:100]}...")
        
        # Phase-specific details
        success_count = len([r for r in results.values() if isinstance(r, dict) and "error" not in r])
        if phase == "plan" and success_count > 0:
            print("\n📋 PLANNING APPROACHES:")
            for agent_id, conf, err, result in rankings[:3]:  # Top 3
                if not err:
                    approach = result.get('recommended_approach', 'N/A')
                    print(f"\n   {agent_id}: {approach[:200]}...")
        
        elif phase == "analyze" and success_count > 0:
            print("\n🧠 ANALYSIS HIGHLIGHTS:")
            for agent_id, conf, err, result in rankings[:3]:
                if not err:
                    analysis = result.get('deep_analysis', 'N/A')
                    print(f"\n   {agent_id}: {analysis[:200]}...")
        
        elif phase == "solve" and success_count > 0:
            print("\n💡 SOLUTION PREVIEWS:")
            for agent_id, conf, err, result in rankings[:3]:
                if not err:
                    overview = result.get('solution_overview', 'N/A')
                    print(f"\n   {agent_id} ({conf:.2f}): {overview[:150]}...")
                    
                    # Show code preview
                    if 'code_examples' in result and result['code_examples']:
                        code = result['code_examples'][0].get('code', '')[:200]
                        print(f"      Code: {code}...")
        
        elif phase == "implement" and success_count > 0:
            print("\n🔨 IMPLEMENTATION DIFFERENCES:")
            implementations = [(aid, r) for aid, _, err, r in rankings if not err and 'complete_code' in r]
            
            if len(implementations) >= 2:
                # Compare first two implementations
                agent1, impl1 = implementations[0]
                agent2, impl2 = implementations[1]
                
                code1 = str(impl1.get('complete_code', ''))[:300]
                code2 = str(impl2.get('complete_code', ''))[:300]
                
                print(f"\n   {agent1} vs {agent2}:")
                print(f"   {agent1}: {code1}...")
                print(f"   {agent2}: {code2}...")
                
                # Show improvements
                for agent_id, impl in implementations[:3]:
                    improvements = impl.get('improvements_made', [])
                    if improvements:
                        print(f"\n   {agent_id} improvements: {', '.join(improvements[:3])}")
        
        print("="*60)
    
    def collaborative_solve(self, problem: str) -> Dict[str, Any]:
        """6-phase parallel collaborative problem solving"""
        print(f"🚀 Starting Redis-based parallel collaboration...")
        print(f"📋 Problem: {problem}")
        print(f"🆔 Session: {self.session_id}")
        print(f"⚡ Parallel agents: {len(self.agents)}")
        
        all_results = {
            "problem": problem,
            "session_id": self.session_id,
            "phases": {},
            "started_at": datetime.now().isoformat()
        }
        
        # Phase 1: Parallel Planning
        print("\n" + "="*60)
        print("📋 PHASE 1: Parallel Strategic Planning")
        print("🎯 Each agent will research and create strategic plans")
        planning_results = self.run_parallel_phase("plan", {
            "problem": problem,
            "instructions": "Research thoroughly and create a comprehensive strategic plan."
        })
        all_results["phases"]["planning"] = planning_results
        
        # Phase 2: Parallel Deep Analysis
        print("\n" + "="*60)
        print("🧠 PHASE 2: Parallel Deep Analysis")
        print("🎯 Each agent will analyze the problem in depth")
        analysis_results = self.run_parallel_phase("analyze", {
            "problem": problem,
            "planning_context": planning_results
        })
        all_results["phases"]["analysis"] = analysis_results
        
        # Phase 3: Parallel Solution Development
        print("\n" + "="*60)
        print("💡 PHASE 3: Parallel Solution Development")
        print("🎯 Each agent will build and test complete solutions")
        solution_results = self.run_parallel_phase("solve", {
            "problem": problem,
            "planning_context": planning_results,
            "analysis_context": analysis_results
        })
        all_results["phases"]["solutions"] = solution_results
        
        # Phase 4: Parallel Cross-Evaluation
        print("\n" + "="*60)
        print("🔍 PHASE 4: Parallel Cross-Evaluation")
        print("🎯 Each agent will evaluate and test all solutions")
        evaluation_results = self.run_parallel_phase("evaluate", {
            "problem": problem,
            "all_solutions": solution_results
        })
        all_results["phases"]["evaluations"] = evaluation_results
        
        # Phase 5: Consensus Building
        print("\n" + "="*60)
        print("🤝 PHASE 5: Consensus Building")
        consensus = self.build_consensus(evaluation_results, solution_results)
        all_results["phases"]["consensus"] = consensus
        
        # Phase 6: Parallel Final Implementation
        print("\n" + "="*60)
        print("🔨 PHASE 6: Parallel Final Implementation")
        print(f"🎯 All agents will implement the consensus solution from {consensus['best_agent']}")
        implementation_results = self.run_parallel_phase("implement", {
            "problem": problem,
            "consensus": consensus,
            "best_solution": solution_results.get(consensus["best_agent"], {})
        })
        all_results["phases"]["implementations"] = implementation_results
        
        # Select final result
        best_implementation = self.select_best_implementation(implementation_results)
        all_results["final_result"] = best_implementation
        all_results["completed_at"] = datetime.now().isoformat()
        
        return all_results
    
    def select_best_implementation(self, implementations: Dict) -> Dict:
        """Select best implementation"""
        print("🏆 Selecting best final implementation...")
        
        best_impl = None
        best_score = 0
        
        for agent_id, impl in implementations.items():
            if isinstance(impl, dict) and "error" not in impl:
                confidence = impl.get("confidence", 0)
                print(f"   🎯 {agent_id}: confidence {confidence}")
                if confidence > best_score:
                    best_score = confidence
                    best_impl = {
                        "agent_id": agent_id,
                        "implementation": impl,
                        "confidence": confidence
                    }
        
        if best_impl:
            print(f"🏆 Best implementation: {best_impl['agent_id']} (confidence: {best_score})")
        else:
            print("❌ No valid implementations found")
        
        return best_impl or {"error": "No valid implementations"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python redis_orchestrator.py '<problem>' [--debug|-d]")
        print("  --debug or -d: Enable detailed debug output")
        sys.exit(1)
    
    problem = sys.argv[1]
    debug = "--debug" in sys.argv or "-d" in sys.argv
    
    orchestrator = RedisMultiAgentOrchestrator()
    orchestrator.debug = debug
    
    if debug:
        print("🐛 DEBUG MODE ENABLED")
    
    result = orchestrator.collaborative_solve(problem)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Create organized directory structure
    # Use absolute path for container compatibility
    base_path = Path("/app")
    solution_dir = base_path / "orchestrator" / "solutions" / f"{timestamp}_{result['session_id']}"
    print(f"\n📁 Creating solution directory: {solution_dir}")
    solution_dir.mkdir(parents=True, exist_ok=True)
    
    # Verify it was created
    if solution_dir.exists():
        print(f"✅ Directory created successfully")
    else:
        print(f"❌ ERROR: Failed to create directory!")
    
    # Save full log
    results_file = solution_dir / "collaboration_log.json"
    with open(results_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    # Save problem description
    with open(solution_dir / "problem.txt", 'w') as f:
        f.write(problem)
    
    # Extract and save the actual solution code
    solution_saved = False
    if isinstance(result.get('final_result'), dict) and 'implementation' in result['final_result']:
        impl = result['final_result']['implementation']
        
        # Create solution subdirectory
        code_dir = f"{solution_dir}/solution"
        Path(code_dir).mkdir(exist_ok=True)
        
        # Check for complete_code
        if 'complete_code' in impl:
            complete_code = impl['complete_code']
            
            if isinstance(complete_code, dict):
                # Multiple files
                for filename, content in complete_code.items():
                    filepath = f"{code_dir}/{filename}"
                    with open(filepath, 'w') as f:
                        f.write(content)
                    print(f"   📄 Saved: {filepath}")
                solution_saved = True
            elif isinstance(complete_code, str):
                # Single file
                filepath = f"{code_dir}/solution.html"
                with open(filepath, 'w') as f:
                    f.write(complete_code)
                print(f"   📄 Saved: {filepath}")
                solution_saved = True
        
        # Fall back to code_examples if no complete_code
        elif 'code_examples' in impl and impl['code_examples']:
            for i, example in enumerate(impl['code_examples']):
                if 'code' in example:
                    ext = example.get('language', 'txt')
                    if ext == 'javascript': ext = 'js'
                    elif ext == 'python': ext = 'py'
                    
                    filename = f"solution_{i+1}.{ext}"
                    filepath = f"{code_dir}/{filename}"
                    with open(filepath, 'w') as f:
                        f.write(example['code'])
                    print(f"   📄 Saved: {filepath}")
                    solution_saved = True
    
    # If still no solution saved, try solutions phase
    if not solution_saved and 'phases' in result and 'solutions' in result['phases']:
        code_dir = f"{solution_dir}/solution"
        Path(code_dir).mkdir(exist_ok=True)
        
        # Get best solution from consensus or confidence
        best_agent = result.get('final_result', {}).get('agent_id')
        if not best_agent and 'phases' in result and 'consensus' in result['phases']:
            best_agent = result['phases']['consensus'].get('best_agent')
        
        if best_agent and best_agent in result['phases']['solutions']:
            solution = result['phases']['solutions'][best_agent]
            if 'code_examples' in solution:
                for i, example in enumerate(solution['code_examples']):
                    if 'code' in example:
                        ext = example.get('language', 'txt')
                        if ext == 'javascript': ext = 'js'
                        elif ext == 'python': ext = 'py'
                        
                        filename = f"solution_{i+1}.{ext}"
                        filepath = f"{code_dir}/{filename}"
                        with open(filepath, 'w') as f:
                            f.write(example['code'])
                        print(f"   📄 Saved: {filepath}")
                        solution_saved = True
    
    if solution_saved:
        print(f"\n✅ Solution code saved to: {solution_dir}/solution/")
    
    print(f"\n🎉 Collaboration completed!")
    print(f"📁 All files saved to: {solution_dir}/")
    print(f"🏆 Final solution by: {result['final_result'].get('agent_id', 'unknown')}")
    print(f"🎯 Final confidence: {result['final_result'].get('confidence', 0)}")
    
    # Display the actual final solution
    print("\n" + "="*60)
    print("📝 FINAL SOLUTION:")
    print("="*60)
    
    if isinstance(result.get('final_result'), dict) and 'implementation' in result['final_result']:
        impl = result['final_result']['implementation']
        
        # Show the final implementation details
        if 'final_implementation' in impl:
            print(f"\n📋 Implementation Summary:")
            print(f"{impl['final_implementation']}")
        
        # Show the complete code if available
        if 'complete_code' in impl:
            print(f"\n💻 Complete Code:")
            print("-"*60)
            complete_code = impl['complete_code']
            if isinstance(complete_code, dict):
                # Multiple files
                for filename, content in complete_code.items():
                    print(f"\n📄 {filename}:")
                    print("-"*40)
                    print(content[:1000] + "..." if len(content) > 1000 else content)
            else:
                # Single file
                print(complete_code[:2000] + "..." if len(complete_code) > 2000 else complete_code)
            print("-"*60)
        
        # Show code examples if no complete code
        elif 'code_examples' in impl and impl['code_examples']:
            print(f"\n💻 Code Examples:")
            for i, example in enumerate(impl['code_examples']):
                print(f"\n--- Example {i+1}: {example.get('purpose', 'Code')} ---")
                print(f"Language: {example.get('language', 'unknown')}")
                print(example.get('code', 'No code available'))
                print("-"*60)
        
        # Show files created
        if 'files_created' in impl and impl['files_created']:
            print(f"\n📁 Files Created:")
            for file_info in impl['files_created']:
                print(f"  - {file_info.get('filename', 'unknown')}: {file_info.get('purpose', 'No description')}")
        
        # Show improvements made
        if 'improvements_made' in impl and impl['improvements_made']:
            print(f"\n✨ Improvements Made:")
            for improvement in impl['improvements_made']:
                print(f"  - {improvement}")
    else:
        print("\n❌ No valid final solution found!")
        print("\nChecking individual agent solutions...")
        
        # Try to show best solution from solution phase
        if 'phases' in result and 'solutions' in result['phases']:
            solutions = result['phases']['solutions']
            best_solution = None
            best_confidence = 0
            
            for agent_id, solution in solutions.items():
                if isinstance(solution, dict) and solution.get('confidence', 0) > best_confidence:
                    best_solution = solution
                    best_confidence = solution['confidence']
            
            if best_solution:
                print(f"\n📋 Best Solution (confidence: {best_confidence}):")
                if 'solution_overview' in best_solution:
                    print(f"\nOverview: {best_solution['solution_overview']}")
                if 'code_examples' in best_solution and best_solution['code_examples']:
                    print(f"\n💻 Code:")
                    for example in best_solution['code_examples']:
                        print("-"*60)
                        print(example.get('code', 'No code available'))
                        print("-"*60)
                        break  # Just show first example
