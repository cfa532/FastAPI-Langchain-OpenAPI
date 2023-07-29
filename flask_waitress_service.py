import os, docx		# python-docx
from flask import Flask, render_template, request, make_response
from case_handler import init_case
from config import print_object
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from ocr import load_pdf

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.pdf', '.txt', '.docx']
app.config['UPLOAD_PATH'] = 'uploads'
app.debug = True

@app.route('/')
def hello_world():
    return 'Hello'

@app.route('/init', methods=["GET", "POST"])
def init():
    # f :FileStorage = request.files['file']
    # # f.save(secure_filename(f.filename))   // to flat the uploaded file name
    # fullname = os.path.join(app.config["UPLOAD_PATH"], secure_filename(f.filename))
    # f.save(fullname)
    # print(fullname)
    # result = init_case( fullname )
    text = ""
    file = request.files['file']
    file_ext = os.path.splitext(file.filename)[1]
    print(file.filename, file_ext)
    if file_ext.lower()==".pdf":
        text += load_pdf(request.files.get('file').read())
        print("text=", text)
    elif file_ext.lower()==".docx":
        for line in docx.Document(file).paragraphs:
            text += "\n"+line.text
        print("text=", text)
    elif file_ext.lower()==".txt":
        for line in file.read().decode('utf8'):
            print(line)
            text += line
    file.close()
    result= {"result": "successful"}

    resp = make_response(result)
    resp.headers["Access-Control-Allow-Origin"] = '*'       # In request header, use {Mode: cors}
    print_object(resp)
    return resp

if __name__=='__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)