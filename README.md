1. Install nginx. Copy nginx.conf to /etc/nginx/conf.d and move ssl certificates to /ssl
2. Setup Python venv and install all dependencies.
3. Setup Leither instance as database engine.


##################################################
1. OCR设置
输出环境变量
TESSDATA_PREFIX=/tessdata文件所在目录。其中eng数据是必须的，否则ocr无法启动。缺省选择chi-sim作为识别语言。如果文件用了不同的语言，需要分别处理。

2. brew install poppler
brew install tesseract

Law documents may update from time to time. How to keep up with it and always have valid information in the collections.
metadata includes { source: file name, category: 司法解释, valid: 1, timestamp: a number}