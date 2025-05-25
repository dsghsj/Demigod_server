# DEMIGOD Secure File Server

A simple, secure, personal file server with basic authentication, file upload, download, and directory browsing capabilities.  
The server features a dark-themed modern UI and can be accessed locally or from other devices on the same network. It also displays a QR code in the terminal for easy mobile access.

---

## Features

- Basic HTTP authentication with configurable username and password.
- Secure file uploads and downloads with support for multiple files.
- Directory listing with file size and navigation.
- Dark-themed responsive UI viewable on desktop and mobile.
- Logout functionality to invalidate authentication.
- Displays local and network access URLs on startup.
- Generates a terminal QR code for the server network URL (optional, requires `qrcode` package).

---

## Installation

### Requirements

- Python 3.6 or higher.
- (Optional) For QR code display: install the `qrcode` Python package.

### Installing Dependencies

To install the optional QR code package, run:

```bash
pip install qrcode[pil]