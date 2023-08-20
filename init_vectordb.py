from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from config import CHROMA_CLIENT, EMBEDDING_FUNC, print_object
from chromadb.api.models.Collection import Collection

def upsert_text(collection:Collection, text:str, filename:str):
    # text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    from langchain.text_splitter import NLTKTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])
    # text_splitter = NLTKTextSplitter()
    try:
        chunks = text_splitter.split_text(text)
        print("chunks:", len(chunks))
        for i,t in enumerate(chunks, start=1):
            collection.upsert(
                embeddings = [EMBEDDING_FUNC.embed_query(t)],  # if using OpenAIEmbedding, do not need [0]
                documents = [t],
                metadatas = [{"source": filename, "类别":"案列"}],
                ids = [filename+'-'+str(i)]
            )
    except Exception as e:
        print("upload error on ", type(e))
        print(e.args)
        print(e)
        raise SystemExit(1)
    return "success"

def init_case_store(collection_name: str, dir:str):
    import docx, re
    from ocr import load_pdf
    from os import walk

    # vectorstore = Chroma(collection_name=collection_name,
    #                      embedding_function=EMBEDDING_FUNC,
    #                      client=CHROMA_CLIENT
    #                      )

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
    
        cols = CHROMA_CLIENT.get_or_create_collection(collection_name)
        # attach file name in the front and behind text. 
        upsert_text(cols, fn+"。 "+text+"。 "+fn, fn)

        # chunks = []
        # chunks.extend(text_splitter.split_text(text))
        # print("chunks:", len(chunks))

        # vectorstore.add_texts(chunks,     # breaks when there are many chunks, such as 53
        #                       [{"source": fn, "类别":"案例"}]*len(chunks),
        #                       list(map(lambda x:fn+'-'+str(x), list(range(1,len(chunks)+1))))
        #                       )


# init_case_store("5ACIVM0ewbQdqpgVtXhO3PW9QsJ", "/Users/cfa532/Downloads/aji/")
init_case_store("huggingface", "/Users/cfa532/Downloads/aji/")
# init_case_store("law-docs", "/Users/cfa532/Downloads/aji/")