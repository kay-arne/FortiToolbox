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

2.  **Configure Environment (Optional but Recommended):**
    You can pre-configure the application by creating a `.env` file. This is useful so you don't have to enter credentials in the UI every time you restart the container. Create a file named `.env` in the project root:
    ```env
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
    *If you do not create a `.env` file, you will need to enter your credentials on the application's `Configuration` page after starting it.*

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
