#!/usr/bin/env python3
"""
DEMIGOD Secure File Server
Zero-database, password-protected, file-serving system
Built for secure, anonymous use with terminal aesthetic
"""

import os
import sys
import time
import socket
import base64
import hashlib
import argparse
import threading
from datetime import datetime, timedelta
from urllib.parse import unquote, quote
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
import mimetypes
import json
import html

# ASCII QR Code generation (fallback if qrcode not available)
try:
    import qrcode
    from PIL import Image
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in separate threads"""
    daemon_threads = True
    allow_reuse_address = True

class SecureFileHandler(BaseHTTPRequestHandler):
    """Main HTTP request handler"""
    
    # Class variables for configuration
    USERNAME = "admin"
    PASSWORD = "admin"
    FAILED_ATTEMPTS = {}  # IP -> {'count': int, 'blocked_until': datetime}
    MAX_ATTEMPTS = 3
    BLOCK_DURATION = 300  # 5 minutes
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def is_ip_blocked(self, ip):
        """Check if IP is currently blocked"""
        if ip in self.FAILED_ATTEMPTS:
            attempt_data = self.FAILED_ATTEMPTS[ip]
            if datetime.now() < attempt_data.get('blocked_until', datetime.min):
                return True
            elif attempt_data['count'] >= self.MAX_ATTEMPTS:
                # Reset if block period expired
                del self.FAILED_ATTEMPTS[ip]
        return False
    
    def record_failed_attempt(self, ip):
        """Record failed login attempt"""
        now = datetime.now()
        if ip not in self.FAILED_ATTEMPTS:
            self.FAILED_ATTEMPTS[ip] = {'count': 1, 'blocked_until': now}
        else:
            self.FAILED_ATTEMPTS[ip]['count'] += 1
            if self.FAILED_ATTEMPTS[ip]['count'] >= self.MAX_ATTEMPTS:
                self.FAILED_ATTEMPTS[ip]['blocked_until'] = now + timedelta(seconds=self.BLOCK_DURATION)
    
    def authenticate(self):
        """Handle HTTP Basic Authentication"""
        client_ip = self.client_address[0]
        
        # Check if IP is blocked
        if self.is_ip_blocked(client_ip):
            self.send_response(429)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Too Many Attempts</h1><p>IP blocked. Try again later.</p></body></html>')
            return False
        
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            self.request_auth()
            return False
        
        try:
            auth_type, auth_string = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                self.request_auth()
                return False
            
            decoded = base64.b64decode(auth_string).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            if username == self.USERNAME and password == self.PASSWORD:
                return True
            else:
                self.record_failed_attempt(client_ip)
                self.request_auth()
                return False
        except:
            self.record_failed_attempt(client_ip)
            self.request_auth()
            return False
    
    def request_auth(self):
        """Send authentication request"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="DEMIGOD SERVER"')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>Authentication Required</h1></body></html>')
    
    def sanitize_path(self, path):
        """Sanitize and validate file paths"""
        # Remove query parameters
        if '?' in path:
            path = path.split('?')[0]
        
        # Decode URL encoding
        path = unquote(path)
        
        # Remove leading slash and normalize
        if path.startswith('/'):
            path = path[1:]
        
        # Prevent directory traversal
        path_parts = []
        for part in path.split('/'):
            if part == '' or part == '.':
                continue
            elif part == '..':
                if path_parts:
                    path_parts.pop()
            else:
                path_parts.append(part)
        
        return os.path.join(os.getcwd(), *path_parts) if path_parts else os.getcwd()
    
    def get_file_info(self, filepath):
        """Get file information"""
        try:
            stat = os.stat(filepath)
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'is_dir': os.path.isdir(filepath)
            }
        except:
            return None
    
    def format_size(self, size):
        """Format file size"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def generate_file_list(self, directory, search_query="", sort_by="name"):
        """Generate file listing HTML"""
        try:
            files = []
            for item in os.listdir(directory):
                if search_query.lower() in item.lower():
                    filepath = os.path.join(directory, item)
                    info = self.get_file_info(filepath)
                    if info:
                        files.append({
                            'name': item,
                            'path': filepath,
                            'info': info
                        })
            
            # Sort files
            if sort_by == "size":
                files.sort(key=lambda x: x['info']['size'], reverse=True)
            elif sort_by == "date":
                files.sort(key=lambda x: x['info']['modified'], reverse=True)
            else:  # name
                files.sort(key=lambda x: x['name'].lower())
            
            # Separate directories and files
            dirs = [f for f in files if f['info']['is_dir']]
            regular_files = [f for f in files if not f['info']['is_dir']]
            
            return dirs + regular_files
        except:
            return []
    
    def generate_html(self, directory, files, current_path, search_query="", sort_by="name"):
        """Generate main HTML interface"""
        rel_path = os.path.relpath(directory, os.getcwd()).replace('\\', '/')
        if rel_path == '.':
            rel_path = ''
        
        # Generate breadcrumb
        path_parts = rel_path.split('/') if rel_path else []
        breadcrumb = '<a href="/" style="color: #fff; text-decoration: none;">ROOT</a>'
        current = ''
        for part in path_parts:
            if part:
                current += '/' + part
                breadcrumb += f' / <a href="{current}" style="color: #fff; text-decoration: none;">{html.escape(part)}</a>'
        
        # Generate file table
        file_rows = ""
        if rel_path:  # Add parent directory link
            parent = os.path.dirname(rel_path)
            parent_url = f"/{parent}" if parent else "/"
            file_rows += f'''
            <tr style="border-bottom: 1px solid #333;">
                <td style="padding: 8px; color: #ccc;">📁</td>
                <td style="padding: 8px;"><a href="{parent_url}" style="color: #fff; text-decoration: none;">..</a></td>
                <td style="padding: 8px; color: #888;">-</td>
                <td style="padding: 8px; color: #888;">-</td>
                <td style="padding: 8px;">-</td>
            </tr>'''
        
        for file_data in files:
            name = file_data['name']
            info = file_data['info']
            encoded_name = quote(name)
            
            if info['is_dir']:
                file_url = f"/{rel_path}/{encoded_name}" if rel_path else f"/{encoded_name}"
                icon = "📁"
                size_str = "-"
                actions = f'<div class="action-btns"><a href="{file_url}">OPEN</a></div>'
            else:
                file_url = f"/{rel_path}/{encoded_name}" if rel_path else f"/{encoded_name}"
                icon = "📄"
                size_str = self.format_size(info['size'])
                actions = f'''<div class="action-btns">
                <a href="{file_url}">GET</a>
                <a href="{file_url}?view=1">VIEW</a>
                </div>'''
            
            date_str = info['modified'].strftime('%Y-%m-%d %H:%M')
            
            file_rows += f'''
            <tr style="border-bottom: 1px solid #333;" onmouseover="this.style.backgroundColor='#222'" onmouseout="this.style.backgroundColor='transparent'">
                <td style="padding: 8px; color: #ccc;">{icon}</td>
                <td style="padding: 8px; color: #fff;">{html.escape(name)}</td>
                <td style="padding: 8px; color: #888;">{size_str}</td>
                <td style="padding: 8px; color: #888;">{date_str}</td>
                <td style="padding: 8px;">{actions}</td>
            </tr>'''
        
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>DEMIGOD SERVER</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            background: #000;
            color: #fff;
            font-family: 'Courier New', monospace;
            line-height: 1.4;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #333;
            padding-bottom: 20px;
        }}
        .header h1 {{
            font-size: 2em;
            margin-bottom: 10px;
            color: #fff;
            letter-spacing: 2px;
        }}
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 20px;
            align-items: center;
        }}
        .search-box {{
            flex: 1;
            min-width: 200px;
            padding: 8px;
            background: #111;
            border: 1px solid #333;
            color: #fff;
            border-radius: 3px;
        }}
        .sort-select {{
            padding: 8px;
            background: #111;
            border: 1px solid #333;
            color: #fff;
            border-radius: 3px;
        }}
        .btn {{
            padding: 8px 16px;
            background: #333;
            color: #fff;
            text-decoration: none;
            border: 1px solid #555;
            border-radius: 3px;
            cursor: pointer;
            display: inline-block;
        }}
        .btn:hover {{
            background: #555;
        }}
        .upload-form {{
            background: #111;
            padding: 15px;
            border: 1px solid #333;
            border-radius: 3px;
            margin-bottom: 20px;
        }}
        .file-table {{
            width: 100%;
            border-collapse: collapse;
            background: #111;
            border: 1px solid #333;
            overflow-x: auto;
            display: block;
            white-space: nowrap;
        }}
        .file-table thead,
        .file-table tbody,
        .file-table tr {{
            display: table;
            width: 100%;
            table-layout: fixed;
        }}
        .file-table th {{
            background: #222;
            padding: 8px 4px;
            text-align: left;
            border-bottom: 2px solid #333;
            color: #fff;
            font-size: 12px;
        }}
        .file-table td {{
            padding: 8px 4px;
            font-size: 12px;
            border-bottom: 1px solid #333;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .file-table th:nth-child(1), .file-table td:nth-child(1) {{ width: 8%; }}
        .file-table th:nth-child(2), .file-table td:nth-child(2) {{ width: 35%; }}
        .file-table th:nth-child(3), .file-table td:nth-child(3) {{ width: 12%; }}
        .file-table th:nth-child(4), .file-table td:nth-child(4) {{ width: 20%; }}
        .file-table th:nth-child(5), .file-table td:nth-child(5) {{ width: 25%; }}
        .action-btns {{
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }}
        .action-btns a {{
            color: #fff;
            background: #333;
            padding: 4px 6px;
            text-decoration: none;
            border-radius: 3px;
            font-size: 10px;
            white-space: nowrap;
        }}
        .action-btns a:hover {{
            background: #555;
        }}
        .breadcrumb {{
            margin-bottom: 20px;
            padding: 10px;
            background: #111;
            border: 1px solid #333;
            border-radius: 3px;
            word-break: break-all;
        }}
        .upload-path {{
            width: 100%;
            padding: 8px;
            background: #000;
            border: 1px solid #333;
            color: #fff;
            margin-bottom: 10px;
            border-radius: 3px;
        }}
        input[type="file"] {{
            padding: 8px;
            background: #000;
            border: 1px solid #333;
            color: #fff;
            width: 100%;
            margin-bottom: 10px;
            border-radius: 3px;
        }}
        
        /* Mobile specific styles */
        @media (max-width: 768px) {{
            .container {{
                padding: 10px;
            }}
            .header h1 {{
                font-size: 1.5em;
                letter-spacing: 1px;
            }}
            .controls {{
                flex-direction: column;
                gap: 8px;
            }}
            .search-box {{
                min-width: 100%;
            }}
            .file-table {{
                font-size: 11px;
            }}
            .file-table th, .file-table td {{
                padding: 6px 2px;
                font-size: 11px;
            }}
            .file-table th:nth-child(1), .file-table td:nth-child(1) {{ width: 10%; }}
            .file-table th:nth-child(2), .file-table td:nth-child(2) {{ width: 30%; }}
            .file-table th:nth-child(3), .file-table td:nth-child(3) {{ width: 15%; }}
            .file-table th:nth-child(4), .file-table td:nth-child(4) {{ width: 20%; }}
            .file-table th:nth-child(5), .file-table td:nth-child(5) {{ width: 25%; }}
            .action-btns {{
                flex-direction: column;
                gap: 2px;
            }}
            .action-btns a {{
                font-size: 9px;
                padding: 3px 5px;
                text-align: center;
            }}
            .upload-form {{
                padding: 10px;
            }}
            .btn {{
                padding: 6px 12px;
                font-size: 12px;
            }}
        }}
        
        /* Very small mobile screens */
        @media (max-width: 480px) {{
            .file-table th:nth-child(3), .file-table td:nth-child(3) {{ 
                display: none; 
            }}
            .file-table th:nth-child(4), .file-table td:nth-child(4) {{ 
                display: none; 
            }}
            .file-table th:nth-child(1), .file-table td:nth-child(1) {{ width: 12%; }}
            .file-table th:nth-child(2), .file-table td:nth-child(2) {{ width: 48%; }}
            .file-table th:nth-child(5), .file-table td:nth-child(5) {{ width: 40%; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ DEMIGOD SERVER ⚡</h1>
            <div style="margin-top: 10px;">
                <a href="/qr" class="btn">QR CODE</a>
                <a href="/logout" class="btn" style="margin-left: 10px;">LOGOUT</a>
            </div>
        </div>
        
        <div class="breadcrumb">
            <strong>Path:</strong> {breadcrumb}
        </div>
        
        <div class="controls">
            <input type="text" class="search-box" placeholder="Search files..." value="{html.escape(search_query)}" 
                   onkeyup="if(event.key==='Enter') search()" id="searchInput">
            <select class="sort-select" onchange="sort(this.value)" id="sortSelect">
                <option value="name" {'selected' if sort_by == 'name' else ''}>Sort by Name</option>
                <option value="size" {'selected' if sort_by == 'size' else ''}>Sort by Size</option>
                <option value="date" {'selected' if sort_by == 'date' else ''}>Sort by Date</option>
            </select>
            <button class="btn" onclick="search()">SEARCH</button>
            <button class="btn" onclick="clearSearch()">CLEAR</button>
        </div>
        
        <div class="upload-form">
            <h3 style="margin-bottom: 10px;">📤 UPLOAD FILE</h3>
            <form method="post" enctype="multipart/form-data">
                <input type="text" name="upload_path" class="upload-path" placeholder="Upload path (leave empty for current directory)" value="{html.escape(rel_path)}">
                <input type="file" name="file" required>
                <button type="submit" class="btn">UPLOAD</button>
            </form>
        </div>
        
        <table class="file-table">
            <thead>
                <tr>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Modified</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {file_rows}
            </tbody>
        </table>
    </div>
    
    <script>
        function search() {{
            const query = document.getElementById('searchInput').value;
            const sort = document.getElementById('sortSelect').value;
            const url = new URL(window.location);
            url.searchParams.set('search', query);
            url.searchParams.set('sort', sort);
            window.location = url;
        }}
        
        function sort(sortBy) {{
            const query = document.getElementById('searchInput').value;
            const url = new URL(window.location);
            url.searchParams.set('search', query);
            url.searchParams.set('sort', sortBy);
            window.location = url;
        }}
        
        function clearSearch() {{
            const url = new URL(window.location);
            url.searchParams.delete('search');
            url.searchParams.delete('sort');
            window.location = url;
        }}
    </script>
</body>
</html>'''
        return html_content
    
    def generate_qr_ascii(self, text):
        """Generate ASCII QR code"""
        if not QR_AVAILABLE:
            return "QR code libraries not available (pip install qrcode pillow)"
        
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=1,
                border=1,
            )
            qr.add_data(text)
            qr.make(fit=True)
            
            # Get the matrix
            matrix = qr.get_matrix()
            
            # Convert to ASCII
            ascii_qr = ""
            for row in matrix:
                line = ""
                for cell in row:
                    line += "██" if cell else "  "
                ascii_qr += line + "\n"
            
            return ascii_qr
        except Exception as e:
            return f"QR generation failed: {str(e)}"
    
    def do_GET(self):
        """Handle GET requests"""
        if not self.authenticate():
            return
        
        # Handle logout
        if self.path == '/logout':
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="DEMIGOD SERVER"')
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Logged Out</h1><p>Please close your browser or clear credentials.</p></body></html>')
            return
        
        # Handle QR code
        if self.path == '/qr':
            server_url = f"http://{get_local_ip()}:{self.server.server_address[1]}"
            qr_ascii = self.generate_qr_ascii(server_url)
            
            html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>QR Code - DEMIGOD SERVER</title>
    <style>
        body {{ background: #000; color: #fff; font-family: 'Courier New', monospace; padding: 20px; text-align: center; }}
        .qr-container {{ margin: 20px auto; display: inline-block; background: #fff; padding: 20px; border-radius: 10px; }}
        pre {{ color: #000; font-size: 4px; line-height: 4px; }}
        .back-btn {{ display: inline-block; margin-top: 20px; padding: 10px 20px; background: #333; color: #fff; text-decoration: none; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>⚡ DEMIGOD SERVER QR CODE ⚡</h1>
    <p>Scan to access: {html.escape(server_url)}</p>
    <div class="qr-container">
        <pre>{html.escape(qr_ascii)}</pre>
    </div>
    <a href="/" class="back-btn">BACK TO FILES</a>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode())
            return
        
        # Parse query parameters
        path_and_query = self.path
        query_params = {}
        if '?' in path_and_query:
            path_part, query_part = path_and_query.split('?', 1)
            for param in query_part.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[unquote(key)] = unquote(value)
        else:
            path_part = path_and_query
        
        # Get search and sort parameters
        search_query = query_params.get('search', '')
        sort_by = query_params.get('sort', 'name')
        view_mode = query_params.get('view', '')
        
        # Sanitize path
        safe_path = self.sanitize_path(path_part)
        
        if not os.path.exists(safe_path):
            self.send_response(404)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>404 Not Found</h1></body></html>')
            return
        
        if os.path.isdir(safe_path):
            # Directory listing
            files = self.generate_file_list(safe_path, search_query, sort_by)
            html_content = self.generate_html(safe_path, files, path_part, search_query, sort_by)
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(html_content.encode())
        else:
            # File download/view
            try:
                if view_mode == '1':
                    # View file content (text files only)
                    mime_type, _ = mimetypes.guess_type(safe_path)
                    if mime_type and mime_type.startswith('text/'):
                        with open(safe_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{html.escape(os.path.basename(safe_path))} - DEMIGOD SERVER</title>
    <style>
        body {{ background: #000; color: #fff; font-family: 'Courier New', monospace; margin: 0; padding: 20px; }}
        .header {{ margin-bottom: 20px; border-bottom: 1px solid #333; padding-bottom: 10px; }}
        .content {{ background: #111; padding: 20px; border: 1px solid #333; white-space: pre-wrap; overflow-x: auto; }}
        .back-btn {{ display: inline-block; padding: 8px 16px; background: #333; color: #fff; text-decoration: none; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📄 {html.escape(os.path.basename(safe_path))}</h2>
        <a href="javascript:history.back()" class="back-btn">BACK</a>
        <a href="{html.escape(path_part)}" class="back-btn" style="margin-left: 10px;">DOWNLOAD</a>
    </div>
    <div class="content">{html.escape(content)}</div>
</body>
</html>'''
                        
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html')
                        self.end_headers()
                        self.wfile.write(html_content.encode())
                    else:
                        # Non-text file, redirect to download
                        self.send_response(302)
                        self.send_header('Location', path_part)
                        self.end_headers()
                else:
                    # Download file
                    mime_type, _ = mimetypes.guess_type(safe_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'
                    
                    file_size = os.path.getsize(safe_path)
                    filename = os.path.basename(safe_path)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
                    self.send_header('Content-Length', str(file_size))
                    self.end_headers()
                    
                    with open(safe_path, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(f'<html><body><h1>Error</h1><p>{html.escape(str(e))}</p></body></html>'.encode())
    
    def parse_multipart(self, data, boundary):
        """Parse multipart form data"""
        parts = data.split(f'--{boundary}'.encode())
        form_data = {}
        
        for part in parts[1:-1]:  # Skip first empty part and last closing part
            if not part.strip():
                continue
                
            # Split headers and content
            if b'\r\n\r\n' in part:
                header_section, content = part.split(b'\r\n\r\n', 1)
            else:
                continue
            
            # Parse Content-Disposition header
            headers = header_section.decode('utf-8', errors='ignore')
            if 'Content-Disposition: form-data;' not in headers:
                continue
            
            # Extract field name
            name_match = None
            filename_match = None
            
            for line in headers.split('\r\n'):
                if 'Content-Disposition:' in line:
                    if 'name="' in line:
                        name_start = line.find('name="') + 6
                        name_end = line.find('"', name_start)
                        name_match = line[name_start:name_end]
                    
                    if 'filename="' in line:
                        filename_start = line.find('filename="') + 10
                        filename_end = line.find('"', filename_start)
                        filename_match = line[filename_start:filename_end]
            
            if name_match:
                # Remove trailing \r\n from content
                content = content.rstrip(b'\r\n')
                
                if filename_match:
                    # File field
                    form_data[name_match] = {
                        'filename': filename_match,
                        'content': content
                    }
                else:
                    # Text field
                    form_data[name_match] = content.decode('utf-8', errors='ignore')
        
        return form_data

    def do_POST(self):
        """Handle POST requests (file uploads)"""
        if not self.authenticate():
            return
        
        try:
            content_type = self.headers.get('Content-Type', '')
            if not content_type.startswith('multipart/form-data'):
                self.send_response(400)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Bad Request</h1><p>Expected multipart/form-data</p></body></html>')
                return
            
            # Extract boundary
            if 'boundary=' not in content_type:
                self.send_response(400)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Bad Request</h1><p>No boundary found</p></body></html>')
                return
            
            boundary = content_type.split('boundary=')[1].strip()
            content_length = int(self.headers.get('Content-Length', 0))
            
            if content_length > 100 * 1024 * 1024:  # 100MB limit
                self.send_response(413)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>File Too Large</h1><p>Maximum file size is 100MB</p></body></html>')
                return
            
            # Read the data
            raw_data = self.rfile.read(content_length)
            
            # Parse multipart data
            form_data = self.parse_multipart(raw_data, boundary)
            
            # Get upload path and file data
            upload_path = form_data.get('upload_path', '')
            file_info = form_data.get('file')
            
            if not file_info or not file_info.get('filename'):
                self.send_response(400)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<html><body><h1>Bad Request</h1><p>No file uploaded</p></body></html>')
                return
            
            filename = file_info['filename']
            file_data = file_info['content']
            
            # Sanitize filename
            filename = os.path.basename(filename)
            if not filename:
                filename = 'uploaded_file'
            
            # Determine upload directory
            if upload_path and upload_path.strip():
                upload_dir = self.sanitize_path(upload_path.strip())
            else:
                upload_dir = os.getcwd()
            
            # Ensure upload directory exists and is valid
            try:
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir, exist_ok=True)
                
                # Verify it's within our allowed paths
                real_upload_dir = os.path.realpath(upload_dir)
                real_cwd = os.path.realpath(os.getcwd())
                
                if not real_upload_dir.startswith(real_cwd):
                    upload_dir = os.getcwd()
                    
            except:
                upload_dir = os.getcwd()
            
            # Save file
            file_path = os.path.join(upload_dir, filename)
            
            # Handle file conflicts
            counter = 1
            original_filename = filename
            while os.path.exists(file_path):
                name, ext = os.path.splitext(original_filename)
                filename = f"{name}_{counter}{ext}"
                file_path = os.path.join(upload_dir, filename)
                counter += 1
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(file_data)
            
            # Generate success response
            success_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Upload Success - DEMIGOD SERVER</title>
    <style>
        body {{ background: #000; color: #fff; font-family: 'Courier New', monospace; padding: 20px; text-align: center; }}
        .success {{ background: #111; padding: 20px; border: 1px solid #333; border-radius: 5px; max-width: 600px; margin: 0 auto; }}
        .btn {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #333; color: #fff; text-decoration: none; border-radius: 3px; }}
        .btn:hover {{ background: #555; }}
    </style>
    <script>
        setTimeout(function() {{
            window.location.href = '/{"" if not upload_path else upload_path}';
        }}, 2000);
    </script>
</head>
<body>
    <div class="success">
        <h2>✅ Upload Successful</h2>
        <p>File: <strong>{html.escape(filename)}</strong></p>
        <p>Size: <strong>{self.format_size(len(file_data))}</strong></p>
        <p>Location: <strong>{html.escape(os.path.relpath(upload_dir, os.getcwd()))}</strong></p>
        <p style="margin-top: 15px; color: #888;">Redirecting in 2 seconds...</p>
        <a href="/{"" if not upload_path else upload_path}" class="btn">Go Back Now</a>
    </div>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            self.wfile.write(success_html.encode())
            
        except Exception as e:
            error_msg = str(e)
            self.send_response(500)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            error_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Upload Error - DEMIGOD SERVER</title>
    <style>
        body {{ background: #000; color: #fff; font-family: 'Courier New', monospace; padding: 20px; text-align: center; }}
        .error {{ background: #111; padding: 20px; border: 1px solid #333; border-radius: 5px; max-width: 600px; margin: 0 auto; }}
        .btn {{ display: inline-block; margin-top: 15px; padding: 10px 20px; background: #333; color: #fff; text-decoration: none; border-radius: 3px; }}
    </style>
</head>
<body>
    <div class="error">
        <h2>❌ Upload Failed</h2>
        <p>Error: {html.escape(error_msg)}</p>
        <a href="javascript:history.back()" class="btn">Go Back</a>
    </div>
</body>
</html>'''
            self.wfile.write(error_html.encode())

def get_local_ip():
    """Get local IP address"""
    try:
        # Connect to a dummy address to get local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def print_banner():
    """Print startup banner"""
    banner = """
██████╗ ███████╗███╗   ███╗██╗ ██████╗  ██████╗ ██████╗ 
██╔══██╗██╔════╝████╗ ████║██║██╔════╝ ██╔═══██╗██╔══██╗
██║  ██║█████╗  ██╔████╔██║██║██║  ███╗██║   ██║██║  ██║
██║  ██║██╔══╝  ██║╚██╔╝██║██║██║   ██║██║   ██║██║  ██║
██████╔╝███████╗██║ ╚═╝ ██║██║╚██████╔╝╚██████╔╝██████╔╝
╚═════╝ ╚══════╝╚═╝     ╚═╝╚═╝ ╚═════╝  ╚═════╝ ╚═════╝ 
    
    SECURE FILE SERVER - ZERO DATABASE - ANONYMOUS USE
    """
    print(banner)

def print_qr_code_cli(text):
    """Print QR code in CLI"""
    if not QR_AVAILABLE:
        print("📱 QR Code libraries not available")
        print("   Install with: pip install qrcode pillow")
        return
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(text)
        qr.make(fit=True)
        
        # Print ASCII QR code
        print("\n📱 QR CODE FOR MOBILE ACCESS:")
        print("=" * 50)
        qr.print_ascii(invert=True)
        print("=" * 50)
        print(f"🔗 URL: {text}")
        print()
    except Exception as e:
        print(f"❌ QR generation failed: {e}")

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="DEMIGOD Secure File Server - Zero-database file serving with terminal aesthetic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python secure_server.py
  python secure_server.py -u admin -p secret123 -P 9000
  python secure_server.py --username hacker --password l33t --port 8080
        """
    )
    
    parser.add_argument('-u', '--username', 
                       default='admin',
                       help='Username for authentication (default: admin)')
    
    parser.add_argument('-p', '--password',
                       default='admin', 
                       help='Password for authentication (default: admin)')
    
    parser.add_argument('-P', '--port',
                       type=int,
                       default=8000,
                       help='Port number to serve on (default: 8000)')
    
    parser.add_argument('--no-qr',
                       action='store_true',
                       help='Disable QR code generation in CLI')
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Set credentials
    SecureFileHandler.USERNAME = args.username
    SecureFileHandler.PASSWORD = args.password
    
    # Get local IP
    local_ip = get_local_ip()
    
    try:
        # Create server
        server = ThreadingHTTPServer(('0.0.0.0', args.port), SecureFileHandler)
        
        print(f"🔐 Authentication:")
        print(f"   Username: {args.username}")
        print(f"   Password: {args.password}")
        print()
        
        print(f"🌐 Server URLs:")
        print(f"   Local:    http://127.0.0.1:{args.port}")
        print(f"   Network:  http://{local_ip}:{args.port}")
        print()
        
        print(f"📁 Serving directory: {os.getcwd()}")
        print()
        
        # Print QR code if enabled
        if not args.no_qr:
            server_url = f"http://{local_ip}:{args.port}"
            print_qr_code_cli(server_url)
        
        print("🛡️  Security Features:")
        print("   ✅ HTTP Basic Authentication")
        print("   ✅ IP-based brute force protection (3 attempts, 5min block)")
        print("   ✅ Directory traversal protection")
        print("   ✅ Filename sanitization")
        print("   ✅ Zero database/logging (RAM only)")
        print()
        
        print("🚀 Server Features:")
        print("   ✅ File upload/download")
        print("   ✅ File search & sorting") 
        print("   ✅ Directory navigation")
        print("   ✅ File preview (text files)")
        print("   ✅ QR code access")
        print("   ✅ Responsive web interface")
        print()
        
        print("⚡ DEMIGOD SERVER STARTED ⚡")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        # Start server
        server.serve_forever()
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        server.shutdown()
        server.server_close()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Error: Port {args.port} is already in use")
            print("   Try a different port with -P option")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()