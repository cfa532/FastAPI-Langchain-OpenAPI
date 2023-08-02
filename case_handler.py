import langchain, docx, re, os
# from langchain import FAISS
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.vectorstores.chroma import Chroma
from werkzeug.datastructures import FileStorage
# from langchain.callbacks import get_openai_callback

# from config import CHROMA_WEB_CLIENT, EMBEDDING_FUNC
from docstore import docstoreReactAgent, retrievalQAChain
from ocr import load_pdf

def init_case(text):
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    chunks.extend(text_splitter.split_text(text))
    file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
    # Upload all the docs to 检查案件名称，答辩人，辩护律师
    res = {}
    res["title"] = retrievalQAChain(file_db, "案件名称？")
    res["plaintiff"] = retrievalQAChain(file_db, "原告？")
    res["defendant"] = retrievalQAChain(file_db, "被告？")
    res["judge"] = retrievalQAChain(file_db, "主审法官？")
    res["brief"] = retrievalQAChain(file_db, "案情简介？")

    return res

def extract_text(file :FileStorage):
    file_ext = os.path.splitext(file.filename)[1]
    text = ""
    if file_ext.lower()==".pdf":
        text += load_pdf(file.read())
        print("text=", text)
    elif file_ext.lower()==".docx":
        for line in docx.Document(file).paragraphs:
            text += "\n"+line.text
        print("text=", text)
    elif file_ext.lower()==".txt":
        for line in file.read().decode('utf8'):
            print(line)
            text += line
    return text