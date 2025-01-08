import asyncio, websockets, os, sys, json, ssl, time
from datetime import datetime
from typing import Any
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory, ConversationBufferMemory
from langchain.chains import ConversationChain, LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_core.messages import get_buffer_string
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.globals import set_verbose

from openaiCBHandler import get_cost_tracker_callback

MAX_TOKEN = {
    "gpt-3.5-turbo": 4096,
    "gpt-4": 4096,
    "gpt-4-turbo": 8192,
    "gpt-4o": 8192,
}

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain(certfile='leither.uk.orig.pem', keyfile='leither.uk.cert.pem')
###########################################################################################
### Format of input
# {
#     "input": {
#         "query": "content of the query",
#         "prompt": "instruction of how to execute the query, such as createa a summary",
#         "history": "previous bouts of conversations"
#     },
#     "parameters": {
#         "llm": "openai",    # LLM to be userd. Different LLM comes with different model parameters
#         "temperatue": "0.0"
#         "client": "mobile"
#         "model": "gpt-4"
#     }
# }
############################################################################################
    
async def openChat(websocket, msg):
    params = msg["parameters"]
    userQuery = msg["input"]["query"]
    # await websocket.send_text(json.dumps({
    #         "type": "result",
    #         "answer": "Message received. " + userQuery, 
    #         "tokens": "111",
    #         "cost": "0.01"}))
    # lapi.bookkeeping("gpt-4o", 0.014, 111, user)
    # continue

    CHAT_LLM = ChatOpenAI(
        temperature=float(params["temperature"]),
        model=params["model"],
        streaming=True,
        verbose=True
        )     # ChatOpenAI cannot have max_token=-1

    # CHAT_LLM.callbacks=[MyStreamingHandler()]
    # query = msg["input"]["query"]
    # memory = ConversationBufferMemory(return_messages=False)

    query = "Human: " + userQuery + "\nAI:"
    if msg["input"].get("history"):
        # memory.clear()  # do not use memory on serverside.
        # Add chat history kept by client.
        for c in msg["input"]["history"]:
            encodedQuerLen += len(tiktoken_encoder.encode(c["Q"] + c["A"]))
            if encodedQuerLen > MAX_TOKEN[params["model"]]*2/3:
                break
            else:
                query = "Human: "+c["Q"]+"\nAI: "+c["A"]+"\n" + query
    query = """
        The following is a friendly conversation between a human and an AI. 
        The AI is talkative and provides lots of specific details from its context.
        If the AI does not know the answer to a question, 
        it truthfully says it does not know.\nCurrent conversation:\n
    """ + query
    print(query)

    start_time = time.time()
    with get_cost_tracker_callback(params["model"]) as cb:
        # chain = ConversationChain(llm=CHAT_LLM, memory=memory, output_parser=StrOutputParser())
        chain = CHAT_LLM
        resp = ""
        async for chunk in chain.astream(query):
            print(chunk.content, end="|", flush=True)    # chunk size can be big
            resp += chunk.content
            await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))
        print('\n', cb)
        print("time diff=", (time.time() - start_time))
        sys.stdout.flush()
        await websocket.send_text(json.dumps({
            "type": "result",
            "answer": resp, 
            "tokens": cb.total_tokens,
            "cost": cb.total_cost}))
        lapi.bookkeeping(params["model"], cb.total_cost, cb.total_tokens, user)