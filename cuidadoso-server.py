#!/usr/bin/env python3
"""Servidor multi-pagina Cuidadoso — serve landing, dashboards e paginas auxiliares."""
import http.server
import os
import sys

PORT = 8090
REPO = "/home/steve/Documentos/Python/Projeto-Home-Care"

# Mapeamento de rotas → arquivos
ROUTES = {
    "/": "index.html",
    "/landing": "landing.html",
    "/index.html": "index.html",
    "/privacidade.html": "privacidade.html",
    "/termos-de-uso.html": "termos-de-uso.html",
    "/manual-do-produto.html": "manual-do-produto.html",
    "/dashboard": "home_care_ia.html",
    "/home_care_ia.html": "home_care_ia.html",
    "/dashboard-cliente": "dashboard_cliente.html",
    "/dashboard_cliente.html": "dashboard_cliente.html",
    "/dashboard-admin": "dashboard.html",
    "/dashboard.html": "dashboard.html",
    "/cuidador": "cuidador_dashboard.html",
    "/cuidador_dashboard.html": "cuidador_dashboard.html",
}

MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css",
    ".js": "application/javascript",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".json": "application/json",
}


class CuidadosoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=REPO, **kwargs)

    def do_GET(self):
        from urllib.parse import urlparse
        path = urlparse(self.path).path

        if path in ROUTES:
            self.path = "/" + ROUTES[path]
        elif path.startswith("/api/"):
            # Tentar proxy para o backend Railway se configurado
            self.send_error(502, "Backend indisponivel localmente")
            return

        return super().do_GET()

    def guess_type(self, path):
        _, ext = os.path.splitext(path)
        return MIME.get(ext, "application/octet-stream")


if __name__ == "__main__":
    os.chdir(REPO)
    server = http.server.HTTPServer(("0.0.0.0", PORT), CuidadosoHandler)
    print(f"✅ Servidor Cuidadoso rodando em http://0.0.0.0:{PORT}")
    print(f"   Landing:     http://localhost:{PORT}/")
    print(f"   Dashboard:   http://localhost:{PORT}/dashboard")
    print(f"   Admin:       http://localhost:{PORT}/dashboard-admin")
    sys.stdout.flush()
    server.serve_forever()
