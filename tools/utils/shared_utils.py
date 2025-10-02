

import time
from proxmoxer import ProxmoxAPI
import paramiko
import socket
import queue
import urllib3
import os

from config_manager import load_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

progress_queues = {}
def log_progress(session_id, message):
    """Logs a message to the correct session's progress queue."""
    # Ensure queue exists for this session
    if session_id not in progress_queues:
        progress_queues[session_id] = queue.Queue()
    
    # Add message to queue
    progress_queues[session_id].put(message)
    print(f"[{session_id}] {message}")


_cache = {}
_CACHE_EXPIRATION_SECONDS = 300
def clear_cache():
    """Clears the connection cache."""
    global _cache
    _cache = {}
    print("--- Cache has been cleared ---")

# --- CHANGE: Split into two functions ---
def test_api_connection(config):
    """Tests only the Proxmox API connection."""
    print("\n--- Performing live API connection test ---")
    try:
        print(f"API Test: Connecting to {config.get('PROXMOX_HOST')}...")
        proxmox_api = ProxmoxAPI(
            config.get('PROXMOX_HOST'),
            user=config.get('PROXMOX_USER'),
            token_name=config.get('PROXMOX_TOKEN_NAME'),
            token_value=config.get('PROXMOX_TOKEN_VALUE'),
            verify_ssl=config.get('PROXMOX_VERIFY_SSL', 'true').lower() == 'true'
        )
        proxmox_api.version.get()
        print("✅ API Test: Connection successful.")
        return (True, "Connection to the Proxmox API was successful!")
    except Exception as e:
        error_message = f"API Test failed: {e}"
        print(f"❌ {error_message}")
        return (False, error_message)

def get_ssh_client(config):
    """
    Creates and configures a Paramiko SSH client based on the given configuration.
    Returns a connected client object.
    """
    ssh_host = config.get('PROXMOX_HOST')
    ssh_port = int(config.get('SSH_PORT', 22))
    auth_method = config.get('SSH_AUTH_METHOD')
    ssh_username = config.get('SSH_USERNAME')

    if not all([ssh_host, ssh_username, auth_method]):
        raise ValueError("SSH host, username, and auth_method must be provided in the config.")

    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    # Use AutoAddPolicy for Docker compatibility - automatically accept unknown host keys
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if auth_method == 'password':
        ssh_password = config.get('SSH_PASSWORD')
        if not ssh_password:
            raise ValueError("SSH password is required for password authentication.")
        ssh_client.connect(
            hostname=ssh_host, port=ssh_port,
            username=ssh_username, password=ssh_password, timeout=10
        )
    elif auth_method == 'key':
        key_path = config.get('SSH_PRIVATE_KEY_PATH')
        if not key_path or not os.path.exists(key_path):
            raise ValueError(f"SSH private key file not found: {key_path}")
        key_pass = config.get('SSH_PRIVATE_KEY_PASSWORD') or None
        
        # Try to load different key types
        key = None
        key_error = None
        for key_class in [paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey]:
            try:
                key = key_class.from_private_key_file(key_path, password=key_pass)
                break
            except paramiko.SSHException as e:
                key_error = e
        
        if not key:
            raise ValueError(f"Could not load any supported private key (RSA, Ed25519, ECDSA). Error: {key_error}")

        ssh_client.connect(
            hostname=ssh_host, port=ssh_port,
            username=ssh_username, pkey=key, timeout=10
        )
    else:
        raise ValueError(f"Invalid SSH auth_method: {auth_method}")
        
    return ssh_client

def test_ssh_connection(config):
    """Tests only the SSH connection."""
    print("\n--- Performing live SSH connection test ---")
    ssh_client = None
    try:
        print(f"SSH Test: Connecting to {config.get('PROXMOX_HOST')}...")
        ssh_client = get_ssh_client(config)
        print("✅ SSH Test: Connection successful.")
        return (True, "Connection with SSH was successful!")
    except Exception as e:
        error_message = f"SSH Test failed: {e}"
        print(f"❌ {error_message}")
        return (False, error_message)
    finally:
        if ssh_client:
            ssh_client.close()

def get_cached_proxmox_api_and_ssh_data():
    """Retrieves Proxmox API (with token) and SSH data."""
    current_time = time.time()
    if 'proxmox_data' in _cache and (current_time - _cache['proxmox_data']['timestamp']) < _CACHE_EXPIRATION_SECONDS:
        return _cache['proxmox_data']['data']

    print("\n--- Performing new connection test with Proxmox (for cache) ---")
    
    try:
        config = load_config()
        is_success, message = test_api_connection(config)
        if not is_success:
            raise ConnectionError(message)

        # Recreate the API instance for the cache
        proxmox_api = ProxmoxAPI(
            config.get('PROXMOX_HOST'),
            user=config.get('PROXMOX_USER'),
            token_name=config.get('PROXMOX_TOKEN_NAME'),
            token_value=config.get('PROXMOX_TOKEN_VALUE'),
            verify_ssl=config.get('PROXMOX_VERIFY_SSL', 'true').lower() == 'true'
        )

        unzip_available = True # Assumption, can be expanded if necessary

        result = (proxmox_api, None, unzip_available, False, "")
        _cache['proxmox_data'] = {'timestamp': current_time, 'data': result}
        print("--- Connection test completed successfully. Result is cached. ---\n")
        return result

    except Exception as e:
        error_message = f"Connection check failed. Error: {e}"
        result = (None, None, False, True, error_message)
        _cache['proxmox_data'] = {'timestamp': current_time, 'data': result}
        print(f"--- Connection test FAILED. Error is cached. Details: {error_message} ---\n")
        return result

def execute_ssh_command_streamed(ssh_client, command, session_id, log_prefix="", allow_failure=False):
    """
    Executes an SSH command and streams the output to the progress queue.
    Returns the full output as a string.
    """
    log_progress(session_id, f"{log_prefix} Executing command: {command}")
    
    channel = ssh_client.get_transport().open_session()
    channel.exec_command(command)
    
    full_output = []

    stdout = channel.makefile('r', -1)
    stderr = channel.makefile_stderr('r', -1)

    # Continuously read from stdout and stderr
    while not channel.exit_status_ready():
        for line in stdout:
            clean_line = line.strip()
            if clean_line:
                log_progress(session_id, f"{log_prefix} > {clean_line}")
                full_output.append(clean_line)
        for line in stderr:
            clean_line = line.strip()
            if clean_line:
                log_progress(session_id, f"{log_prefix} [STDERR] > {clean_line}")
                full_output.append(clean_line)

    exit_status = channel.recv_exit_status()
    
    # Read any remaining output after the command finishes
    for line in stdout:
        clean_line = line.strip()
        if clean_line:
            log_progress(session_id, f"{log_prefix} > {clean_line}")
            full_output.append(clean_line)
    for line in stderr:
        clean_line = line.strip()
        if clean_line:
            log_progress(session_id, f"{log_prefix} [STDERR] > {clean_line}")
            full_output.append(clean_line)

    stdout.close()
    stderr.close()
    channel.close()

    output_str = "\n".join(full_output)
    
    if exit_status != 0 and not allow_failure:
        raise RuntimeError(f"Command '{command}' failed with exit code {exit_status}. Full output:\n{output_str}")
        
    return output_str