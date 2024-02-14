import asyncio, websockets, os, sys, json
from typing import Any
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain.memory import ConversationBufferWindowMemory
from langchain.chains import ConversationChain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

from config import EMBEDDING_FUNC, LegalCase, llm_chain, LAW_COLLECTION_NAME, MAX_TOKENS, LLM

async def handler(websocket):
    class MyStreamingHandler(StreamingStdOutCallbackHandler):
        def __init__(self) -> None:
            super().__init__()

        async def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
            sys.stdout.write(token)
            # emit("stream_in", token)    # reply to event sent from the client, socketio.emit reply to all clients
            await websocket.send(json.dumps({"type": "stream", "data": token}))
            sys.stdout.flush()

    CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", max_tokens=2048, streaming=True,
                        callbacks=[MyStreamingHandler()])     # ChatOpenAI cannot have max_token=-1
    chain = ConversationChain(llm=CHAT_LLM, memory=ConversationBufferWindowMemory(k=6), verbose=True)
    chain.output_parser=StrOutputParser()

    while True:
        try:
            async for message in websocket:
                print(message)
                event = json.loads(message)
                assert event["type"] == "gpt_api", "Only accept gpt_api"
                for chunk in chain.stream(event["query"]):
                    print(chunk, end="", flush=True)    # chunk size can be big
                await websocket.send(json.dumps({"type": "result", "answer": chunk["response"]}))

        except websockets.ConnectionClosedOK:
            break

async def main():
    async with websockets.serve(handler, "", 5050):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())