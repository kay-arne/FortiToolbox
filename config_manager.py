import configparser
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.ini')

# Define which keys are considered sensitive and should be prioritized from environment variables.
SENSITIVE_KEYS = [
    "PROXMOX_HOST", "PROXMOX_USER", "PROXMOX_PASSWORD", "PROXMOX_TOKEN_ID", "PROXMOX_TOKEN_SECRET",
    "SSH_HOST", "SSH_PORT", "SSH_USERNAME", "SSH_PASSWORD", 
    "SSH_PRIVATE_KEY_PATH", "SSH_PRIVATE_KEY_PASSWORD"
]

def load_config():
    """
    Loads the configuration. Prioritizes environment variables for sensitive data,
    otherwise uses the values from config.ini.
    """
    config = configparser.ConfigParser(interpolation=None)
    settings = {}

    # 1. Read the config.ini file (as a fallback)
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
        if 'PROXMOX' in config:
            for key in config['PROXMOX']:
                settings[f"PROXMOX_{key.upper()}"] = config.get('PROXMOX', key)
        if 'SSH' in config:
            for key in config['SSH']:
                settings[f"SSH_{key.upper()}"] = config.get('SSH', key)
        if 'SCRAPER' in config:
            for key in config['SCRAPER']:
                settings[f"SCRAPER_{key.upper()}"] = config.get('SCRAPER', key)

    # 2. Override with environment variables if present
    for key in SENSITIVE_KEYS:
        env_value = os.environ.get(key)
        if env_value:
            settings[key] = env_value
            
    return settings

def save_config(data):
    """
    Saves only non-sensitive data to config.ini.
    Sensitive data should be managed as environment variables.
    """
    config = configparser.ConfigParser(interpolation=None)
    
    # Initialize sections
    if os.path.exists(CONFIG_PATH):
        config.read(CONFIG_PATH)
    if 'PROXMOX' not in config:
        config['PROXMOX'] = {}
    if 'SSH' not in config:
        config['SSH'] = {}
    if 'SCRAPER' not in config:
        config['SCRAPER'] = {}

    for key, value in data.items():
        # Only save values that are NOT sensitive.
        if key.upper() not in SENSITIVE_KEYS:
            if key.startswith('PROXMOX_'):
                config['PROXMOX'][key.replace('PROXMOX_', '').lower()] = value or ''
            elif key.startswith('SSH_'):
                config['SSH'][key.replace('SSH_', '').lower()] = value or ''
            elif key.startswith('SCRAPER_'):
                config['SCRAPER'][key.replace('SCRAPER_', '').lower()] = value or ''

    with open(CONFIG_PATH, 'w') as configfile:
        config.write(configfile)