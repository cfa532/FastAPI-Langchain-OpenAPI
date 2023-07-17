import langchain
from langchain import OpenAI, LLMChain, PromptTemplate, SerpAPIWrapper, LLMMathChain, GoogleSearchAPIWrapper
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory, ConversationBufferWindowMemory
from langchain.agents import load_tools, initialize_agent, Tool, AgentType
from langchain.callbacks import get_openai_callback

from langchain.agents.agent_toolkits import create_python_agent
from langchain.tools.python.tool import PythonAstREPLTool
from langchain.python import PythonREPL

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def main():
    # st.set_page_config(page_title="OpenAI Chat")
    # st.header("Ask a question 💬")
    # user_question = st.text_input("Input text here....")
    user_question="What is the 25% of 300?"
    user_question="背诵随便一首唐诗"
    user_question = "杭州今日的天气。用中文回答"
    llm = ChatOpenAI(temperature=0)
    llm2 = OpenAI(temperature=0)

    if user_question:
        search = SerpAPIWrapper(params={
            "engine": "google",
        })
        llm_math_chain = LLMMathChain.from_llm(llm=llm, verbose=True)
        tools = [
            Tool(
                name="search", 
                func=search.run,
                description="useful when you need to answer questions about current events. You should ask pointed questions"
            ),
            # Tool(
            #     name="Calculator",
            #     func=llm_math_chain.run,
            #     description="useful when you need to answer math questions"
            # )
        ]
        tools.extend(load_tools(["llm-math"], llm=llm))

        agent = initialize_agent(
            tools=tools,
            llm=llm2,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,      # only one works
            memory=ConversationBufferMemory(memory_key="chat_history"),
            handle_parsing_errors=True,
            verbose=True
        )
        # agent.agent.llm_chain.prompt. += "Always reply in Chinese"
        langchain.debug = True
        print(agent.run(user_question))
        langchain.debug = False

        # with get_openai_callback() as cb:
        #     response = agent.run(user_question)
        #     st.write(response)

main()

# template = """Assistant is a large language model trained by OpenAI.

# Assistant is designed to be able to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. As a language model, Assistant is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.

# Assistant is constantly learning and improving, and its capabilities are constantly evolving. It is able to process and understand large amounts of text, and can use this knowledge to provide accurate and informative responses to a wide range of questions. Additionally, Assistant is able to generate its own text based on the input it receives, allowing it to engage in discussions and provide explanations and descriptions on a wide range of topics.

# Overall, Assistant is a powerful tool that can help with a wide range of tasks and provide valuable insights and information on a wide range of topics. Whether you need help with a specific question or just want to have a conversation about a particular topic, Assistant is here to assist.

# {history}
# Human: {human_input}
# Assistant:"""

# prompt = PromptTemplate(input_variables=["history", "human_input"], template=template)
# chat_chain = LLMChain(
#     llm=OpenAI(temperature=0),
#     prompt=prompt,
#     verbose=True,
#     memory=ConversationBufferMemory(memory_key="chat_history", input_key="input"),
# )
# output = chat_chain.predict(
#     human_input="I want you to act as a Linux terminal. I will type commands and you will reply with what the terminal should show. I want you to only reply with the terminal output inside one unique code block, and nothing else. Do not write explanations. Do not type commands unless I instruct you to do so. When I need to tell you something in English I will do so by putting text inside curly brackets {like this}. My first command is pwd."

# )
# print(output)
