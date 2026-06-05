import json
from http.server import HTTPServer, BaseHTTPRequestHandler


class TestAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/hello":
            self.send_json({"message": "Hello from cummand!", "method": "GET"})
        elif self.path == "/api/items":
            self.send_json({"items": ["apple", "banana", "cherry"], "method": "GET"})
        else:
            self.send_json({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        data = json.loads(body) if body else {}
        self.send_json({
            "message": "Item created",
            "method": "POST",
            "received": data
        }, 201)

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode() if length else "{}"
        data = json.loads(body) if body else {}
        self.send_json({
            "message": "Item updated",
            "method": "PUT",
            "received": data
        })

    def do_DELETE(self):
        self.send_json({
            "message": "Item deleted",
            "method": "DELETE"
        })

    def send_json(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = 8000
    server = HTTPServer(("0.0.0.0", port), TestAPIHandler)
    print(f"Test API running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  GET    /api/hello  — returns greeting")
    print(f"  GET    /api/items  — returns item list")
    print(f"  POST   /api/items  — create item (send JSON body)")
    print(f"  PUT    /api/items  — update item (send JSON body)")
    print(f"  DELETE /api/items  — delete item")
    print()
    print("Press Ctrl+C to stop")
    server.serve_forever()
