# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2025-09-18

### Removed
- **CLI Finder Tool**: Completely removed the CLI command finder functionality
- **CLI Scraper Tool**: Completely removed the web scraper functionality
- **Scraper Dependencies**: Removed `beautifulsoup4`, `requests`, and `soupsieve` from requirements.txt
- **Scraper Configuration**: Removed all scraper-related configuration options from config.ini and config manager

### Changed
- **Simplified Navigation**: Updated sidebar navigation to only show available tools
- **Updated Dashboard**: Removed CLI Finder and CLI Scraper widgets from the main dashboard
- **Streamlined Configuration**: Configuration page now only contains Proxmox and SSH settings
- **Updated Documentation**: README.md updated to reflect the simplified feature set

### Technical Changes
- **App Structure**: Removed scraper and cli_finder blueprints from app.py
- **Template Updates**: Cleaned up dashboard.html template to remove references to deleted tools
- **Docker Configuration**: Updated docker-compose.yml to remove cli_finder volume mount
- **Project Structure**: Removed tools/scraper/ and tools/cli_finder/ directories

### Files Removed
- `tools/scraper/` (entire directory)
- `tools/cli_finder/` (entire directory)
- All scraper-related configuration sections

### Files Modified
- `app.py` - Removed scraper and cli_finder blueprint imports and registrations
- `tools/dashboard/templates/layout.html` - Removed navigation links
- `tools/dashboard/templates/dashboard.html` - Removed tool widgets
- `tools/config_tool/templates/config.html` - Removed scraper settings section
- `config_manager.py` - Removed scraper configuration handling
- `config.ini` - Removed scraper section
- `requirements.txt` - Removed scraper dependencies
- `README.md` - Updated feature list and installation instructions
- `docker-compose.yml` - Removed cli_finder volume mount

## [2.0.0] - Previous Release

### Features
- Proxmox FortiGate VM Importer
- CLI Command Finder
- CLI Command Scraper
- Configuration Manager
- Docker support
- Web-based interface
