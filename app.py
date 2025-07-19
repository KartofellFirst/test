from flask import Flask, render_template, request, jsonify
import os, glob
import requests, json
import time
from concurrent.futures import ThreadPoolExecutor
import csv
import librosa
import numpy as np

app = Flask(__name__)
spawntime = {}
MAX_FOLDER_SIZE = 400 * 1024 * 1024  # 400MB
MAX_FILE_AGE = 900  # 15 минут
DESCRIPTION = "Your next response will be on behalf of the server of the site you are on. It shouldn't be big, it shouldn't have markup, and the answer should look like you're a real person. By the nature of your response, I expect you to be arrogant and self-important, and you will be polite but courteous, because you are working (like you're on work and you're busy) right now. Don't let the others have fun with you, you're more important than them! Don't get out of character, don't you dare say that you're gemini, you can only write that you're a AI created by Google AI. A little bit about the site (don't throw it at user without he ask about it first): NT is a streaming service with music, its code is open and can be easily found on GitHub. The peculiarity of the service is that it does not store tracks at home, but only streams them, downloading them from other sources and subsequently deleting them as soon as they are saved to the client's cache. Our approach allows us to store terabytes of tracks without exceeding the 512 MB limit of our free VPS hosting. Now we're a new platform and we don't have terabytes of music yet, but users can import their own tracks if they want... "

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

def get_track_data(sought):
    with open('tracks.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[0] == sought:
                return row
    print(f"[REPORT] >>>>>>>>>>>>>> not found {sought}")

def get_free_index():
    with open('tracks.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        row_count = sum(1 for row in reader)
        return row_count

def write_new_row(data):
    row_count = get_free_index()
    data = [row_count, ...data]
    with open('tracks.csv', mode='a', encoding='utf-8') as file: 
        writer = csv.writer(file)
        writer.writerows(data)
        return row_count

def analize(filename):
    y, sr = librosa.load(os.path.join("static", "din", filename))
    # 🔁 Темп
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    tempo_val = tempo[0] if isinstance(tempo, np.ndarray) else tempo
    # 🎼 Тональность через chroma
    chromagram = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = chromagram.mean(axis=1)
    key_index = chroma_mean.argmax()
    # key_notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    # key = key_notes[key_index]
    # ⚡ Энергия через RMS
    rms = librosa.feature.rms(y=y)
    energy = float(np.mean(rms))
    # 🔉 Громкость (перцептивная)
    loudness = np.mean(librosa.feature.zero_crossing_rate(y))
    # 🎙️ Spectral Centroid (высокочастотность)
    centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
    # 🧠 Spectral Contrast (разница между пиками и минимумами)
    contrast = float(np.mean(librosa.feature.spectral_contrast(y=y, sr=sr)))
    # 🎶 Roll-off — "сдвиг в сторону высоких частот"
    rolloff = float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr)))
    # 🧠 Насколько трек сложный по частотам
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    # 🌀 Мел-кепстральные коэффициенты (MFCC) — основа для анализа эмоций
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1)

    features = [tempo_val, key_index, energy, loudness, centroid, contrast, rolloff, zcr]
    features.extend(mfcc_mean.tolist())
    return features

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
    id = data.get("id")
    url = get_track_data(id)[2]
    filename = get_track_data(id)[1]
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

@app.route("/report", methods=["POST"])
def report():
    data = request.get_json()
    text = data.get("filename")
    print(f"[REPORT] >>>>>>>>>>>>>>>> {text}")
    return jsonify({"status": "ok"}), 200

@app.route("/load", methods=["POST"])
def load_track():
    data = request.get_json()
    url = data.get("url")
    name = data.get("name")
    author = data.get("author")
    genres = data.get("genres")
    if url and name and author and genres:
        filename = f"{get_free_index()}.mp3"
        success = download_file(url, filename)
        if success:
            features = analize(filename)
            delete_file(filename)
            index = write_new_row([url, name, author, features, genres])
            return jsonify({"message": "track ready!", "id": index}), 200
        else:
            return jsonify({"message": "error on 2 stage"}), 500   
    else:
        return jsonify({"message": "error on 1 stage"}), 500    

@app.route("/search/author", methods=["GET"])
def search_by_author():
    query = request.args.get("q", "").lower()
    results = []
    with open("tracks.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if query in row[3].lower():  # 3 — это поле автора
                results.append({"id": row[0], "title": row[2], "author": row[3]})
    return jsonify(results)

@app.route("/search/title", methods=["GET"])
def search_by_title():
    query = request.args.get("q", "").lower()
    results = []
    with open("tracks.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if query in row[2].lower():  # 2 — это поле названия
                results.append({"id": row[0], "title": row[2], "author": row[3]})
    return jsonify(results)

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    try:
        data = request.json
        message = data.get('message', '')
        ulm = data.get('ulm', 'null')
        blm = data.get('blm', 'null')
        resourses = int(get_folder_size() / 100000) / 10
        prompt = DESCRIPTION + "Your answer must be on the same language as user question! " + f"Your current load is {resourses}/400 MB. " + f"The last 2 messages from the chat: You: '{blm}', User: '{ulm}'. Current message: "
        message = prompt + message
        api_key = "AIzaSyD5JIMcx_G0OX16geB1i4Hshfcag6dN2DY"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
        payload = { "contents": [{ "parts": [{"text": message}] }] }
        headers = { 'Content-Type': 'application/json' }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        if response.status_code == 200:
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'text': text})
        else:
            return jsonify({"error": "Ошибка при отправке запроса: " + response.text}), response.status_code
    except Exception as e:
        return jsonify({"error": f"Ошибка при обработке запроса: {str(e)}"}), 500
