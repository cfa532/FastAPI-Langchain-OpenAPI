import langchain, docx, re, os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from werkzeug.datastructures import FileStorage
from io import BytesIO
# from langchain.callbacks import get_openai_callback

from config import CHROMA_CLIENT, EMBEDDING_FUNC
from docstore import docstoreReactAgent, retrievalQAChain
from ocr import load_pdf

def init_case(text):
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    chunks.extend(text_splitter.split_text(text))
    file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
    # Upload all the docs to 检查案件名称，答辩人，辩护律师
    res = {}
    res["title"] = retrievalQAChain(file_db, "给这起案件起一个标题")
    res["plaintiff"] = retrievalQAChain(file_db, "原告是谁？")
    res["defendant"] = retrievalQAChain(file_db, "被告是谁？")
    res["judge"] = retrievalQAChain(file_db, "主审法官名称？")
    res["brief"] = retrievalQAChain(file_db, "写一个案情简介？")

    return res

def extract_text(filename, filetype, filedata):
    file = FileStorage(
        stream=BytesIO(filedata), 
        filename=filename,
        content_type=filetype, 
        content_length=len(filedata)
    )
    file_ext = os.path.splitext(filename)[1]
    text = ""
    if file_ext.lower()==".pdf":
        text += load_pdf(file.read())
        # print("text=", text)
    elif file_ext.lower()==".docx":
        for line in docx.Document(file).paragraphs:
            text += "\n"+line.text
        # print("text=", text)
    elif file_ext.lower()==".txt":
        for line in file.read().decode('utf8'):
            # print(line)
            text += line
    return text
