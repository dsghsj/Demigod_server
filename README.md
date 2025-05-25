`README.md`
  markdown
# DEMIGOD Secure File Server

A lightweight Python-based personal file server providing secure file upload, browsing, and download over local networks with basic HTTP authentication. It features a dark-themed responsive web UI and terminal QR code for easy mobile access.

---

## Features

- HTTP Basic Authentication with configurable username and password.
- Secure file upload and download.
- Directory browsing with file size display.
- Responsive dark theme UI.
- Logout functionality.
- Network and local URLs displayed with terminal QR code.
- Compatible with desktop browsers and mobile devices.

---

## Installation & Usage Instructions

Follow the instructions below based on your operating system.

---

### Prerequisites

- Python 3.6 or later installed.
- (Optional) Install the `qrcode` package for QR code generation.

---

## Windows

### 1. Install Python

- Download and install Python from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/).
- During installation, **check the box "Add Python to PATH"**.
- Verify installation:
  
  Open Command Prompt and run:

   
  python --version
    

### 2. Install Required Python Package (Optional)

Open Command Prompt and run:

pip install qrcode[pil]
  

This enables displaying a QR code in the terminal for easy mobile access.

### 3. Prepare Project Files

- Download or clone the repository containing `secure_server.py`.
- Ensure the following files are present in the project folder:
  - `secure_server.py`
  - `README.md`
  - `.gitignore`
  - `LICENSE`
  - `requirements.txt` (optional)

### 4. Run the Server

In Command Prompt, navigate to your project folder:

cd path\to\your\project
  

Run the server:

python secure_server.py
  

Follow prompts to:

- Set username
- Set password (input hidden)
- Set port number (default 8000 if left blank)

### 5. Access Server

- Open the URLs shown (local and network) in your browser.
- Or scan the QR code displayed in the terminal on your mobile device.
- Use the web UI to upload, download, or browse files.
- Click **Logout** button in the top-right to sign out.

---

## Linux (Ubuntu/Debian)

### 1. Install Python 3

Open Terminal and run:


sudo apt update
sudo apt install python3 python3-pip -y
  

Verify installation:


python3 --version
pip3 --version
  

> Use `python3` and `pip3` commands for Python 3.

### 2. Install Required Package (Optional)


pip3 install qrcode[pil]
  

### 3. Prepare Project Files

- Download or clone your project.
- Navigate to the project directory:

cd /path/to/your/project
  

### 4. Run the Server

python3 secure_server.py
  

Set username, password, and port when prompted.

### 5. Access Server

Open the displayed URLs in a browser or scan QR code.

---

## Termux (Android)

### 1. Install Termux

- Download Termux app from F-Droid (recommended) [https://f-droid.org/en/packages/com.termux/].

### 2. Update and Install Python

Open Termux and run:

pkg update && pkg upgrade
pkg install python
  

### 3. Install Required Package (Optional)

pip install qrcode[pil]
  

### 4. Prepare Project Files

- You can clone the repo using Git:

pkg install git
git clone https://github.com/<username>/<repo-name>.git
cd <repo-name>
  

- Or transfer `secure_server.py` from PC to Termux storage and navigate to the folder.

### 5. Run the Server

python secure_server.py
  

Provide username, password, and port as prompted.

### 6. Access Server

- From your Android browser via `localhost:port` or from network URL on other devices.
- Terminal shows a QR code to scan for quick access.

---

## Additional Notes

- **Firewall:** If accessing from other devices, ensure your firewall allows traffic on the selected port.
- **Security:** This server uses basic authentication and is intended for trusted local networks only.
- **Stopping Server:** Press `Ctrl + C` in terminal to stop.
- **Uploading Files:** Use the upload form at the bottom of directory listings. You must select files first; "Browse" button is visible to open file picker.

---

## Troubleshooting

- **Git Not Found:** On Windows, install Git and add it to PATH if you need version control.
- **QR Code Not Displaying:** Make sure the `qrcode` package is installed (`pip install qrcode[pil]`).
- **Port Conflicts:** If port 8000 is in use, choose a different port when prompted.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

Feel free to contribute or open issues on GitHub!

---

If you need any further assistance, don’t hesitate to ask.