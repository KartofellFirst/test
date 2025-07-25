from flask import Flask, render_template, request, jsonify, send_from_directory
import os, glob
import requests, json
import time
import csv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
    client_id="fd90af2b1c1447669656004c905a12c4",
    client_secret="34055e885c0a419a8e56f22d8bc3c242"
))

app = Flask(__name__)
spawntime = {}
MAX_FOLDER_SIZE = 400 * 1024 * 1024  # 400MB
MAX_FILE_AGE = 900  # 15 минут
TRACKS_FILE = 'tracks.json'
DESCRIPTION = "Your next response will be on behalf of the server of the site you are on. It shouldn't be big, it shouldn't have markup, and the answer should look like you're a real person. By the nature of your response, I expect you to be arrogant and self-important, and you will be polite but courteous, because you are working right now (but dont put it in every message please). Don't let the others have fun with you, you're more important than them! Don't get out of character, don't you dare say that you're Gemini, you can only write that you're a AI created by Google AI. A little bit about the site (don't throw it at user without he ask about it first): NT is a streaming service with music, its code is open and can be easily found on GitHub. The peculiarity of the service is that it does not store tracks at home, but only streams them, downloading them from other sources and subsequently deleting them as soon as they are saved to the client's cache. Our approach allows us to store terabytes of tracks without exceeding the 512 MB limit of our free VPS hosting. Now we're a new platform and we don't have terabytes of music yet, but users can import their own tracks if they want... "
still_needed_ids = set()

def clean_old_files():
    now = time.time()
    for name, ts in list(spawntime.items()):
        if now - ts > MAX_FILE_AGE:
            delete_file(name)

def download_file(url, filename):
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join("static", "din", filename)
    file_id = int(filename.replace(".mp3", ""))

    # 🔍 Проверка — если файл уже есть
    if os.path.isfile(filepath):
        still_needed_ids.add(file_id)
        print(f"[INFO] Файл {filename} уже существует — даём вторую жизнь")
        return True

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
    id = int(filename.replace(".mp3", ""))
    if id in still_needed_ids:
        still_needed_ids.discard(id)
        print(f"[INFO] файл {filename} всё ещё нужен — не удаляем")
        return True
    
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
    if not os.path.exists(TRACKS_FILE):
        return None
    with open(TRACKS_FILE, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            return None
    for entry in data:
        if str(entry[0]) == str(sought):
            return entry
    print(f"[REPORT] >>>>>>>>>>>>>> not found {sought}")
    return None

def get_free_index():
    if not os.path.exists(TRACKS_FILE):
        return 0
    with open(TRACKS_FILE, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            return 0
    return len(data)

def write_new_row(row_data):
    index = get_free_index()
    new_entry = [index] + row_data
    if os.path.exists(TRACKS_FILE):
        with open(TRACKS_FILE, 'r', encoding='utf-8') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    data.append(new_entry)
    with open(TRACKS_FILE, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    return index

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
    data_json = request.get_json()
    id = data_json.get("id")
    data = get_track_data(id)
    url = data[1]
    filename = f"{data[0]}.mp3"
    success = download_file(url, filename)
    return jsonify({"success": success, "filename": "static/din/" + filename, "data": data})

@app.route("/metadata", methods=["POST"])
def extract_metadata():
    data_json = request.get_json()
    data = data_json.get("data")
    filename = f"static/din/{data[0]}.jpg"

    # ожидание появления файла
    timeout = 5
    while not os.path.exists(filename) or os.path.getsize(filename) == 0:
        time.sleep(0.2)
        timeout -= 0.2
        if timeout <= 0:
            return jsonify({ "error": "File not ready" })

    audio = MP3(filename, ID3=ID3)
    metadata = {
        "title": data[2],
        "artist": data[3],
        "album": "NT collection (Spotify+)",
        "picture": "fill.jpg"
    }

    for tag in audio.tags.values():
        if isinstance(tag, APIC):
            picture_path = filename.replace(".mp3", ".jpg").replace("static/din/", "")
            full_path = f"static/din/{picture_path}"
            with open(full_path, 'wb') as img:
                img.write(tag.data)
            metadata["picture"] = full_path
            break
    return jsonify({ "metadata": metadata })


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
    species = data.get("species")
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

@app.route("/tracks-info", methods=["GET"])
def throw_csv_data():
    try:
        with open("tracks.csv", mode="r", encoding="utf-8") as file:
            reader = csv.reader(file)
            rows = list(reader)  # читаем все строки
        return jsonify(rows), 200
    except Exception as e:
        return f"Error happened while opening file: {str(e)}", 500

@app.route("/search/title", methods=["GET"])
def search_by_title():
    query = request.args.get("q", "").lower()
    results = []

    # 🔍 Поиск в локальном CSV
    with open("tracks.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            if query in row[2].lower():  # 2 — поле названия
                results.append({
                    "id": row[0],
                    "title": row[2],
                    "author": row[3],
                    "source": "local",
                    "genres": row[4] if len(row) > 4 else ""  # если есть жанры
                })

    # 🔁 Если ничего не нашли — ищем в Spotify
    if not results:
        spotify_result = sp.search(q=query, type="track", limit=5)
        for item in spotify_result["tracks"]["items"]:
            artist_id = item["artists"][0]["id"]
            artist = sp.artist(artist_id)
            genre_list = artist.get("genres", [])
            genres = ", ".join(genre_list) if genre_list else "unknown"

            results.append({
                "id": item["id"],
                "title": item["name"],
                "author": item["artists"][0]["name"],
                "source": "spotify",
                "genres": genres,
                "verified": False
            })

    return jsonify(results)
    
@app.route("/import_page")
def ipage():
    return render_template("import.html")

@app.route("/url-check", methods=["POST"])
def url_check():
    data = request.get_json()
    url = data.get("url")

    if url:
        free_filename = f"{get_free_index()}.mp3"
        success = download_file(url, free_filename)
        if success:
            return jsonify({"success": success, "filename": free_filename})
        return jsonify({"message": "Url not usable"}), 500
    return jsonify({"message": "Url not received"}), 500

@app.route("/html-preview")
def html_preview():
    url = request.args.get("site")

    if not url or not url.startswith("http"):
        return jsonify({"error": "❌ Неверный URL"}), 400

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/115 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        html_snippet = res.text[:1000]  # первые 1000 символов

        return jsonify({
            "status_code": res.status_code,
            "content_type": res.headers.get("Content-Type"),
            "html": html_snippet
        })

    except Exception as e:
        print("🔥 Ошибка запроса:", str(e))
        return jsonify({"error": "Ошибка запроса"}), 500


@app.route("/usage", methods=["GET"])
def total_project_usage():
    path = "."
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)
    size_in_mb = round(total_size / 1024 / 1024, 2)
    return jsonify({"total_size_mb": size_in_mb})

@app.route('/api/generate-content', methods=['POST'])
def generate_content():
    try:
        data = request.json
        message = data.get('message', '')
        ulm = data.get('ulm', 'null')
        blm = data.get('blm', 'null')
        resourses = int(get_folder_size() / 100000) / 10
        prompt = DESCRIPTION + "Your answer must be on the same language as user question! " + f"Your current load is {resourses}/400 MB. " + f"The last 3 messages from the chat: User: '{ulm}', You: '{blm}', User: "
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
            print(response.text, f"error {response.status_code}")
            return jsonify({"text": "Sorry, server is unable to respond to you at the moment. Try again later 👉👈"})
    except Exception as e:
        return jsonify({"error": f"Ошибка при обработке запроса: {str(e)}"}), 500

@app.route('/service-worker.js')
def sw():
    return send_from_directory('static', 'service-worker.js')
