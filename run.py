"""Inicia o Radar Inteligente de Notícias e abre o navegador."""
import sys
import threading
import webbrowser

import uvicorn

from app import config

if __name__ == "__main__":
    url = f"http://{'localhost' if config.HOST in ('127.0.0.1', '0.0.0.0') else config.HOST}:{config.PORT}"
    if "--no-browser" not in sys.argv:
        threading.Timer(2.5, lambda: webbrowser.open(url)).start()
    print(f"\n  Radar Inteligente de Notícias em {url}\n  Para encerrar, feche esta janela ou pressione Ctrl+C.\n")
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, log_level="info")
