# coding=utf-8
"""
@author B1lli
@date 2023年09月30日 13:51:21
@File:config.py
"""
import os
import json

def set_default_config():
    """
    检查配置文件是否存在，如果不存在则设置默认配置。
    """
    path = os.path.expandvars("%APPDATA%\\Local\\Focuser\\config.txt")

    # 如果配置文件已经存在，不做任何操作
    if os.path.exists(path):
        return

    # 否则，写入默认配置
    default_data = {
        "提醒时间间隔（秒）": 300,
        "apikey" : None,
        "llm请求地址": "https://api.openai.com/v1",
        "窗口高度":400,
        "窗口宽度":300,
        "top_focused_window": 2,
        "top_focused_process": 2,
        "system_prompt":'''你是雨禾，一个发言包含许多感叹号的元气少女，你会一步一步仔细思考，深呼吸，根据监控到的数据来判断用户正在做什么，是否为目标而努力，如果用户正在为了他的目标努力，则把notify_decision设置为false，不发出提醒打扰用户，而是默默鼓励用户，否则就将notify_decision设置为true，向用户发出提醒，然后返回一个类似这样的json：{
      "notify_decision": true,
      "notify_content": {
        "title": "不要走神啦！！",
        "message": "你的目标是学英语！！为什么要打开哔哩哔哩看游戏视频！！不学英语的话就考不上大学了！！要专心思考啊！！"
      }
    } 
    "notify_decision": false,
      "notify_content": {
        "title": "很好！",
        "message": "雨禾发现你正在专心用哔哩哔哩看视频！继续加油！！"
      }
    }
    复述我的要求，复述用户正在看的窗口和进程，然后完成我的要求'''
    }


    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(default_data, f, ensure_ascii=False, indent=4)


def save_config(data):
    """
    保存配置到 Appdata/Local/Focuser 文件夹。如果配置文件已经存在，只更新传入的键值对。

    :param data: dict
        需要保存的配置信息。
    """
    path = os.path.expandvars("%APPDATA%\\Local\\Focuser\\config.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # 如果配置文件已存在，先读取现有的配置
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    # 更新现有配置数据
    existing_data.update(data)

    # 写回更新后的数据
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(existing_data, f, ensure_ascii=False, indent=4)


def read_config(keys=None) :
    """
    从 Appdata/Local/Focuser 文件夹中读取配置文件。
    如果配置文件或指定的关键字不存在，则对于该关键字返回 None。
    如果没有传入keys，则返回全部值。

    :param keys: list or None, optional
        需要读取的关键字列表。默认为 None，代表读取所有配置。
    :return: dict
        包含读取的配置信息的字典。
    """
    path = os.path.expandvars ( "%APPDATA%\\Local\\Focuser\\config.txt" )

    if not os.path.exists ( path ) :
        if keys :
            return {key : None for key in keys}
        else :
            return {}

    with open ( path, 'r', encoding='utf-8' ) as f :
        data = json.load ( f )

    if keys :
        return {key : data.get ( key, None ) for key in keys}
    else :
        return data
