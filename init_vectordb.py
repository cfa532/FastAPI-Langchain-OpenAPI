from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain.document_loaders.text import TextLoader
from langchain.vectorstores import Chroma
from config import CHROMA_CLIENT, EMBEDDING_FUNC

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
# docsearch = Chroma.from_texts(texts, embeddings, metadatas=[{"source": f"Text chunk {i} of {len(texts)}"} for i in range(len(texts))], persist_directory="db")

def upsert_text(collection_name:str, text:str, filename:str):
    collection = CHROMA_CLIENT.get_or_create_collection(collection_name, embedding_function=EMBEDDING_FUNC)
    texts = text_splitter.split_text(text)
    for i,t in enumerate(texts, start=1):
        collection.upsert(
            # embeddings = [EMBEDDING_FUNC(t)[0]],  # if using OpenAIEmbedding, do not need [0]
            documents = [t],
            metadatas = [{"source": filename, "类别":"案列"}],
            ids = [filename+'-'+str(i)]
        )
    return "success"
