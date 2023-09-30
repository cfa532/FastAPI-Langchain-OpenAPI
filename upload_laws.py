import sys
from init_vectordb import init_law_db

# 第一个参数是doc_type，比如 司法解释；第二个参数是原司法文件所在目录
print("命令行参数", sys.argv[1:])
init_law_db(sys.argv[1], sys.argv[2])