import chromadb
from chromadb.utils import embedding_functions
from langchain.llms import OpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chat_models import ChatOpenAI
from chromadb.config import Settings

# Init environment variables in .env file
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()

MAX_TOKENS = -1
VERBOSE = True

"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""

CHROMA_CLIENT = chromadb.HttpClient(host='localhost', port=8000)

LLM = OpenAI(temperature=0, model="gpt-4", max_tokens=MAX_TOKENS, verbose=VERBOSE,)
CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", max_tokens=MAX_TOKENS, verbose=VERBOSE)     # ChatOpenAI cannot have max_token=-1

# EMBEDDING_FUNC = OpenAIEmbeddings()
# EMBEDDING_FUNC = embedding_functions.DefaultEmbeddingFunction()
EMBEDDING_FUNC = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

def print_object(obj):
    pprint(vars(obj))
