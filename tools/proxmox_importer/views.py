import os
import time
import re
from flask import Blueprint, request, render_template, Response, jsonify, url_for, session
from threading import Thread
import subprocess
import shutil
import socket
import queue
import paramiko

from tools.utils.shared_utils import (
    get_cached_proxmox_api_and_ssh_data,
    execute_ssh_command_streamed,
    log_progress,
    progress_queues,
    get_ssh_client
)
from proxmoxer import ProxmoxAPI, core
from config_manager import load_config

SESSION_QCOW_FILES_KEY = 'uploaded_qcow_files'
SESSION_LOCAL_ZIP_PATH_KEY = 'local_zip_file_path'

proxmox_vm_importer_bp = Blueprint(
    'proxmox_vm_importer',
    __name__,
    template_folder='templates'
)

# CHANGE: The redundant '/' route has been removed here.

@proxmox_vm_importer_bp.route('/tool/proxmox-importer')
def proxmox_importer_tool():
    """Renders the HTML partial for the Proxmox Importer tool."""
    # Check if we have a valid configuration first
    try:
        from config_manager import load_config
        config = load_config()
        
        # Check if required Proxmox settings are present
        required_settings = ['PROXMOX_HOST', 'PROXMOX_USER', 'PROXMOX_TOKEN_NAME', 'PROXMOX_TOKEN_VALUE']
        missing_settings = [setting for setting in required_settings if not config.get(setting)]
        
        if missing_settings:
            return render_template(
                'proxmox_importer.html',
                nodes=[],
                used_vm_ids=[],
                storage_locations=[],
                connection_error=f"Proxmox configuration incomplete. Missing: {', '.join(missing_settings)}. Please configure these settings in the Configuration tool."
            )
        
        # Try to get connection data
        proxmox_api, _, _, is_error, error_message = get_cached_proxmox_api_and_ssh_data()
        if is_error or not proxmox_api:
            return render_template(
                'proxmox_importer.html',
                nodes=[],
                used_vm_ids=[],
                storage_locations=[],
                connection_error=error_message or "Proxmox connection failed. Please check your configuration."
            )
        
        # If we get here, connection is working - get the data
        nodes_data = []
        used_vm_ids = []
        storage_locations_names = []
        
        try:
            nodes_list = proxmox_api.nodes.get()
            vms = proxmox_api.cluster.resources.get(type='vm')
            used_vm_ids = sorted([vm['vmid'] for vm in vms])
            temp_storage_locations = []
            for node in nodes_list:
                node_name = node['node']
                try:
                    node_storages = proxmox_api.nodes(node_name).storage.get()
                    for s in node_storages:
                        if 'content' in s and ('images' in s['content'].split(',') or 'rootdir' in s['content'].split(',')):
                            if s['storage'] not in [item['storage'] for item in temp_storage_locations]:
                                temp_storage_locations.append({'storage': s['storage'], 'type': s['type']})
                except Exception as e:
                    print(f"[{__name__}] Warning: Could not retrieve storage locations from node '{node_name}': {e}")
            storage_locations_names = sorted([s['storage'] for s in temp_storage_locations])
            nodes_data = [node['node'] for node in nodes_list]
        except Exception as e:
            print(f"[{__name__}] ERROR retrieving Proxmox data: {e}")
            return render_template(
                'proxmox_importer.html',
                nodes=[],
                used_vm_ids=[],
                storage_locations=[],
                connection_error=f"Failed to retrieve Proxmox data: {str(e)}"
            )

        return render_template(
            'proxmox_importer.html',
            nodes=nodes_data,
            used_vm_ids=used_vm_ids,
            storage_locations=storage_locations_names
        )
        
    except Exception as e:
        return render_template(
            'proxmox_importer.html',
            nodes=[],
            used_vm_ids=[],
            storage_locations=[],
            connection_error=f"Configuration error: {str(e)}"
        )

@proxmox_vm_importer_bp.route('/upload-and-extract-zip', methods=['POST'])
def upload_and_extract_zip():
    session_id = int(time.time())
    file_storage_obj = request.files.get('zipfile')
    if not file_storage_obj:
        return jsonify({"success": False, "error": "No ZIP file uploaded."})

    local_zip_file_path = None
    unzip_dir = None
    try:
        UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..', 'temp_uploads')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        local_zip_file_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{file_storage_obj.filename}")
        file_storage_obj.save(local_zip_file_path)

        unzip_executable = shutil.which('unzip')
        if not unzip_executable:
            raise RuntimeError("The 'unzip' command was not found on the local server.")

        unzip_dir = os.path.join(UPLOAD_FOLDER, f"_tmp_proxmox_importer_{session_id}")
        os.makedirs(unzip_dir, exist_ok=True)
        unzip_command_local = [
            unzip_executable, "-o", "-qq", local_zip_file_path, "-d", unzip_dir
        ]
        subprocess.run(unzip_command_local, check=True, capture_output=True, text=True)

        qcow_files_local = sorted([f for f in os.listdir(unzip_dir) if f.lower().endswith(('.qcow2', '.qcow'))])
        if not qcow_files_local:
            raise ValueError("No .qcow2 or .qcow files found in the ZIP archive.")

        session[SESSION_QCOW_FILES_KEY] = qcow_files_local
        session[SESSION_LOCAL_ZIP_PATH_KEY] = local_zip_file_path

        return jsonify({
            "success": True, 
            "qcow_files": qcow_files_local, 
            "session_id": session_id,
            "message": "ZIP successfully uploaded and extracted."
        })
    except Exception as e:
        if local_zip_file_path and os.path.exists(local_zip_file_path): os.remove(local_zip_file_path)
        if unzip_dir and os.path.exists(unzip_dir): shutil.rmtree(unzip_dir)
        return jsonify({"success": False, "error": str(e)})

@proxmox_vm_importer_bp.route('/get-network-bridges/<node_name>')
def get_network_bridges(node_name):
    proxmox_api, _, _, is_error, _ = get_cached_proxmox_api_and_ssh_data()
    if is_error or not proxmox_api:
        return jsonify([]), 500
    try:
        node_networks = proxmox_api.nodes(node_name).network.get(type='bridge')
        network_bridges = sorted([net['iface'] for net in node_networks if net.get('active', 0) == 1])
        return jsonify(network_bridges)
    except Exception as e:
        print(f"Error retrieving bridges for node '{node_name}': {e}")
        return jsonify([]), 500

@proxmox_vm_importer_bp.route('/finalize-vm-import', methods=['POST'])
def finalize_vm_import():
    vm_data_json = request.json
    session_id = vm_data_json.get('session_id')
    if not session_id:
        return jsonify({"success": False, "error": "Session ID is missing."})

    progress_queues[session_id] = queue.Queue()
    log_progress(session_id, "--- Starting VM import finalization ---")
    
    local_zip_file_path = session.get(SESSION_LOCAL_ZIP_PATH_KEY)
    if not local_zip_file_path:
        log_progress(session_id, "❌ ERROR: Session has expired or the ZIP path could not be found. Please start over.")
        return jsonify({"success": False, "error": "Session expired"})

    thread = Thread(target=_perform_full_vm_import_task, args=(session_id, vm_data_json, local_zip_file_path))
    thread.start()

    return jsonify({"success": True, "message": "VM import process started. Follow the progress."})

@proxmox_vm_importer_bp.route('/progress/<int:session_id>')
def progress(session_id):
    def generate():
        q = progress_queues.get(session_id)
        if not q: return
        while True:
            try:
                message = q.get(timeout=60)
                yield f"data: {message}\n\n"
                if "✅ Import completed successfully!" in message or "❌" in message:
                    break
            except queue.Empty:
                break
    return Response(generate(), mimetype='text/event-stream')

def _perform_full_vm_import_task(session_id, vm_data, local_zip_file_path):
    """The full import task that runs in a separate thread."""
    
    vm_id = vm_data.get('vm_id')
    vm_name = vm_data.get('vm_name')
    proxmox_node = vm_data.get('proxmox_node')
    proxmox_storage_target = vm_data.get('proxmox_storage')
    cores = vm_data.get('cores')
    memory = vm_data.get('memory')
    ostype = vm_data.get('ostype')
    uploaded_disks = vm_data.get('uploaded_disks', [])
    additional_disks = vm_data.get('additional_disks', [])
    network_adapters = vm_data.get('network_adapters', [])
    
    PROXMOX_REMOTE_TEMP_DIR = f"/tmp/fortitoolbox_{session_id}"
    local_unzipped_qcow_dir = os.path.join(os.path.dirname(local_zip_file_path), f"_tmp_proxmox_importer_{session_id}")
    ssh_client = None

    try:
        log_progress(session_id, "Step A: Validation and preparation.")
        task_proxmox, _, unzip_available, is_error, err_msg = get_cached_proxmox_api_and_ssh_data()
        if is_error: raise RuntimeError(f"Environment checks failed: {err_msg}")
        if not unzip_available: raise RuntimeError("The 'unzip' command is not available on the Proxmox server.")
        
        log_progress(session_id, "Step B: Establishing SSH connection.")
        current_config = load_config()
        ssh_client = get_ssh_client(current_config)
        log_progress(session_id, "✅ SSH connection established successfully.")
        
        log_progress(session_id, "Step C: Creating VM.")
        vm_config = {
            'vmid': vm_id, 'name': vm_name, 'memory': memory, 'cores': cores,
            'ostype': ostype, 'scsihw': 'virtio-scsi-pci',
        }
        for net_adapter in network_adapters:
            net_id = net_adapter['interface_id']
            bridge = net_adapter['bridge']
            vlan_tag = net_adapter.get('vlan')
            if not bridge: continue
            net_config = f"virtio,bridge={bridge}"
            if vlan_tag:
                net_config += f",tag={vlan_tag}"
            vm_config[f'net{net_id}'] = net_config
        
        task_proxmox.nodes(proxmox_node).qemu.post(**vm_config)
        log_progress(session_id, f"✅ VM '{vm_name}' created successfully.")

        log_progress(session_id, "Step D: Importing and attaching uploaded disks.")
        boot_disk_scsi_id = None
        if uploaded_disks:
            log_progress(session_id, f"--- Copying uploaded files to Proxmox ---")
            
            # Helper for SFTP progress
            class ProgressTracker:
                def __init__(self, total_size, session_id, filename):
                    self.total_size = total_size
                    self.bytes_transferred = 0
                    self.session_id = session_id
                    self.filename = filename
                    self.last_reported_percent = -1

                def __call__(self, bytes_transferred, total_size):
                    self.bytes_transferred = bytes_transferred
                    percent = int((self.bytes_transferred / self.total_size) * 100)
                    if percent > self.last_reported_percent:
                        # Report in 5% increments to avoid flooding the log
                        if percent % 5 == 0 or percent == 100:
                            log_progress(self.session_id, f"    Uploading '{self.filename}': {percent}%")
                            self.last_reported_percent = percent

            with ssh_client.open_sftp() as sftp_client:
                sftp_client.mkdir(PROXMOX_REMOTE_TEMP_DIR)
                for disk in uploaded_disks:
                    filename = disk['filename']
                    local_path = os.path.join(local_unzipped_qcow_dir, filename)
                    remote_path = os.path.join(PROXMOX_REMOTE_TEMP_DIR, filename)
                    
                    file_size = os.path.getsize(local_path)
                    progress_callback = ProgressTracker(file_size, session_id, filename)
                    
                    sftp_client.put(local_path, remote_path, callback=progress_callback)
                    log_progress(session_id, f"✅ '{filename}' copied successfully.")
            
            for disk in uploaded_disks:
                filename = disk['filename']
                scsi_id = disk['scsi_id']
                remote_path = os.path.join(PROXMOX_REMOTE_TEMP_DIR, filename)
                log_progress(session_id, f"--- Importing: '{filename}' to '{proxmox_storage_target}' ---")
                import_cmd = f"qm importdisk {vm_id} {remote_path} {proxmox_storage_target}"
                import_output = execute_ssh_command_streamed(ssh_client, import_cmd, session_id, log_prefix=f"Import '{filename}'")

                vol_id_match = re.search(r"successfully imported disk '([^']+)'", import_output, re.IGNORECASE)
                if not vol_id_match: raise RuntimeError(f"Could not find Volume ID for '{filename}'. Output: {import_output}")
                volume_id = vol_id_match.group(1)
                log_progress(session_id, f"✅ Disk '{filename}' imported as '{volume_id}'.")

                log_progress(session_id, f"--- Attaching '{volume_id}' to {scsi_id} ---")
                attach_cmd = f"qm set {vm_id} --{scsi_id} {volume_id}"
                execute_ssh_command_streamed(ssh_client, attach_cmd, session_id, log_prefix=f"Attach '{filename}'")
                log_progress(session_id, f"✅ Disk successfully attached to {scsi_id}.")

                if disk.get('is_boot'):
                    boot_disk_scsi_id = disk['scsi_id']

        log_progress(session_id, "Step E: Creating and attaching additional disks.")
        for disk in additional_disks:
            scsi_id = disk['scsi_id']
            size_gb = disk['size']
            if not scsi_id or not size_gb: continue
            log_progress(session_id, f"--- Creating new disk on {scsi_id} ({size_gb}GB) ---")
            attach_cmd = f"qm set {vm_id} --{scsi_id} {proxmox_storage_target}:{size_gb}"
            execute_ssh_command_streamed(ssh_client, attach_cmd, session_id, log_prefix=f"Create Disk '{scsi_id}'")
            log_progress(session_id, f"✅ Additional disk on {scsi_id} created successfully.")
        
        log_progress(session_id, "Step F: Setting boot order.")
        if boot_disk_scsi_id:
            task_proxmox.nodes(proxmox_node).qemu(vm_id).config.put(boot=f'order={boot_disk_scsi_id}')
            log_progress(session_id, f"✅ Boot order set to {boot_disk_scsi_id}.")
        else:
            log_progress(session_id, "⚠️ No boot disk selected, boot order not set.")

        log_progress(session_id, "✅ Import completed successfully!")

    except (paramiko.SSHException, socket.timeout) as e:
        log_progress(session_id, f"❌ An SSH connection error occurred: {str(e)}")
    except core.ResourceException as e:
        log_progress(session_id, f"❌ A Proxmox API error occurred: {str(e)}")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        log_progress(session_id, f"❌ A configuration or file error occurred: {str(e)}")
    except Exception as e:
        log_progress(session_id, f"❌ A critical unexpected error occurred: {str(e)}")
        import traceback
        log_progress(session_id, f"--- Traceback ---\n{traceback.format_exc()}")
    finally:
        log_progress(session_id, "--- Cleaning up temporary files ---")
        if ssh_client and ssh_client.get_transport() and ssh_client.get_transport().is_active():
            try:
                cleanup_cmd = f"rm -rf {PROXMOX_REMOTE_TEMP_DIR}"
                execute_ssh_command_streamed(ssh_client, cleanup_cmd, session_id, log_prefix="Remote Cleanup", allow_failure=True)
                log_progress(session_id, "✅ Remote cleanup completed.")
            except Exception as e:
                log_progress(session_id, f"⚠️ Error during remote cleanup: {e}.")
            finally:
                ssh_client.close()
        
        if local_zip_file_path and os.path.exists(local_zip_file_path):
            os.remove(local_zip_file_path)
        if os.path.exists(local_unzipped_qcow_dir):
            shutil.rmtree(local_unzipped_qcow_dir)
        log_progress(session_id, "✅ Local cleanup completed.")

        if session_id in progress_queues:
            del progress_queues[session_id]