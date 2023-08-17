import langchain
from langchain.vectorstores.chroma import Chroma
from langchain import Wikipedia
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from langchain.prompts import PromptTemplate
from config import LLM, CHROMA_CLIENT, CHAT_LLM, EMBEDDING_FUNC
from CaseInfo import CaseInfo

def docstoreReactAgent(collection_name:str, query:str)->str:
    collection_name = "5ACIVM0ewbQdqpgVtXhO3PW9QsJ"
    # db = Chroma(client=CHROMA_WEB_CLIENT, collection_name="law-docs")
    # docstore = DocstoreExplorer(db)
    print(collection_name, query)
    docstore = DocstoreExplorer(CaseInfo(collection_name))     # only one that work is Wikipedia, which is a wrapper class.
    tools = [
        Tool(
            name="Search",
            func=docstore.search,
            description="useful when never you need to find information about anything",
            # given search term, find a document
        ),
        Tool(
            name="Lookup",
            func=docstore.lookup,
            description="useful for when you need to ask with lookup",
            # find data within a document
        )
    ]
    react = initialize_agent(tools, CHAT_LLM, agent=AgentType.REACT_DOCSTORE, verbose=True)
    # query = "原告方基本信息"
    langchain.debug = True
    res= react.run(query)
    langchain.debug = False
    print(res)
    return res

# print(docstoreReactAgent(db="", query="案件名称？"))
def retrievalQAChain(collection_name:str, query:str):
    collection_name = "5ACIVM0ewbQdqpgVtXhO3PW9QsJ"
    # Chroma.embeddings = EMBEDDING_FUNC
    db = Chroma(client=CHROMA_CLIENT, collection_name=collection_name, embedding_function=EMBEDDING_FUNC)
    prompt_temp = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, don't try to make up an answer.

    {context}

    Question: {question}
    Answer all questions in Chinese."""
    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])

    question_prompt = PromptTemplate(input_variables=['question', 'context'],
        template="")

    refine_prompt = PromptTemplate(input_variables=['question', 'existing_answer', 'context'], template="")

    chain_type_kwargs = {"refine_prompt": PROMPT}
    # qa_chain = load_qa_chain(LLM, chain_type="refine")
    # qa = RetrievalQA(
    #     combine_documents_chain=qa_chain,
    #     retriever=db.as_retriever(),
    # )
    qa = RetrievalQA.from_chain_type(LLM, 
                                     chain_type="refine",
                                     retriever=db.as_retriever(),
                                     chain_type_kwargs={
                                        "question_prompt": question_prompt,
                                        "refine_prompt" : refine_prompt
                                    })
    # chain_type_kwargs only acceptable 'prompt' for STUFF chain. 
    # Refine chain accept more prompts: question_prompt, refine_prompt
    res = qa({"query": query})
    print(res)
    return res["result"]

res = retrievalQAChain("", "查找原告方信息")
print(res)