import os
from langchain.vectorstores import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

from langchain.callbacks.base import BaseCallbackManager as CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.chains import (
    ConversationalRetrievalChain,
    LLMChain
)
from langchain.chains.question_answering import load_qa_chain
from langchain.llms import OpenAI
from langchain.prompts.prompt import PromptTemplate


OPENAI_API_KEY = 'sk-XXXXX'
os.environ['OPENAI_API_KEY'] = "sk-XXXX"
persist_directory = 'adidas'
# we will use OpenAI as our embeddings provider
embedding = OpenAIEmbeddings()
vectordb = Chroma(persist_directory=persist_directory, embedding_function=embedding)


template = """Given the following chat history and a follow up question, rephrase the follow up input question to be a standalone question.


Chat History:\"""
{chat_history}
\"""

Follow Up Input: \"""
{question}
\"""

Standalone question:"""

condense_question_prompt = PromptTemplate.from_template(template)

template = """You are a friendly Shopping E-commerce Assistant, designed to assist with a variety of tasks related to online shopping. Assistant can answer questions, provide detailed explanations, and engage in natural-sounding conversations about various products and services available for purchase, by using the context given. The Assistant continually learns and improves, utilizing its vast knowledge base to offer accurate and informative responses. Assitant can also generate its own text to discuss, describe, and recommend products to users. Assistant can understand the question well and answer accordingly.
Context:\"""
{context}
\"""
 
Question:\"
\"""

Helpful Answer:"""

qa_prompt= PromptTemplate.from_template(template)


# define two LLM models from OpenAI
llm = OpenAI(temperature=0,model='text-davinci-003')
# llm=OpenAI()

streaming_llm = OpenAI(
    streaming=True,
    model='text-davinci-003',
    callback_manager=CallbackManager([
        StreamingStdOutCallbackHandler()]),
    verbose=True,
    temperature=0.2,
    max_tokens=150
)
# use the LLM Chain to create a question creation chain
question_generator = LLMChain(
    llm=llm,
    prompt=condense_question_prompt
)

# use the streaming LLM to create a question answering chain
doc_chain = load_qa_chain(
    llm=streaming_llm,
    chain_type="stuff",
    prompt=qa_prompt
)


chatbot = ConversationalRetrievalChain(
    retriever=vectordb.as_retriever(),
    combine_docs_chain=doc_chain,
    question_generator=question_generator,
    
)

# create a chat history buffer
chat_history = []

# gather user input for the first question to kick off the bot
question = input("Hi! What are you looking for today?")

# keep the bot running in a loop to simulate a conversation
while True:
    result = chatbot(
        {"question": question, "chat_history": chat_history}
    )
    print("\n")
    chat_history.append((result["question"], result["answer"]))
    question = input()