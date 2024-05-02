import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")
tokens = len(encoding.encode("你是個智能秘書。提取下述文字中的重要內容，做一份全面的摘要。新加坡直升機不對強大不知在於武力東南亞最強空中救援德國和蘇聯的裝甲部隊誰更強鋼鐵的碰撞兩個最強軍團二戰最精彩突圍戰躲避將軍的巔峰之戰也是賣身海鷹的羨慕之戰二戰前全世界對航空母艦的神鼓勵蟲蟲美國的看法是什麼的看法是什麼。"))
print(tokens)
