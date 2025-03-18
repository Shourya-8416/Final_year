from flask import Flask, request, render_template, jsonify, send_from_directory
import os
import boto3
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'
PHOTO_FOLDER = 'static/photos'  # Directory containing stored images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Initialize AWS Rekognition client
rekognition = boto3.client('rekognition', region_name='us-east-1')  # Change region if needed


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['POST'])
def upload_file():
    if 'sketch' not in request.files:
        return "No file part"
    
    file = request.files['sketch']
    if file.filename == '':
        return "No selected file"
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Perform face matching
        best_match, similarity_score = find_best_match(file_path)
        
        if best_match:
            result = {
                "sketch_path": filename,
                "photo_path": best_match,
                "similarity": round(similarity_score, 2),
                "details": {
                    "name": best_match.split('.')[0],  # Assuming filename has person's name
                    "age": "Unknown",
                    "dob": "Unknown"
                },
                "interpretation": "Match found" if similarity_score > 50 else "Low similarity"
            }
            return render_template('result.html', result=result)
        else:
            return "No match found"

    return "Invalid file type"

def find_best_match(uploaded_image):
    """Compare uploaded image with stored images using AWS Rekognition"""
    best_match = None
    best_score = 0
    
    with open(uploaded_image, 'rb') as source_image:
        source_bytes = source_image.read()
    
    for file in os.listdir(PHOTO_FOLDER):
        if file.endswith(tuple(ALLOWED_EXTENSIONS)):
            img_path = os.path.join(PHOTO_FOLDER, file)
            with open(img_path, 'rb') as target_image:
                target_bytes = target_image.read()
                
                try:
                    response = rekognition.compare_faces(
                        SourceImage={'Bytes': source_bytes},
                        TargetImage={'Bytes': target_bytes},
                        SimilarityThreshold=50
                    )
                    
                    if response['FaceMatches']:
                        similarity = response['FaceMatches'][0]['Similarity']
                        if similarity > best_score:
                            best_score = similarity
                            best_match = file
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    return best_match, best_score if best_match else (None, 0)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
