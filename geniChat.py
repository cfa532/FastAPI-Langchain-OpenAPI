import json, sys, os, tiktoken, ast, logging
from google import genai
from google.genai import types
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_vertexai import ChatVertexAI

MAX_TOKEN = {
    "gemini-1.5-flash": 8192,
}

async def geniChat(websocket, msg):
    params = msg["parameters"]
    userQuery = msg["input"]["query"]
    print(userQuery)

    CHAT_LLM = ChatVertexAI(
        model=params["model"],
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )
    response = CHAT_LLM.invoke(userQuery)

    print(response)
    
    # usage_metadata = ast.literal_eval(response.usage_metadata)
    await websocket.send_text(json.dumps({
        "type": "result",
        "answer": response.content, 
        "tokens": response.usage_metadata["total_tokens"],
        "cost": 0}))

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