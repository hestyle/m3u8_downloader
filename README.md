# m3u8_downloader
m3u8（HLS流）下载，实现了AES解密、合并、多线程、批量下载

# 1、开车姿势
## 1.1、导入源码中依赖的库（Python3）
     beautifulsoup4、m3u8、pycryptodome、requests、threadpool
## 1.2、根据实际情况修改下载配置
```python
###############################配置信息################################
# m3u8链接批量输入文件(必须是utf-8编码)
m3u8InputFilePath = "D:/input/m3u8_input.txt"
# 设置视频保存路径
saveRootDirPath = "D:/output"
# 下载出错的m3u8保存文件
errorM3u8InfoDirPath = "D:/output/error.txt"
# m3u8文件、key文件下载尝试次数，ts流默认无限次尝试下载，直到成功
m3u8TryCountConf = 10
# 线程数（同时下载的分片数）
processCountConf = 50
######################################################################
```
# 2、车速展示
![image](https://user-images.githubusercontent.com/44233477/95989627-1743d180-0e5d-11eb-981a-ab2917ee9263.png)
![image](https://user-images.githubusercontent.com/44233477/95989823-570ab900-0e5d-11eb-81bf-9c9c2d984496.png)
![image](https://user-images.githubusercontent.com/44233477/95989904-71449700-0e5d-11eb-946f-280839da3b47.png)
# 3、开车规范
## 3.1、注意身体！注意身体！注意身体！
## 3.2、以上源码仅作为Python技术学习、交流之用，切勿用于其他任何可能造成违法场景，否则后果自负！
