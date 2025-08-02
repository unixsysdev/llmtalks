#!/usr/bin/env python3
"""Extract and save the final solution from collaboration logs"""

import json
import sys
from pathlib import Path
from datetime import datetime

def extract_solution(log_file):
    """Extract the final solution from a collaboration log file"""
    
    with open(log_file, 'r') as f:
        data = json.load(f)
    
    problem = data.get('problem', 'Unknown problem')
    print(f"\n📋 Problem: {problem[:100]}...")
    
    # Try to get final implementation
    final_code = None
    agent_id = "unknown"
    
    if 'final_result' in data and isinstance(data['final_result'], dict):
        if 'implementation' in data['final_result']:
            impl = data['final_result']['implementation']
            agent_id = data['final_result'].get('agent_id', 'unknown')
            
            # Try different fields for code
            if 'complete_code' in impl:
                final_code = impl['complete_code']
            elif 'code_examples' in impl and impl['code_examples']:
                # Get the first complete code example
                for example in impl['code_examples']:
                    if 'code' in example:
                        final_code = example['code']
                        break
    
    # If no final implementation, try to get from solutions phase
    if not final_code and 'phases' in data and 'solutions' in data['phases']:
        solutions = data['phases']['solutions']
        best_confidence = 0
        
        for aid, solution in solutions.items():
            if isinstance(solution, dict) and solution.get('confidence', 0) > best_confidence:
                if 'code_examples' in solution and solution['code_examples']:
                    for example in solution['code_examples']:
                        if 'code' in example:
                            final_code = example['code']
                            agent_id = aid
                            best_confidence = solution['confidence']
                            break
    
    if final_code:
        # Check if it's a dictionary of files or a single file
        if isinstance(final_code, dict):
            # Multiple files - save each one
            saved_files = []
            for filename, content in final_code.items():
                with open(filename, 'w') as f:
                    f.write(content)
                saved_files.append(filename)
            
            print(f"\n✅ Solution extracted from agent: {agent_id}")
            print(f"📁 Saved files: {', '.join(saved_files)}")
            
            # Show the main HTML file if it exists
            if 'index.html' in final_code:
                print(f"\n📊 Main file preview (index.html):")
                print("-" * 60)
                preview = final_code['index.html']
                print(preview[:500] + "..." if len(preview) > 500 else preview)
                print("-" * 60)
            
            return saved_files
        else:
            # Single file - save as before
            output_file = f"solution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            with open(output_file, 'w') as f:
                f.write(final_code)
            
            print(f"\n✅ Solution extracted from agent: {agent_id}")
            print(f"📁 Saved to: {output_file}")
            print(f"\n📊 Solution preview:")
            print("-" * 60)
            print(final_code[:500] + "..." if len(final_code) > 500 else final_code)
            print("-" * 60)
            
            return output_file
    else:
        print("\n❌ No solution code found in the log file!")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        # Try to find the most recent log file
        log_dir = Path("orchestrator/logs")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("redis_collaboration_*.json"))
            if log_files:
                log_file = log_files[-1]
                print(f"Using most recent log: {log_file}")
                extract_solution(log_file)
            else:
                print("No collaboration logs found!")
        else:
            print("Usage: python extract_solution.py <log_file>")
            print("   or: python extract_solution.py  (uses most recent log)")
    else:
        extract_solution(sys.argv[1])