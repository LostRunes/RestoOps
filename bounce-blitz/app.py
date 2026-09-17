# app.py - Bounce Blitz Application & Desktop Runner with File Downloads & Exports

import os
import sys
import uuid
import socket
import csv
import io
import json
import threading
from flask import Flask, request, jsonify, send_file, Response, render_template
from flask_cors import CORS
from verifier import VerificationJob, STATUS_DETAILS

# Determine base path for PyInstaller support
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

template_folder = os.path.join(BASE_DIR, 'templates')
app = Flask(__name__, template_folder=template_folder)
CORS(app)

jobs = {}

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/verify', methods=['POST'])
def verify():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    filename = file.filename
    content = file.read().decode('utf-8', errors='ignore')

    job_id = str(uuid.uuid4())
    job = VerificationJob(job_id, filename, content)
    jobs[job_id] = job

    threading.Thread(target=job.process, daemon=True).start()
    return jsonify({"job_id": job_id})

@app.route('/progress')
def progress():
    job_id = request.args.get('job_id')
    job = jobs.get(job_id)
    if not job:
        return jsonify({"percent": 0, "row": 0, "total": 0, "stats": {}})
    return jsonify({
        "percent": job.progress,
        "row": job.row_count,
        "total": job.total,
        "stats": job.stats
    })

@app.route('/log')
def log():
    job_id = request.args.get('job_id')
    job = jobs.get(job_id)
    return Response(job.log if job else "", mimetype='text/plain')

@app.route('/cancel', methods=['POST'])
def cancel():
    job_id = request.args.get('job_id')
    job = jobs.get(job_id)
    if job:
        job.cancelled = True
    return '', 204

@app.route('/results')
def results():
    job_id = request.args.get('job_id')
    job = jobs.get(job_id)
    if not job or not job.output_file:
        return jsonify({"error": "Job not ready"}), 404

    with open(job.output_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    return jsonify({
        "filename": job.filename,
        "total": len(reader),
        "stats": job.stats,
        "records": reader
    })

@app.route('/download')
def download():
    job_id = request.args.get('job_id')
    filter_type = request.args.get('type', 'all')
    fmt = request.args.get('format', 'csv').lower()
    
    job = jobs.get(job_id)
    if not job or not job.output_file:
        return "File not ready", 404

    with open(job.output_file, 'r', encoding='utf-8') as f:
        reader = list(csv.DictReader(f))

    if filter_type == 'safe':
        filtered = [r for r in reader if r.get('status') == 'safe']
    elif filter_type == 'role':
        filtered = [r for r in reader if r.get('status') == 'role']
    elif filter_type == 'catch_all':
        filtered = [r for r in reader if r.get('status') == 'catch_all']
    elif filter_type == 'invalid_risky':
        filtered = [r for r in reader if r.get('status') in ['invalid', 'disposable', 'spamtrap', 'disabled']]
    else:
        filtered = reader

    base_name = os.path.splitext(job.filename)[0]

    # JSON Export Format
    if fmt == 'json':
        download_name = f"{filter_type}-bounceblitz-{base_name}.json"
        return Response(
            json.dumps(filtered, indent=2),
            mimetype='application/json',
            headers={"Content-Disposition": f"attachment; filename={download_name}"}
        )

    # Excel (.xlsx) Export Format
    elif fmt in ['xlsx', 'excel']:
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Verified Leads"

            if filtered:
                headers = list(filtered[0].keys())
                ws.append(headers)
                for r in filtered:
                    ws.append([r.get(h, '') for h in headers])

            output = io.BytesIO()
            wb.save(output)
            output.seek(0)
            download_name = f"{filter_type}-bounceblitz-{base_name}.xlsx"
            return Response(
                output.getvalue(),
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                headers={"Content-Disposition": f"attachment; filename={download_name}"}
            )
        except Exception as e:
            pass

    # Default CSV Export Format
    output = io.StringIO()
    if filtered:
        writer = csv.DictWriter(output, fieldnames=filtered[0].keys())
        writer.writeheader()
        for r in filtered:
            writer.writerow(r)

    download_name = f"{filter_type}-bounceblitz-{base_name}.csv"
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment; filename={download_name}"}
    )

def run_flask_server(port):
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

def main():
    port = get_free_port()
    server_thread = threading.Thread(target=run_flask_server, args=(port,), daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}/"

    # Native PySide6 Desktop Window with Qt WebEngine File Download Handling
    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtWebEngineCore import QWebEngineDownloadRequest
        from PySide6.QtCore import QUrl

        qt_app = QApplication(sys.argv)
        window = QMainWindow()
        window.setWindowTitle("☕ Bounce Blitz Desktop — Email Verifier Engine")
        window.resize(1100, 820)

        web_view = QWebEngineView()
        
        # Intercept Qt WebEngine file download requests and trigger native Save File Dialog
        def on_download_requested(download_item):
            suggested_name = download_item.downloadFileName() or "bounceblitz-leads.csv"
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            default_path = os.path.join(downloads_dir, suggested_name)
            
            file_path, _ = QFileDialog.getSaveFileName(window, "Save Verified Leads", default_path, "Files (*.csv *.json *.xlsx)")
            if file_path:
                download_item.setDownloadDirectory(os.path.dirname(file_path))
                download_item.setDownloadFileName(os.path.basename(file_path))
                download_item.accept()
            else:
                download_item.cancel()

        web_view.page().profile().downloadRequested.connect(on_download_requested)
        web_view.setUrl(QUrl(url))
        window.setCentralWidget(web_view)

        window.show()
        sys.exit(qt_app.exec())
    except Exception as e:
        # Fallback to default browser if Qt GUI fails
        import webbrowser
        webbrowser.open(url)

if __name__ == '__main__':
    main()
