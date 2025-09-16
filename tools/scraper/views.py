from flask import Blueprint, render_template, jsonify, Response
from threading import Thread
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import queue
from urllib.parse import urljoin

from tools.utils.shared_utils import log_progress, progress_queues
from config_manager import load_config

scraper_bp = Blueprint(
    'scraper',
    __name__,
    template_folder='templates'
)

def _run_scraper_task(session_id):
    """The actual scraping task that runs in a separate thread."""
    
    config = load_config()
    base_url = config.get("SCRAPER_BASE_URL")
    toc_url = config.get("SCRAPER_TOC_URL")
    output_path = config.get("SCRAPER_OUTPUT_PATH")

    if not all([base_url, toc_url, output_path]):
        log_progress(session_id, "❌ ERROR: Scraper configuration (BASE_URL, TOC_URL, OUTPUT_PATH) is not fully set in config.ini.")
        return
        
    log_progress(session_id, f"Starting the scraper...")
    log_progress(session_id, f"1. Fetching table of contents from: {toc_url}")
    
    try:
        response = requests.get(toc_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        response.raise_for_status()
        log_progress(session_id, "✅ Table of contents fetched successfully.")
    except requests.exceptions.RequestException as e:
        log_progress(session_id, f"❌ ERROR fetching the table of contents: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find all links that point to a command reference page
    links = soup.select('a[href*="/cli-reference/"]')
    sub_pages = {
        urljoin(base_url, link['href']): link.get_text(strip=True)
        for link in links
        if link.get_text(strip=True).lower() in ['get', 'diagnose', 'execute', 'config', 'show']
    }

    if not sub_pages:
        log_progress(session_id, "❌ ERROR: Could not find any links to subpages. The website structure may have changed.")
        return

    log_progress(session_id, f"✅ {len(sub_pages)} command categories found. Starting processing...")
    all_commands = []
    
    for i, (page_url, page_name) in enumerate(sub_pages.items()):
        log_progress(session_id, f"\n[{i+1}/{len(sub_pages)}] Processing category: '{page_name}'...")
        log_progress(session_id, f" -> URL: {page_url}")
        
        try:
            page_response = requests.get(page_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
            page_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            log_progress(session_id, f"    -> ⚠️ Could not fetch this page: {e}")
            continue

        page_soup = BeautifulSoup(page_response.content, 'html.parser')
        command_table = page_soup.find('table')
        
        if not command_table:
            log_progress(session_id, "    -> ⚠️ No command table found on this page.")
            continue

        rows = command_table.find_all('tr')
        found_count = 0
        for row in rows[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                command_tag = cells[0].find('code')
                if command_tag:
                    command = command_tag.get_text(strip=True)
                    description = cells[1].get_text(strip=True)
                    if command and description:
                        all_commands.append({"command": command, "description": description})
                        found_count += 1
        
        log_progress(session_id, f"    -> ✅ {found_count} commands found in this category.")
        time.sleep(0.2) # Small delay to avoid overwhelming the server

    if not all_commands:
        log_progress(session_id, "❌ ERROR: Could not extract any commands. Check the HTML structure.")
        return

    log_progress(session_id, f"\n--- Total {len(all_commands)} commands found ---")
    log_progress(session_id, f"Writing to file: {output_path}")

    try:
        # Ensure the directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_commands, f, indent=4, ensure_ascii=False)
        log_progress(session_id, "✅ File saved successfully. The CLI Finder is now updated.")
        log_progress(session_id, "✅ Scraper completed successfully!")
    except IOError as e:
        log_progress(session_id, f"❌ ERROR writing the file: {e}")

@scraper_bp.route('/tool/scraper')
def scraper_tool():
    """Renders the HTML partial for the scraper tool."""
    return render_template('scraper.html')

@scraper_bp.route('/scraper/run', methods=['POST'])
def run_scraper():
    """Starts the scraping process in a background thread."""
    session_id = int(time.time())
    progress_queues[session_id] = queue.Queue()
    
    thread = Thread(target=_run_scraper_task, args=(session_id,))
    thread.start()
    
    return jsonify({"success": True, "session_id": session_id})

@scraper_bp.route('/scraper/progress/<int:session_id>')
def scraper_progress(session_id):
    """Streams the scraper's progress to the client."""
    def generate():
        q = progress_queues.get(session_id)
        if not q: return
        while True:
            try:
                message = q.get(timeout=60)
                yield f"data: {message}\n\n"
                if "✅ Scraper completed successfully!" in message or "❌" in message:
                    break
            except queue.Empty:
                break
    return Response(generate(), mimetype='text/event-stream')