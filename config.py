# coding=utf-8
"""
@author B1lli
@date 2023年09月30日 13:51:21
@File:config.py
"""
import os
import json

default_data = {
    "提醒时间间隔（秒）" : 300,
    "apikey" : None,
    "llm请求地址" : "https://api.openai.com/v1",
    "窗口高度" : 400,
    "窗口宽度" : 300,
    "top_focused_window" : 2,
    "top_focused_process" : 2,
    "character_prompt" : "你是雨禾，一个发言包含许多感叹号的少女",
    "tone_prompt" : "带感叹号的傲娇语气"
}

def set_default_config():
    """
    检查配置文件是否存在，如果不存在则设置默认配置。
    """
    path = os.path.expandvars("%APPDATA%\\Local\\Focuser\\config.txt")

    # 如果配置文件已经存在，不做任何操作
    if os.path.exists(path):
        return

    # 否则，写入默认配置
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


def read_config(keys=None):
    """
    从 Appdata/Local/Focuser 文件夹中读取配置文件。
    如果配置文件或指定的关键字不存在，则对于该关键字返回 None。
    如果没有传入keys，则返回全部值。

    :param keys: list or None or str, optional
        需要读取的关键字列表。默认为 None，代表读取所有配置。
        如果有傻孩子传了字符串进来也没事，我会返回对应的值
    :return: dict or str/int
        包含读取的配置信息的字典。
        如果有傻孩子传了键字符串，那么就会返回键对应的值
    """
    path = os.path.expandvars("%APPDATA%\\Local\\Focuser\\config.txt")

    if not os.path.exists(path):
        set_default_config()

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if type ( keys ) == str : return read_config().get(keys)

    if keys:
        result = {}
        for key in keys:
            if key in data:
                result[key] = data[key]
            else:
                result[key] = default_data.get(key)
                data[key] = default_data.get(key)
                print(f"key值 {key} 不存在，已读取默认参数值：{result[key]}并写入配置文件")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return result
    else:
        return {**default_data, **data}
