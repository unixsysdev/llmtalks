#!/usr/bin/env python3
import re
import json
from typing import Dict, Any

def improved_extract_json(response: str) -> str:
    """Improved JSON extraction that handles more edge cases"""
    print(f"Input response length: {len(response)}")
    print(f"Input preview: {response[:200]}...")
    
    # Remove thinking tags if present
    if "<tool_call>" in response:
        # Try to find JSON after thinking tags
        json_match = re.search(r'<tool_call>\s*({[\s\S]*})', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try without whitespace requirement
            json_match = re.search(r'<tool_call>({[\s\S]*})', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response
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
    
    # Handle common LLM response issues
    # 1. Remove any text before the first {
    first_brace = json_str.find('{')
    if first_brace > 0:
        json_str = json_str[first_brace:]
    
    # 2. Remove any text after the last }
    last_brace = json_str.rfind('}')
    if last_brace > 0 and last_brace < len(json_str) - 1:
        json_str = json_str[:last_brace + 1]
    
    print(f"Extracted JSON length: {len(json_str)}")
    print(f"Extracted JSON preview: {json_str[:200]}...")
    
    return json_str

# Test cases
test_cases = [
    # Normal JSON
    '{"test": "value"}',
    
    # JSON with markdown
    '```json\n{"test": "value"}\n```',
    
    # JSON with thinking tags
    '<tool_call>\n{"test": "value"}',
    
    # JSON with text before
    'Here is my response: {"test": "value"}',
    
    # JSON with text after
    '{"test": "value"} Here is more text',
    
    # Complex JSON with text
    'Sure, here is the JSON:\n```json\n{"analysis": "This is a test", "approach": "Simple approach", "confidence": 0.8}\n```\nLet me know if you need anything else!',
]

print("Testing JSON extraction...")
for i, test_case in enumerate(test_cases):
    print(f"\n=== Test Case {i+1} ===")
    try:
        extracted = improved_extract_json(test_case)
        parsed = json.loads(extracted)
        print(f"✅ Success: {parsed}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse: {e}")
        print(f"Extracted content was: {extracted}")