from flask import Flask, render_template, request, jsonify
import os
import requests
import time
import aiohttp
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
spawntime = {}
MAX_FOLDER_SIZE = 400 * 1024 * 1024  # 400MB
MAX_FILE_AGE = 900  # 15 минут
chunk_size = 1024 * 1024  # 1MB

def clean_old_files():
    now = time.time()
    for name, ts in list(spawntime.items()):
        if now - ts > MAX_FILE_AGE:
            delete_file(name)

async def fetch_chunk(session, url, start, end):
    headers = {'Range': f'bytes={start}-{end}'}
    async with session.get(url, headers=headers) as resp:
        return await resp.read()

async def download_async(url, filename, workers=8):
    folder = os.path.join("static", "din")
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    # 🧹 Очистка
    clean_old_files()
    if get_folder_size(folder) > MAX_FOLDER_SIZE:
        print("❌ Превышен лимит размера папки")
        return

    try:
        async with session.get(url, headers={"Range": "bytes=0-1"}) as resp:
            content_range = resp.headers.get("Content-Range")
            if content_range:
                total_size = int(content_range.split("/")[-1])
            else:
                total_size = int(resp.headers.get("Content-Length", 0))

            ranges = [(i, min(i + chunk_size - 1, total_size - 1)) for i in range(0, total_size, chunk_size)]

            tasks = [fetch_chunk(session, url, start, end) for start, end in ranges[:workers]]
            start_time = time.time()
            chunks = await asyncio.gather(*tasks)
            end_time = time.time()

            with open(filepath, "wb") as f:
                for chunk in chunks:
                    f.write(chunk)

            spawntime[filename] = time.time()
            print(f"⚡ Загрузка завершена за {end_time - start_time:.2f} сек")

    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def download_file_async_background(url: str, filename: str):
    threading.Thread(target=lambda: asyncio.run(download_async(url, filename))).start()

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
    success = download_file_async_background(url, filename)
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
