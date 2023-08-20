import langchain
from langchain.vectorstores.chroma import Chroma
from langchain.chains import RetrievalQA, SimpleSequentialChain, LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain.agents.react.base import DocstoreExplorer
from langchain.prompts import PromptTemplate
from config import LLM, CHROMA_CLIENT, CHAT_LLM, EMBEDDING_FUNC, VERBOSE
from CaseInfo import CaseInfo

def docstoreReactAgent(collection_name:str, query:str)->str:
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
    # format question
    db = Chroma(client=CHROMA_CLIENT, collection_name=collection_name, embedding_function=EMBEDDING_FUNC)
    prompt_temp = """Use the following pieces of context to answer the question at the end. If you don't know the answer, just say that you don't know, leave the answer blank. 

    {context}

    Question: {question}
    Examples:
    SYSTEM: the answers are plaintiff is Cisco Co., and defendant is Goo Ltd.
    OUTPUT: {{plaintiff: Cisco Co., defendant:Goo Ltd.}}

    Answer all questions in Chinese and export result in JSON format as the examples, use keyword in the question
    as KEY and result as VALUE in the JSON output"""

    PROMPT = PromptTemplate(template=prompt_temp, input_variables=["context", "question"])
    # qa_chain = load_qa_chain(LLM, chain_type="refine")
    # qa = RetrievalQA(
    #     combine_documents_chain=qa_chain,
    #     retriever=db.as_retriever(),
    # )
    # 
    qa = RetrievalQA.from_chain_type(
        CHAT_LLM, 
        chain_type="stuff",
        retriever=db.as_retriever(),
        # return_source_documents=True,
        chain_type_kwargs = {"prompt": PROMPT},
        #  chain_type_kwargs={
        #     "question_prompt": question_prompt,
        #     "refine_prompt" : refine_prompt
        # },
        )
    # chain_type_kwargs only acceptable 'prompt' for STUFF chain. 
    # Refine chain accept more prompts: question_prompt, refine_prompt

    format_query_chain = LLMChain(
        llm=CHAT_LLM,
        prompt=PromptTemplate(
            input_variables=["query"],
            # template="refine the following question, {query}"),
            template="refine the following question in Chinese, {query}"),
        # verbose=VERBOSE
    )
    res = format_query_chain.run(query)

    # return res["result"]
    res = qa({"query": res})
    print(res)

res = retrievalQAChain("huggingface", "根据所提供资料，分别确定原告方及被告名称")
# res = retrievalQAChain("5ACIVM0ewbQdqpgVtXhO3PW9QsJ", "refine my question below. \n\n find full name of the defendant")
# res = retrievalQAChain("5ACIVM0ewbQdqpgVtXhO3PW9QsJ", "Tell me what the plaintiff is suing for.")