#!/usr/bin/env python3
"""
Quick test script for the LLM fix functionality
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.llm_calls import transform_discussion_json
import json

# Sample test data
test_data = [
    {
        "id": "1",
        "speaker": "Alice",
        "text": "This is the root message",
        "target_id": "0"
    },
    {
        "id": "1.1",
        "speaker": "Bob",
        "text": "This is a reply to root",
        "target_id": "1"
    },
    {
        "id": "1.2",
        "speaker": "Charlie",
        "text": "This is another reply to root",
        "target_id": "1"
    },
    {
        "id": "1.1.1",
        "speaker": "Alice",
        "text": "Reply to Bob",
        "target_id": "1.1"
    }
]

print("🧪 Testing LLM transformation...")
print(f"📊 Input has {len(test_data)} flat items")
print()

try:
    result = transform_discussion_json(test_data)
    print()
    print("=" * 60)
    print("📤 RESULT:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    print("✅ Test successful!")
    
except Exception as e:
    print()
    print("❌ Test failed!")
    print(f"Error: {e}")
    sys.exit(1)
