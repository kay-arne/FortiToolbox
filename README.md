# FortiToolbox App v2

FortiToolbox is a web-based toolbox for network engineers working with Fortinet and Proxmox environments. It's built using the Flask web framework in Python.

## Features

-   **Proxmox FortiGate VM Importer**: Provides a web interface to upload a FortiGate virtual machine image and automatically create a new virtual machine in a Proxmox VE environment.
-   **FortiOS CLI Finder**: A handy tool that displays a searchable list of FortiOS CLI commands and their descriptions.
-   **Web Scraper**: This tool automatically builds the command list for the CLI Finder by scraping the official Fortinet CLI reference documentation.
-   **Configuration Manager**: A settings page where you can configure the connection details for your Proxmox server.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd FortiToolbox_App_v2
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **Set Environment Variables:**
    This application uses environment variables to manage sensitive configuration data. Create a `.env` file in the project root and add the following variables:

    ```env
    FLASK_SECRET_KEY='a_very_long_and_random_secret_string'
    
    # Proxmox API Configuration
    PROXMOX_HOST='your_proxmox_ip'
    PROXMOX_USER='root@pam'
    PROXMOX_TOKEN_NAME='your_api_token_name'
    PROXMOX_TOKEN_VALUE='your_api_token_secret'

    # SSH Configuration
    SSH_USERNAME='your_ssh_username'
    SSH_AUTH_METHOD='password'  # or 'key'
    SSH_PASSWORD='your_ssh_password' # if using password auth
    SSH_PRIVATE_KEY_PATH='/path/to/your/private/key' # if using key auth
    ```
    
    *Note: A `config.ini` file is present for non-sensitive settings, such as the scraper URLs, but all secrets **must** be set as environment variables.*

2. **Add SSH Host Key:**
   For security, the application requires the Proxmox server's SSH host key to be present in the `known_hosts` file of the user running the application. You can add it by running:
   ```bash
   ssh-keyscan -H your_proxmox_ip >> ~/.ssh/known_hosts
   ```

## Running the Application

### With Docker (Recommended)

1.  **Build and run the container using Docker Compose:**
    ```bash
    docker-compose up --build
    ```

    *This command will build the Docker image, start the container, and automatically use the variables from your `.env` file.*

### Manually

Once you have set the environment variables, you can start the application with the following command:

```