import re
from typing import List
from langchain.docstore.document import Document
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Chroma
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
embeddings = OpenAIEmbeddings()
# CHROMA_CLIENT.delete_collection("law-docs")
# CHROMA_CLIENT.reset()
# exit()

def load_directory(path:str) -> List[Document]:
    docs:List[Document] = []
    loader = DirectoryLoader(path, glob='**/*.doc', loader_cls=Docx2txtLoader, silent_errors=True)
    docs.extend(loader.load())
    loader = DirectoryLoader(path, glob='**/*.docx', loader_cls=Docx2txtLoader, silent_errors=True)
    docs.extend(loader.load())
    # # loader = DirectoryLoader(path, glob='**/*.pdf', loader_cls=PyPDFLoader, silent_errors=True)
    loader = PyPDFDirectoryLoader(path)
    docs.extend(loader.load())
    return docs

# collection = CHROMA_CLIENT.get_collection("law-docs", embedding_function=embeddings)
collection = CHROMA_CLIENT.get_or_create_collection("law-docs")
# exit()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
dir_docs = load_directory("./files")
texts = text_splitter.split_documents(dir_docs)
# collection = Chroma.from_documents(documents=texts, embedding=embeddings)

print("docs len=", len(texts))
# print(texts[1].metadata)

for i,t in enumerate(texts, start=1):
    src = re.findall('files\/(.+)\.',t.metadata.get("source"))[0][:-1]
    print(src)
    collection.add(
    # collection.upsert(
        embeddings=embeddings.embed_query(t.page_content),
        documents=[t.page_content],
        metadatas=[{"source": src, "类别":"法律条文"}],
        ids=[src+'-'+str(i)]
    )
print(collection.peek())

# docsearch = Chroma.from_texts(texts, embeddings, metadatas=[{"source": f"Text chunk {i} of {len(texts)}"} for i in range(len(texts))], persist_directory="db")
# docsearch.persist()
# docsearch = None