from flask import Flask, render_template, request, make_response
from flask_socketio import SocketIO, emit, send
from flask_cors import CORS
from init_vectordb import upsert_text
from langchain.vectorstores.chroma import Chroma
from case_handler import init_case, get_JSON_output, get_request, get_argument
from init_vectordb import extract_text
from config import CHROMA_CLIENT, EMBEDDING_FUNC, LegalCase

# os.environ["TOKENIZERS_PARALLELISM"] = "false"
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
app.debug = False

app.config['SECRET_KEY'] = "secret!"
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=app.config['MAX_CONTENT_LENGTH'])

@socketio.on("hello")
def sayHi(arg):
    print(arg); # "world"
    return {"status": "greata"}     # returned parameter to the callback defined in client

# given a file to extract basic information of a case, such as plaintiff and defendent
@socketio.on("init_case")
def init(filename, filetype, filedata):
    print("Init case:", filename, filetype)
    text = extract_text(filename, filetype, filedata)
    res = init_case(text)
    print(res)   # AI result and refined query
    # res = {"title": "田产地头纠纷", "brief":"张三告李四多吃多占", "plaintiff":"张三", "defendant":"李四"}
    return res

# query case documents to figure basic informations about involved parties.
# Always return the result and refined query
@socketio.on("case_info")
def case_info(my_case:LegalCase, query:str):
    print(my_case["id"], query)
    db = Chroma(client=CHROMA_CLIENT, collection_name=my_case["mid"], embedding_function=EMBEDDING_FUNC)
    # ret = db.as_retriever(search_kwargs={"filter":{"doc_type":my_case["id"]}})
    ret = db.as_retriever()
    # query = "根据所提供资料，分别确定原告方及被告的基本信息。如当事人是公民（自然人），应写明姓名、性别、民族、出生年月日、住址、身份证号码、联系方式；当事人如是机关、团体、企事业单位，则写明名称、地址、统一社会信用代码、法定代表人姓名、职务"
    return get_JSON_output(ret, query)

@socketio.on("case_request")
def case_request(collection_name:str, query:str):
    res, query = get_request(collection_name, query, 0.5)
    print("Request: ", res, query)
    return res, query

@socketio.on("case_argument")
def case_argument(collection_name:str, query:str):
    res, query = get_argument(collection_name, query)
    print("Argument: ", res, query)
    return res, query

# Upload a file from web client
@socketio.on("upload_file")
def upload(collection_name, case_name, filename, filetype, filedata):
    print("Received file: ", collection_name, case_name, filename, len(filedata))
    text = extract_text(filename, filetype, filedata)
    print(text[:100])
    res =  upsert_text(collection_name, text, filename, case_name)
    print(res)
    # emit("file_uploaded", filename)
    return res

@app.route('/')
def hello_world():
    return 'Hello'

if __name__=='__main__':
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=5000)
    socketio.run(app, host='0.0.0.0', port=5050)



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
