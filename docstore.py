from langchain.vectorstores import Chroma
# from langchain.docstore.base import Docstore
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from config import LLM, CHROMA_WEB_CLIENT, CHAT_LLM

def docstoreReactAgent(db, query:str, verbose=False)->str:
    db = Chroma(client=CHROMA_WEB_CLIENT, collection_name="law-docs")
    docstore = DocstoreExplorer(db)
    # db.as_retriever()
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
    query = "反电信诈骗法的要点是什么？全部问题使用中文问答问题。"
    return react.run(query)
    
print(docstoreReactAgent(db="", query="反电信诈骗法的要点是什么？", verbose=True))
