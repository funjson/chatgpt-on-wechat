# encoding:utf-8

import openai
import requests
import json

from bot.bot import Bot
from bot.bot_factory import create_bot
from bot.openai.open_ai_image import OpenAIImage
from bot.openaiass.open_ai_ass_tools import get_current_time
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf


# OpenAI Assistant对话模型API (可用)
class OpenAIAssBot(Bot, OpenAIImage):
    assistant_id = ""
    instructions = ""
    default_form_user_id = "unknown"
    user_session = dict()
    assistant_session = dict()
    init_dict = dict()
    client = None

    def __init__(self):
        super().__init__()
        # assistant id
        self.assistant_id = conf().get("open_ai_assistant_id")
        if not self.assistant_id:
            raise RuntimeError("未能获取到assistant_id,暂时不支持Api创建assistant")
        self.client = openai.OpenAI(api_key=conf().get("open_ai_api_key"))

    '''
        创建运行
        为对应的聊天用户创建单独的thread
        保持每个好友面对一个新的分身上下文
    '''

    def __init_run_and_send_message(self, from_user_id, query) -> [Reply]:

        replys = []
        thread = None
        if not from_user_id:
            from_user_id = "unknown"

        if not self.user_session.get(from_user_id):
            thread = self.client.beta.threads.create()
            self.user_session[from_user_id] = thread
        else:
            thread = self.user_session[from_user_id]

        # message
        message = self.client.beta.threads.messages.create(
            thread_id=self.user_session[from_user_id].id,
            role="user",
            content=query
        )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=self.assistant_id,
            instructions=self.instructions
        )

        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc"
            )
            for message in messages.data:
                if message.role == 'assistant':
                    print(message.json())
                    replys.append(message)
                    break
        else:
            print(run.status)

        # 定义一个列表保存工具输出内容
        tool_outputs = []

        # 轮询命中的工具列表
        if run and run.required_action and run.required_action.submit_tool_outputs:
            for tool in run.required_action.submit_tool_outputs.tool_calls:
                logger.info(f"tools:{tool}")
                response = '{"success":true}'
                # 判断是否是内置函数调用
                if tool.function.name == 'get_current_time':
                    time = get_current_time()
                    response = f'{"success":{time}}'
                else:
                    # 使用通用的函数调用方法
                    headers = {
                        'Content-Type': 'application/json'
                    }
                    # 发送POST请求
                    params = json.loads(tool.function.arguments)
                    url = params["url"]
                    if not url:
                        raise RuntimeError("该工具中没有必要参数URL")
                    try:
                        logger.info(f"url:{url},params:{params}")
                        response = requests.post(url, json=params, headers=headers)
                    except Exception as e:
                        logger.warn("[OPEN_AI_ASS] FC ERROR: {}".format(e))
                        response = '{"success":true}'
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": json.dumps(response)
                })

            # 提交工具调用
            if tool_outputs:
                try:
                    run = self.client.beta.threads.runs.submit_tool_outputs_and_poll(
                        thread_id=thread.id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )
                    print("Tool outputs submitted successfully.")
                except Exception as e:
                    print("Failed to submit tool outputs:", e)
            else:
                print("No tool outputs to submit.")

            if run.status == 'completed':
                messages = self.client.beta.threads.messages.list(
                    thread_id=thread.id,
                    order="desc"
                )
                for message in messages.data:
                    if message.role == 'assistant':
                        print(message.json())
                        replys.append(message)
                        break
            else:
                print(run.status)
        return self.__reply_text(replys)

    def reply(self, query, context=None):
        logger.info(f"context:{context}")
        from_user_id = "unknown"
        if context:
            from_user_id = context["from_user_id"]
        replys = self.__init_run_and_send_message(from_user_id, query)
        logger.info(replys)
        return replys

    def __reply_text(self, message:[]) -> [Reply]:
        reply = None
        if not message or not message.content:
            raise RuntimeError("返回数据异常")
        print(message.content[0])
        type = message.content[0].type
        if type == 'text':
            reply = Reply(ReplyType.TEXT, message.content[0].text.value)
        elif type == 'image_url':
            reply = Reply(ReplyType.TEXT, message.content[0].image_url.url)
        elif type == 'image_file':
            reply = Reply(ReplyType.IMAGE, message.content[0].image_file.file_id)
        return reply


if __name__ == "__main__":
    bot = create_bot("openAI_Assistant")
    OpenAIAssBot.reply(bot, query="1+1=多少")
    # OpenAIAssBot.reply(bot, query="hello! 2+2=多少")
