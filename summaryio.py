from typing import Any
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferWindowMemory, ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from typing import Any, Dict, List, Union
from langchain_core.messages import get_buffer_string
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain.memory.chat_memory import BaseChatMemory

from aiohttp import web
import socketio, sys
import eventlet
import eventlet.wsgi

load_dotenv()
MAX_TOKEN = 4096

sio = socketio.Server(cors_allowed_origins="*")

class MyStreamingHandler(StreamingStdOutCallbackHandler):
    def __init__(self) -> None:
        super().__init__()

    async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        sys.stdout.write(token)
        await sio.emit("stream", token)
        sys.stdout.flush()

CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", streaming=True,
                    callbacks=[MyStreamingHandler()])     # ChatOpenAI cannot have max_token=-1
memory = ConversationBufferMemory(return_messages=False)
chain = ConversationChain(llm=CHAT_LLM, memory=memory, verbose=True)
chain.output_parser=StrOutputParser()

async def index(request):
    """Serve the client-side application."""
    with open('index.html') as f:
        return web.Response(text=f.read(), content_type='text/html')

@sio.event
def connect(sid, environ, auth):
    print("connect ", sid, environ)

@sio.on("query")
def get_query(sid, query):
    print(query)
    params = query["parameters"]
    if params["llm"] == "openai":
        CHAT_LLM.temperature = float(params["temperature"])
    elif params["llm"] == "qianfan":
        pass

    hlen = 0
    if "history" in query["input"]:
        # user server history if history key is not present in user request
        memory.clear()  # do not use memory on serverside. Add chat history kept by client.
        for c in query["input"]["history"]:
            hlen += len(c["Q"]) + len(c["A"])
            if hlen > MAX_TOKEN/2:
                break
            else:
                memory.chat_memory.add_messages([HumanMessage(content=c["Q"]), AIMessage(content=c["A"])])

    for chunk in chain.stream(query["input"]["query"]):
        print(chunk, end="", flush=True)    # chunk size can be big
    # sio.emit("result", {"answer": chunk["response"]})
    return chunk["response"]

@sio.on('summary')
def get_summary(sid, query):
    print(f"Summary: ${query}")

    # for chunk in chain.stream(event["input"]["query"]):
    # print(chunk, end="", flush=True)    # chunk size can be big

    sio.emit("summary", {"result": "summrary of input"})

@sio.event
def disconnect(sid):
    print('disconnect ', sid)

# app.router.add_static('/static', 'static')
# app.router.add_get('/', index)

if __name__ == '__main__':
    # web.run_app(app, port=8505)
    # uvicorn.run(app, host='0.0.0.0', port="8080")
    # app.run(host='0.0.0.0', port="8080")
    app = socketio.WSGIApp(sio)
    eventlet.wsgi.server(eventlet.listen(('', 8505)), app)


