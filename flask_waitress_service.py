from flask import Flask, render_template, request, make_response
from case_handler import init_case, extract_text
from config import print_object

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
    # assume there is only one file
    file = request.files.getlist('file')[0]
    # get text content of the file

    text = extract_text(file)
    text = init_case(text)
    resp = make_response(text)
    resp.headers["Access-Control-Allow-Origin"] = '*'       # In request header, use {Mode: cors}
    # print_object(resp)
    return resp

if __name__=='__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)