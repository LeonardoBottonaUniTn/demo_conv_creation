from groq import Groq
from dotenv import load_dotenv
import os
import json
import re
from typing import Dict, Any, List
import sys

# Lazily loaded prompt constants to avoid circular imports with the routes package.
_SYSTEM_PROMPT = None
_SYSTEM_BIO_PROMPT = None
_REWRITE_MESSAGE_SYSTEM = None


def _ensure_prompts_loaded() -> None:
    """Import prompt constants from routes.prompt_llm only when first needed.

    This avoids importing the routes package at module import time, which
    previously caused a circular import between scripts.llm_calls and
    routes.llm via routes.__init__.
    """
    global _SYSTEM_PROMPT, _SYSTEM_BIO_PROMPT, _REWRITE_MESSAGE_SYSTEM
    if _SYSTEM_PROMPT is not None:
        return
    from routes.prompt_llm import SYSTEM_PROMPT, SYSTEM_BIO_PROMPT, REWRITE_MESSAGE_SYSTEM

    _SYSTEM_PROMPT = SYSTEM_PROMPT
    _SYSTEM_BIO_PROMPT = SYSTEM_BIO_PROMPT
    _REWRITE_MESSAGE_SYSTEM = REWRITE_MESSAGE_SYSTEM

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
    # Lazily import prompt constants to avoid circular imports
    _ensure_prompts_loaded()
    
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
                    "content": _SYSTEM_PROMPT
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


def generate_user_bio(existing_bio: str, chat_messages: List[str], *, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct", temperature: float = 1.2, max_completion_tokens: int = 2048) -> str:
    """
    Generate a concise third-person user biography paragraph from an existing
    biography and a list of chat messages.

    Returns the generated paragraph as a string. Raises ValueError for missing
    configuration or Exception for API/LLM errors.
    """
    # verify client
    if not client:
        raise ValueError("Groq client not initialized. Check GROQ_API_KEY in the environment.")
    # Ensure system bio prompt is available
    _ensure_prompts_loaded()

    # Build the user message according to the input format described in the prompt
    try:
        messages_json = json.dumps(chat_messages, ensure_ascii=False, indent=2)
    except Exception:
        # fallback: coerce into simple list representation
        messages_json = '[' + ', '.join('"%s"' % str(m).replace('"', '\\"') for m in chat_messages) + ']' 

    user_input = f"# Input\n1. {existing_bio}\n2.{messages_json}\n\n# Output"
    print("User input", user_input)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_BIO_PROMPT},
                {"role": "user", "content": user_input}
            ],
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            top_p=0.9,
            stream=False,
            stop=None,
            seed=42
        )

        # Extract and return the text content
        out = completion.choices[0].message.content.strip()
        return out

    except Exception as e:
        err = str(e)
        print(f"❌ generate_user_bio failed: {err}", file=sys.stderr)
        if "authentication" in err.lower() or "api key" in err.lower():
            raise Exception("Authentication failed. Please check your GROQ_API_KEY in the .env file.")
        elif "rate limit" in err.lower():
            raise Exception("Rate limit exceeded. Please try again later.")
        elif "connection" in err.lower() or "network" in err.lower():
            raise Exception("Network error. Please check your internet connection.")
        else:
            raise

def generate_message_rewrite(message_obj: Dict[str, Any], speaker_profile: Dict[str, Any] = None, messages_in_chat: List[str] = None, *, temperament: str = None, style: str = None, length: str = None, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct", temperature: float = 0.7, max_completion_tokens: int = 512) -> str:
    """
    Rewrite a single chat message using the LLM while preserving meaning.

    Args:
        message_obj: dict with keys like 'speaker', 'text', optionally 'addressees' and 'referenceId'.
        tree_user_messages: optional list of other messages from the same speaker extracted from the tree.
        messages_in_chat: optional list of all messages in the chat (strings) for wider context.

    Returns:
        The rewritten message as a string. Raises Exception on LLM/API errors.
    """
    if not client:
        raise ValueError("Groq client not initialized. Check GROQ_API_KEY in the environment.")
    # Ensure rewrite system prompt is available
    _ensure_prompts_loaded()


    # Build contextual prompt
    context_parts = []
    if speaker_profile:
        context_parts.append(f"1. User Description: \"{speaker_profile.get('description', 'No description available.')}\"")
    if messages_in_chat:
        # include a short excerpt only if provided
        try:
            recent = messages_in_chat[-10:]
        except Exception:
            recent = messages_in_chat
        context_parts.append("2. Conversation History:\n" + json.dumps(recent, ensure_ascii=False, indent=2))


    # If the caller provided guidance for temperament/style/length, add it as a map of instructions
    guidance_instructions = {}
    if temperament:
        guidance_instructions['temperament'] = temperament
    if style:
        guidance_instructions['style'] = style
    if length:      
        guidance_instructions['length'] = length

    guidance_text = json.dumps(guidance_instructions, ensure_ascii=False) if guidance_instructions else ""
    #message just the text, addressees and speaker, all in the fourth point
    message_text = message_obj.get('text', '')
    addressees = message_obj.get('addressees', [])
    speaker = message_obj.get('speaker', '')
    context_parts.append(f"3. \n{guidance_text}")
    context_parts.append(f"4.User’s Draft Message: \n{message_text}\nAddressees: {addressees}\nSpeaker: {speaker}")

    user_prompt = "# Input\n" + "\n".join(context_parts) + "\n\n# Output"
    
    print("User prompt for message rewrite:", user_prompt)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _REWRITE_MESSAGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
            top_p=0.9,
            stream=False,
            stop=None,
            seed=42,
        )

        out = completion.choices[0].message.content.strip()
        # Attempt to extract a clean single-line/paragraph reply (strip surrounding quotes)
        out = out.strip('"\n ')
        print("Rewritten message:", out)
        return out

    except Exception as e:
        err = str(e)
        print(f"❌ generate_message_rewrite failed: {err}", file=sys.stderr)
        if "authentication" in err.lower() or "api key" in err.lower():
            raise Exception("Authentication failed. Please check your GROQ_API_KEY in the .env file.")
        elif "rate limit" in err.lower():
            raise Exception("Rate limit exceeded. Please try again later.")
        elif "connection" in err.lower() or "network" in err.lower():
            raise Exception("Network error. Please check your internet connection.")
        else:
            raise



