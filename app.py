import logging
from flask import Flask, request, render_template, send_from_directory
from waitress import serve
from openai import OpenAI
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from google.cloud import language_v2
import platform

app = Flask(__name__)

# Load environment variables
load_dotenv('.env')
# Get the API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No OpenAI API key found in environment variables")

def sample_analyze_sentiment(text_content):
    client = language_v2.LanguageServiceClient()
    document_type_in_plain_text = language_v2.Document.Type.PLAIN_TEXT
    document = {
        "content": text_content,
        "type_": document_type_in_plain_text,
    }
    encoding_type = language_v2.EncodingType.UTF8
    response = client.analyze_sentiment(
        request={"document": document, "encoding_type": encoding_type}
    )
    return response

@app.route('/', methods=['GET', 'POST'])
def home():
    transcript = None
    filename = None
    sentiment_data = None
    if request.method == 'POST':
        if 'form02-whats-on-your-mind' in request.form and request.form['form02-whats-on-your-mind']:
            transcript = request.form['form02-whats-on-your-mind']
            sentiment_data = sample_analyze_sentiment(transcript)
        elif 'form02-upload-audio-instead' in request.files:
            file = request.files['form02-upload-audio-instead']
            if file.filename == '':
                return 'No selected file', 400
            if file:
                filename = secure_filename(file.filename)
                # Check the operating system
                if platform.system() == 'Windows':
                    # Save the file in the current directory for Windows
                    filepath = os.path.join(os.getcwd(), filename)
                else:
                    # Save the file in the /tmp directory for other operating systems
                    filepath = os.path.join('/tmp', filename)
                file.save(filepath)
                try:
                    client = OpenAI(api_key=api_key)
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=open(filepath, "rb"),
                        response_format="text"
                    )
                    sentiment_data = sample_analyze_sentiment(transcript)
                except Exception as e:
                    print(str(e))
                finally:
                    # Delete the file after processing
                    if os.path.exists(filepath):
                        os.remove(filepath)
    return render_template('index.html', transcript=transcript, audio_file=filename, sentiment_data=sentiment_data)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve(app, host="0.0.0.0", port=8080)