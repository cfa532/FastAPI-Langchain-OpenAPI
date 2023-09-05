import langchain, docx, re, os
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from werkzeug.datastructures import FileStorage
from io import BytesIO
# from langchain.callbacks import get_openai_callback
from config import CHROMA_CLIENT, EMBEDDING_FUNC, CHAT_LLM, llm_chain
from ocr import load_pdf

# Give text to create a in memory vector DB and answer query based on its content
def init_case(text):
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    chunks.extend(text_splitter.split_text(text))
    file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
    # Upload all the docs to 检查案件名称，答辩人，辩护律师
    return get_JSON_output(file_db, "给这个案件起一个标题，找出原告和被告全称，还有辩护律师和主审法官的姓名。")

def get_JSON_output(db, query:str):
    prompt_temp = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say nothing and leave the answer blank. 

    {context}

    Question: {question}
    Examples:
    SYSTEM: the answers are plaintiff is Cisco Co., and defendant is Goo Ltd.
    OUTPUT: {{plaintiff: Cisco Co., address: 123 Main Street, CEO: John Smith}}
            {{defendant:Goo Ltd., phone: 312-2334-576, CEO: Charlie Brown}}

    Answer all questions in Chinese and export result in JSON format as the examples, use keyword in the question
    as KEY and result as VALUE in the JSON output"""

    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])
    qa = RetrievalQA.from_chain_type(
        CHAT_LLM, 
        chain_type="stuff",
        retriever=db.as_retriever(),
        # return_source_documents=True,
        chain_type_kwargs = {"prompt": PROMPT},
    )
    refined_query = llm_chain("refine the following question in Chinese," + query)
    res = qa({"query": refined_query})
    # print(res)
    # the first returned value is refined question, the 2nd is the result.
    return res, refined_query

# Process file upload from socket client. Referred by flask service code
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
