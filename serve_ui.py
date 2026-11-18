import http.server
import socketserver
import webbrowser
import os

PORT = 8000


folder = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(folder, "ui"))

handler = http.server.SimpleHTTPRequestHandler
socketserver.TCPServer.allow_reuse_address = True

with socketserver.TCPServer(("", PORT), handler) as server:
    url = "http://localhost:" + str(PORT)
    print("Dashboard running at " + url)
    print("Press Ctrl+C to stop")

    webbrowser.open(url)  

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped")