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
    """Import prompt constants from routes.prompt_llm only when first needed."""
    global _SYSTEM_PROMPT, _SYSTEM_BIO_PROMPT, _REWRITE_MESSAGE_SYSTEM
    if _SYSTEM_PROMPT is not None:
        return
    from routes.prompt_llm import SYSTEM_PROMPT, SYSTEM_BIO_PROMPT, REWRITE_MESSAGE_SYSTEM

    _SYSTEM_PROMPT = SYSTEM_PROMPT
    _SYSTEM_BIO_PROMPT = SYSTEM_BIO_PROMPT
    _REWRITE_MESSAGE_SYSTEM = REWRITE_MESSAGE_SYSTEM


# Load environment variables from .env file
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(backend_dir, '.env')

if not os.path.exists(env_path):
    parent_dir = os.path.dirname(backend_dir)
    env_path = os.path.join(parent_dir, '.env')

if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    load_dotenv()


def _create_client(provider: str, api_key: str):
    if provider == "groq":
        from groq import Groq
        return Groq(api_key=api_key)
    if provider == "openai":
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    raise ValueError(f"Unsupported LLM provider: {provider}")


def _chat_completion(
    *,
    provider: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_completion_tokens: int,
    top_p: float = 0.9,
    seed: int = 42,
) -> str:
    client = _create_client(provider, api_key)
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "stream": False,
        "seed": seed,
    }
    if provider == "groq":
        kwargs["max_completion_tokens"] = max_completion_tokens
        kwargs["stop"] = None
    else:
        kwargs["max_tokens"] = max_completion_tokens

    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content.strip()


def _format_llm_error(provider: str, err: str) -> Exception:
    provider_label = provider.upper()
    if "authentication" in err.lower() or "api key" in err.lower() or "invalid_api_key" in err.lower():
        return Exception(f"Authentication failed. Please check your {provider_label} API key in Settings.")
    if "rate limit" in err.lower():
        return Exception("Rate limit exceeded. Please try again later.")
    if "connection" in err.lower() or "network" in err.lower():
        return Exception("Network error. Please check your internet connection.")
    if "model_not_found" in err.lower() or "does not exist" in err.lower():
        return Exception(
            f"The selected model is unavailable on {provider_label}. "
            "Open Settings → API Settings and choose a supported model."
        )
    return Exception(f"LLM API error: {err}")


def extract_json_from_text(text: str) -> str:
    """Extract JSON from text that might contain additional content."""
    text = text.strip()

    first_brace = text.find('{')
    first_bracket = text.find('[')

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
    """Attempt to fix common JSON syntax errors."""
    json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

    open_braces = json_text.count('{')
    close_braces = json_text.count('}')
    if open_braces > close_braces:
        json_text += '}' * (open_braces - close_braces)

    open_brackets = json_text.count('[')
    close_brackets = json_text.count(']')
    if open_brackets > close_brackets:
        json_text += ']' * (open_brackets - close_brackets)

    return json_text


def transform_discussion_json(
    input_data: List[Dict[str, Any]],
    *,
    provider: str,
    api_key: str,
    model: str,
) -> Dict[str, Any]:
    """Transform a flat discussion JSON into the hierarchical tree structure."""
    if not api_key:
        raise ValueError("LLM API key is not configured.")
    _ensure_prompts_loaded()

    user_prompt = f"""Transform the following JSON into the target schema.

### Input JSON

{json.dumps(input_data, ensure_ascii=False, indent=2)}


Make sure that the output ends **immediately** after the last valid closing bracket.
If you produce an empty node or any content after the valid JSON tree, delete it before returning.

### Output JSON"""

    try:
        print(f"📤 Sending request to {provider.upper()} API...")
        result = _chat_completion(
            provider=provider,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=8192,
            top_p=0.7,
        )

        print(f"📥 Received response from {provider.upper()} API")
        json_text = extract_json_from_text(result)

        try:
            json_output = json.loads(json_text)
            print("✅ Successfully parsed JSON from LLM")
            return json_output
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON parsing failed: {e}")
            print("   Attempting to fix incomplete JSON...")
            fixed_json = fix_incomplete_json(json_text)
            json_output = json.loads(fixed_json)
            print("✅ Recovered by fixing incomplete JSON")
            return json_output

    except ValueError:
        raise
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing failed: {e}")
        print(f"   Raw LLM output: {result[:500] if 'result' in locals() else 'N/A'}")
        raise Exception(f"Could not parse LLM output as JSON: {e}") from e
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        raise _format_llm_error(provider, str(e)) from e


def generate_user_bio(
    existing_bio: str,
    chat_messages: List[str],
    *,
    provider: str,
    api_key: str,
    model: str,
    temperature: float = 1.2,
    max_completion_tokens: int = 2048,
) -> str:
    """Generate a concise third-person user biography paragraph."""
    if not api_key:
        raise ValueError("LLM API key is not configured.")
    _ensure_prompts_loaded()

    try:
        messages_json = json.dumps(chat_messages, ensure_ascii=False, indent=2)
    except Exception:
        messages_json = '[' + ', '.join('"%s"' % str(m).replace('"', '\\"') for m in chat_messages) + ']'

    user_input = f"# Input\n1. {existing_bio}\n2.{messages_json}\n\n# Output"

    try:
        return _chat_completion(
            provider=provider,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_BIO_PROMPT},
                {"role": "user", "content": user_input},
            ],
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
    except Exception as e:
        print(f"❌ generate_user_bio failed: {e}", file=sys.stderr)
        raise _format_llm_error(provider, str(e)) from e


def generate_message_rewrite(
    message_obj: Dict[str, Any],
    speaker_profile: Dict[str, Any] = None,
    messages_in_chat: List[str] = None,
    *,
    provider: str,
    api_key: str,
    model: str,
    temperament: str = None,
    style: str = None,
    length: str = None,
    temperature: float = 0.7,
    max_completion_tokens: int = 512,
) -> str:
    """Rewrite a single chat message using the LLM while preserving meaning."""
    if not api_key:
        raise ValueError("LLM API key is not configured.")
    _ensure_prompts_loaded()

    context_parts = []
    if speaker_profile:
        context_parts.append(
            f"1. User Description: \"{speaker_profile.get('description', 'No description available.')}\""
        )
    if messages_in_chat:
        try:
            recent = messages_in_chat[-10:]
        except Exception:
            recent = messages_in_chat
        context_parts.append("2. Conversation History:\n" + json.dumps(recent, ensure_ascii=False, indent=2))

    guidance_instructions = {}
    if temperament:
        guidance_instructions['temperament'] = temperament
    if style:
        guidance_instructions['style'] = style
    if length:
        guidance_instructions['length'] = length

    guidance_text = json.dumps(guidance_instructions, ensure_ascii=False) if guidance_instructions else ""
    message_text = message_obj.get('text', '')
    addressees = message_obj.get('addressees', [])
    speaker = message_obj.get('speaker', '')
    context_parts.append(f"3. \n{guidance_text}")
    context_parts.append(f"4.User’s Draft Message: \n{message_text}\nAddressees: {addressees}\nSpeaker: {speaker}")

    user_prompt = "# Input\n" + "\n".join(context_parts) + "\n\n# Output"

    try:
        out = _chat_completion(
            provider=provider,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": _REWRITE_MESSAGE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_completion_tokens=max_completion_tokens,
        )
        return out.strip('"\n ')
    except Exception as e:
        print(f"❌ generate_message_rewrite failed: {e}", file=sys.stderr)
        raise _format_llm_error(provider, str(e)) from e
