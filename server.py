import http.server
import socketserver
import os

# Configuração da porta
PORT = 8080

# Manipulador de requisições HTTP
class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Se o caminho for a raiz ou não existir, servir o index.html
        if self.path == '/' or not os.path.exists(os.path.join(os.getcwd(), self.path[1:])):
            self.path = '/index.html'
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

# Configurar e iniciar o servidor
Handler = MyHttpRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Servidor rodando em http://localhost:{PORT}")
    print("Pressione Ctrl+C para encerrar o servidor")
    httpd.serve_forever()