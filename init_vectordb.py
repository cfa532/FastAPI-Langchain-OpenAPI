from langchain.text_splitter import CharacterTextSplitter, RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from config import CHROMA_CLIENT, EMBEDDING_FUNC, print_object
from chromadb.api.models.Collection import Collection
import os, shutil, docx, re
from werkzeug.datastructures import FileStorage
from io import BytesIO
from ocr import load_pdf

def upsert_text(collection_name:str, text:str, filename:str, case_name="law", chunk_size=1000, chunk_overlap=100):
    # from langchain.text_splitter import NLTKTextSplitter
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=['.', '\n\n', '\n', ',', '。','，'])
    # text_splitter = NLTKTextSplitter()
    try:
        collection = CHROMA_CLIENT.get_or_create_collection(collection_name)
        chunks = text_splitter.split_text(text)
        print("chunks:", len(chunks))
        pattern = re.compile(r'[\n\r\t]')   # necessary to process chinese 换行符
        for i,t in enumerate(chunks, start=1):
            txt = re.sub(pattern, ' ', t)
            print(txt)
            collection.upsert(
                embeddings = [EMBEDDING_FUNC.embed_query(txt)],  # if using OpenAIEmbedding, do not need [0]
                documents = [txt],
                # for law case, the id is mid of the case. for laws, it is "law" which won't conflict with mid
                metadatas = [{"source": filename, "doc_type":case_name}],
                ids = [filename+'-'+str(i)]
            )
    except Exception as e:
        print("upload error on ", type(e))
        print(e.args)
        print(e)
        raise SystemExit(1)
    return "success"

def init_case_store(collection_name: str, dir:str, doc_type="law"):
    from os import walk
    if not os.path.exists(dir + "loaded"): os.mkdir(dir + "loaded")

    # vectorstore = Chroma(collection_name=collection_name,
    #                      embedding_function=EMBEDDING_FUNC,
    #                      client=CHROMA_CLIENT
    #                      )

    # load all files in a folder
    for fn in next(walk(dir), (None, None, []))[2]:  # [] if no file
        text = ""
        if re.search("\.pdf$", fn):
            print("Reading:", fn)
            fo = open(dir+fn, "rb")
            text += load_pdf(fo.read())
        elif re.search("\.docx$", fn):
            print("Reading:", fn)
            for line in docx.Document(dir+fn).paragraphs:
                text += "\n"+line.text
        elif re.search("\.txt$", fn):
            print("Reading:", fn)
            fo = open(dir+fn)
            for line in fo.readlines():
                text += line
        else:
            continue
        
        print(text[:100])
    
        # attach file name in the front and behind text. 
        upsert_text(collection_name, text, fn, doc_type)

        # move the file to other folder once it is done
        if fo: fo.close()
        shutil.move(dir+fn, dir+"loaded")

        # chunks = []
        # chunks.extend(text_splitter.split_text(text))
        # print("chunks:", len(chunks))

        # vectorstore.add_texts(chunks,     # breaks when there are many chunks, such as 53
        #                       [{"source": fn, "类别":"案例"}]*len(chunks),
        #                       list(map(lambda x:fn+'-'+str(x), list(range(1,len(chunks)+1))))
        #                       )

# Process file upload from socket client. Referred by flask service code
def extract_text(filename, filetype, filedata):
    file = FileStorage(
        stream=BytesIO(filedata), 
        filename=filename,
        content_type=filetype, 
        content_length=len(filedata)
    )
    file_ext = os.path.splitext(filename)[1]
    text = ""
    if file_ext.lower()==".pdf":
        text += load_pdf(file.read())
    elif file_ext.lower()==".docx":
        for line in docx.Document(file).paragraphs:
            text += "\n"+line.text
        # print("text=", text)
    elif file_ext.lower()==".txt":
        for line in file.read().decode('utf8'):
            # print(line)
            text += line
    print("text=", text[:100])
    return text
