from flask import Flask, render_template, request, jsonify
import os
import requests
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
needs = {}

def download_file_multithreaded(url, filename):
    if file_exists(filename):
        needs[filename] += 1
        return True
    else: 
        needs[filename] = 1
        
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        chunk_size = 1024 * 1024  # 1MB
        chunks = []

        def write_chunk(start):
            headers = {'Range': f'bytes={start}-{start + chunk_size - 1}'}
            r = requests.get(url, headers=headers, stream=True)
            return r.content

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(write_chunk, i) for i in range(0, total_size, chunk_size)]
            with open(filepath, 'wb') as f:
                for future in futures:
                    f.write(future.result())

        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False

def file_exists(filename):
    filepath = os.path.join("static", "din", filename)
    return os.path.isfile(filepath)

def delete_file(filename):
    if needs[filename] < 2:  
        filepath = os.path.join("static", "din", filename)
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True
        return False
    else:
        needs[filename] -= 1
        return True

@app.route("/")
def home():
    print("hello")
    return render_template("index.html")

@app.route("/play", methods=["POST"])
def download():
    data = request.get_json()
    url = "https://drive.google.com/uc?export=download&id=1g8wZM8On54kOHTI21fssDZEr-iXZfzBn"
    filename = "1.mp3"
    success = download_file_multithreaded(url, filename)
    return jsonify({"success": success, "filename": "static/din/" + filename})

@app.route("/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("filename")
    print("deleted" + filename)
    success = delete_file(filename)
    return jsonify({"success": success})
