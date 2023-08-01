from flask import Flask, render_template, request, make_response
from case_handler import init_case, extract_text
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
from config import print_object

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.debug = True

app.config['SECRET_KEY'] = "secret!"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=app.config['MAX_CONTENT_LENGTH'])

# @socketio.on('connect')
# def handle_chat(data):
#     print(data)
    # chat entrence here

# @socketio.on('file')
# def handle_upload(file):
#     text = extract_text(file)
#     text = init_case(text)
#     resp = make_response(text)
#     # resp.headers["Access-Control-Allow-Origin"] = '*'       # In request header, use {Mode: cors}
#     # print_object(resp)
#     return resp

@socketio.on("hello")
def sayHi(arg):
    print(arg); # "world"
    # emit("Hi", {}, callback=ack)

@socketio.on("init_case")
def init_case(file):
    text = extract_text(file)
    print(text)

def ack():
    print('message was received!')

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

def ack():
    print('message was received!')

if __name__=='__main__':
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=5000)
    socketio.run(app, host='0.0.0.0', port=5000)