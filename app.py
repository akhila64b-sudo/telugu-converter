import os
import subprocess
import platform
from flask import Flask, render_template, request, send_file, flash, redirect

app = Flask(__name__)
app.secret_key = "telugu_word_converter_secret"

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
OUTPUT_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'converted')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'doc', 'docx', 'rtf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_to_pdf(input_path, output_dir):
    """Converts DOC/DOCX to PDF using LibreOffice on cloud servers or local Windows."""
    if platform.system() == "Windows":
        libreoffice_exec = r"C:\Program Files\LibreOffice\program\soffice.exe"
    else:
        libreoffice_exec = "libreoffice"

    cmd = [
        libreoffice_exec,
        '--headless',
        '--convert-to', 'pdf',
        '--outdir', output_dir,
        input_path
    ]
    subprocess.run(cmd, check=True)
    
    filename = os.path.basename(input_path)
    base_name = os.path.splitext(filename)[0]
    return os.path.join(output_dir, f"{base_name}.pdf")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'document' not in request.files:
            flash('No file provided.')
            return redirect(request.url)
            
        file = request.files['document']
        if file.filename == '':
            flash('No selected file.')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = file.filename
            input_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(input_path)

            try:
                pdf_path = convert_to_pdf(input_path, OUTPUT_FOLDER)
                return send_file(pdf_path, as_attachment=True)
            except Exception as e:
                flash(f"Conversion failed: {str(e)}")
                return redirect(request.url)
        else:
            flash('Only .doc, .docx, and .rtf files are supported.')
            return redirect(request.url)

    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)