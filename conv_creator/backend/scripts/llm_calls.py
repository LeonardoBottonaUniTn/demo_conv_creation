from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
from typing import Dict, Any, List
import sys

# Load environment variables from .env file
# Try multiple locations: backend/.env, then conv_creator/.env
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')

# If .env doesn't exist in backend, try parent directory (conv_creator)
if not os.path.exists(env_path):
    parent_dir = os.path.dirname(backend_dir)
    env_path = os.path.join(parent_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
    print(f"📝 Loaded .env from: {env_path}", file=sys.stderr)
else:
    # Try default dotenv loading (checks current directory and parents)
    load_dotenv()
    print(f"⚠️  No .env file found at expected locations", file=sys.stderr)

# Initialize Groq client
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    error_msg = (
        "GROQ_API_KEY not found in environment variables. "
        f"Please create a .env file with your API key.\n"
        f"Checked locations: {env_path}"
    )
    print(f"❌ {error_msg}", file=sys.stderr)
    raise ValueError(error_msg)

try:
    client = Groq(api_key=api_key)
    print(f"✅ Groq client initialized successfully", file=sys.stderr)
except Exception as e:
    error_msg = f"Failed to initialize Groq client: {e}"
    print(f"❌ {error_msg}", file=sys.stderr)
    raise

SYSTEM_PROMPT = """You are a precise data transformation assistant.
You must convert input JSON into a new JSON tree that follows this schema exactly:

{
    "id": "string",
    "speaker": "string",
    "text": "string",
    "children": "list"
}

### Transformation Rules
- Output must be valid JSON only — no text or explanations.
- Each node must follow the schema exactly.
- The "children" field must always be a list.
- Only include child nodes that actually exist in the input or are logically derived from it.
- Never add empty or placeholder nodes.
- If a node has no children, its "children" must be an empty list [].
- Do not invent extra hierarchy levels.
- If any field value is missing in the input:
  - use "" for id, speaker, or text
  - use [] for children
- IDs should reflect hierarchy (e.g. "1", "1.1", "1.2", "2").
- The output must contain only valid JSON that can be parsed directly.

### Validation Rule
After constructing the JSON:
- **Remove any node** where speaker == "" AND text == "" AND children == [].
- Ensure no child has all empty fields.
Return the cleaned, valid JSON tree only."""


def extract_json_from_text(text: str) -> str:
    """
    Extract JSON from text that might contain additional content.
    
    Args:
        text: Raw text that may contain JSON
    
    Returns:
        str: Extracted JSON string
    """
    text = text.strip()
    
    # Try to find JSON object or array boundaries
    first_brace = text.find('{')
    first_bracket = text.find('[')
    
    # Determine which comes first
    if first_brace == -1 and first_bracket == -1:
        return text
    
    if first_brace == -1:
        start_pos = first_bracket
        start_char = '['
        end_char = ']'
    elif first_bracket == -1:
        start_pos = first_brace
        start_char = '{'
        end_char = '}'
    else:
        start_pos = min(first_brace, first_bracket)
        start_char = text[start_pos]
        end_char = ']' if start_char == '[' else '}'
    
    # Count braces/brackets to find the matching closing character
    count = 0
    end_pos = -1
    
    for i in range(start_pos, len(text)):
        if text[i] == start_char:
            count += 1
        elif text[i] == end_char:
            count -= 1
            if count == 0:
                end_pos = i
                break
    
    if end_pos != -1:
        return text[start_pos:end_pos + 1]
    
    return text


def fix_incomplete_json(json_text: str) -> str:
    """
    Attempt to fix common JSON syntax errors.
    
    Args:
        json_text: Potentially malformed JSON string
    
    Returns:
        str: Fixed JSON string
    """
    # Remove trailing commas before closing braces/brackets
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
    
    # Ensure proper closing of the JSON
    open_braces = json_text.count('{')
    close_braces = json_text.count('}')
    if open_braces > close_braces:
        json_text += '}' * (open_braces - close_braces)
    
    open_brackets = json_text.count('[')
    close_brackets = json_text.count(']')
    if open_brackets > close_brackets:
        json_text += ']' * (open_brackets - close_brackets)
    
    return json_text


def transform_discussion_json(input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Transform a flat discussion JSON into the hierarchical tree structure.
    
    Args:
        input_data: List of discussion items with id, speaker, text, target_id
    
    Returns:
        Dict: Hierarchical JSON tree following the schema
        
    Raises:
        ValueError: If API key is not set
        Exception: If LLM call fails or JSON parsing fails
    """
    # Verify client is initialized
    if not client:
        raise ValueError("Groq client not initialized. Check API key configuration.")
    
    user_prompt = f"""Transform the following JSON into the target schema.

### Input JSON

{json.dumps(input_data, ensure_ascii=False, indent=2)}


Make sure that the output ends **immediately** after the last valid closing bracket.
If you produce an empty node or any content after the valid JSON tree, delete it before returning.

### Output JSON"""
    
    try:
        print("📤 Sending request to Groq API...")
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0,
            max_completion_tokens=8192,
            top_p=0.7,
            stream=False,
            stop=None,
            seed=42
        )
        
        print("📥 Received response from Groq API")
        result = completion.choices[0].message.content.strip()
        
        # Extract JSON from the response
        json_text = extract_json_from_text(result)
        
        # Try to parse the JSON
        try:
            json_output = json.loads(json_text)
            print("✅ Successfully parsed JSON from LLM")
            return json_output
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print(f"   Attempting to fix incomplete JSON...")
            
            # Try to salvage partial JSON
            fixed_json = fix_incomplete_json(json_text)
            json_output = json.loads(fixed_json)
            print("✅ Recovered by fixing incomplete JSON")
            return json_output
            
    except ValueError as e:
        # Re-raise ValueError for API key issues
        print(f"❌ Configuration error: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"   Raw LLM output: {result[:500] if 'result' in locals() else 'N/A'}")
        raise Exception(f"Could not parse LLM output as JSON: {e}")
    except Exception as e:
        error_msg = str(e)
        print(f"❌ LLM call failed: {error_msg}")
        
        # Provide more specific error messages
        if "authentication" in error_msg.lower() or "api key" in error_msg.lower():
            raise Exception("Authentication failed. Please check your GROQ_API_KEY in the .env file.")
        elif "rate limit" in error_msg.lower():
            raise Exception("Rate limit exceeded. Please try again later.")
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            raise Exception("Network error. Please check your internet connection.")
        else:
            raise Exception(f"LLM API error: {error_msg}")


if __name__ == "__main__":
    # Test example
    test_data = [
        {
            "id": "1",
            "speaker": "OG",
            "text": "Water is a basic human right and over a billion people lack reliable access to safe drinking water.",
            "target_id": "0"
        },
        {
            "id": "1.1",
            "speaker": "OO",
            "text": "Not all water sources cross borders; many are contained within one country making sovereignty over water legitimate.",
            "target_id": "1"
        }
    ]
    
    print("Testing LLM transformation...")
    result = transform_discussion_json(test_data)
    print("\nResult:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
