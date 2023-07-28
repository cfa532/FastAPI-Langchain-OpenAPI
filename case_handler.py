import langchain, docx, re
# from chromadb.config import Settings
from langchain import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
# from langchain.callbacks import get_openai_callback

from config import CHROMA_WEB_CLIENT, EMBEDDING_FUNC
from docstore import docstoreReactAgent, retrievalQAChain
from ocr import load_pdf

def init_case(file):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    text = ""
    chunks = []
    
    if re.search("\.pdf$", file.name):
        text += load_pdf(file.getvalue())
    elif re.search("\.docx$", file.name):
        for line in docx.Document(file).paragraphs:
            text += "\n"+line.text
    elif re.search("\.txt$", file.name):
        for line in file:
            text += line

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