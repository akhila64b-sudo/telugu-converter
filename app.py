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
    Scans DOCX files and standardizes legacy font codes, custom TTF symbols, 
    and color emoji glyphs into universal plain-text vector Unicode characters.
    """
    try:
        doc = Document(docx_path)
        
        symbol_map = {
            # --- 1. DEVOTIONAL & RELIGIOUS SYMBOLS ---
            '🕉': 'ॐ',        # Replace purple emoji Om with plain Devanagari Om
            '\u0C00': 'ॐ',   # Telugu Candrabindu/Om
            '\u0950': 'ॐ',   # Standard Devanagari Om
            '\uFD3F': 'ॐ',   # Custom mapped legacy font Om
            '\u5355': '卐',   # Standard Swastika
            '卐': '卐',
            '\u0970': 'ੴ',   # Ek Onkar

            # --- 2. CONTACT & OFFICE SYMBOLS ---
            '\xF0\x28': '☎', # Wingdings Phone
            '\xF0\x29': '📞', # Wingdings Handset
            '\xF0\x2A': '📱', # Wingdings Mobile
            '\u260E': '☎',   # Landline Phone
            '\u260F': '📞',   # Call Icon
            '\u2709': '✉',   # Envelope / Mail
            '\xF0\x41': '✉', # Wingdings Mail
            '📍': '📍',       # Location Pin
            '📞': '📞',
            '📱': '📱',
            '☎': '☎',
            '✉': '✉',
            
            # --- 3. GENERAL BULLETS & UI ICONS ---
            '\xF0\xFC': '✓', # Wingdings Checkmark
            '\xF0\xFE': '☑', # Wingdings Boxed Checkmark
            '\xF0\xE0': '➔', # Wingdings Right Arrow
            '\u2713': '✓',   # Standard Checkmark
            '\u2714': '✔',   # Heavy Checkmark
            '\u2605': '★',   # Solid Star
            '\u2606': '☆',   # Outline Star
            '\u2022': '•',   # Bullet Point
            '\xF0\xA7': '•', # Wingdings Bullet
        }

        # Fonts that trigger fallback boxes on Linux if not explicitly mapped
        problematic_fonts = [
            'Wingdings', 'Wingdings 2', 'Wingdings 3', 
            'Webdings', 'Symbol', 'GanpatiBappa', 
            'Priyanka', 'Dineleve'
        ]

        def process_run(run):
            # Neutralize problematic legacy font assignments so system text fonts handle rendering
            if run.font.name in problematic_fonts:
                run.font.name = 'Noto Sans'
            
            # Replace mapped symbol characters with clean Unicode text
            for old_char, new_char in symbol_map.items():
                if old_char in run.text:
                    run.text = run.text.replace(old_char, new_char)

        # Process main document body paragraphs
        for p in doc.paragraphs:
            for run in p.runs:
                process_run(run)

        # Process table cells
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        for run in p.runs:
                            process_run(run)

        doc.save(docx_path)
    except Exception as e:
        print(f"Symbol pre-processing skipped: {e}")

def convert_to_pdf(input_path, output_dir):
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
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)