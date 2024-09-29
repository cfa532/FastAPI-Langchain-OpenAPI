# Contents
The content in Main branch is way outdated. The two meaningful branches are Secretari and AI-Chat.

## Secretari
FastAPI for authentication and authroization, Langchain for AI interface. This one is for 

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

Law documents may update from time to time. How to keep up with it and always have valid information in the collections.
metadata includes { source: file name, category: 司法解释, valid: 1, timestamp: a number}
