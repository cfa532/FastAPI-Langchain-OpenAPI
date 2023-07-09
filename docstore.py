from langchain import OpenAI
from langchain.vectorstores import Chroma
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from config import CHROMA_CLIENT
from dotenv import load_dotenv
load_dotenv()
db = Chroma(client=CHROMA_CLIENT, collection_name="law-docs")
docstore = DocstoreExplorer(db)
# db.as_retriever()
tools = [
    Tool(
        name="Search",
        func=docstore.search,
        description="需要搜索信息的时候使用"
    ),
    Tool(
        name="Lookup",
        func=docstore.lookup,
        description="需要查找信息时使用"
    )
]
llm = OpenAI(temperature=0, model="text-davinci-002")
react = initialize_agent(tools, llm, agent=AgentType.REACT_DOCSTORE, verbose=True)
question = "反电信诈骗法的要点是什么？全部问题使用中文问答问题。"
react.run(question)