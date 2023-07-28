import streamlit as st, re, docx, langchain
# from chromadb.config import Settings
from langchain import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
# from langchain.callbacks import get_openai_callback

from config import CHROMA_WEB_CLIENT, EMBEDDING_FUNC
from docstore import docstoreReactAgent, retrievalQAChain
from ocr import load_pdf

def main():
    st.set_page_config("Open AI")
    st.header("初始化项目")
    files = st.file_uploader("上传文件", accept_multiple_files=True, type=["pdf","docx","txt"])
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100, separators=['.', '\n\n', '\n', ',', '。','，'])

    if len(files) > 0:
        text = ""
        chunks = []
        for f in files:
            if re.search("\.pdf$", f.name):
                text += load_pdf(f.getvalue())
            elif re.search("\.docx$", f.name):
                for line in docx.Document(f).paragraphs:
                    text += "\n"+line.text
            elif re.search("\.txt$", f.name):
                for line in f:
                    text += line

            chunks.extend(text_splitter.split_text(text))

        print("num of chunks=", len(chunks))

        file_db = Chroma.from_texts(chunks, embedding=EMBEDDING_FUNC)
        # Upload all the docs to 检查案件名称，答辩人，辩护律师

        res = retrievalQAChain(file_db, "案件名称？")
        res += retrievalQAChain(file_db, "原告？")
        res += retrievalQAChain(file_db, "被告？")
        res += retrievalQAChain(file_db, "主审法官？")
        res += retrievalQAChain(file_db, "案情简介？")
        # res = retrievalQAChain(file_db, "从上传的第三方文件中，查询下列信息，并且用Json格式输出中文答案。1、案件名称，2、原告，3、被告，、主审法院，4、主审法官，5、案情简介", True)
        # res = docstoreReactAgent(file_db, "案件名称是什么？全部问题使用中文问答问题。", True)     # does not work
        # docs = file_db.similarity_search("案件名称")
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