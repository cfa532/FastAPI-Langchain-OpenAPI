import langchain
from langchain.vectorstores import Chroma, FAISS
from langchain import Wikipedia
from langchain.chains import RetrievalQA
# from langchain.docstore.base import Docstore
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from config import LLM, CHROMA_WEB_CLIENT, CHAT_LLM

def docstoreReactAgent(db, query:str, verbose=False)->str:
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
    react = initialize_agent(tools, LLM, agent=AgentType.REACT_DOCSTORE, verbose=verbose)
    # query = "反电信诈骗法的要点是什么？全部问题使用中文问答问题。"
    # langchain.debug = True
    res= react.run(query)
    # langchain.debug = False
    return res

# print(docstoreReactAgent(db="", query="案件名称？", verbose=True))
def retrievalQAChain(db, query, verbose=False):
    LLM.verbose = verbose
    qa = RetrievalQA.from_chain_type(
        llm=LLM,
        chain_type="refine",
        retriever=db.as_retriever(),
    )
    return qa.run(query)

# res = docstoreReactAgent("", "反电信诈骗法的要点是什么？")
# print(res)