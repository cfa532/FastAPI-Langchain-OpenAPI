import chromadb
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.embeddings import SentenceTransformerEmbeddings
# from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
# from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.embeddings import HuggingFaceInstructEmbeddings

# Init environment variables in .env file
from pprint import pprint
from dotenv import load_dotenv
load_dotenv()

VERBOSE = True

"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""

CHROMA_CLIENT = chromadb.HttpClient(host='192.168.0.5', port=8000)
LAW_COLLECTION_NAME = "law-docs"     # collection name for all public laws and regulations
cols = CHROMA_CLIENT.list_collections()
print(cols)
# cols = CHROMA_CLIENT.get_collection("2TQDMb-Ug71i_iFIGCc-V7XnKv0")
# print(cols.peek(1))
# CHROMA_CLIENT.reset()
# CHROMA_CLIENT.delete_collection("law-docs")

LLM = OpenAI(temperature=0, model="gpt-3.5-turbo", max_tokens=-1, verbose=VERBOSE,)
CHAT_LLM = ChatOpenAI(temperature=0, model="gpt-4", max_tokens=1024, verbose=VERBOSE)     # ChatOpenAI cannot have max_token=-1

# EMBEDDING_FUNC = OpenAIEmbeddings()
# EMBEDDING_FUNC = DefaultEmbeddingFunction()
# EMBEDDING_FUNC = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
# EMBEDDING_FUNC = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")
EMBEDDING_FUNC = HuggingFaceInstructEmbeddings(model_name="hkunlp/instructor-xl")

def print_object(obj):
    pprint(vars(obj))

def llm_chain(query:str, llm=CHAT_LLM):
    return LLMChain(llm=llm, prompt=PromptTemplate.from_template("{query}"),
        # verbose=VERBOSE
    ).run(query)

class LegalCase:
    def __init__(self, lc):
        self.mid = lc.mid           # Memei id of the user obj
        self.id = lc.id             # id of the case
        self.title = lc.title
        self.brief = lc.title
        self.plaintiff = lc.plaintiff
        self.defendant = lc.defendant
        self.attorney = lc.attorney
        self.judge = lc.judge