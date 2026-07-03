import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Azure Identity libraries (Used in production)
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

load_dotenv()

app = Flask(__name__)
CACHED_API_KEY = None

def get_google_api_key():
    global CACHED_API_KEY
    
    # 1. LOCAL CHECK: Check if running locally with .env
    local_key = os.environ.get("GOOGLE_API_KEY")
    if local_key:
        return local_key

    # Return memory cache if already fetched from Azure
    if CACHED_API_KEY:
        return CACHED_API_KEY

    # 2. AZURE FALLBACK: Fetch from Azure Key Vault in production
    vault_url = os.environ.get("AZURE_KEYVAULT_URL")
    if vault_url:
        try:
            # Authenticates securely using the App Service Managed Identity
            credential = DefaultAzureCredential()
            client = SecretClient(vaultUrl=vault_url, credential=credential)
            
            # Fetches the secret named "GOOGLE-API-KEY"
            retrieved_secret = client.get_secret("GOOGLE-API-KEY")
            CACHED_API_KEY = retrieved_secret.value
            return CACHED_API_KEY
        except Exception as e:
            print(f"Azure Key Vault Error: {e}")
            return None
    return None

@app.route('/')
def home():
    return "Welcome to the Weather Summary App! Append /weather?city=YourCity to the URL."

@app.route('/weather', methods=['GET'])
def get_weather():
    city = request.args.get('city', 'New Delhi')
    api_key = get_google_api_key()
    
    if not api_key:
        return jsonify({"error": "No API key configured locally or on Azure."}), 500
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"Give me a brief 1-sentence casual summary of what the weather feels like in {city} right now."
        response = model.generate_content(prompt)
        
        return jsonify({
            "status": "success",
            "city": city,
            "summary": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Azure App Service expects the app to run on port 8000 or read from environment
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)