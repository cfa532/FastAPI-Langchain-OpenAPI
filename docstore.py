import langchain
# from langchain.vectorstores import Chroma, FAISS
from langchain import Wikipedia
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from langchain.prompts import PromptTemplate
from config import LLM, CHROMA_WEB_CLIENT, CHAT_LLM

def docstoreReactAgent(db, query:str)->str:
    # db = Chroma(client=CHROMA_WEB_CLIENT, collection_name="law-docs")
    # docstore = DocstoreExplorer(db)

    docstore = DocstoreExplorer(Wikipedia())     # only one that work is Wikipedia, which is a wrapper class.
    tools = [
        Tool(
            name="Search",
            func=docstore.search,
            description="useful for when you need to ask with search",
            # given search term, find a document
        ),
        Tool(
            name="Lookup",
            func=docstore.lookup,
            description="useful for when you need to ask with lookup",
            # find data within a document
        )
    ]
    react = initialize_agent(tools, LLM, agent=AgentType.REACT_DOCSTORE)
    # query = "反电信诈骗法的要点是什么？全部问题使用中文问答问题。"
    # langchain.debug = True
    res= react.run(query)
    # langchain.debug = False
    return res

# print(docstoreReactAgent(db="", query="案件名称？"))
def retrievalQAChain(db, query):
    prompt_temp = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.

    {context}

    Question: {question}
    Answer all questions in Chinese."""
    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])
    chain_type_kwargs = {"prompt": PROMPT}
    qa_chain = load_qa_chain(LLM, chain_type="refine")
    qa = RetrievalQA(
        combine_documents_chain=qa_chain,
        retriever=db.as_retriever(),
    )
    # qa = RetrievalQA.from_chain_type(LLM, chain_type="stuff", chain_type_kwargs=chain_type_kwargs, retriever=db.as_retriever(),)
    # chain_type_kwargs only acceptable with STUFF chain. Validation error for RefineDocumentsChain prompt extra fields not permitted
    res = qa({"query": query})
    print(res)
    return res["result"]

# res = docstoreReactAgent("", "反电信诈骗法的要点是什么？")
# print(res)