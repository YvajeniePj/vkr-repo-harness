#!/usr/bin/env python3
"""
Ollama WSL Reverse Proxy Bridge
Listens on http://127.0.0.1:11435 in WSL Linux and proxies requests
to the Windows Ollama daemon (127.0.0.1:11434) using WSL Interop curl.exe.
This bypasses Windows Firewall / VPN routing isolation between WSL2 and Windows Host.
"""
import http.server
import socketserver
import subprocess
import sys
import os

PORT = int(os.environ.get("OLLAMA_PROXY_PORT", "11435"))
TARGET_URL = os.environ.get("OLLAMA_TARGET_URL", "http://127.0.0.1:11434")
CURL_BIN = os.environ.get("CURL_EXE", "/mnt/c/Windows/System32/curl.exe")

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

class OllamaProxyHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self.proxy_request("GET")

    def do_POST(self):
        self.proxy_request("POST")

    def do_HEAD(self):
        self.proxy_request("HEAD")

    def do_DELETE(self):
        self.proxy_request("DELETE")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def proxy_request(self, method):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        cmd = [CURL_BIN, "-s", "-i", "-N", "-X", method, f"{TARGET_URL}{self.path}"]
        for k, v in self.headers.items():
            if k.lower() not in ["host", "connection", "transfer-encoding"]:
                cmd.extend(["-H", f"{k}: {v}"])
        if body:
            cmd.extend(["--data-binary", "@-"])

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if body else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if body:
            stdout_data, _ = proc.communicate(input=body)
        else:
            stdout_data, _ = proc.communicate()

        parts = stdout_data.split(b"\r\n\r\n", 1)
        header_text = parts[0].decode("utf-8", errors="replace")
        response_body = parts[1] if len(parts) > 1 else b""

        lines = header_text.split("\r\n")
        status_line = lines[0].split(" ", 2)
        try:
            status_code = int(status_line[1])
        except (IndexError, ValueError):
            status_code = 200

        self.send_response(status_code)
        for line in lines[1:]:
            if ": " in line:
                k, v = line.split(": ", 1)
                if k.lower() not in ["transfer-encoding", "content-length", "connection"]:
                    self.send_header(k, v)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        pass

def main():
    server = ThreadedHTTPServer(("127.0.0.1", PORT), OllamaProxyHandler)
    print(f"Ollama Proxy bridge active: http://127.0.0.1:{PORT} -> {TARGET_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
