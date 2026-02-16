from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import logging

from scripts.llm_calls import transform_discussion_json, generate_user_bio, generate_message_rewrite

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/health")
def llm_health_check():
    """Check if LLM module can be loaded"""
    try:
        test_result = transform_discussion_json([{"id": 1, "text": "test"}])
        return {"status": "ok", "message": "LLM module loaded and callable"}
    except Exception as e:
        import traceback
        logging.error(f"LLM health check failed: {e}\n{traceback.format_exc()}")
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}


@router.post('/generate-bio')
async def api_generate_bio(request: Request):
    """Generate a concise user biography paragraph from provided inputs."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    existing_bio = body.get('existing_bio') or body.get('existing') or body.get('bio') or ""
    messages = body.get('messages')
    if messages is None:
        messages = body.get('chat_messages')
    
    if messages is None or not isinstance(messages, list):
        print("Messages format: ", type(messages), " Messages: ", messages)
        raise HTTPException(status_code=400, detail="'messages' must be provided as a list of strings")

    for i, m in enumerate(messages):
        if not isinstance(m, str):
            raise HTTPException(status_code=400, detail=f"messages[{i}] must be a string")

    try:
        bio = generate_user_bio(existing_bio, messages)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "bio": bio})


@router.post('/rewrite-message')
async def api_rewrite_message(request: Request):
    """Rewrite a single chat message using the LLM."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    message = body.get('messageToRewrite') or body.get('message') or None
    speaker_profile = body.get('speakerProfile') or None
    chat_msgs = body.get('messagesInTheChat') or body.get('messages') or None
    temperament = body.get('temperament') or None
    style = body.get('style') or None
    length = body.get('length') or None

    if message is None or not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="'messageToRewrite' must be provided as an object with a 'text' field")

    text = message.get('text')
    if text is None or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="message.text must be a string")

    if speaker_profile is not None and not isinstance(speaker_profile, dict):
        raise HTTPException(status_code=400, detail="speakerProfile must be an object if provided")
    if chat_msgs is not None and not isinstance(chat_msgs, list):
        raise HTTPException(status_code=400, detail="messagesInTheChat must be a list of strings if provided")

    try:
        rewritten = generate_message_rewrite(
            message,
            speaker_profile=speaker_profile,
            messages_in_chat=chat_msgs,
            temperament=temperament,
            style=style,
            length=length,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")

    return JSONResponse({"success": True, "rewritten": rewritten})
