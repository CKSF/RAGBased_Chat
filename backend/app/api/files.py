from flask import Blueprint, send_from_directory, current_app
import os

files_bp = Blueprint('files', __name__)

@files_bp.route('/source/<path:filename>', methods=['GET'])
def get_source_file(filename):
    """
    Serve the source file.
    Currently returns a static placeholder for confidentiality.
    """
    # In a real scenario, you would serve the actual file:
    # return send_from_directory(Config.DOC_STORE_DIR, filename)
    
    # For now, serve the confidential placeholder
    static_folder = os.path.join(current_app.root_path, 'static')
    return send_from_directory(static_folder, 'placeholder.html')
