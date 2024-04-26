import asyncio, websockets, os, sys, json, ssl
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
from dotenv import load_dotenv
set_verbose(True)
load_dotenv()
MAX_TOKEN = 4096
# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain(certfile='leither.uk.orig.pem', keyfile='leither.uk.cert.pem')

async def handler(websocket):
    class MyStreamingHandler(StreamingStdOutCallbackHandler):
        def __init__(self) -> None:
            super().__init__()

        async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
            sys.stdout.write(token)
            await websocket.send(json.dumps({"type": "stream", "data": token}))     # streaming message to client
            sys.stdout.flush()

###########################################
### Format of input
# {
#     "input": {
#         "query": "content of the query",
#         "prompt": "instruction of how to execute the query, such as createa a summary",
#         "history": "previous bouts of conversations"
#     },
#     "parameters": {
#         "llm": "openai",    # LLM to be userd. Different LLM comes with different other parameters
#         "temperatue": "0.0"
#     }
# }
############################################
    
    while True:
        try:
            async for message in websocket:
                event = json.loads(message)
                params = event["parameters"]
                if params["llm"] == "openai":
                    CHAT_LLM = ChatOpenAI(
                        temperature=float(params["temperature"]),
                        model=params["model"],
                        streaming=True
                        )     # ChatOpenAI cannot have max_token=-1
                elif params["llm"] == "qianfan":
                    pass

                # if params["client"] == "mobile":
                #     CHAT_LLM.streaming = False

                if "rawtext" in event["input"]:
                    print(message)
                    # the request is from secretary APP. If it is too long, seperate it.
                    splitter = RecursiveCharacterTextSplitter(chunk_size=3072, chunk_overlap=200)
                    chunks_in = splitter.create_documents([event["input"]["rawtext"]])

                    # prompt is sent from client, so that it can be customized.
                    prompt = PromptTemplate(input_variables=["text"],
                                            template=event["input"]["prompt"] + """

                        {text} 

                        SUMMARY:
                        """)
                    # chain = LLMChain(llm=CHAT_LLM, prompt=prompt, verbose=True)
                    chain = prompt | CHAT_LLM
                    resp = ""
                    for ci in chunks_in:
                        async for chunk in chain.astream({"text": ci.page_content}):
                            print(chunk.content, end="|", flush=True)    # chunk size can be big
                            resp += chunk.content
                            await websocket.send(json.dumps({"type": "stream", "data": chunk.content}))
                    await websocket.send(json.dumps({"type": "result", "answer": resp}))

                elif "query" in event["input"]:
                    CHAT_LLM.callbacks=[MyStreamingHandler()]
                    # CHAT_LLM = ChatOpenAI(
                    #     temperature=float(params["temperature"]),
                    #     model=params["model"],
                    #     streaming=True,
                    #     callbacks=[MyStreamingHandler()]
                    #     )     # ChatOpenAI cannot have max_token=-1
                    memory = ConversationBufferMemory(return_messages=False)
                    if "history" in event["input"]:
                        # user server history if history key is not present in user request
                        memory.clear()  # do not use memory on serverside. Add chat history kept by client.
                        hlen = 0
                        for c in event["input"]["history"]:
                            hlen += len(c["Q"]) + len(c["A"])
                            if hlen > MAX_TOKEN/2:
                                break
                            else:
                                memory.chat_memory.add_messages([HumanMessage(content=c["Q"]), AIMessage(content=c["A"])])

                    chain = ConversationChain(llm=CHAT_LLM, memory=memory, output_parser=StrOutputParser())
                    async for chunk in chain.astream(event["input"]["query"]):
                        print(chunk, end="|", flush=True)    # chunk size can be big
                    await websocket.send(json.dumps({"type": "result", "answer": chunk["response"]}))

        except websockets.exceptions.WebSocketException as e:
            # keep abnormal messages from logging
            print("Error:", type(e), e)
        finally:
            try:
                await websocket.close()
            except NameError:
                pass

async def main():
    # async with websockets.serve(handler, "", 8505, ssl=ssl_context):
    async with websockets.serve(handler, "", 8505):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())