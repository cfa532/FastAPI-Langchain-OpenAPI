import langchain, re, os
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

# from langchain.callbacks import get_openai_callback
from config import CHROMA_CLIENT, EMBEDDING_FUNC, CHAT_LLM, llm_chain

# Give text to create a in memory vector DB and answer query based on its content
def init_case(text):
    chunks = []
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    chunks.extend(text_splitter.split_text(text))
    file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
    # Upload all the docs to 检查案件名称，答辩人，辩护律师
    return get_JSON_output(file_db, "给这个案件起一个标题，找出原告和被告全称，还有辩护律师和主审法官的姓名。")

# Try to figure out the purpose of the lawsuit.
def get_request(collection_name:str, query:str, temperature=0.0):
    db = Chroma(client=CHROMA_CLIENT, collection_name=collection_name, embedding_function=EMBEDDING_FUNC)
    prompt_temp = """ Use the following pieces of context to answer question at the end. If you don't know the answer, just say nothing and leave the answer blank. Try to find more than a couple of faults of the defendant.

    {context}

    Question: {question}
    Answer all questions in Chinese."""

    # Export result in JSON format. Using "FACT" as key to indicate fact and "REQUEST" as key to indicate the corresponding compensation request.
    # Example:
    # {{fact: the defendant costed $100,000 lost to the plaintiff, request: plaintiff requires $120,000 as compensation. }}
    # {{fact: the defendant close road to access the facility, request: plaintiff requires $20,000 compensation due to incapcity of normal operation. }}

    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])
    CHAT_LLM.temperature = temperature
    qa = RetrievalQA.from_chain_type(
        CHAT_LLM, 
        chain_type="stuff",
        retriever=db.as_retriever(),
        # return_source_documents=True,
        chain_type_kwargs = {"prompt": PROMPT},
    )
    # refine the query to get a better solution
    query = llm_chain("refine the following question in Chinese," + query)
    res = qa({"query": query})
    CHAT_LLM.temperature = 0
    return res, query

# getRequest("huggingface", "列举杭州栖溪对杭州阿家造成的经济损失事实，并且提出合理的诉讼请求。")

def get_argument(collection_name:str, query:str, temperature=0.0):
    db = Chroma(client=CHROMA_CLIENT, collection_name=collection_name, embedding_function=EMBEDDING_FUNC)
    prompt_temp = """ Use the following pieces of context to answer question at the end. If you don't know the answer, just say nothing and leave the answer blank. Try to find more than a couple of faults of the defendant.

    {context}

    Question: {question}
    Answer all questions in Chinese."""

    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])
    CHAT_LLM.temperature = temperature
    qa = RetrievalQA.from_chain_type(
        CHAT_LLM, 
        chain_type="stuff",
        retriever=db.as_retriever(),
        # return_source_documents=True,
        chain_type_kwargs = {"prompt": PROMPT},
    )
    query = llm_chain("refine the following question in Chinese," + query)
    res = qa({"query": query})
    CHAT_LLM.temperature = 0
    return res, query

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
