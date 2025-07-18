from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    print(hello)
    return "hello"
