#!/usr/bin/env python3
"""
Secure File Server with DEMIGOD Neon Theme
Features: HTTP Basic Auth, IP-based brute force protection, file upload/download, QR code generation
"""

import os
import sys
import time
import base64
import socket
import hashlib
import secrets
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, unquote, urlparse, quote
from collections import defaultdict
import html
import mimetypes
import json
import getpass

try:
    import qrcode
    from PIL import Image
    HAS_QR = True
except ImportError:
    HAS_QR = False
    print("Warning: qrcode and/or PIL not installed. QR code generation disabled.")

class SecurityManager:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.blocked_ips = set()
        self.max_attempts = 3
        self.block_duration = 300  # 5 minutes
        
    def is_blocked(self, ip):
        if ip in self.blocked_ips:
            return True
        
        # Clean old attempts
        cutoff = datetime.now() - timedelta(minutes=5)
        self.failed_attempts[ip] = [t for t in self.failed_attempts[ip] if t > cutoff]
        
        return len(self.failed_attempts[ip]) >= self.max_attempts
    
    def record_failed_attempt(self, ip):
        self.failed_attempts[ip].append(datetime.now())
        if len(self.failed_attempts[ip]) >= self.max_attempts:
            self.blocked_ips.add(ip)
            print(f"IP {ip} blocked due to too many failed attempts")
    
    def clear_attempts(self, ip):
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]

class SecureFileServer(BaseHTTPRequestHandler):
    username = None
    password = None
    security_manager = SecurityManager()
    server_root = os.getcwd()
    
    def log_message(self, format, *args):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {self.client_address[0]} - {format % args}")
    
    def authenticate(self):
        client_ip = self.client_address[0]
        
        # Check if IP is blocked
        if self.security_manager.is_blocked(client_ip):
            self.send_response(429)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Too Many Requests</h1><p>Your IP has been temporarily blocked.</p>')
            return False
        
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            self.request_auth()
            return False
        
        try:
            auth_type, credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                self.request_auth()
                return False
            
            decoded = base64.b64decode(credentials).decode('utf-8')
            provided_username, provided_password = decoded.split(':', 1)
            
            if provided_username == self.username and provided_password == self.password:
                self.security_manager.clear_attempts(client_ip)
                return True
            else:
                self.security_manager.record_failed_attempt(client_ip)
                self.request_auth()
                return False
                
        except Exception as e:
            self.security_manager.record_failed_attempt(client_ip)
            self.request_auth()
            return False
    
    def request_auth(self):
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="DEMIGOD SERVER"')
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html_content = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>DEMIGOD SERVER - Authentication Required</title>
            <style>
                body { 
                    background: #0a0a0a; 
                    color: #ffffff; 
                    font-family: 'Orbitron', 'Consolas', monospace; 
                    text-align: center; 
                    padding: 50px;
                }
                h1 { 
                    color: #ffffff; 
                    text-shadow: 0 0 10px #ffffff, 0 0 20px #ffffff, 0 0 30px #ffffff;
                    font-size: 2.5em;
                }
            </style>
        </head>
        <body>
            <h1>🔒 DEMIGOD SERVER</h1>
            <p>Authentication Required</p>
        </body>
        </html>
        '''
        self.wfile.write(html_content.encode())
    
    def do_GET(self):
        if self.path == '/logout':
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="DEMIGOD SERVER"')
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<h1>Logged Out</h1><p>Please refresh to login again.</p>')
            return
        
        if self.path == '/qr':
            if not self.authenticate():
                return
            self.serve_qr_code()
            return
        
        if not self.authenticate():
            return
        
        self.serve_file_or_directory()
    
    def do_POST(self):
        if not self.authenticate():
            return
        
        if self.path == '/upload':
            self.handle_upload()
        else:
            self.send_error(404)
    
    def serve_qr_code(self):
        if not HAS_QR:
            self.send_error(501, "QR code generation not available")
            return
        
        try:
            server_url = f"http://{self.get_server_ip()}:{self.server.server_port}"
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(server_url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="white", back_color="black")
            
            from io import BytesIO
            img_buffer = BytesIO()
            img.save(img_buffer, format='PNG')
            img_data = img_buffer.getvalue()
            
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Content-length', str(len(img_data)))
            self.end_headers()
            self.wfile.write(img_data)
            
        except Exception as e:
            self.send_error(500, f"QR code generation failed: {str(e)}")
    
    @staticmethod
    def get_server_ip():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "localhost"
    
    def serve_file_or_directory(self):
        # Parse the full URL
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path.lstrip('/'))
        query_params = parse_qs(parsed_url.query)
        
        print(f"DEBUG: Original path: {self.path}")
        print(f"DEBUG: Parsed path: {path}")
        print(f"DEBUG: Query params: {query_params}")
        
        full_path = os.path.join(self.server_root, path)
        
        # Security check - prevent directory traversal
        if not os.path.abspath(full_path).startswith(os.path.abspath(self.server_root)):
            self.send_error(403, "Access denied")
            return
        
        print(f"DEBUG: Full file path: {full_path}")
        print(f"DEBUG: File exists: {os.path.exists(full_path)}")
        
        if not os.path.exists(full_path):
            self.send_error(404, f"File not found: {full_path}")
            return
        
        if os.path.isfile(full_path):
            # Check if it's a view request
            is_view_request = 'view' in query_params
            print(f"DEBUG: Is view request: {is_view_request}")
            
            if is_view_request:
                self.serve_file_view(full_path)
            else:
                self.serve_file_download(full_path)
        else:
            self.serve_directory(full_path, path)
    
    def serve_file_view(self, file_path):
        print(f"DEBUG: Serving view for: {file_path}")
        try:
            # Simple approach - just serve the file with appropriate content type
            content_type, _ = mimetypes.guess_type(file_path)
            
            # For text files, try to display them in a simple viewer
            if content_type and content_type.startswith('text/'):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                filename = os.path.basename(file_path)
                simple_viewer = f'''<!DOCTYPE html>
<html>
<head>
    <title>View: {html.escape(filename)}</title>
    <style>
        body {{ background: #0a0a0a; color: #fff; font-family: monospace; padding: 20px; }}
        pre {{ background: #111; padding: 20px; border: 1px solid #fff; }}
        .header {{ color: #fff; text-shadow: 0 0 10px #fff; }}
    </style>
</head>
<body>
    <h1 class="header">📄 {html.escape(filename)}</h1>
    <a href="javascript:history.back()" style="color: #ff0000;">← Back</a>
    <pre>{html.escape(content)}</pre>
</body>
</html>'''
                
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(simple_viewer.encode('utf-8'))
            else:
                # For other files, serve directly
                self.send_response(200)
                self.send_header('Content-type', content_type or 'application/octet-stream')
                self.end_headers()
                
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                
        except Exception as e:
            print(f"DEBUG: Error in serve_file_view: {e}")
            self.send_error(500, f"Error viewing file: {str(e)}")
    
    def serve_file_download(self, file_path):
        try:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(file_size))
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    
        except Exception as e:
            self.send_error(500, f"Error downloading file: {str(e)}")
    
    def serve_directory(self, dir_path, relative_path):
        try:
            items = []
            for item in sorted(os.listdir(dir_path)):
                if item.startswith('.'):
                    continue
                    
                item_path = os.path.join(dir_path, item)
                # Fix URL construction to handle spaces and special characters
                if relative_path:
                    item_url = f"/{relative_path.strip('/')}/{quote(item)}".replace('//', '/')
                else:
                    item_url = f"/{quote(item)}"
                
                if os.path.isdir(item_path):
                    items.append({
                        'name': item,
                        'type': 'directory',
                        'url': item_url,
                        'size': '-',
                        'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M")
                    })
                else:
                    size = os.path.getsize(item_path)
                    items.append({
                        'name': item,
                        'type': 'file',
                        'url': item_url,
                        'size': self.format_size(size),
                        'modified': datetime.fromtimestamp(os.path.getmtime(item_path)).strftime("%Y-%m-%d %H:%M")
                    })
            
            html_content = self.generate_directory_listing_html(relative_path, items)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error listing directory: {str(e)}")
    
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def generate_directory_listing_html(self, path, items):
        current_path = f"/{path}" if path else "/"
        parent_path = "/".join(current_path.split("/")[:-1]) if current_path != "/" else None
        
        qr_link = '<a href="/qr" class="neon-btn qr-btn">📱 QR Code</a>' if HAS_QR else ''
        
        html_content = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DEMIGOD SERVER - {html.escape(current_path)}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            background: #0a0a0a;
            color: #ffffff;
            font-family: 'Orbitron', 'Consolas', monospace;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        /* Header */
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding: 20px 0;
            border-bottom: 2px solid #ffffff;
        }}
        
        .logo {{
            font-size: 2.5em;
            font-weight: 900;
            color: #ffffff;
            text-shadow: 
                0 0 5px #ffffff,
       
        }}}}
        
        .header-actions {{
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        
        /* Buttons */
        .neon-btn {{
            background: #000000;
            color: #ff0000;
            border: 2px solid #ffffff;
            padding: 12px 20px;
            text-decoration: none;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-shadow: 0 0 5px #ff0000;
            display: inline-block;
        }}
        
        .neon-btn:hover {{
            background: #111111;
            box-shadow: 
                0 0 10px #ffffff,
                inset 0 0 10px rgba(255, 255, 255, 0.1);
            transform: scale(1.05);
            text-shadow: 0 0 10px #ff0000, 0 0 15px #ff0000;
        }}
        
        .logout-btn {{
            background: #330000;
        }}
        
        .logout-btn:hover {{
            background: #550000;
        }}
        
        /* Path Navigation */
        .path-nav {{
            background: #111111;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid #333333;
        }}
        
        .path-nav code {{
            color: #ffffff;
            font-size: 1.1em;
        }}
        
        /* Upload Form */
        .upload-section {{
            background: #111111;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 2px solid #ffffff;
        }}
        
        .upload-form {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        
        .file-input {{
            background: #000000;
            color: #ffffff;
            border: 2px solid #ffffff;
            padding: 10px 15px;
            border-radius: 8px;
            font-family: inherit;
            flex: 1;
            min-width: 200px;
        }}
        
        .file-input:focus {{
            outline: none;
            box-shadow: 0 0 10px #ffffff;
        }}
        
        /* File Table */
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            background: #111111;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #ffffff;
        }}
        
        .file-table th {{
            background: #000000;
            color: #ffffff;
            padding: 15px;
            text-align: left;
            font-weight: 700;
            border-bottom: 2px solid #ffffff;
            text-shadow: 0 0 5px #ffffff;
        }}
        
        .file-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #333333;
            transition: background 0.2s ease;
        }}
        
        .file-table tr:hover td {{
            background: #222222;
        }}
        
        .file-icon {{
            width: 20px;
            text-align: center;
            font-size: 1.2em;
        }}
        
        .file-name {{
            color: #ffffff;
            text-decoration: none;
            font-weight: 600;
        }}
        
        .file-name:hover {{
            color: #ffffff;
            text-shadow: 0 0 5px #ffffff;
        }}
        
        .directory-link {{
            color: #00ffff !important;
            text-shadow: 0 0 5px #00ffff;
        }}
        
        .directory-link:hover {{
            text-shadow: 0 0 10px #00ffff;
        }}
        
        /* Action Buttons */
        .action-buttons {{
            display: flex;
            gap: 10px;
        }}
        
        .action-btn {{
            background: #000000;
            color: #ff0000;
            border: 1px solid #ffffff;
            padding: 6px 12px;
            text-decoration: none;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: inherit;
            transition: all 0.2s ease;
        }}
        
        .action-btn:hover {{
            background: #111111;
            box-shadow: 0 0 5px #ffffff;
            transform: scale(1.05);
        }}
        
        .view-btn {{
            color: #00ff00 !important;
            text-shadow: 0 0 3px #00ff00;
        }}
        
        .download-btn {{
            color: #ff0000 !important;
            text-shadow: 0 0 3px #ff0000;
        }}
        
        /* Mobile Responsive */
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            
            .header {{
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }}
            
            .logo {{
                font-size: 2em;
            }}
            
            .upload-form {{
                flex-direction: column;
            }}
            
            .file-input {{
                min-width: 100%;
            }}
            
            .file-table {{
                font-size: 0.9em;
            }}
            
            .file-table th,
            .file-table td {{
                padding: 8px;
            }}
            
            .action-buttons {{
                flex-direction: column;
                gap: 5px;
            }}
        }}
        
        @media (max-width: 480px) {{
            .file-table th:nth-child(3),
            .file-table td:nth-child(3),
            .file-table th:nth-child(4),
            .file-table td:nth-child(4) {{
                display: none;
            }}
        }}
        
        /* Footer */
        .footer {{
            margin-top: 40px;
            padding: 20px 0;
            border-top: 1px solid #333333;
            text-align: center;
            color: #666666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1 class="logo">🔱 DEMIGOD SERVER</h1>
            <div class="header-actions">
                {qr_link}
                <a href="/logout" class="neon-btn logout-btn">🔓 Logout</a>
            </div>
        </header>
        
        <div class="path-nav">
            <strong>Current Path:</strong> <code>{html.escape(current_path)}</code>
        </div>
        
        <div class="upload-section">
            <h3 style="margin-bottom: 15px; color: #ffffff; text-shadow: 0 0 5px #ffffff;">📤 Upload File</h3>
            <form method="post" action="/upload" enctype="multipart/form-data" class="upload-form">
                <input type="file" name="file" class="file-input" required>
                <input type="hidden" name="path" value="{html.escape(path)}">
                <button type="submit" class="neon-btn">⬆️ Upload</button>
            </form>
        </div>
        
        <table class="file-table">
            <thead>
                <tr>
                    <th></th>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Modified</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        '''
        
        # Parent directory link
        if parent_path is not None:
            html_content += f'''
                <tr>
                    <td class="file-icon">📁</td>
                    <td><a href="{parent_path}" class="file-name directory-link">.. (Parent Directory)</a></td>
                    <td>-</td>
                    <td>-</td>
                    <td>-</td>
                </tr>
            '''
        
        # Directory and file listings
        for item in items:
            if item['type'] == 'directory':
                icon = '📁'
                name_class = 'file-name directory-link'
                actions = '-'
            else:
                icon = '📄'
                name_class = 'file-name'
                # Fix URL construction - ensure proper path encoding
                view_url = item['url'] + '?view=1'
                download_url = item['url']
                actions = f'''
                    <div class="action-buttons">
                        <a href="{view_url}" class="action-btn view-btn">👁️ View</a>
                        <a href="{download_url}" class="action-btn download-btn">⬇️ Download</a>
                    </div>
                '''
            
            html_content += f'''
                <tr>
                    <td class="file-icon">{icon}</td>
                    <td><a href="{item['url']}" class="{name_class}">{html.escape(item['name'])}</a></td>
                    <td>{item['size']}</td>
                    <td>{item['modified']}</td>
                    <td>{actions}</td>
                </tr>
            '''
        
        html_content += '''
            </tbody>
        </table>
        
        <footer class="footer">
            <p>🔱 DEMIGOD SERVER - Secure File Management System</p>
        </footer>
    </div>
</body>
</html>
        '''
        
        return html_content
    
    def handle_upload(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error(400, "No file data received")
                return
            
            post_data = self.rfile.read(content_length)
            
            # Parse multipart form data (simplified)
            boundary = self.headers.get('Content-Type').split('boundary=')[1].encode()
            parts = post_data.split(b'--' + boundary)
            
            uploaded_file = None
            upload_path = ""
            
            for part in parts:
                if b'Content-Disposition' in part and b'filename=' in part:
                    # Extract filename
                    lines = part.split(b'\r\n')
                    filename = None
                    for line in lines:
                        if b'filename=' in line:
                            filename = line.decode().split('filename="')[1].split('"')[0]
                            break
                    
                    if filename:
                        # Extract file data
                        data_start = part.find(b'\r\n\r\n') + 4
                        file_data = part[data_start:-2]  # Remove trailing \r\n
                        uploaded_file = (filename, file_data)
                
                elif b'name="path"' in part:
                    # Extract path
                    data_start = part.find(b'\r\n\r\n') + 4
                    upload_path = part[data_start:-2].decode()
            
            if not uploaded_file:
                self.send_error(400, "No file found in upload")
                return
            
            filename, file_data = uploaded_file
            
            # Security check for filename
            filename = os.path.basename(filename)  # Remove any path components
            if not filename or filename.startswith('.'):
                self.send_error(400, "Invalid filename")
                return
            
            # Determine upload directory
            if upload_path:
                upload_dir = os.path.join(self.server_root, upload_path.lstrip('/'))
            else:
                upload_dir = self.server_root
            
            # Security check for upload directory
            if not os.path.abspath(upload_dir).startswith(os.path.abspath(self.server_root)):
                self.send_error(403, "Access denied")
                return
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Redirect back to directory
            redirect_path = f"/{upload_path}" if upload_path else "/"
            self.send_response(302)
            self.send_header('Location', redirect_path)
            self.end_headers()
            
            print(f"File uploaded: {filename} -> {file_path}")
            
        except Exception as e:
            self.send_error(500, f"Upload failed: {str(e)}")

def setup_server():
    print("🔱 DEMIGOD SERVER Setup")
    print("=" * 50)
    
    # Get configuration
    username = input("Enter username: ").strip()
    password = getpass.getpass("Enter password: ").strip()
    
    while True:
        try:
            port = int(input("Enter port (default 8000): ").strip() or "8000")
            if 1 <= port <= 65535:
                break
            else:
                print("Port must be between 1 and 65535")
        except ValueError:
            print("Please enter a valid port number")
    
    # Set server configuration
    SecureFileServer.username = username
    SecureFileServer.password = password
    
    return port

def main():
    try:
        port = setup_server()
        
        # Start server
        server = HTTPServer(('0.0.0.0', port), SecureFileServer)
        server_ip = SecureFileServer.get_server_ip()
        
        print("\n🔱 DEMIGOD SERVER Started")
        print("=" * 50)
        print(f"Server running on: http://{server_ip}:{port}")
        print(f"Local access: http://localhost:{port}")
        print(f"Root directory: {os.getcwd()}")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 50)
        
        if HAS_QR:
            print(f"QR Code available at: http://{server_ip}:{port}/qr")
        
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n\n🔱 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
