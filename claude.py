import json, sys, os, time, io, base64, requests
from langchain_anthropic import ChatAnthropic
import anthropic

MAX_TOKEN = {
    "claude-3-7-sonnet-20250219": 20000,
}

async def claude(websocket, msg, lapi, user):
    params = msg["parameters"]
    instructions = msg["input"]["query"]
    model = anthropic.Anthropic()
    inputTokenCount = model.messages.count_tokens(
        model=params["model"],
        messages=[{"role": "user", "content": instructions}]
    ).input_tokens

    if len(msg["input"]["urls"]) > 0:
        for url in msg["input"]["urls"]:
            video_data = Part.from_uri(uri=url, mime_type="video/mp4")
            response = model.generate_content([video_data, instructions])
            print(response.usage_metadata)
            await websocket.send_text(json.dumps({
                "tokens": response.usage_metadata.total_token_count,
                "cost": 0,
                "type": "result",
                "answer": response.text}))
    else:
        CHAT_LLM = ChatAnthropic(
            model=params["model"],
            temperature=0,
            max_tokens=MAX_TOKEN[params["model"]],
            timeout=None,
            max_retries=2,
            streaming=True,
            verbose=True
        )
        query = "Human: " + instructions + "\nAI:"
        if msg["input"].get("history"):
            # Add chat history kept by client.
            for c in msg["input"]["history"]:
                inputTokenCount += model.messages.count_tokens(
                    model=params["model"],
                    messages=[{"role": "user", "content": c["Q"] + c["A"]}]
                ).input_tokens
                if inputTokenCount > MAX_TOKEN[params["model"]]*2/3:
                    break
                else:
                    query = "Human: "+c["Q"]+"\nAI: "+c["A"]+"\n" + query

        token_count = 0
        cost = 0
        answer = ""
        chain = CHAT_LLM
        start_time = time.time()
        # chat_session = model.start_chat()

        async for chunk in chain.astream(query):
            answer += chunk.content
            print(chunk.content)
            await websocket.send_text(json.dumps({"type": "stream", "data": chunk.content}))
            sys.stdout.flush()
            # the last chuck contains the usage metadata
        if chunk.usage_metadata is not None:
            token_count = chunk.usage_metadata["total_tokens"]

        print("time diff=", (time.time() - start_time))
        
        await websocket.send_text(json.dumps({
            "type": "result",
            "answer": answer, 
            "tokens": token_count,
            "cost": cost}))

        lapi.bookkeeping(params["model"], cost, token_count, user)

    sys.stdout.flush()
