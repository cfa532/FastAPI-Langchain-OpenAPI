from typing import List
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
# from langchain.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.document_loaders.word_document import Docx2txtLoader
from langchain.document_loaders.directory import DirectoryLoader
from langchain.document_loaders.text import TextLoader
from langchain.document_loaders.csv_loader import CSVLoader
from langchain.document_loaders.json_loader import JSONLoader
from langchain.document_loaders.pdf import PyPDFLoader, PyPDFDirectoryLoader
from dotenv import load_dotenv
load_dotenv()

from config import CHROMA_CLIENT

def load_directory(path:str) -> List[Document]:
    docs:List[Document] = []
    loader = DirectoryLoader(path, glob='**/*.doc', loader_cls=Docx2txtLoader, silent_errors=True)
    docs.extend(loader.load())
    loader = DirectoryLoader(path, glob='**/*.docx', loader_cls=Docx2txtLoader, silent_errors=True)
    docs.extend(loader.load())
    # loader = DirectoryLoader(path, glob='**/*.pdf', loader_cls=PyPDFLoader, silent_errors=True)
    loader = PyPDFDirectoryLoader(path)
    docs.extend(loader.load())
    return docs

# embeddings = OpenAIEmbeddings()
collection = CHROMA_CLIENT.get_or_create_collection("law-docs")
# print(collection.peek())
# exit()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
dir_docs = load_directory("./files")
texts = text_splitter.split_documents(dir_docs)
print(len(texts))
print(texts[1].metadata)

for i,t in enumerate(texts, start=1):
    collection.upsert(
        documents=[t.page_content],
        metadatas=[t.metadata],
        ids=[t.metadata.get("source")+str(i)]
    )

# docsearch = Chroma.from_texts(texts, embeddings, metadatas=[{"source": f"Text chunk {i} of {len(texts)}"} for i in range(len(texts))], persist_directory="db")
# docsearch.persist()
# docsearch = None