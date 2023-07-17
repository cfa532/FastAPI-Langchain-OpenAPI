import streamlit as st, re, docx, chromadb
from chromadb.config import Settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.callbacks import get_openai_callback

from config import CHROMA_WEB_CLIENT, EMBEDDING_FUNC
from docstore import docstoreReactAgent
from ocr import load_pdf, load_doc

def main():
    st.set_page_config("Upload files")
    st.header("Upload")
    files = st.file_uploader("Upload your files", accept_multiple_files=True, type=["pdf","docx","txt"])
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])

    if len(files) > 0:
        text = ""
        chunks = []
        for f in files:
            if re.search("\.pdf$", f.name):
                text += load_pdf(f.getvalue())
            elif re.search("\.docx$", f.name):
                d = docx.Document(f)
                for line in d.paragraphs:
                    text += "\n"+line.text
            # elif re.search("\.doc$", f.name):
                # text = load_doc(f.getvalue())
            elif re.search("\.txt$", f.name):
                for line in f:
                    text += line
            chunks.extend(text_splitter.split_text(text))
        print("num of chunks=", len(chunks))

        # 检查案件名称，答辩人，辩护律师
        file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
        res = docstoreReactAgent(file_db, "案件名称是什么？")

        # docs = file_db.similarity_search("案件名称")
        # print(docs[0])
        # chain = load_qa_chain(llm=OpenAI())
        # res = chain.run(input_documents=docs, question="案件名称")
        print(res)
    
        # if res != "I don't know." and res != "我不知道。":
        #     col = chroma_dir_client.get_or_create_collection(str(hash(res)))
        #     for i, t in enumerate(chunks, start=1):
        #         col.add(
        #             embeddings = OpenAIEmbeddings().embed_query(t),
        #             documents=[t],
        #             metadatas=[{"source": res, "类别":"案例"}],
        #             ids=[res+'-'+str(i)]
        #         )

if __name__ == "__main__":
    main()