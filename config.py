import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from langchain.llms import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI

# Init environment variables in .env file
from dotenv import load_dotenv
load_dotenv()

MAX_TOKENS = -1
VERBOSE = True

"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""

CHROMA_WEB_CLIENT = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="localhost",
                                        chroma_server_http_port="8000"
                                    ))

LLM = OpenAI(temperature=0, max_tokens=MAX_TOKENS, verbose=VERBOSE,)
CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-3.5-turbo", verbose=VERBOSE)     # ChatOpenAI cannot have max_token=-1

# EMBEDDING_FUNC = OpenAIEmbeddings()
# EMBEDDING_FUNC = embedding_functions.DefaultEmbeddingFunction()
EMBEDDING_FUNC = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
