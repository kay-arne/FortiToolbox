# FortiToolbox App v2.0.0 - Production Release

FortiToolbox is a production-ready, Docker-based web application for network engineers working with Fortinet and Proxmox environments. It provides a streamlined interface for importing FortiGate virtual machines into Proxmox VE environments.

## ✨ Features

-   **🐳 Docker-First Deployment**: Complete containerization with production-ready configuration
-   **📦 Proxmox FortiGate VM Importer**: Web interface to upload and import FortiGate VM images into Proxmox VE
-   **⚙️ Configuration Manager**: Secure settings management with environment variable support
-   **📊 Real-time Progress Tracking**: Live updates during import operations with Server-Sent Events
-   **🔒 Production Security**: Environment variable support for sensitive credentials
-   **🔄 Persistent Configuration**: Settings survive container restarts

## 🚀 Quick Start (Production Ready)

### Prerequisites

- **Docker Engine**: 20.10+ 
- **Docker Compose**: 2.0+
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 10GB free space
- **Network**: Access to Proxmox server

### 🐳 Docker Deployment (Recommended)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/kay-arne/FortiToolbox.git
    cd FortiToolbox
    ```

2.  **Create Environment File:**
    Create a `.env` file in the project root:
    ```bash
    # Required for session security
    FLASK_SECRET_KEY='your-very-long-and-random-secret-key-here'

    # Optional: Pre-configure Proxmox settings
    PROXMOX_HOST=your_proxmox_ip
    PROXMOX_USER=root@pam
    PROXMOX_TOKEN_NAME=your_api_token_name
    PROXMOX_TOKEN_VALUE=your_api_token_secret

    # Optional: Pre-configure SSH settings
    SSH_USERNAME=your_ssh_username
    SSH_AUTH_METHOD=password
    SSH_PASSWORD=your_ssh_password
    ```

3.  **Deploy with Docker Compose:**
    ```bash
    # Start the application
    docker compose up -d

    # View logs
    docker compose logs -f

    # Stop the application
    docker compose down
    ```

4.  **Access the Application:**
    Open your browser and navigate to `http://localhost:5001`

### 🔧 Production Configuration

For production deployments, consider these additional settings:

```bash
# Production environment variables
FLASK_SECRET_KEY='your-production-secret-key'
PROXMOX_VERIFY_SSL=true
SSH_PORT=22
```

### 📊 Monitoring

```bash
# Check container status
docker compose ps

# View real-time logs
docker compose logs -f fortitoolbox

# Check resource usage
docker stats fortitoolbox
```

## 🔧 Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `FLASK_SECRET_KEY` | ✅ | Secret key for session security | - |
| `PROXMOX_HOST` | ❌ | Proxmox server IP/hostname | - |
| `PROXMOX_USER` | ❌ | Proxmox API user | - |
| `PROXMOX_TOKEN_NAME` | ❌ | API token name | - |
| `PROXMOX_TOKEN_VALUE` | ❌ | API token secret | - |
| `SSH_USERNAME` | ❌ | SSH username | - |
| `SSH_PASSWORD` | ❌ | SSH password (if using password auth) | - |
| `SSH_PRIVATE_KEY_PATH` | ❌ | Path to SSH private key (if using key auth) | - |

### Docker Compose Configuration

The `docker-compose.yml` file includes:

- **Build Configuration**: Uses local Dockerfile for custom image
- **Port Mapping**: Maps host port 5001 to container port 5001
- **Volume Mapping**: Persistent configuration storage in `./config/`
- **Environment Loading**: Loads variables from `.env` file
- **Restart Policy**: `unless-stopped` for automatic recovery

## 🛠️ Troubleshooting

### Common Issues

#### 1. Container Won't Start
```bash
# Check container logs
docker compose logs fortitoolbox

# Check if port is already in use
netstat -tulpn | grep 5001
```

#### 2. Progress Updates Not Showing
```bash
# Check if progress files are being created
docker compose exec fortitoolbox ls -la /tmp/progress_*

# Restart the container
docker compose restart fortitoolbox
```

#### 3. SSH Connection Issues
- Ensure SSH credentials are correct in Configuration page
- Check if Proxmox server allows SSH connections
- Verify firewall settings allow SSH traffic

#### 4. Import Fails
```bash
# Check detailed logs
docker compose logs -f fortitoolbox

# Verify Proxmox API credentials
# Test SSH connection manually
```

### Performance Optimization

#### For Large Files (>10GB)
```bash
# Increase Docker memory limit
docker compose up -d --memory=4g

# Monitor resource usage
docker stats fortitoolbox
```

#### For High Availability
```bash
# Use external database (future feature)
# Implement load balancing (future feature)
# Set up monitoring (future feature)
```

## 📚 Advanced Usage

### Manual Installation (Development)

For development or if Docker is not available:

1. **Clone and setup:**
   ```bash
   git clone https://github.com/kay-arne/FortiToolbox.git
   cd FortiToolbox
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```bash
   python app.py
   ```

3. **Access at:** `http://localhost:5001`

### Custom Configuration

Create a custom `docker-compose.override.yml`:

```yaml
version: '3.8'
services:
  fortitoolbox:
    environment:
      - FLASK_ENV=production
    volumes:
      - ./custom-config:/app/config
    ports:
      - "8080:5001"  # Custom port
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **GitHub Issues**: [Report bugs or request features](https://github.com/kay-arne/FortiToolbox/issues)
- **Documentation**: [Complete setup guide](https://github.com/kay-arne/FortiToolbox#readme)
- **Release Notes**: [View latest changes](https://github.com/kay-arne/FortiToolbox/blob/main/RELEASE_NOTES.md)
