import os
import subprocess
import tempfile
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "telugu_pdf_converter_secret_key"

# Allow file uploads up to 100 MB for 500+ page documents
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

ALLOWED_EXTENSIONS = {'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Check if a file was uploaded
        if 'file' not in request.files:
            flash('No file part in the request.')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected.')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            
            # Create a secure temporary directory to isolate file processing
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, filename)
                file.save(input_path)
                
                try:
                    # Execute LibreOffice in headless mode with a 300-second timeout
                    subprocess.run(
                        [
                            'soffice',
                            '--headless',
                            '--convert-to', 'pdf',
                            '--outdir', temp_dir,
                            input_path
                        ],
                        check=True,
                        timeout=300
                    )
                    
                    # Determine the generated PDF filename
                    base_name = os.path.splitext(filename)[0]
                    pdf_filename = f"{base_name}.pdf"
                    pdf_path = os.path.join(temp_dir, pdf_filename)
                    
                    if os.path.exists(pdf_path):
                        return send_file(
                            pdf_path,
                            as_attachment=True,
                            download_name=pdf_filename,
                            mimetype='application/pdf'
                        )
                    else:
                        flash('Conversion failed: PDF file was not generated.')
                        return redirect(request.url)
                        
                except subprocess.TimeoutExpired:
                    flash('Conversion timed out. The document is too large to process within 5 minutes.')
                    return redirect(request.url)
                except subprocess.CalledProcessError as e:
                    flash(f'Conversion error occurred during rendering: {str(e)}')
                    return redirect(request.url)
        else:
            flash('Invalid file format. Please upload a .doc or .docx Word document.')
            return redirect(request.url)
            
    return render_template('index.html')

if __name__ == '__main__':
    # Standard local development port configuration
    app.run(host='0.0.0.0', port=10000, debug=False)