import os
from dotenv import load_dotenv
from google import genai # The new, recommended SDK

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("Error: GEMINI_API_KEY not found in environment.")
else:
    try:
        # Create a client instance by passing the API key directly.
        client = genai.Client(api_key=api_key)

        print("Listing models available to this API key:")
        found_gemini_pro = False
        found_gemini_1_5_pro = False

        # Iterate through models returned by client.models.list()
        for m in client.models.list():
            # Check the attribute to see if it supports content generation
            # Based on documentation, 'supported_generation_methods' or 'supported_actions'
            # should contain 'generateContent'. Let's stick to 'supported_generation_methods'
            # as it's more semantically clear for content generation.
            
            # --- THE POTENTIALLY TROUBLESOME LINE ---
            if hasattr(m, 'supported_generation_methods') and "generateContent" in m.supported_generation_methods:
                print(f"  - {m.name} (DisplayName: {m.display_name})")
                if m.name == "models/gemini-pro":
                    found_gemini_pro = True
                if m.name == "models/gemini-1.5-pro-latest":
                    found_gemini_1_5_pro = True
            elif hasattr(m, 'supported_actions') and "generateContent" in m.supported_actions: # Fallback check
                 print(f"  - {m.name} (DisplayName: {m.display_name}) (via supported_actions)")
                 if m.name == "models/gemini-pro":
                    found_gemini_pro = True
                 if m.name == "models/gemini-1.5-pro-latest":
                    found_gemini_1_5_pro = True
            else:
                # If neither attribute works, print the model object to inspect its structure
                print(f"  - {m.name} (DisplayName: {m.display_name}) - Attributes for generation methods not found.")
                # print(f"    Raw Model Object: {m}") # Uncomment this line if you still get an error, it will show all attributes

        print("\n--- Summary of key models ---")
        if found_gemini_pro:
            print("✔️ 'gemini-pro' (models/gemini-pro) is available and supports generateContent.")
        else:
            print("❌ 'gemini-pro' (models/gemini-pro) is NOT available or does not support generateContent. This is unusual, double check API key and project enablement.")

        if found_gemini_1_5_pro:
            print("✔️ 'gemini-1.5-pro-latest' (models/gemini-1.5-pro-latest) is available and supports generateContent.")
        else:
            print("❌ 'gemini-1.5-pro-latest' (models/gemini-1.5-pro-latest) is NOT available or does not support generateContent. This model might require specific access or be region-locked.")

        print("\nAttempting a test chat with 'gemini-pro'...")
        # Use the 'client' instance we created for generate_content calls
        response = client.models.generate_content(
            model="gemini-pro", # Try with the most common model first
            contents=[{"role": "user", "parts": [{"text": "Hello, AI!"}]}]
        )

        print("\n--- API Test SUCCESSFUL! ---")
        print(f"Model: gemini-pro")
        generated_text = ""
        if response.contents and response.contents[0].parts:
            for part in response.contents[0].parts:
                if part.text:
                    generated_text += part.text
        print(f"Response: {generated_text[:100]}...")
        print(f"Full response object: {response}")

    except Exception as e:
        print(f"\n--- API Test FAILED ---")
        print(f"Error: {e}")
        print("Possible causes: Incorrect API Key, Model not found/enabled, network issues, or a fundamental problem with the API setup.")
