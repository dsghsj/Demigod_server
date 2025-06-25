# DEMIGOD Secure File Server

A lightweight, secure, and stealth file server with a terminal-inspired interface. Zero database, maximum security, pure Python.

![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Security](https://img.shields.io/badge/security-enterprise-red.svg)

## 🔥 Features

### 🔐 Enterprise Security
- **HTTP Basic Authentication** with custom realm
- **IP-based Brute Force Protection** (3 attempts → 5min auto-block)
- **Directory Traversal Protection** with path validation
- **Filename Sanitization** prevents malicious uploads
- **Zero Database Architecture** - everything stored in RAM
- **No Persistent Logging** for maximum stealth

### 📁 File Management
- **Upload/Download Files** with drag-and-drop support
- **Real-time File Search** across all directories
- **Multi-column Sorting** (name, size, date modified)
- **Directory Navigation** with breadcrumb trails
- **File Preview** for text files
- **Auto-conflict Resolution** for duplicate filenames
- **Responsive File Icons** with hover effects

### 🎨 Terminal Aesthetic
- **Pure Black & White** monospace design
- **Courier New Font** for authentic terminal feel
- **Fully Responsive** - works on desktop, tablet, and mobile
- **No Flashy Colors** - professional and clean
- **Mobile-Optimized** with smart column management

### 📱 CLI & QR Features
- **ASCII QR Code** displayed in terminal for mobile access
- **Web QR Code** generation at `/qr` endpoint
- **Configurable Credentials** via command line
- **Professional Banner** with server status
- **Zero Configuration** - works out of the box

## 🚀 Quick Start

### Prerequisites
- Python 3.6 or higher
- No additional dependencies required (uses only standard library)

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/demigod-file-server.git
cd demigod-file-server

# Make executable (optional)
chmod +x secure_server.py
```

### Basic Usage
```bash
# Default setup (admin/admin on port 8000)
python secure_server.py

# Custom credentials and port
python secure_server.py -u hacker -p l33tpass -P 9000

# Disable QR code display
python secure_server.py --no-qr

# Full custom configuration
python secure_server.py --username operator --password secure123 --port 8080
```

## 📋 Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--username` | `-u` | Set authentication username | `admin` |
| `--password` | `-p` | Set authentication password | `admin` |
| `--port` | `-P` | Set server port | `8000` |
| `--no-qr` | | Disable QR code generation | `False` |
| `--help` | `-h` | Show help message | |

## 🛡️ Security Features

### Authentication
- HTTP Basic Authentication with custom realm
- Configurable username/password via CLI
- Session-based authentication tracking

### Brute Force Protection
- **3 failed attempts** triggers automatic IP blocking
- **5-minute cooldown** period for blocked IPs
- **Real-time monitoring** of authentication attempts
- **Automatic cleanup** of expired blocks

### Path Security
- Directory traversal attack prevention
- Real path validation for all file operations
- Secure filename sanitization
- Upload directory validation

### Zero Persistence
- No database files created
- No persistent logs stored
- All data stored in memory only
- Clean shutdown leaves no traces

## 📱 Mobile Access

The server automatically generates QR codes for easy mobile access:

### Terminal QR Code
When you start the server, an ASCII QR code is displayed in the terminal. Simply scan it with your phone to access the file server.

### Web QR Code
Visit `http://your-server:port/qr` to get a web-based QR code for sharing.

### Mobile Responsiveness
- **Desktop**: Full feature set with all columns
- **Tablet (768px)**: Optimized layout with smaller fonts
- **Mobile (480px)**: Compact view with essential columns only
- **Touch-Friendly**: Properly sized buttons and touch targets

## 🔍 File Operations

### Upload Files
- Drag and drop files onto the upload area
- Or click "Choose Files" to select manually
- Automatic conflict resolution (file_1.txt, file_2.txt, etc.)
- Real-time upload feedback with success/error messages

### Download Files
- Click "GET" button next to any file
- Direct download with proper MIME type detection
- Secure path validation prevents unauthorized access

### Search & Sort
- **Real-time Search**: Type to filter files instantly
- **Column Sorting**: Click headers to sort by name, size, or date
- **Cross-Directory**: Search works across all accessible directories
- **Case-Insensitive**: Flexible search matching

### Directory Navigation
- **Breadcrumb Navigation**: Click any path segment to jump there
- **Parent Directory**: Quick ".." navigation
- **Root Access**: Easy return to home directory

## 🎯 Use Cases

### Development
- **Local File Sharing** during development
- **Cross-device Testing** with mobile QR codes
- **Team Collaboration** with secure authentication
- **Asset Distribution** for development teams

### Enterprise
- **Secure File Transfer** within corporate networks
- **Temporary File Sharing** with auto-cleanup
- **Department File Access** with controlled authentication
- **Mobile File Access** for field teams

### Personal
- **Home Network Sharing** between devices
- **Mobile Photo Backup** via QR code access
- **Document Synchronization** across devices
- **Temporary File Storage** with no traces

## 🔧 Technical Details

### Architecture
- **Single File Application** - everything in one Python file
- **Standard Library Only** - no external dependencies
- **HTTP/1.1 Server** with custom request handling
- **In-Memory Storage** for all server state

### File Handling
- **Chunked Upload** support for large files
- **Multipart Form Data** parsing
- **MIME Type Detection** for proper downloads
- **Binary File Support** for all file types

### Performance
- **Lightweight** - minimal resource usage
- **Fast Response** - optimized for speed
- **Concurrent Connections** - handles multiple users
- **Memory Efficient** - smart garbage collection

## 🚨 Security Considerations

### Network Security
- **Always use HTTPS** in production environments
- **Firewall Rules** - restrict access to trusted networks only
- **VPN Access** - consider VPN for remote access
- **Regular Updates** - keep Python installation current

### Access Control
- **Strong Passwords** - use complex authentication credentials
- **Regular Rotation** - change passwords periodically
- **Network Monitoring** - watch for suspicious access patterns
- **Audit Logs** - monitor authentication attempts

### Data Security
- **Temporary Use** - designed for temporary file sharing
- **Clean Shutdown** - ensure proper server termination
- **No Persistence** - verify no data remains after shutdown
- **File Permissions** - ensure proper OS-level file permissions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Add comments for complex logic
- Test on multiple Python versions
- Ensure mobile responsiveness
- Maintain security standards

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Python's standard library only
- Inspired by terminal aesthetics and hacker culture
- Designed for security-conscious developers
- Mobile-first responsive design principles

## 📞 Support

- **Issues**: Report bugs via GitHub Issues
- **Features**: Request features via GitHub Issues
- **Security**: Email security issues privately
- **Documentation**: Contribute to README improvements

---

**DEMIGOD Secure File Server** - Because sometimes you need to share files like a boss. 🎯