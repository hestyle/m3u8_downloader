# UTF-8
# author hestyle
# desc 必须在终端直接执行，不能在pycharm等IDE中直接执行，否则看不到动态进度条效果

import os
import sys
import m3u8
import time
import requests
import traceback
import threadpool
from Crypto.Cipher import AES

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
}

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


# 全局变量
# 全局线程池
taskThreadPool = None
# 当前下载的m3u8 url
m3u8Url = None
# url前缀
rootUrlPath = None
# title
title = None
# ts count
sumCount = 0
# 已处理的ts
doneCount = 0
# cache path
cachePath = saveRootDirPath + "/cache"
# log path
logPath = cachePath + "/log.log"
# log file
logFile = None
# download bytes(0.5/1 s)
downloadedBytes = 0
# download speed
downloadSpeed = 0

# 1、下载m3u8文件
def getM3u8Info():
    global m3u8Url
    global logFile
    global rootUrlPath
    tryCount = m3u8TryCountConf
    while True:
        if tryCount < 0:
            print("\t{0}下载失败！".format(m3u8Url))
            logFile.write("\t{0}下载失败！".format(m3u8Url))
            return None
        tryCount = tryCount - 1
        try:
            response = requests.get(m3u8Url, headers=headers, timeout=20)
            if response.status_code == 301:
                nowM3u8Url = response.headers["location"]
                print("\t{0}重定向至{1}！".format(m3u8Url, nowM3u8Url))
                logFile.write("\t{0}重定向至{1}！\n".format(m3u8Url, nowM3u8Url))
                m3u8Url = nowM3u8Url
                rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
                continue
            expected_length = int(response.headers.get('Content-Length'))
            actual_length = len(response.content)
            if expected_length > actual_length:
                raise Exception("m3u8下载不完整")
            print("\t{0}下载成功！".format(m3u8Url))
            logFile.write("\t{0}下载成功！".format(m3u8Url))
            rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
            break
        except:
            print("\t{0}下载失败！正在重试".format(m3u8Url))
            logFile.write("\t{0}下载失败！正在重试".format(m3u8Url))
    # 解析m3u8中的内容
    m3u8Info = m3u8.loads(response.text)
    # 有可能m3u8Url是一个多级码流
    if m3u8Info.is_variant:
        print("\t{0}为多级码流！".format(m3u8Url))
        logFile.write("\t{0}为多级码流！".format(m3u8Url))
        for rowData in response.text.split('\n'):
            # 寻找响应内容的中的m3u8
            if rowData.endswith(".m3u8"):
                m3u8Url = m3u8Url.replace("index.m3u8", rowData)
                rootUrlPath = m3u8Url[0:m3u8Url.rindex('/')]
                return getM3u8Info()
        # 遍历未找到就返回None
        print("\t{0}响应未寻找到m3u8！".format(response.text))
        logFile.write("\t{0}响应未寻找到m3u8！".format(response.text))
        return None
    else:
        return m3u8Info

# 2、下载key文件
def getKey(keyUrl):
    global logFile
    tryCount = m3u8TryCountConf
    while True:
        if tryCount < 0:
            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
            return None
        tryCount = tryCount - 1
        try:
            response = requests.get(keyUrl, headers=headers, timeout=20, allow_redirects=True)
            if response.status_code == 301:
                nowKeyUrl = response.headers["location"]
                print("\t{0}重定向至{1}！".format(keyUrl, nowKeyUrl))
                logFile.write("\t{0}重定向至{1}！\n".format(keyUrl, nowKeyUrl))
                keyUrl = nowKeyUrl
                continue
            expected_length = int(response.headers.get('Content-Length'))
            actual_length = len(response.content)
            if expected_length > actual_length:
                raise Exception("key下载不完整")
            print("\t{0}下载成功！key = {1}".format(keyUrl, response.content.decode("utf-8")))
            logFile.write("\t{0}下载成功！ key = {1}".format(keyUrl, response.content.decode("utf-8")))
            break
        except :
            print("\t{0}下载失败！".format(keyUrl))
            logFile.write("\t{0}下载失败！".format(keyUrl))
    return response.text

# 3、多线程下载ts流
def mutliDownloadTs(playlist):
    global logFile
    global sumCount
    global doneCount
    global taskThreadPool
    global downloadedBytes
    global downloadSpeed
    taskList = []
    # 每个ts单独作为一个task
    for index in range(len(playlist)):
        dict = {"playlist": playlist, "index": index}
        taskList.append((None, dict))
    # 重新设置ts数量，已下载的ts数量
    doneCount = 0
    sumCount = len(taskList)
    printProcessBar(sumCount, doneCount, 50)
    # 构造thread pool
    requests = threadpool.makeRequests(downloadTs, taskList)
    [taskThreadPool.putRequest(req) for req in requests]
    # 等待所有任务处理完成
    while doneCount < sumCount:
        # 统计1秒钟下载的byte
        beforeDownloadedBytes = downloadedBytes
        time.sleep(1)
        downloadSpeed = downloadedBytes - beforeDownloadedBytes
    print("")
    return True

# 4、下载单个ts playlists[index]
def downloadTs(playlist, index):
    global logFile
    global sumCount
    global doneCount
    global cachePath
    global rootUrlPath
    global downloadedBytes
    succeed = False
    while not succeed:
        # 文件名格式为 "00000001.ts"，index不足8位补充0
        outputPath = cachePath + "/" + "{0:0>8}.ts".format(index)
        outputFp = open(outputPath, "wb+")
        if playlist[index].startswith("http"):
            tsUrl = playlist[index]
        else:
            tsUrl = rootUrlPath + "/" + playlist[index]
        try:
            response = requests.get(tsUrl, timeout=5, headers=headers, stream=True)
            if response.status_code == 200:
                expected_length = int(response.headers.get('Content-Length'))
                actual_length = len(response.content)
                # 累计下载的bytes
                downloadedBytes += actual_length
                if expected_length > actual_length:
                    raise Exception("分片下载不完整")
                outputFp.write(response.content)
                doneCount += 1
                printProcessBar(sumCount, doneCount, 50, isPrintDownloadSpeed=True)
                logFile.write("\t分片{0:0>8} url = {1} 下载成功！".format(index, tsUrl))
                succeed = True
        except Exception as exception:
            logFile.write("\t分片{0:0>8} url = {1} 下载失败！正在重试...msg = {2}".format(index, tsUrl, exception))
        outputFp.close()

# 5、合并ts
def mergeTs(tsFileDir, outputFilePath, cryptor, count):
    global logFile
    outputFp = open(outputFilePath, "wb+")
    for index in range(count):
        printProcessBar(count, index + 1, 50)
        logFile.write("\t{0}\n".format(index))
        inputFilePath = tsFileDir + "/" + "{0:0>8}.ts".format(index)
        if not os.path.exists(outputFilePath):
            print("\n分片{0:0>8}.ts, 不存在，已跳过！".format(index))
            logFile.write("分片{0:0>8}.ts, 不存在，已跳过！\n".format(index))
            continue
        inputFp = open(inputFilePath, "rb")
        fileData = inputFp.read()
        try:
            if cryptor is None:
                outputFp.write(fileData)
            else:
                outputFp.write(cryptor.decrypt(fileData))
        except Exception as exception:
            inputFp.close()
            outputFp.close()
            print(exception)
            return False
        inputFp.close()
    print("")
    outputFp.close()
    return True

# 6、删除ts文件
def removeTsDir(tsFileDir):
    # 先清空文件夹
    for root, dirs, files in os.walk(tsFileDir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tsFileDir)
    return True

# 7、convert to mp4（调用了FFmpeg，将合并好的视频内容放置到一个mp4容器中）
def ffmpegConvertToMp4(inputFilePath, ouputFilePath):
    global logFile
    if not os.path.exists(inputFilePath):
        print(inputFilePath + " 路径不存在！")
        logFile.write(inputFilePath + " 路径不存在！\n")
        return False
    cmd = r'.\lib\ffmpeg -i "{0}" -vcodec copy -acodec copy "{1}"'.format(inputFilePath, ouputFilePath)
    if os.system(cmd) == 0:
        print(inputFilePath + "转换成功！")
        logFile.write(inputFilePath + "转换成功！\n")
        return True
    else:
        print(inputFilePath + "转换失败！")
        logFile.write(inputFilePath + "转换失败！\n")
        return False

# 8、模拟输出进度条(默认不打印网速)
def printProcessBar(sumCount, doneCount, width, isPrintDownloadSpeed=False):
    global downloadSpeed
    precent = doneCount / sumCount
    useCount = int(precent * width)
    spaceCount = int(width - useCount)
    precent = precent*100
    if isPrintDownloadSpeed:
        # downloadSpeed的单位是B/s, 超过1024*1024转换为MiB/s, 超过1024转换为KiB/s
        if downloadSpeed > 1048576:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}MiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1048576),
                  file=sys.stdout, flush=True, end='')
        elif downloadSpeed > 1024:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}KiB/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed / 1024),
                  file=sys.stdout, flush=True, end='')
        else:
            print('\r\t{0}/{1} {2}{3} {4:.2f}% {5:>7.2f}B/s'.format(sumCount, doneCount, useCount * '■', spaceCount * '□', precent, downloadSpeed),
                  file=sys.stdout, flush=True, end='')
    else:
        print('\r\t{0}/{1} {2}{3} {4:.2f}%'.format(sumCount, doneCount, useCount*'■', spaceCount*'□', precent), file=sys.stdout, flush=True, end='')

# m3u8下载器
def m3u8VideoDownloader():
    global title
    global logFile
    global m3u8Url
    global cachePath
    global downloadedBytes
    global downloadSpeed
    # 1、下载m3u8
    print("\t1、开始下载m3u8...")
    logFile.write("\t1、开始下载m3u8...\n")
    m3u8Info = getM3u8Info()
    if m3u8Info is None:
        return False
    tsList = []
    for playlist in m3u8Info.segments:
        tsList.append(playlist.uri)
    # 2、获取key
    keyText = ""
    cryptor = None
    # 判断是否加密
    if (len(m3u8Info.keys) != 0) and (m3u8Info.keys[0] is not None):
        # 默认选择第一个key，且AES-128算法
        key = m3u8Info.keys[0]
        if key.method != "AES-128":
            print("\t{0}不支持的解密方式！".format(key.method))
            logFile.write("\t{0}不支持的解密方式！\n".format(key.method))
            return False
        # 如果key的url是相对路径，加上m3u8Url的路径
        keyUrl = key.uri
        if not keyUrl.startswith("http"):
            keyUrl = m3u8Url.replace("index.m3u8", keyUrl)
        print("\t2、开始下载key...")
        logFile.write("\t2、开始下载key...\n")
        keyText = getKey(keyUrl)
        if keyText is None:
            return False
        # 判断是否有偏移量
        if key.iv is not None:
            cryptor = AES.new(bytes(keyText, encoding='utf8'), AES.MODE_CBC, bytes(key.iv, encoding='utf8'))
        else:
            cryptor = AES.new(bytes(keyText, encoding='utf8'), AES.MODE_CBC, bytes(keyText, encoding='utf8'))
    # 3、下载ts
    print("\t3、开始下载ts...")
    logFile.write("\t3、开始下载ts...\n")
    # 清空bytes计数器
    downloadSpeed = 0
    downloadedBytes = 0
    if mutliDownloadTs(tsList):
        logFile.write("\tts下载完成---------------------\n")
    # 4、合并ts
    print("\t4、开始合并ts...")
    logFile.write("\t4、开始合并ts...\n")
    if mergeTs(cachePath, cachePath + "/cache.flv", cryptor, len(tsList)):
        logFile.write("\tts合并完成---------------------\n")
    else:
        print(keyText)
        print("\tts合并失败！")
        logFile.write("\tts合并失败！\n")
        return False
    # 5、开始转换成mp4
    print("\t5、开始mp4转换...")
    logFile.write("\t5、开始mp4转换...\n")
    if not ffmpegConvertToMp4(cachePath + "/cache.flv", saveRootDirPath + "/" + title + ".mp4"):
        return False
    return True


if __name__ == '__main__':
    # 判断m3u8文件是否存在
    if not (os.path.exists(m3u8InputFilePath)):
        print("{0}文件不存在！".format(m3u8InputFilePath))
        exit(0)
    m3u8InputFp = open(m3u8InputFilePath, "r", encoding="utf-8")
    # 设置error的m3u8 url输出
    errorM3u8InfoFp = open(errorM3u8InfoDirPath, "a+", encoding="utf-8")
    # 设置log file
    if not os.path.exists(cachePath):
        os.makedirs(cachePath)
    logFile = open(logPath, "w+", encoding="utf-8")
    # 初始化线程池
    taskThreadPool = threadpool.ThreadPool(processCountConf)
    while True:
        rowData = m3u8InputFp.readline()
        rowData = rowData.strip('\n')
        if rowData == "":
            break
        m3u8Info = rowData.split(',')
        title = m3u8Info[0]
        m3u8Url = m3u8Info[1]
        try:
            print("{0} 开始下载:".format(m3u8Info[0]))
            logFile.write("{0} 开始下载:\n".format(m3u8Info[0]))
            if m3u8VideoDownloader():
                # 成功下载完一个m3u8则清空logFile
                logFile.seek(0)
                logFile.truncate()
                print("{0} 下载成功！".format(m3u8Info[0]))
            else:
                errorM3u8InfoFp.write(title + "," + m3u8Url + '\n')
                errorM3u8InfoFp.flush()
                print("{0} 下载失败！".format(m3u8Info[0]))
                logFile.write("{0} 下载失败！\n".format(m3u8Info[0]))
        except Exception as exception:
            print(exception)
            traceback.print_exc()
    # 关闭文件
    logFile.close()
    m3u8InputFp.close()
    errorM3u8InfoFp.close()
    print("----------------下载结束------------------")