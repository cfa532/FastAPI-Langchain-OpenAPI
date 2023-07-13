import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv
load_dotenv()

CHROMA_CLIENT = chromadb.Client(Settings(chroma_api_impl="rest",
                                        chroma_server_host="localhost",
                                        chroma_server_http_port="8000"
                                    ))
