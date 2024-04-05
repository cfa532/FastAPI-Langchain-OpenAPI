import asyncio, websockets, os, sys, json
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
    BaseMessage,
    HumanMessage,
    get_buffer_string,
)

load_dotenv()
MAX_TOKEN = 4096

from typing import Any, Dict, List, Union
from langchain_core.messages import get_buffer_string
from langchain_core.messages.ai import AIMessage
from langchain_core.messages.human import HumanMessage
from langchain.memory.chat_memory import BaseChatMemory

def trim(messages, max_len):
    if sum([len(m.content) for m in messages]) > max_len:
        messages.pop(0)
        trim(messages, max_len)
    else:
        return

async def handler(websocket):
    class MyStreamingHandler(StreamingStdOutCallbackHandler):
        def __init__(self) -> None:
            super().__init__()

        async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
            sys.stdout.write(token)
            await websocket.send(json.dumps({"type": "stream", "data": token}))
            sys.stdout.flush()

    # class MyConversationWindowMemory(ConversationBufferWindowMemory):
    #     def __init__(self) -> None:
    #         super().__init__()

    #     @property
    #     def buffer_as_str(self) -> str:
    #         """Exposes the buffer as a string in case return_messages is True."""
    #         messages = self.chat_memory.messages[-self.k * 2 :] if self.k > 0 else []
            
    #         """remove the early messages to keep buffer from exceeding max token length"""
    #         trim(messages, MAX_TOKEN/2)

    #         return get_buffer_string(
    #             messages,
    #             human_prefix=self.human_prefix,
    #             ai_prefix=self.ai_prefix,
    #         )

    CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", streaming=True,
                        callbacks=[MyStreamingHandler()])     # ChatOpenAI cannot have max_token=-1
    memory = ConversationBufferMemory(return_messages=False)
    chain = ConversationChain(llm=CHAT_LLM, memory=memory, verbose=True)
    chain.output_parser=StrOutputParser()

    # blacklist = ["172.31.9.52"]
    # if websocket.remote_address[0] in blacklist:
    #     return
    
    while True:
        try:
            async for message in websocket:
                event = json.loads(message)
                params = event["parameters"]
                if params["llm"] == "openai":
                    CHAT_LLM.temperature = float(params["temperature"])
                elif params["llm"] == "qianfan":
                    pass

                if params["client"] == "mobile":
                    CHAT_LLM.callbacks = [StreamingStdOutCallbackHandler()]

                hlen = 0
                if "history" in event["input"]:
                    # user server history if history key is not present in user request
                    memory.clear()  # do not use memory on serverside. Add chat history kept by client.
                    for c in event["input"]["history"]:
                        hlen += len(c["Q"]) + len(c["A"])
                        if hlen > MAX_TOKEN/2:
                            break
                        else:
                            memory.chat_memory.add_messages([HumanMessage(content=c["Q"]), AIMessage(content=c["A"])])

                for chunk in chain.stream(event["input"]["query"]):
                    print(chunk, end="", flush=True)    # chunk size can be big
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
    async with websockets.serve(handler, "", 5050):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())