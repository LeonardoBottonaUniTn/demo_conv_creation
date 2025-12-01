import os
import json
import sys

from scripts.llm_calls import generate_user_bio

existing = "This Telegram user"
messages = [
    "Green investments are attractive to private equity and pension funds when supported by central bank policies.",
    "Green central banking creates jobs, aids developing countries, and aligns economic and environmental goals.",
    "Central banks have historically shifted priorities and can shift to support green policies without huge disruption.",
    "Central banks act independently and without political lobbying, unlike governments.",
    "Monetary policy can funnel capital quickly into green businesses, incentivizing faster development.",
    "OO contradict themselves by claiming green investment is already high but also causing unemployment harm.",
    "Big polluters have money and patents but stall green tech for profit motives; central bank incentives align private and social interests.",
    "Climate disaster is urgent with worsening impacts and slow government action.",
    "Central bank policy changes cost of borrowing, directly pressuring companies to shift business models.",
    "Client relationships and regulation prevent companies from simply switching banks to avoid green mandates."
]


def main():
    # If no API key is set, avoid making a live LLM call and show how to run instead.
    key = os.getenv("GROQ_API_KEY")
    if not key:
        print("GROQ_API_KEY environment variable is not set. Skipping live LLM call.")
        print("")
        print("To run the live test, set GROQ_API_KEY in your environment or create a .env file in the project root with GROQ_API_KEY=your_key and then run:")
        print("")
        print("    python3 backend/test_generate_bio.py")
        print("")
        print("Payload preview:")
        print(json.dumps({"existing_bio": existing, "messages": messages}, ensure_ascii=False, indent=2))
        return

    try:
        bio = generate_user_bio(existing, messages)
        print("\nGenerated biography:\n")
        print(bio)
    except Exception as e:
        print("Error during generation:", str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
