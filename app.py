import os
from flask import Flask, request, jsonify, send_from_directory
from PIL import Image, ImageEnhance, ImageFilter
from paddleocr import PaddleOCR
from io import BytesIO
import requests  # Import requests to send data to Make.com

# Initialize Flask and PaddleOCR with Croatian language
app = Flask(__name__)
ocr = PaddleOCR(use_angle_cls=True, lang='hr')  # Croatian language ('hr')

# Function to preprocess the image before extracting text
def preprocess_image(image):
    image = image.convert('L')  # Convert image to grayscale
    image = image.point(lambda p: p > 128 and 255)  # Binary threshold
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)  # Enhance contrast
    image = image.filter(ImageFilter.SHARPEN)  # Sharpen the image
    return image

# Function to extract text from an image
def extract_text_from_image(image):
    preprocessed_image = preprocess_image(image)
    image_bytes = BytesIO()
    preprocessed_image.save(image_bytes, format='PNG')  # Save image as bytes
    image_bytes = image_bytes.getvalue()
    
    # Run OCR on the preprocessed image
    result = ocr.ocr(image_bytes)
    text = '\n'.join([word[1][0] for line in result for word in line])  # Extract text
    return text

# Route to serve index.html
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/process-image', methods=['POST'])
def process_image():
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')  # Get all uploaded files
    if not files:
        return jsonify({'error': 'No files selected'}), 400
    
    if len(files) > 10:
        return jsonify({'error': 'You can upload a maximum of 10 images'}), 400
    
    extracted_text = ""
    for file in files:
        try:
            image = Image.open(file)
            extracted_text += extract_text_from_image(image) + "\n\n"
        except Exception as e:
            print(f"Error processing file: {e}")
            return jsonify({'error': f'Error processing file: {file.filename}'}), 500
    
    return jsonify({'extracted_text': extracted_text})

# New route to send extracted text to Make.com
@app.route('/send-to-make', methods=['POST'])
def send_to_make():
    data = request.get_json()
    text = data.get('text', '')  # Get the extracted text from the request
    
    make_url = "https://hook.eu2.make.com/y94u5xvkf97g5nym3trgz2j2107nuu12"  # Replace with your Make.com webhook URL
    
    try:
        # Send the extracted text to Make.com via the webhook
        response = requests.post(make_url, json={'text': text})
        response.raise_for_status()

        # Return the summary (Make.com should send this back)
        summarized_text = response.json().get('summary', '')
        if summarized_text:
            return jsonify({'summary': summarized_text}), 200
        else:
            return jsonify({'error': 'No summary returned from Make.com'}), 500

    except requests.exceptions.RequestException as e:
        print(f"Failed to send to Make.com: {e}")
        return jsonify({'error': 'Failed to send to Make.com'}), 500

if __name__ == '__main__':
    app.run(debug=True)
