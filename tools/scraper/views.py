from flask import Blueprint, render_template, jsonify, Response, request
from threading import Thread
import requests
from bs4 import BeautifulSoup
import json
import os
import time
import queue
from urllib.parse import urljoin, urlparse
import concurrent.futures
import threading

from tools.utils.shared_utils import progress_queues
from config_manager import load_config

# Dictionary to track running scraper tasks and their stop flags
scraper_tasks = {}

def log_progress(session_id, data):
    """Puts a JSON-serializable message into the queue for a session."""
    if session_id in progress_queues:
        progress_queues[session_id].put(json.dumps(data))

scraper_bp = Blueprint(
    'scraper',
    __name__,
    template_folder='templates'
)

def _get_fortinet_commands(base_url, category):
    """
    Fetches command list for a specific category from Fortinet docs.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return {"error": f"Could not fetch the documentation page: {e}"}

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Construct the search text to be more specific
    category_search_string = f"CLI {category} commands"
    
    category_link = soup.find('a', class_='toc', string=lambda t: t and category_search_string.lower() in t.lower())

    if not category_link:
        return {"error": f"Could not find the link for category '{category}'. The page structure might have changed."}

    # Find the parent list item, then the sibling unordered list
    category_li = category_link.find_parent('li')
    if not category_li:
        return {"error": "Could not find the parent list item for the category link."}
        
    command_list_ul = category_li.find_next_sibling('ul')
    if not command_list_ul:
        # It might be a child instead of a sibling in some cases.
        command_list_ul = category_li.find('ul')
        if not command_list_ul:
            return {"error": "Could not find the command list for the category."}

    commands = []
    # Find all leaf list items which represent actual commands
    command_links = command_list_ul.select('li.leaf a.toc')

    parsed_base_url = urlparse(base_url)
    scheme_netloc = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}"


    for link in command_links:
        command_name = link.get_text(strip=True)
        href = link.get('href')
        
        # Make sure the URL is absolute
        full_url = urljoin(scheme_netloc, href)
        
        if command_name and href:
            commands.append({
                "command": command_name,
                "url": full_url
            })
            
    return {"commands": commands}

def _run_scraper_task(session_id, commands_to_scrape):
    """
    Scrapes the selected command pages for details in parallel.
    """
    output_path = load_config().get("SCRAPER_OUTPUT_PATH")

    if not output_path:
        log_progress(session_id, {"status": "error", "message": "❌ ERROR: Scraper output path is not set in config.ini."})
        return
        
    log_progress(session_id, {"message": f"Starting parallel scraper for {len(commands_to_scrape)} commands..."})
    
    all_commands_details = []
    progress_lock = threading.Lock()
    progress_counter = 0
    total_commands = len(commands_to_scrape)

    def _scrape_single_command(command_info):
        nonlocal progress_counter
        
        # Check for stop signal before starting
        if scraper_tasks.get(session_id, {}).get('stop_flag'):
            return None

        command_name = command_info['command']
        command_url = command_info['url']
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        try:
            page_response = requests.get(command_url, headers=headers, timeout=30)
            page_response.raise_for_status()
            
            page_soup = BeautifulSoup(page_response.content, 'html.parser')
            summary_tag = page_soup.find('meta', attrs={'name': 'description'})
            summary = summary_tag['content'] if summary_tag else "No summary available."
            
            with progress_lock:
                progress_counter += 1
                log_progress(session_id, {
                    "progress": progress_counter,
                    "total": total_commands,
                    "message": f"({progress_counter}/{total_commands}) Scraped: '{command_name}'"
                })

            return {
                "command": command_name,
                "description": summary,
                "url": command_url
            }

        except requests.exceptions.RequestException as e:
            with progress_lock:
                progress_counter += 1
                log_progress(session_id, {
                    "progress": progress_counter,
                    "total": total_commands,
                    "message": f"    -> ⚠️ Could not fetch '{command_name}': {e}"
                })
            return None

    # Use a ThreadPoolExecutor to scrape in parallel
    # Limiting to 10 workers to avoid overwhelming the server
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit all scraping tasks
        future_to_command = {executor.submit(_scrape_single_command, cmd): cmd for cmd in commands_to_scrape}
        
        for future in concurrent.futures.as_completed(future_to_command):
            result = future.result()
            if result:
                all_commands_details.append(result)
            
            # Check for stop signal after each command finishes
            if scraper_tasks.get(session_id, {}).get('stop_flag'):
                # Cancel remaining futures
                for f in future_to_command:
                    f.cancel()
                log_progress(session_id, {"status": "cancelled", "message": "🛑 Scraper task cancelled by user."})
                # Ensure the executor is shut down cleanly on cancellation
                executor.shutdown(wait=False, cancel_futures=True)
                return

    # Final check for cancellation before writing file
    if scraper_tasks.get(session_id, {}).get('stop_flag'):
        return

    if not all_commands_details:
        log_progress(session_id, {"status": "error", "message": "❌ ERROR: Could not extract details for any of the selected commands."})
        return

    log_progress(session_id, {"message": f"\n--- Total {len(all_commands_details)} commands scraped ---"})
    log_progress(session_id, {"message": f"Writing to file: {output_path}"})

    try:
        # Ensure the directory exists
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_commands_details, f, indent=4, ensure_ascii=False)
        log_progress(session_id, {"message": "✅ File saved successfully. The CLI Finder is now updated."})
        log_progress(session_id, {"status": "finished", "message": "✅ Scraper completed successfully!"})
    except IOError as e:
        log_progress(session_id, {"status": "error", "message": f"❌ ERROR writing the file: {e}"})


@scraper_bp.route('/tool/scraper')
def scraper_tool():
    """Renders the HTML partial for the scraper tool."""
    return render_template('scraper.html')

@scraper_bp.route('/scraper/fetch-commands', methods=['POST'])
def fetch_commands():
    """Fetches the list of commands for a given category from the URL."""
    data = request.get_json()
    base_url = data.get('base_url')
    category = data.get('category')

    if not base_url or not category:
        return jsonify({"error": "Missing base_url or category"}), 400

    result = _get_fortinet_commands(base_url, category)
    return jsonify(result)

@scraper_bp.route('/scraper/run', methods=['POST'])
def run_scraper():
    """Starts the scraping process for selected command pages."""
    session_id = int(time.time())
    progress_queues[session_id] = queue.Queue()
    
    data = request.get_json()
    commands_to_scrape = data.get('commands')

    if not commands_to_scrape:
        return jsonify({"success": False, "error": "No commands selected for scraping."})

    scraper_tasks[session_id] = {'stop_flag': False}
    thread = Thread(target=_run_scraper_task, args=(session_id, commands_to_scrape))
    thread.start()
    
    return jsonify({"success": True, "session_id": session_id})

@scraper_bp.route('/scraper/stop', methods=['POST'])
def stop_scraper():
    """Stops a running scraper task."""
    data = request.get_json()
    session_id = data.get('session_id')
    if session_id in scraper_tasks:
        scraper_tasks[session_id]['stop_flag'] = True
        return jsonify({"success": True, "message": "Stop signal sent."})
    return jsonify({"success": False, "error": "Session not found or already stopped."}), 404

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
                # The frontend will handle the loop break based on message status
            except queue.Empty:
                # This timeout allows the request to terminate if no new messages are sent
                break
        
        # Clean up the task entry when the streaming is done
        if session_id in scraper_tasks:
            del scraper_tasks[session_id]
        if session_id in progress_queues:
            del progress_queues[session_id]

    return Response(generate(), mimetype='text/event-stream')