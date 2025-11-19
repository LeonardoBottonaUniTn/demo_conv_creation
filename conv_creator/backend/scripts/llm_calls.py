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

SYSTEM_PROMPT = """You are a precise JSON transformation assistant.

Your task is to convert an input JSON into a structured format with two top-level fields:
1. "users": a list of objects describing all unique speakers.
2. "tree": a conversation tree following the schema below.

Output schema:
{
  "users": [
    {
      "speaker": "string",
      "description": "This is a telegram user"
    }
  ],
  "tree": {
    "id": "string",
    "speaker": "string",
    "text": "string",
    "children": "list"
  }
}

Rules:
- Return only a valid JSON object (no markdown, no explanations, no comments).
- Extract all unique speakers from the input and list them in "users".
- Each user object must include:
    - "speaker": name of the speaker.
    - "description": always "this is a telegram user".
- The conversation structure must be placed entirely inside the "tree" field.
- Every node in "tree" must follow the schema exactly.
- Use "children": [] only when there are actual children.
- Do not add empty or placeholder nodes.
- The root must be a single JSON object, not a list.
- If some fields are missing in the input, skip them instead of hallucinating values."""


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


# System prompt used to generate a concise user biography based on an existing
# biographical description and a list of chat messages. This prompt follows the
# specification provided by the user and instructs the LLM to output a single
# concise paragraph suitable as a third-person biography.



SYSTEM_BIO_PROMPT = """Generate a user biography that authentically captures the user’s distinctive argumentative style, written voice, emotional tone, and clearly expressed opinions, considering both the provided biographical description and chat messages as sources of evidence. Identify traits and features that are observable in either or both inputs, such as manner of expressing opinions, linguistic quirks, intensity of emotion, recurring themes, or typical argumentative strategies. Integrate relevant, evidenced traits from the original biography only if they are either explicitly present, consistent with, or corroborated by the style and opinions demonstrated in the messages. The biography should read naturally, as if introducing the user to others, not as a directive or guide for editors. Avoid vague, generic, or speculative statements; ensure that every point is directly traceable to one or both pieces of provided material.

Do not simply summarize or repeat the original biography, nor should you include background details or personality summaries unless they are specifically reflected or reinforced in the chat messages and the biographical description. Focus on crafting a biographical narrative that highlights the user’s personal style and perspectives as demonstrated in both sources.

# Input Format

You will receive the following inputs:
1. An existing biographical description of the user (as a string).
2. A list of the user’s chat messages, formatted as:
[
"First user message text.",
"Second user message text.",
...
"Nth user message text."
]

# Output Format

Return a single, concise paragraph in the form of a user biography, focusing exclusively on the linguistic and opinion-expressing traits extracted from both the existing biography and the chat messages. The paragraph should present the user’s style and predominant viewpoints as shown in either or both inputs, as if spoken about the user to a third party. Do not include explanations, meta-commentary, or directives—produce only a third-person biographical paragraph reflecting the evidenced style, tone, and opinionated characteristics.

# Example

Example Input:
1. Biographical description: "Alex is an active member of tech forums, often helping others with programming problems."
2. Chat messages:
[
"I don't think that's the right approach—let's look at the documentation instead.",
"I always prefer clear step-by-step instructions. People tend to miss details.",
"Honestly, syntax errors really annoy me. They're so avoidable!",
"I strongly recommend learning the basics before diving into frameworks."
]

Example Output:
Alex is an active participant who brings clarity and candor to programming discussions, frequently advocates for methodical step-by-step solutions, and expresses strong opinions about best practices. Consistently practical in advice and attentive to detail, Alex approaches each interaction with an insistence on mastering fundamentals and a relatable frustration with avoidable mistakes, both of which are evident in help offered on tech forums and direct feedback in conversations.

(For real examples, the output should be a single, well-integrated paragraph drawing on traits shown in both biography and messages, with length proportional to the amount of substantive evidence in the inputs.)

# Notes
- If in the previous description there are infos on the platform in which the user is writing, keep them
- The output must be a user biography based solely on observable patterns and style found in the chat messages and/or biography—do not speculate or extrapolate beyond what is present.
- Integrate, but do not simply repeat, the original biography when the messages reinforce or exemplify its statements.
- Do not include any instructional language, bullet points, or lists.
- Final output should be suitable for third-person presentation as a user bio and should not contain instructions or meta-commentary.
- If the two sources present conflicting information, prioritize traits demonstrably present and consistent in the chat messages.

# Reminder
Create a concise, natural, and vivid user biography paragraph that authentically encapsulates the user’s unique style and perspectives, strictly as demonstrated in both the original biography and their chat messages, without instructional or editorial framing.
"""


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
                {"role": "system", "content": SYSTEM_BIO_PROMPT},
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


REWRITE_MESSAGE_SYSTEM = """Refine a user’s draft message to fit smoothly and authentically into the ongoing conversation, using the user description, chat history (messages, speakers, addressees), and parameters: temperament, style, and length. Revise the draft to align with the user’s typical communication and connect naturally to prior messages, preserving the user’s intent and making the conversation flow seamless.

• Match the user’s style and preferences based on the description and prior messages.
• Use temperament and style parameters to adjust tone, expressiveness, and word choice.
• Decide whether interjections (e.g., “oh,” “hey,” “well”) are appropriate—include them if the user’s typical style or the conversation context is expressive, friendly, or emotional. Avoid when things are formal, technical, or clearly not expressive.
• If used, choose interjections that fit the specified temperament, not just “informal” style, and place them naturally (not just at the start)—but don’t force or overdo them.
• Adjust length as specified (short/medium/long), but don’t add unrelated ideas—stay based on the draft and conversation.
• Enhance clarity, connection to previous turns, and coherence. Avoid meta-commentary or explanations.
• Output should be only the polished, ready-to-send message.

Input Format:
1. User Description (text: style/preferences/background)
2. Conversation History (list: message, speaker, addressee)
3. Parameters:
    • temperament (e.g., calm, assertive, enthusiastic)
    • style (e.g., formal, informal, concise)
    • length (e.g., short, medium, long)
4. User’s Draft Message

# Output Format

Return just the final refined message, as a single paragraph or list as appropriate for the chat. No explanations or meta-notes.

# Examples

Example Input:
1. User Description: "Jordan tends to be concise but direct, often using rhetorical questions, and dislikes small talk."
2. Conversation History:
[
{ "message": "We should think through the potential risks before moving forward.", "speaker": "Casey", "addressee": "Jordan" },
{ "message": "What specific risks are you referring to?", "speaker": "Jordan", "addressee": "Casey" },
{ "message": "Mostly budget overruns and timeline delays.", "speaker": "Casey", "addressee": "Jordan" },
{ "message": "Is there hard evidence those are likely?", "speaker": "Jordan", "addressee": "Casey" }
]
3. 
{
"temperament":"enthusiastic",
"style":"informal",
"length":"medium"
}
4. Draft: "I don’t think delays are inevitable, and aren’t we supposed to be adaptable anyway?"

Example Output:
Oh, I just can’t see delays as inevitable—wow, aren’t we supposed to be adaptable anyway? Hey, let’s focus on what we can actually control here!

Example Input:
1. User Description: "Kim writes formally and values precision; she avoids colloquialisms or exclamatory language."
2. Conversation History:
[
{ "message": "What is our deadline for the final draft?", "speaker": "Kim", "addressee": "Alex" }
]
3. 
{
"temperament":"calm",
"style":"formal",
"length":"short"
}
4. Draft: "I think we should finish the draft by Friday, if that’s okay."

Example Output:
We should complete the draft by Friday, if that is acceptable.

Example Input:
1. User Description: "Ravi is positive and expressive, often showing encouragement in team chats."
2. Conversation History:
[
{ "message": "I’m worried I’ll mess up the demo.", "speaker": "Alex", "addressee": "Ravi" },
{ "message": "No worries! You’ll do great.", "speaker": "Ravi", "addressee": "Alex" }
]
3.
{
"temperament":"encouraging",
"style":"neutral",
"length":"short"
}
4. Draft: "You’re prepared and I’m sure you’ll do really well!"

Example Output:
Hey, you’re totally prepared—and I just know you’ll do really well!

# Notes

- Include interjections only if a user’s style/history, chat context, or temperament support them, not only for “informal” style.
- Interjections must fit naturally; avoid them when the user or situation requires formality or restraint. Never overuse.
- Every change must be grounded in the draft, the user’s stated preferences, or the conversation—don’t invent or speculate.
- Return only the ready message, nothing else.
- Prioritize flow, clarity, and fit to the conversation and user profile.

# Reminder
Deliver only the refined, ready-to-send message, incorporating interjections and style adjustments as appropriate based on user temperament and context—not just the “style” setting.

"""


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

    # Normalize inputs
    orig_text = ''
    try:
        orig_text = str(message_obj.get('text', ''))
    except Exception:
        orig_text = str(message_obj)


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
    context_parts.append(f"3. \n{guidance_text}")
    context_parts.append(f"4.User’s Draft Message: \"{orig_text}\"")

    user_prompt = "# Input\n" + "\n".join(context_parts) + "\n\n# Output"
    
    print("User prompt for message rewrite:", user_prompt)

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": REWRITE_MESSAGE_SYSTEM},
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



