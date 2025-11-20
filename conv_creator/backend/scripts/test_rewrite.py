
import os
import sys
from dotenv import load_dotenv

# Add backend directory to path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)

# Load env vars
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

from scripts.llm_calls import generate_message_rewrite

def test_rewrite():
    user_description = "Tommaso is a concerned physician, strictly anti-legalization. Tommaso focuses on public health, addiction risks, and scientific evidence, using careful, clinical language."
    
    history = [
      "Legalization risks normalizing a substance linked to increased psychiatric disorders, addiction, and respiratory illness—Italy should put health first and maintain prohibition.",
      "I agree. Society must err on the side of caution. Keeping marijuana illegal signals the seriousness of its health risks, especially to youth and vulnerable individuals.",
      "Making policy on fear, not facts, harms citizens. Regulation allows us to manage risks responsibly, without criminalizing non-violent behavior.",
      "Most public health experts agree: regulation, not prohibition, is the best way to address harms—through transparency, not denial.",
      "Public health crises are often triggered by failing to maintain clear social norms around drug use. Prohibition is the safest path.",
      "That's true. Prevention, not normalization, should be the cornerstone of drug policy—especially with substances that cause long-term harm.",
      "Prohibition hasn't succeeded—criminalization feeds organized crime while punishing individuals without reducing use. Legalization offers a safer, regulated alternative.",
      "Yes! And also, economic data from regions with legal cannabis demonstrate that legalization can fund social programs that directly strengthen communities.",
      "No amount of money is worth risking our communities' integrity or the health of our youth."
    ]

    draft_message = "Economics must not override medical concerns—public health systems already struggle with addiction-related costs."
    
    message_obj = {
        "text": draft_message,
        "speaker": "Tommaso",
        "addressees": ["Serena"]
    }
    
    speaker_profile = {
        "description": user_description
    }
    
    print("Testing generate_message_rewrite...")
    print(f"Draft: {draft_message}")
    print("Params: Exuberant, Informal, Much longer")
    
    try:
        result = generate_message_rewrite(
            message_obj=message_obj,
            speaker_profile=speaker_profile,
            messages_in_chat=history,
            temperament="Exuberant",
            style="Informal",
            length="Much longer"
        )
        
        print("\n--- Result ---")
        print(result)
        print("--------------")
        
        # Basic length check
        draft_len = len(draft_message)
        result_len = len(result)
        ratio = result_len / draft_len
        print(f"\nDraft length: {draft_len}")
        print(f"Result length: {result_len}")
        print(f"Ratio: {ratio:.2f}x")
        
        if ratio > 2.5: # Allow a bit of leeway but 2x is the target
            print("❌ FAIL: Result is too long (> 2.5x draft)")
        else:
            print("✅ PASS: Result length is within acceptable limits")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_rewrite()
