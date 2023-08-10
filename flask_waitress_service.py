from flask import Flask, render_template, request, make_response
from case_handler import extract_text, init_case
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
from config import print_object

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.debug = True

app.config['SECRET_KEY'] = "secret!"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=app.config['MAX_CONTENT_LENGTH'])

@socketio.on("hello")
def sayHi(arg):
    print(arg); # "world"
    return {"status": "greata"}     # returned parameter to the callback defined in client

@socketio.on("init_case")
def init(filename, filetype, filedata):
    print(filename, filetype)
    text = extract_text(filename, filetype, filedata)
    text = init_case(text)
    print(text)
    emit("Done", {"title": "田产地头纠纷", "brief":"张三告李四多吃多占", "plaintiff":"张三", "defendant":"李四"})
    return "succeed"
    # print(file.decode())  # work for text, html 

@app.route('/')
def hello_world():
    return 'Hello'

if __name__=='__main__':
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=5000)
    socketio.run(app, host='0.0.0.0', port=5000)



"""
@app.route('/init', methods=["GET", "POST"])
def init():
    # assume there is only one file
    file = request.files.getlist('file')[0]
    # get text content of the file
    # text = extract_text(file)
    text = init_case(text)
    resp = make_response(text)
    resp.headers["Access-Control-Allow-Origin"] = '*'       # In request header, use {Mode: cors}
    # print_object(resp)
    return resp
"""
