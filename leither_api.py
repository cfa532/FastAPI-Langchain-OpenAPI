import hprose

client = hprose.HttpClient('http://localhost:8080/webapi/')
print(client.GetVar("", "ver"))
ppt = client.GetVarByContext("", "context_ppt")
reply = client.Login(ppt)
print("reply", reply)
print("sid  ", reply.sid)
print("uid  ", reply.uid)

def verifyIdentiry(username, passwd):
    client.
    return True