# coding=utf-8
"""
@author B1lli
@date 2023年09月28日 18:49:18
@File:utils.py
"""
import json
import openai
from plyer import notification

def send_notification(title, message):
    """
    发送Windows通知

    参数:
        title (str): 通知的标题
        message (str): 通知的内容
    """
    notification.notify(
        title=title,
        message=message,
        app_name="YourAppName",  # 你可以替换为你的应用名称
        timeout=10  # 通知显示的时间（秒）
    )

class llm():
    def __init__(self,system_prompt=None,model='gpt-3.5-turbo-0613'):
        self.system_prompt = system_prompt
        self.model = model

    def single_generate(self, user_query, decode=True):
        '''
        单次生成回复，用于种种只需要单轮上下文的调用场景
        :param user_query: content
        :return: content
        '''
        messages = [
            {"role" : "system", "content" : self.system_prompt},
            {"role" : "user", "content" : user_query}
        ]
        response = openai.ChatCompletion.create (
            model=self.model,
            messages=messages,
        )
        self.single_generate_content = response["choices"][0]["message"]['content']
        if decode :
            self.single_generate_content = decode_chr ( self.single_generate_content )
            return self.single_generate_content
        return self.single_generate_content

    def custom_generate(self,messages,decode=True):
        '''
        自定义生成，需要组装好message上下文传进去，返回给你的也是message
        :param messages:message
        :return:message
        '''
        response = openai.ChatCompletion.create (
            model=self.model,
            messages=messages,
        )
        if decode:
            response["choices"][0]["message"]['content'] = decode_chr(response["choices"][0]["message"]['content'])
            return response["choices"][0]["message"]
        return response["choices"][0]["message"]

    def stream_generate(self, messages, decode=True) :
        '''
        流式传输
        :param messages: message
        :param decode: bool，是否返回解码文字
        :return: 流式传输的content
        '''
        completion = openai.ChatCompletion.create (
            model="gpt-3.5-turbo",
            messages=messages,
            stream=True
        )

        if decode :
            return self._stream_generate_decoded ( completion )
        else :
            return self._stream_generate_raw ( completion )

    def _stream_generate_decoded(self, completion) :
        for chunk in completion :
            try :
                if chunk.choices[0].delta :
                    yield decode_chr ( chunk.choices[0].delta.content )
            except Exception as e :
                print ( e )
                continue

    def _stream_generate_raw(self, completion) :
        for chunk in completion :
            try :
                if chunk.choices[0].delta :
                    yield chunk.choices[0].delta.content
            except Exception as e :
                print ( e )
                continue


def extract_json_from_text(text):
    """
    从文本中解析JSON并转换为字典。

    :param text: 输入的长文本
    :return: 如果找到并成功解析JSON，则返回字典；否则返回None
    """
    # 定义起始和结束标识符
    start_marker = '{'
    end_marker = '}'

    # 查找标识符的位置
    start_index = text.find(start_marker)
    end_index = text.rfind(end_marker)

    # 如果文本中包含标识符
    if start_index != -1 and end_index != -1 and start_index < end_index:
        json_str = text[start_index:end_index+1]
        try:
            # 尝试解析JSON
            parsed_dict = json.loads(json_str)
            return parsed_dict
        except json.JSONDecodeError:
            # 如果解析失败
            return None
    else:
        return None