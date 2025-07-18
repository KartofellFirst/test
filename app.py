from flask import Flask, render_template, request, jsonify
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
spawntime = {}
MAX_FOLDER_SIZE = 400 * 1024 * 1024  # 400MB
MAX_FILE_AGE = 900  # 15 минут

def download_file_multithreaded(url, filename):
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)

    # clean old files
    now = time.time()
    for filename, timestamp in list(spawntime.items()):
        if now - timestamp > MAX_FILE_AGE:
            delete_file(filename)

    # monitoring
    if get_folder_size(folder) > MAX_FOLDER_SIZE:
        print("❌ Превышен лимит размера папки")
        return False
    
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

        with ThreadPoolExecutor(max_workers=8) as executor:
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
    filepath = os.path.join("static", "din", filename)
    if os.path.isfile(filepath):
        os.remove(filepath)
        spawntime.pop(filename, None)
        return True
    return False

def get_folder_size(path="static/din"):
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size  # в байтах

@app.route("/")
def home():
    print("hello")
    return render_template("index.html")

@app.route("/awake")
def for_awake():
    print("website pinged by UptimeRobot")
    return "Now I`m awake, thank you!"

@app.route("/play", methods=["POST"])
def download():
    data = request.get_json()
    url = "https://drive.google.com/uc?export=download&id=1g8wZM8On54kOHTI21fssDZEr-iXZfzBn"
    filename = "1.mp3"
    start = time.time()
    success = download_file_multithreaded(url, filename)
    end = time.time()
    print(f"⏳ Время загрузки: {end - start:.2f} секунд")
    return jsonify({"success": success, "filename": "static/din/" + filename})

@app.route("/delete", methods=["POST"])
def delete():
    data = request.get_json()
    filename = data.get("filename")
    print("deleted" + filename)
    success = delete_file(filename)
    return jsonify({"success": success})

@app.route("/monitor", methods=["GET"])
def monitor_resourses():
    calc = int(get_folder_size() / 100000) / 10
    return jsonify(calc)
