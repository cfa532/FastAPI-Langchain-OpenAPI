import json, sys, os, time, logging
from google import genai
from google.genai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI

MAX_TOKEN = {
    "gemini-2.0-flash-exp": 8192,
    "gemini-1.5-flash": 8192,
    "gemini-1.5-pro": 8192,
}

async def geniChat(websocket, msg):
    params = msg["parameters"]
    userQuery = msg["input"]["query"]
    encodedQuerLen = len(userQuery)

    CHAT_LLM = ChatVertexAI(
        model=params["model"],
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        streaming=True,
        verbose=True
    )
    query = "Human: " + userQuery + "\nAI:"
    if msg["input"].get("history"):
        # memory.clear()  # do not use memory on serverside.
        # Add chat history kept by client.
        for c in msg["input"]["history"]:
            encodedQuerLen += len(c["Q"] + c["A"])
            if encodedQuerLen > MAX_TOKEN[params["model"]]*2/3:
                break
            else:
                query = "Human: "+c["Q"]+"\nAI: "+c["A"]+"\n" + query
    print(query)
    start_time = time.time()
    chain = CHAT_LLM
    resp = ""
    token_count = 0
    cost = 0
    async for chunk in chain.astream(query):
        print(chunk.content, end="|", flush=True)    # chunk size can be big
        resp += chunk.content
        # the last chuck contains the usage metadata
        if chunk.usage_metadata is not None:
            token_count = chunk.usage_metadata["total_tokens"]

        await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))
    print("time diff=", (time.time() - start_time))
    sys.stdout.flush()
    
    await websocket.send_text(json.dumps({
        "type": "result",
        "answer": resp, 
        "tokens": token_count,
        "cost": cost}))

###
# content='Hello! 👋  How can I help you today? 😊 \n' additional_kwargs={} 
# response_metadata={'is_blocked': False, 'safety_ratings': [{'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 
# 'probability_label': 'NEGLIGIBLE', 'probability_score': 0.1533203125, 'blocked': False, 
# 'severity': 'HARM_SEVERITY_NEGLIGIBLE', 'severity_score': 0.0244140625}], 
# 'usage_metadata': {'prompt_token_count': 2, 'candidates_token_count': 14, 'total_token_count': 16,
# 'cached_content_token_count': 0}, 'finish_reason': 'STOP', 'avg_logprobs': -0.046805624450956075}
# id='run-64e16461-ec28-4133-97f6-17b4f839578d-0' 
# usage_metadata={'input_tokens': 2, 'output_tokens': 14, 'total_tokens': 16}
###