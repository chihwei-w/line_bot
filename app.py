from flask import Flask, request, abort
import os
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)

from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()

configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 呼叫openai
import openai
from dotenv import load_dotenv
import os

load_dotenv()
# 將你的 API KEY 放在這裡
openai.api_key = os.getenv("OPENAI_API_KEY")

# 初始化對話歷史
conversation = [
    {"role": "system", "content": "你是一個有幫助的助手。"}
]

# 呼叫 OpenAI API 來獲取回應
response = openai.ChatCompletion.create(
        model="gpt-4",  # 可以選擇不同的模型
        messages=conversation,
        temperature=1,
        max_tokens=5000,
        n=1,
        stop=None,
    )

# 顯示並將新的回應加入到對話歷史
def get_gpt_response(user_input):
    global conversation  # 確保修改全域對話
    conversation.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversation, # 將對話歷史傳遞給OpenAI API
        temperature=1,
        max_tokens=5000,
        n=1,
        stop=None,
    )

    return response.choices[0].message.content # 回傳OpenAI的回應


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_input = event.message.text  # 獲取使用者輸入的訊息
    response = get_gpt_response(user_input)  # 獲取OpenAI的回應

    with ApiClient(configuration) as api_client:  # 使用Line API進行回應
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,  # 回覆的token
                messages=[TextMessage(text=response)]  # 設定要發送的訊息
            )
        )
response = get_gpt_response("")

if __name__ == "__main__":
    app.run() # 啟動Flask應用程式