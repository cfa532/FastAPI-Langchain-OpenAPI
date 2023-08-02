# Chroma and LangChain Demo
This repository contains code and resources for demonstrating the power of Chroma and LangChain for asking questions about your own data. 
The demo showcases how to pull data from the English Wikipedia using their API. The project also demonstrates how to vectorize data in chunks and get embeddings using OpenAI embeddings model.

We then use [LangChain](https://github.com/hwchase17/langchain) to ask questions based on our data which is vectorized using OpenAI embeddings model. 
I used [Chroma](https://github.com/chroma-core/chroma) a database for storing and querying vectorized data.

## Getting Started
To get started with the demo, you will need to have Python (I use Python 3.8) installed on your machine. You will also need to install the required Python packages by running the following command:
`pip install -r requirements.txt`

 **You can change the `_ALGORITHMS` constant to whatever you want to query other topics on Wikipedia.**

From there on you can simply run `wikipedia.py` which generates the text file which will be vectorized and stored in the database.
You need to use the name of the created textfile in the `ask_wikipedia.py` file.

Now you can run `ask_wikipedia.py`.

**Simply change the `print(genie.ask("Can you tell me the formula for Linear Regression?"))` in the `ask_wikipedia.py` file to whatever question you want to ask.**


## Video

I also created a video to demonstrate the demo. 
[![Screenshot](https://i.ibb.co/LCzVkff/embedding-vid.jpg)](https://youtu.be/ytt4D5br6Fk)

1. OCR设置
输出环境变量
TESSDATA_PREFIX=/tessdata文件所在目录。其中eng数据是必须的，否则ocr无法启动。缺省选择chi-sim作为识别语言。如果文件用了不同的语言，需要分别处理。

2. brew install poppler
brew install tesseract