import docx, json		# python-docx
from flask import Flask, render_template, request, make_response, jsonify
from case_handler import init_case

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.debug = True

@app.route('/')
def hello_world():
    return 'Hello'

@app.route('/init', methods=["GET", "POST"])
def init():
    result = init_case( request.files['file'] )
    print(result)
    resp = make_response(result)
    resp.headers["Access-Control-Allow-Origin"] = '*'       # In request header, use {Mode: cors}
    return resp

if __name__=='__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)