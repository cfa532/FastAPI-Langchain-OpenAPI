from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from config import CHROMA_CLIENT, EMBEDDING_FUNC, print_object

# docsearch = Chroma.from_texts(texts, embeddings, metadatas=[{"source": f"Text chunk {i} of {len(texts)}"} for i in range(len(texts))], persist_directory="db")

def upsert_text(collection_name:str, text:str, filename:str):
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    try:
        collection = CHROMA_CLIENT.get_or_create_collection(collection_name, embedding_function=EMBEDDING_FUNC)
        texts = text_splitter.split_text(text)
        for i,t in enumerate(texts, start=1):
            collection.upsert(
                # embeddings = [EMBEDDING_FUNC(t)[0]],  # if using OpenAIEmbedding, do not need [0]
                documents = [t],
                metadatas = [{"source": filename, "类别":"案列"}],
                ids = [filename+'-'+str(i)]
            )
    except Exception:
        print("upload error on ", Exception)
    return "success"

def init_case_store(collection_name: str, dir:str):
    import docx, re
    from ocr import load_pdf
    from os import walk
    import PyPDF2
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    # db = CHROMA_CLIENT.get_or_create_collection(collection_name)
    vectorstore = Chroma(collection_name=collection_name,
                         embedding_function=EMBEDDING_FUNC,
                         client=CHROMA_CLIENT
                         )

    # load all files in a folder
    for fn in next(walk(dir), (None, None, []))[2]:  # [] if no file
        text = ""
        if re.search("\.pdf$", fn):
            print("Reading:", fn)
            text += load_pdf(open(dir+fn, 'rb').read())
        elif re.search("\.docx$", fn):
            print("Reading:", fn)
            for line in docx.Document(dir+fn).paragraphs:
                text += "\n"+line.text
        elif re.search("\.txt$", fn):
            print("Reading:", fn)
            for line in open(dir+fn).readlines():
                text += line
        else:
            continue
        
        print(text[:100])
        chunks = []
        chunks.extend(text_splitter.split_text(text))
        print("chunks:", len(chunks))
        vectorstore.add_texts(chunks,
                              [{"source": fn, "类别":"案例"}]*len(chunks),
                              list(map(lambda x:fn+'-'+str(x), list(range(1,len(chunks)+1))))
                              )

        # for i, t in enumerate(chunks, start=1):
        #     db.add(
        #         embeddings=[EMBEDDING_FUNC.embed_query(t)],
        #         documents=[t],
        #         metadatas=[{"source": fn, "类别":"案例"}],
        #         ids=[fn+'-'+str(i)]
        #     )

init_case_store("5ACIVM0ewbQdqpgVtXhO3PW9QsJ", "/Users/cfa532/Downloads/aji/")