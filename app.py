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

# 設置 Line Bot 的 channel 設定
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 初始化用戶對話歷史的字典
user_history = {}

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature 標頭的值
    signature = request.headers['X-Line-Signature']

    # 以文字形式獲取請求主體
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # 處理 Webhook 主體
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# 呼叫 OpenAI API
import openai
from dotenv import load_dotenv
import os

load_dotenv()
# API KEY
openai.api_key = os.getenv("OPENAI_API_KEY")

# 初始化對話歷史
conversation = [
    {"role": "system", "content": "你是一個有幫助的助手。"}
]

# 獲取 OpenAI 回應
response = openai.ChatCompletion.create(
        model="gpt-4",  # 可以選擇不同的模型
        messages=conversation,
        temperature=1,
        max_tokens=5000,
        n=1,
        stop=None,
    )

# 顯示並將新的回應加入到對話歷史
def get_gpt_response(conversation):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=conversation, # 將對話歷史傳遞給 OpenAI API
        temperature=1,
        max_tokens=5000,
        n=1,
        stop=None,
    )

    return response.choices[0].message.content # 回傳 OpenAI 的回應

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id  # 獲取用戶的唯一識別符號
    user_input = event.message.text  # 獲取使用者輸入的訊息

    # 查找用戶的對話歷史
    if user_id in user_history:
        conversation = user_history[user_id]
    else:
        # 如果用戶的對話歷史不存在，則創建一個新的對話
        conversation = [
            {"role": "system", "content": "你是一個有幫助的助手。"}
        ]

    # 將用戶當前的訊息加入到歷史中
    conversation.append({"role": "user", "content": user_input})
    user_history[user_id] = conversation

    # 將對話歷史傳送給 OpenAI API
    response = get_gpt_response(conversation)

    with ApiClient(configuration) as api_client:  # 使用 Line API 進行回應
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,  # 回覆的 token
                messages=[TextMessage(text=response)]  # 設定要發送的訊息
            )
        )

if __name__ == "__main__":
    app.run() # 啟動 Flask 應用程式
