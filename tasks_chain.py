import langchain
from config import CHROMA_CLIENT, MAX_TOKENS
from langchain import OpenAI
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import ConstitutionalChain
from chromadb.utils import embedding_functions

embedding_function = OpenAIEmbeddings()
db_law = Chroma(client=CHROMA_CLIENT, collection_name="law-docs", embedding_function=embedding_function)

llm = OpenAI(temperature=0)
qa = RetrievalQA.from_chain_type(llm, chain_type="map_reduce", retriever=db_law.as_retriever())
query = "2018年9月19日，答辩人与原告就案涉店铺承租主体变更达成一致并签订《店铺租赁合同》主体变更协议，各方同意将案涉店铺的承租方由答辩人变更为阿家公司。因主体变更协议签订当时，阿家公司尚未注册成立，故双方在协议中进一步明确了在阿家公司取得营业执照之前，答辩人仍需作为共同承租人与阿家公司承担共同连带责任，但自阿家公司取得营业执照之日起，则原合同承租方的权利义务全部由阿家公司独自承担。而阿家公司已经于2018年10月12日取得营业执照，故自2018年10月12日之后的债务应该由阿家公司独自承担，于答辩人无关。\n\n"

query += "根据案件内容，列出回应的要点提纲，不要超过五条。用中文回答。"
print(qa)
# langchain.debug = True
task_list = qa.run(query)
# langchain.debug = False
print(task_list)

# Get human input to confirm the list
