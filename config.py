import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
load_dotenv()

"""The maximum number of tokens to generate in the completion.
    -1 returns as many tokens as possible given the prompt and
    the models maximal context size."""
MAX_TOKENS = -1

CHROMA_WEB_CLIENT = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="localhost",
                                        chroma_server_http_port="8000"
                                    ))
