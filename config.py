import chromadb
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import SentenceTransformerEmbeddings
# from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
# from langchain.embeddings.openai import OpenAIEmbeddings
# from langchain.embeddings import HuggingFaceInstructEmbeddings

# Init environment variables in .env file
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()

VERBOSE = True

"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""

CHROMA_CLIENT = chromadb.HttpClient(host='localhost', port=8000)
LAW_COLLECTION_NAME = "law-docs"     # collection name for all public laws and regulations
cols = CHROMA_CLIENT.list_collections()
print(cols)
# cols = CHROMA_CLIENT.get_collection("5ACIVM0ewbQdqpgVtXhO3PW9QsJ")
# print(cols.peek(1))
# CHROMA_CLIENT.reset()

LLM = OpenAI(temperature=0, model="gpt-4", max_tokens=-1, verbose=VERBOSE,)
CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", max_tokens=512, verbose=VERBOSE)     # ChatOpenAI cannot have max_token=-1

# EMBEDDING_FUNC = OpenAIEmbeddings()
# EMBEDDING_FUNC = DefaultEmbeddingFunction()
# EMBEDDING_FUNC = HuggingFaceInstructEmbeddings()
EMBEDDING_FUNC = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

def print_object(obj):
    pprint(vars(obj))
