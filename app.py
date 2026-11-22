import os
import subprocess
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash, make_response
from werkzeug.utils import secure_filename
from docx import Document

app = Flask(__name__)
app.secret_key = 'supersecretkey'

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
CONVERTED_FOLDER = os.path.join(os.getcwd(), 'converted')
ALLOWED_EXTENSIONS = {'doc', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CONVERTED_FOLDER'] = CONVERTED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CONVERTED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def fix_document_symbols(docx_path):
    """
    Scans the DOCX file for symbol mappings:
    1. Phone / Call Symbols (☎, 📞, 📱)
    2. Om Symbol (Replaces purple emoji 🕉 and legacy font codes with plain text ॐ)
    """
    try:
        doc = Document(docx_path)
        
        symbol_map = {
            # Legacy Wingdings phone/call characters
            '\xF0\x28': '☎',
            '\xF0\x29': '📞',
            '\xF0\x2A': '📱',
            '\u260E': '☎',
            '\u260F': '📞',
            
            # Map ALL Om variations (including the purple emoji 🕉) to plain text Devanagari Om (ॐ)
            '🕉': 'ॐ',        # Replaces violet box emoji Om with plain text Om
            '\u0C00': 'ॐ',   # Telugu Candrabindu/Om
            '\u0950': 'ॐ',   # Standard Devanagari Om
            '\uFD3F': 'ॐ',   # Legacy font Om
        }

        # Process standard body paragraphs
        for p in doc.paragraphs:
            for run in p.runs:
                if run.font.name in ['Wingdings', 'Wingdings 2', 'Wingdings 3', 'Symbol', 'GanpatiBappa']:
                    run.font.name = 'Noto Color Emoji'
                for old_char, new_char in symbol_map.items():
                    if old_char in run.text:
                        run.text = run.text.replace(old_char, new_char)

        # Process table cells
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for run in p.runs:
                            if run.font.name in ['Wingdings', 'Wingdings 2', 'Wingdings 3', 'Symbol', 'GanpatiBappa']:
                                run.font.name = 'Noto Color Emoji'
                            for old_char, new_char in symbol_map.items():
                                if old_char in run.text:
                                    run.text = run.text.replace(old_char, new_char)

        doc.save(docx_path)
    except Exception as e:
        print(f"Symbol pre-processing skipped: {e}")

def convert_to_pdf(input_path, output_dir):
    # Execute symbol normalization on .docx files prior to rendering
    if input_path.endswith('.docx'):
        fix_document_symbols(input_path)

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["LANG"] = "C.UTF-8"
    
    export_options = (
        'pdf:writer_pdf_Export:{'
        '"SelectPdfVersion":{"type":"long","value":"0"},'
        '"UseLosslessCompression":{"type":"boolean","value":"true"},'
        '"EmbedFonts":{"type":"boolean","value":"true"},'
        '"ExportFormFields":{"type":"boolean","value":"false"},'
        '"Quality":{"type":"long","value":"100"},'
        '"ReduceImageResolution":{"type":"boolean","value":"false"}'
        '}'
    )
    
    cmd = [
        "soffice",
        "--headless",
        "--convert-to", export_options,
        "--outdir", output_dir,
        input_path
    ]
    
    subprocess.run(cmd, env=env, check=True, timeout=180)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading.')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(input_path)
            
            try:
                convert_to_pdf(input_path, app.config['CONVERTED_FOLDER'])
                pdf_filename = os.path.splitext(filename)[0] + '.pdf'
                return redirect(url_for('download_file', filename=pdf_filename))
                
            except subprocess.TimeoutExpired:
                flash('Conversion timed out. The document is too large or complex.')
                return redirect(request.url)
            except subprocess.CalledProcessError as e:
                flash(f'Conversion error occurred during rendering: {e}')
                return redirect(request.url)
        else:
            flash('Invalid file format. Please upload a .doc or .docx file.')
            return redirect(request.url)
            
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    response = make_response(send_from_directory(app.config['CONVERTED_FOLDER'], filename, as_attachment=True))
    response.set_cookie('fileDownload', 'true', max_age=60, path='/')
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=False)