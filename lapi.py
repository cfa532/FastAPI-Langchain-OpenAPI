import hprose
import streamlit as st


class LApi:
    sid = ""
    uid = ""
    #hprose.Client
    client = None
    
    def __init__(self, url):
        self.client = hprose.HttpClient(url)
        ppt = self.client.GetVarByContext("", "context_ppt")
        reply = self.client.Login(ppt)
        self.sid = reply.sid
        self.uid = reply.uid

    def bytes2Ipfs(self, bytesdata):
        mmsid = self.client.MFOpenTempFile(self.sid)
        self.client.MFSetData(mmsid, bytesdata, 0)
        cid = self.client.MFTemp2Ipfs(mmsid, "")
        return cid

    def bytes2url(self, bytesdata):
        cid = self.bytes2Ipfs(bytesdata)
        return "http://vzhan.cn/ipfs/" + cid

@st.cache_resource
def get_lapi() -> LApi:
    print("get_lapi ok")
    lapi = LApi("http://127.0.0.1:4800/webapi/")
    return lapi


#挂接工具函数
from tool_registry import register_tool

@register_tool
def get_ver(
) -> str:
    """
    Get the current version for Leither node
    """

    import requests
    try:
        resp = requests.get("http://127.0.0.1:4800/getvar?name=ver", timeout=10)
        resp.raise_for_status()
        resp = resp.json()
        print("resp", resp)
        ret = resp
    except:
        import traceback
        ret = "Error encountered while fetching weather data!\n" + traceback.format_exc()

    return str(ret)


@register_tool
def swarmaddrs(
) -> str:
    """
    Return nearby Leither nodes
    """

    import requests
    try:
        
        resp = get_lapi().client.SwarmAddrs("")
        # print("resp", resp)
        # resp = requests.get("http://127.0.0.1:4800/getvar?name=ver", timeout=10)
        # resp.raise_for_status()
        # resp = resp.json()
        # arr_str = ''.join(map(str, resp)) #这里只有id
        # print("arr_str", arr_str)  # 输出：12345

        # print("resp", resp)
        # ret = resp
        ret = ""
        # resp是一个字典，轮询显示resp中的内容
        i=1
        for nodeid, addrs in resp.items():
            ret = ret + "  \n节点"+ str(i) +":" +nodeid+ ""
            i+=1
        # ret = ret + "\naddress:" + value + "\n"
        # print("nodeid", key)
        # print( "addrs", addrs)
            for addr in addrs:
            # print(addr)
                ret = ret + "\taddrs:" + addr + "  \n"
        ret = ret + "共计"+ str(i-1) +"个节点" + "  \n"
        # print(key, value)
        print("ret=\n", ret)    

    except:
        import traceback
        ret = "Error encountered while fetching weather data!\n" + traceback.format_exc()

    return str(ret)


def main():

    lapi = LApi("http://127.0.0.1:4800/webapi/")

    #测试SwarmAddrs
    # resp = lapi.client.SwarmAddrs("")
    # ret = ""
    # # print("resp", resp)
    # # resp是一个字典，轮询显示resp中的内容
    # for key, addrs in resp.items():
    #     ret = ret + key+ "\n"
    #     # ret = ret + "\naddress:" + value + "\n"
    #     # print("nodeid", key)
    #     # print( "addrs", addrs)
    #     for addr in addrs:
    #         # print(addr)
    #         ret = ret + "\t" + addr + "\n"
    #     # print(key, value)
    # print("ret=\n", ret)    
    
    #测试文件上传
    # data = b'bytes data bytes2ipfs'
    # print("data", data)
    # cid = lapi.bytes2Ipfs(data)
    # print("cid", cid)


    # 	#打开一个临时文件
	# mmsid = lapi.client.MFOpenTempFile(lapi.sid)
	# print("mmsid", mmsid)
	# #写入文件
 	# # strObj = "setobj => ipfsfile"
	# # client.MFSetObject(mmsid, strObj)
	# data = b'bytes data'
	# lapi.client.MFSetData(mmsid, data, 0)
 
	# #转为ipfs文件
	# cid = lapi.client.MFTemp2Ipfs(mmsid, "")
	# print("cid", cid)

    # data = b'bytes data bytes2ipfs'
 
if __name__ == '__main__':
	main()
 
