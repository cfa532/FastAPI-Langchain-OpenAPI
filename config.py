import chromadb
from chromadb.config import Settings
from langchain.llms import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI

# Init environment variables
from dotenv import load_dotenv
load_dotenv()

LLM = OpenAI(temperature=0, model="text-davinci-002")
CHAT_LLM = ChatOpenAI(temperature=0)
EMBEDDING_FUNC = OpenAIEmbeddings()

MAX_TOKENS = -1
"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""

CHROMA_WEB_CLIENT = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="localhost",
                                        chroma_server_http_port="8000"
                                    ))
