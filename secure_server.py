from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import base64
import os
import getpass
import socket
import urllib
import html
import cgi

MAX_ATTEMPTS = 3
BLOCKED_CLIENTS = {}
CHUNK_SIZE = 1024 * 1024  # 1 MB

class AuthHandler(SimpleHTTPRequestHandler):
    def do_AUTHHEAD(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Secure Area"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def is_blocked(self, client_ip):
        return BLOCKED_CLIENTS.get(client_ip, 0) >= MAX_ATTEMPTS

    def record_failed_attempt(self, client_ip):
        BLOCKED_CLIENTS[client_ip] = BLOCKED_CLIENTS.get(client_ip, 0) + 1

    def is_authenticated(self):
        auth_header = self.headers.get('Authorization')
        if auth_header is None:
            return False
        expected = 'Basic ' + base64.b64encode(
            f"{self.server.USERNAME}:{self.server.PASSWORD}".encode()
        ).decode()
        return auth_header == expected

    def log_client_info(self):
        client_ip = self.client_address[0]
        try:
            client_host = socket.gethostbyaddr(client_ip)[0]
        except Exception:
            client_host = 'Unknown'
        print(f"Connection from {client_ip} ({client_host})")

    def styled_html(self, msg):
        return f"""
        <html>
        <head><title>Access Denied</title></head>
        <body style="background:#111;color:white;display:flex;justify-content:center;align-items:center;height:100vh;margin:0;">
            <div style="text-align:center;">
                <h1 style="font-size:3em;">{msg}</h1>
            </div>
        </body>
        </html>
        """.encode()

    def do_GET(self):
        client_ip = self.client_address[0]

        if self.path == "/logout":
            self.handle_logout()
            return

        if self.is_blocked(client_ip):
            self.send_forbidden("LIMIT REACHED BITCH!GO FUCK YOURSELF")
            return

        if not self.is_authenticated():
            self.record_failed_attempt(client_ip)
            self.do_AUTHHEAD()
            self.wfile.write(self.styled_html("WRONG CREDENTIALS BITCH"))
            return

        self.log_client_info()
        self.handle_file_request()

    def handle_logout(self):
        """Force logout by sending 401 with WWW-Authenticate header"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Secure Area"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"LOGIN AGAIN U LIL SHIT!")

    def send_forbidden(self, message):
        self.send_response(403)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(self.styled_html(message))

    def handle_file_request(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_path.query)
        filepath = urllib.parse.unquote(parsed_path.path)
        full_path = self.translate_path(filepath)

        if os.path.isfile(full_path):
            if "download" in query:
                self.send_file(full_path, download=True)
            else:
                self.send_file(full_path)
        else:
            self.list_directory(full_path)

    def send_file(self, full_path, download=False):
        try:
            if download:
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{os.path.basename(full_path)}"')
            else:
                ctype = self.guess_type(full_path)
                self.send_response(200)
                self.send_header("Content-Type", ctype)

            self.send_header('Content-Length', os.path.getsize(full_path))
            self.end_headers()

            with open(full_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except Exception as e:
            self.send_error(500, f"Error serving file: {e}")

    def list_directory(self, path):
        try:
            file_list = os.listdir(path)
        except OSError:
            self.send_error(404, "Cannot access directory.")
            return

        file_list.sort(key=lambda a: a.lower())
        display_path = urllib.parse.unquote(self.path)
        if not display_path.endswith('/'):
            display_path += '/'

        html_content = self.generate_directory_listing_html(display_path, file_list, path)
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

    def format_size(self, size):
        if size >= 1 << 30:
            return f"{size / (1 << 30):.2f} GB"
        elif size >= 1 << 20:
            return f"{size / (1 << 20):.2f} MB"
        else:
            return f"{size} bytes"

    def generate_directory_listing_html(self, display_path, file_list, path):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Secure File Server - {html.escape(display_path)}</title>
            <style>
                body {{
                    background-color: #121212;
                    color: #ffffff;
                    font-family: Arial, sans-serif;
                    margin: 0; padding: 1em;
                }}
                header {{
                    background: #000;
                    color: white;
                    padding: 1em;
                    text-align: center;
                    font-weight: bold;
                    font-size: 1.5em;
                    position: relative;
                }}
                nav {{
                    position: absolute;
                    top: 1rem;
                    right: 1rem;
                }}
                nav a {{
                    background-color: #000;
                    color: white;
                    padding: 0.3em 0.8em;
                    border-radius: 4px;
                    text-decoration: none;
                    font-size: 0.9em;
                }}
                nav a:hover {{
                    background-color: #444;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 1em;
                    font-size: 1em;
                }}
                th, td {{
                    padding: 0.8em;
                    border-bottom: 1px solid #444;
                    text-align: left;
                }}
                th {{
                    background-color: #222;
                }}
                tr:hover {{
                    background-color: #333;
                }}
                .button {{
                    background-color: #000;
                    color: white;
                    padding: 0.5em 1em;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    transition: background-color 0.3s;
                    text-decoration: none;
                    display: inline-block;
                    margin-right: 10px;
                    font-size: 0.9em;
                }}
                .button:hover {{
                    background-color: #444;
                }}
                @media (max-width: 600px) {{
                    header {{
                        font-size: 1.2em;
                    }}
                    table {{
                        font-size: 0.9em;
                    }}
                    .button {{
                        padding: 0.4em 0.8em;
                        margin-right: 5px;
                        font-size: 0.85em;
                    }}
                }}
                form {{
                    margin-top: 1em;
                    font-size: 1em;
                }}
                label {{
                    cursor: pointer;
                    color: #ccc;
                    display: block;
                    margin-bottom: 0.5em;
                }}
                input[type="file"] {{
                    display: block;
                    margin-bottom: 0.5em;
                }}
            </style>
        </head>
        <body>
            <header>
                DEMIGOD SERVER
                <nav>
                    <a href="/logout">Logout</a>
                </nav>
            </header>
            <main>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Size</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        if display_path != "/":
            parent_path = urllib.parse.urljoin(display_path, "..")
            html_content += f"""<tr><td colspan="3"><a href="{parent_path}">.. (parent directory)</a></td></tr>"""
        for filename in file_list:
            full_item_path = os.path.join(path, filename)
            display_name = html.escape(filename)
            size_str = self.format_size(os.path.getsize(full_item_path)) if os.path.isfile(full_item_path) else "-"
            file_url = urllib.parse.quote(display_path + filename)
            if os.path.isdir(full_item_path):
                file_url += "/"
            actions = self.generate_file_actions(full_item_path, file_url)
            html_content += f"""
            <tr>
                <td>{display_name}</td>
                <td>{size_str}</td>
                <td>{actions}</td>
            </tr>"""
        html_content += """
                    </tbody>
                </table>
                <form enctype="multipart/form-data" method="post" action="">
                    <label for="fileElem">Select files to upload</label>
                    <input type="file" id="fileElem" multiple name="file" />
                    <button type="submit" class="button">Upload</button>
                </form>
            </main>
        </body>
        </html>
        """
        return html_content

    def generate_file_actions(self, full_item_path, file_url):
        if os.path.isfile(full_item_path):
            return f'<a class="button" href="{file_url}" target="_blank" rel="noopener noreferrer">View</a>' \
                   f'<a class="button" href="{file_url}?download=1">Download</a>'
        else:
            return f'<a class="button" href="{file_url}">Open</a>'

    def do_POST(self):
        if not self.is_authenticated():
            self.do_AUTHHEAD()
            self.wfile.write(b"Authentication required")
            return

        ctype, pdict = cgi.parse_header(self.headers.get('Content-Type'))
        if ctype != 'multipart/form-data':
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Bad Request: Expected multipart/form-data")
            return

        pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
        pdict['CONTENT-LENGTH'] = int(self.headers.get('Content-Length'))
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={'REQUEST_METHOD': 'POST'},
                                keep_blank_values=True)

        if not form.list:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No files selected for upload.")
            return

        for field in form.list:
            if field.filename:
                filename = os.path.basename(field.filename)
                file_path = os.path.join(self.translate_path(urllib.parse.unquote(self.path)), filename)
                with open(file_path, 'wb') as f:
                    data = field.file.read()
                    f.write(data)
        self.send_response(303)
        self.send_header('Location', self.path)
        self.end_headers()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def print_qr_code(url):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print("qrcode library not installed. To show QR code, please install it via 'pip install qrcode[pil]'.")

def print_heading():
    heading = "=== DEMIGOD SERVER ==="
    print("\n" + "="*len(heading))
    print(heading)
    print("="*len(heading) + "\n")

def run_server():
    print_heading()
    username = input("Set username for server login: ")
    password = getpass.getpass("Set password for server login: ")
    while True:
        port_str = input("Enter port to run server on (default 8000): ").strip()
        if port_str == "":
            PORT = 8000
            break
        elif port_str.isdigit() and 1 <= int(port_str) <= 65535:
            PORT = int(port_str)
            break
        else:
            print("Please enter a valid port number (1-65535) or leave blank for default 8000.")
    local_ip = get_local_ip()
    url_local = f"http://localhost:{PORT}/"
    url_network = f"http://{local_ip}:{PORT}/"
    print("\n" + "="*60)
    print("  🚀 Secure Personal File Server Running 🚀")
    print(f"  Access URLs:")
    print(f"  - Local:   {url_local}")
    print(f"  - Network: {url_network}")
    print("\n  Scan this QR code from your mobile device to open the server URL:")
    print_qr_code(url_network)
    print("="*60 + "\n")
    server_address = ('', PORT)
    httpd = ThreadingHTTPServer(server_address, AuthHandler)
    httpd.USERNAME = username
    httpd.PASSWORD = password
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")

if __name__ == "__main__":
    run_server()
