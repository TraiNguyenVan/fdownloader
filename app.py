from flask import Flask, render_template, request, jsonify, send_from_directory, after_this_request
import os
import uuid
import shutil
import zipfile
import threading
from main import download_post

app = Flask(__name__)
DOWNLOAD_BASE = "/app/downloads"

# Ensure base dir exists
if not os.path.exists(DOWNLOAD_BASE):
    os.makedirs(DOWNLOAD_BASE)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Create a unique session ID for this download
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(DOWNLOAD_BASE, session_id)
    
    try:
        # Run download (Synchronous for now, might timeout on long ones but okay for MVP)
        # For better UX, we'd use celery or a thread, but let's keep it simple.
        # Use a thread to avoid blocking completely if allowed, checking status via polling?
        # User asked for SIMPLE. Let's block for now or use a basic thread and polling.
        # Let's do blocking first, if it times out we can do polling.
        # Actually, blocking 50+ images takes time. Let's do a simple thread join or just block.
        # Given "simple", let's try blocking. If it hangs, we'll upgrade.
        
        result = download_post(url, session_dir)
        
        if result.get("count", 0) > 0:
            # Zip the directory
            zip_filename = f"{session_id}.zip"
            zip_path = os.path.join(DOWNLOAD_BASE, zip_filename)
            
            make_zip(session_dir, zip_path)
            
            # Cleanup source folder to save space? Optional.
            # shutil.rmtree(session_dir) 
            
            return jsonify({
                "status": "success", 
                "count": result["count"],
                "download_url": f"/files/{zip_filename}"
            })
        else:
             return jsonify({
                "status": "error", 
                "error": "No images found. Check URL or cookies."
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def make_zip(source_dir, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                zipf.write(os.path.join(root, file), 
                           os.path.relpath(os.path.join(root, file), 
                           os.path.join(source_dir, '..')))

@app.route('/files/<filename>')
def download_file(filename):
    return send_from_directory(DOWNLOAD_BASE, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
