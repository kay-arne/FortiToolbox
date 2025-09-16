# FortiToolbox App v2

FortiToolbox is a web-based toolbox for network engineers working with Fortinet and Proxmox environments. It's built using the Flask web framework in Python.

## Features

-   **Proxmox FortiGate VM Importer**: Provides a web interface to upload a FortiGate virtual machine image and automatically create a new virtual machine in a Proxmox VE environment.
-   **FortiOS CLI Finder**: A handy tool that displays a searchable list of FortiOS CLI commands and their descriptions.
-   **Web Scraper**: This tool automatically builds the command list for the CLI Finder by scraping the official Fortinet CLI reference documentation.
-   **Configuration Manager**: A settings page where you can configure the connection details for your Proxmox server.

## Installation and Setup

### Method 1: Using Docker (Recommended)

This is the easiest way to get the application running.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/kay-arne/FortiToolbox.git
    cd FortiToolbox
    ```

2.  **Create `.env` File:**
    You **must** create a file named `.env` in the project root to set the application's secret key. You can also add your Proxmox and SSH credentials here for convenience, but they can also be added later through the web interface.

    Create the `.env` file with the following content:
    ```env
    # This is REQUIRED for session security
    FLASK_SECRET_KEY='a_very_long_and_random_secret_string_please_change_me'

    # --- Optional Convenience Variables ---
    # If you do not set these, you can configure them on the app's Configuration page.
    
    # Proxmox API Configuration
    PROXMOX_HOST=your_proxmox_ip
    PROXMOX_USER=root@pam
    PROXMOX_TOKEN_NAME=your_api_token_name
    PROXMOX_TOKEN_VALUE=your_api_token_secret

    # SSH Configuration
    SSH_USERNAME=your_ssh_username
    SSH_AUTH_METHOD=password  # or 'key'
    SSH_PASSWORD=your_ssh_password # if using password auth
    SSH_PRIVATE_KEY_PATH=/path/to/your/private/key # if using key auth
    ```

3.  **Build and Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```
    The application will be available at `http://127.0.0.1:5001`.

### Method 2: Manual Installation

1.  **Clone the repository and navigate into the directory.**

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    
4.  **Run the Application:**
    ```bash
    python app.py
    ```
    The application will be available at `http://127.0.0.1:5001`.

5.  **Configure the Application:**
    Navigate to the `Configuration` page in the web interface to enter your Proxmox and SSH credentials. These will be saved in the `config.ini` file.
