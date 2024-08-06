from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import json
from pypdf import PdfReader  # Updated to use pypdf
from pptx import Presentation
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

api_key = "AIzaSyDbWXReucO5RoKUyvijf7TiQEvwTfKCs7w"
genai.configure(api_key=api_key)
model_gen = genai.GenerativeModel('gemini-1.5-flash')

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extract_text_from_pdf(file_path):
    reader = PdfReader(file_path)
    text = []
    for page in reader.pages:
        text.append(page.extract_text())
    return " ".join(text)

def extract_text_from_pptx(file_path):
    presentation = Presentation(file_path)
    text = []
    for slide in presentation.slides:
        for shape in slide.shapes:
            if hasattr(shape, "text"):
                text.append(shape.text)
    return "\n".join(text)

def extract_text(file_path):
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith('.pptx'):
        return extract_text_from_pptx(file_path)
    else:
        raise ValueError("Unsupported file format")

def generate_flashcards(text, number_of_cards):
    response = model_gen.generate_content(
        f"generate {number_of_cards} flashcards for the following as an array of objects only nothing else just the array as 'front': for the question and 'back': for the answer (no ```json```): {text}"
    )

    if hasattr(response, 'text'):
        result = response.text
    else:
        result = response

    cleaned_data = result.strip()
    
    if cleaned_data.startswith('```javascript'):
        cleaned_data = cleaned_data.strip('```javascript').strip('```')
    elif cleaned_data.startswith('```json'):
        cleaned_data = cleaned_data.strip('```json').strip('```')

    try:
        flashcards = json.loads(cleaned_data)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        flashcards = []

    return flashcards

@app.route('/create-flashcards', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        try:
            number_of_cards = int(request.form.get('number_of_cards', 10))
            text = extract_text(file_path)
            flashcards = generate_flashcards(text, number_of_cards)
            os.remove(file_path)
            return jsonify({'flashcards': flashcards}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)