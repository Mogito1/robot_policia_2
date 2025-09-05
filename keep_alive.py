from flask import Flask
import threading
import os

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot activo en Render"

def run():
    port = int(os.environ.get("PORT", 5000))  # Render asigna el puerto
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
