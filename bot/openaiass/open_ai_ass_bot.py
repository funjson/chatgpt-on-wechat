# encoding:utf-8

from openai import OpenAI
from openai.types.beta.threads import Message

from bot.bot import Bot
from bot.bot_factory import create_bot
from bot.openai.open_ai_image import OpenAIImage
from bridge.reply import Reply, ReplyType
from common.log import logger
from config import conf


# OpenAI Assistant对话模型API (可用)
class OpenAIAssBot(Bot, OpenAIImage):
    assistant_id = ""
    instructions = ""
    default_form_user_id="unknown"
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
        self.client = OpenAI(api_key=conf().get("open_ai_api_key"))

    '''
        创建运行
        为对应的聊天用户创建单独的thread
        保持每个好友面对一个新的分身上下文
    '''

    def __init_run_and_send_message(self, from_user_id, query) -> Reply:

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

        content = None
        if run.status == 'completed':
            messages = self.client.beta.threads.messages.list(
                thread_id=thread.id,
                order="desc"
            )
            for message in messages.data:
                if message.role == 'assistant':
                    print(message.json())
                    content = message
                    break
        else:
            print(run.status)

        return self.__reply_text(content)

    def reply(self, query, context=None):
        logger.info(f"context:{context}")
        from_user_id = "unknown"
        if context:
            from_user_id = context["from_user_id"]
        reply = self.__init_run_and_send_message(from_user_id, query)
        logger.info(reply)
        return reply

    def __reply_text(self, message: Message) -> Reply:
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
