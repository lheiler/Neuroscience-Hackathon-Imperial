from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import os
import json
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

app = Flask(__name__, static_folder='ui')
CORS(app)

PROFILES_DIR = 'profiles'
WEIGHTS_DIR = 'weights'
os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(WEIGHTS_DIR, exist_ok=True)

# ----------------------------
# Dataset Helpers
# ----------------------------
HEADSET_CHANNELS = {
    'unicorn_8': 8,
    'emotiv_epoc_14': 14,
    'emotiv_insight_5': 5,
    'neurosity_8': 8,
    'openbci_16': 16
}

def generate_random_weights(profile_id, headset_type):
    """
    Generates naturally-shaped random weights for the FilterBankRiemannian pipeline.
    Pipeline features = num_bands(4) * (channels * (channels+1) / 2)
    """
    channels = HEADSET_CHANNELS.get(headset_type, 8) # Default to 8
    num_bands = 4 
    cov_features = int((channels * (channels + 1)) / 2)
    total_features = num_bands * cov_features
    
    # 4 classes for commands
    num_classes = 4
    
    # Generate completely uniform random weights for Logistic Regression
    weights = np.random.uniform(low=-0.05, high=0.05, size=(num_classes, total_features))
    biases = np.random.uniform(low=-0.05, high=0.05, size=(num_classes,))
    
    weights_data = {
        'coef_': weights,
        'intercept_': biases,
        'classes_': np.array([0, 1, 2, 3])
    }
    
    filepath = os.path.join(WEIGHTS_DIR, f"{profile_id}_weights.npy")
    np.save(filepath, weights_data)
    
    return filepath

@app.route('/api/profiles/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    try:
        # Delete JSON file
        json_path = os.path.join(PROFILES_DIR, f"{profile_id}.json")
        if os.path.exists(json_path):
            os.remove(json_path)
            
        # Delete Weights file if it exists
        weights_path = os.path.join(WEIGHTS_DIR, f"{profile_id}_weights.npy")
        if os.path.exists(weights_path):
            os.remove(weights_path)
            
        return jsonify({"message": "Profile and weights deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ----------------------------
# Static File Serving
# ----------------------------
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# ----------------------------
# 2. Profile API Endpoints
# ----------------------------
@app.route('/api/profiles', methods=['GET'])
def get_profiles():
    """Reads all JSON profiles from the profiles directory."""
    profiles = []
    try:
        if os.path.exists(PROFILES_DIR):
            for filename in os.listdir(PROFILES_DIR):
                if filename.endswith('.json'):
                    filepath = os.path.join(PROFILES_DIR, filename)
                    with open(filepath, 'r') as f:
                        profiles.append(json.load(f))
        
        # Sort by creation time if available, newest first
        profiles.sort(key=lambda x: x.get('id', '0'), reverse=True)
        return jsonify(profiles), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profiles', methods=['POST'])
def save_profile():
    """Saves a new profile as a JSON file and generates initial weights."""
    try:
        data = request.json
        if not data or 'id' not in data:
            return jsonify({"error": "Invalid profile data format"}), 400
            
        filepath = os.path.join(PROFILES_DIR, f"{data['id']}.json")
        is_new = not os.path.exists(filepath)
        
        # Ensure new profiles have usage data initialized
        if 'usage_data' not in data:
            data['usage_data'] = {
                "total_time_min": 0,
                "sessions": 0,
                "avg_accuracy": 0.0,
                "last_prediction": "--"
            }
            
        if 'calibration_status' not in data:
            data['calibration_status'] = 'uncalibrated'
            
        # Generate model pipeline weights according to the selected hardware format ONLY if new
        if is_new or 'weights_path' not in data:
            headset = data.get('headset', 'unicorn_8')
            weights_path = generate_random_weights(data['id'], headset)
            data['weights_path'] = weights_path
            data['weights_status'] = "Weights Initialized"
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)
            
        return jsonify({"message": "Profile saved successfully", "profile": data}), 201
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/llm/questions", methods=["POST"])
def llm_questions():
    # 🔒 Hardcoded for demo: always medical / physical
    system = """
You generate EXACTLY 4 short messages for an ALS patient using an assistive communication device.

The messages MUST be things an ALS patient would realistically ask a caregiver *right now*.
They MUST be concrete, immediate, and caregiver-actionable.

Allowed themes (choose from these only):
- pain/discomfort
- repositioning/pressure relief
- breathing/ventilator/mask adjustment
- suction/saliva/choking/cough support
- hydration/feeding/tube feeding
- toileting/urinal/diaper/cleanup
- temperature/blanket/clothing adjustment
- medication timing/need
- urgent help / call nurse / emergency

STRICT RULES:
- Return exactly 4 lines.
- Each line is a single question or request (no lists, no numbering, no bullets).
- Keep each line <= 80 characters if possible.
- Do NOT mention ALS, diagnosis, hospitals, or speculation.
- Do NOT suggest emotional therapy, life advice, or non-caregiver actions.
- Do NOT include disclaimers or extra text.
- Use simple, clear language.
""".strip()

    user = """
Generate 4 distinct caregiver-actionable questions/requests from the allowed themes.
No numbering. Plain text. 4 lines only.
""".strip()

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

        text = resp.output_text.strip()

        lines = [
            ln.strip().lstrip("-•0123456789. ").strip()
            for ln in text.splitlines()
            if ln.strip()
        ]

        questions = (lines + [
            "I’m in pain — can you help me get comfortable?",
            "Can we check my breathing support?",
            "Can we review my medication schedule?",
            "Can you reposition me, please?"
        ])[:4]

        return jsonify({"questions": questions})

    except Exception as e:
        print("LLM ERROR:", e)

        # Safe fallback
        return jsonify({
            "questions": [
                "I’m in pain — can you help me get comfortable?",
                "Can we check my breathing support?",
                "Can we review my medication schedule?",
                "Can you reposition me, please?"
            ]
        })

# ----------------------------
# Run Server
# ----------------------------
if __name__ == '__main__':
    print("Starting Thinking Out Loud Backend server at http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
