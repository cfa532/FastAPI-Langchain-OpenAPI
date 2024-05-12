import asyncio
import websockets
import ssl, json

message = '{"parameters":{"client":"mobile","llm":"openai","temperature":"0.0","model":"gpt-4-turbo"},"input":{"prompt":"你是個智能秘書。 提取下述文字中的重要內容，做一份全面的备忘录。輸出格式採用 JSON 序列，每個JSON項格式為 {\"id\": 1, \"title\": \"Item 1\", \"isChecked\": false}。JSON序列格式為\n[ {\"id\": 1, \"title\": \"Item 1\", \"isChecked\": false},\n{\"id\": 2, \"title\": \"Item 2\", \"isChecked\": true},\n{\"id\": 3, \"title\": \"Item 3\", \"isChecked\": false} ]","rawtext":"並且馬斯克抵達中國後特斯拉官方微博先後兩次發生提到了加速自動駕駛技術落地但對於市場近期關注的特斯拉潤滑的消息特斯拉方面今日回應成目前FED入華還沒有時間表不過值得注意的是昨日中國汽車工業協會國家計算機網絡應急技術處理協調租金發佈關於汽車數據處理事項安全要求檢測情況的通報第一批其中指出特斯拉上海車長正生產的車行全部符合合規要求是唯一議價符合合規要求的外資及企業。"}}'

event = json.loads(message)
print(event["input"]["prompt"])
