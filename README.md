# Contents
The content in Main branch is way outdated. The two meaningful branches are Secretari and AI-Chat.

## Secretari
FastAPI Python backend for authentication and authroization, Langchain for AI interface. This one is for iOS application Bounny. It handles anonymous service, user registration and authentication.

More importantly, there are python code that handles Serverside messaging from Applestore server. All user data and application data are stored in Leither database.

## AI-Chat
FastAPI and Python backend for a user friendly OpenAI chatbox. The python part deliver user queries OpenAI. Langchain is used to wrap OpenAI. It calculates token usage correctly.

1. OCR设置
输出环境变量
TESSDATA_PREFIX=/tessdata文件所在目录。其中eng数据是必须的，否则ocr无法启动。缺省选择chi-sim作为识别语言。如果文件用了不同的语言，需要分别处理。

2. brew install poppler
brew install tesseract

Law documents may update from time to time. How to keep up with it and always have valid information in the collections.
metadata includes { source: file name, category: 司法解释, valid: 1, timestamp: a number}
