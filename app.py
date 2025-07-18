from flask import Flask, render_template, request, jsonify
import os, glob
import requests
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
spawntime = {}
MAX_FOLDER_SIZE = 400 * 1024 * 1024  # 400MB
MAX_FILE_AGE = 900  # 15 минут

def clean_old_files():
    now = time.time()
    for name, ts in list(spawntime.items()):
        if now - ts > MAX_FILE_AGE:
            delete_file(name)

def download_file(url, filename):
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    clean_old_files()
    if get_folder_size(folder) > MAX_FOLDER_SIZE:
        print("❌ Превышен лимит размера папки")
        return False

    chunk_size = 1024 * 1024  # ← добавили!

    try:
        response = requests.get(url, stream=True)
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size):
                if chunk:
                    f.write(chunk)

        spawntime[filename] = time.time()
        print(f"✅ Файл {filename} загружен успешно")
        return True

    except Exception as e:
        print(f"❌ Ошибка обычной загрузки: {e}")
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
    

with app.app_context():
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)
    
    for path in glob.glob(os.path.join(folder, "*")):
        if os.path.isfile(path):
            os.remove(path)
    
    spawntime.clear()
    print("🧼 static/din очищена при запуске WSGI-приложения")
    

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
    success = download_file(url, filename)
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
