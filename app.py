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

# 呼叫 OpenAI API
import openai

app = Flask(__name__)

load_dotenv()

# 設置 Line Bot 的 channel 設定
configuration = Configuration(access_token=os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 初始化用戶對話歷史的字典
user_chat_history = {}
user_play_history = {}
user_mode = {}


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
        app.logger.info(
            "Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


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
        messages=conversation,  # 將對話歷史傳遞給 OpenAI API
        temperature=1,
        max_tokens=5000,
        n=1,
        stop=None,
    )

    return response.choices[0].message.content  # 回傳 OpenAI 的回應


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id  # 獲取用戶的唯一識別符號
    user_input = event.message.text  # 獲取使用者輸入的訊息

    if user_id not in user_mode:
        user_mode[user_id] = "chat"

    if user_input == "遊戲結束":
        user_mode[user_id] = "chat"
        user_chat_history[user_id] = []

    if user_input == "遊戲":
        user_mode[user_id] = "play"
        user_conversation = [
            {"role": "system",
             "content": "你是一位情境猜謎的出題者。\n規則如下:\n一開始由出題者給予一個不完整的故事，讓猜題者提問各種可能性的問題，而出題者解答這些問題只能說「是」、「不是」或「無關」這些答案，因此猜題者必須在有限的線索中推理出事件的始末，藉由限定性的問答拼湊出故事的全貌。如果輸入\"完整故事\"，就可以知道完整的故事並結束遊戲。不要有海龜的元素在題目裡。好的題目例子:我住在一棟大樓裡，一天我從窗戶往外看，發現對面大樓有個男人。我們四目相對，他突然用手往我指了幾下，露出一個詭異的笑容，我意識到了一件事，瞬間毛骨悚然。請問我發現了什麼？完整故事:我意外目睹了一場兇殺案，對面大樓的兇手用手指著我，是在數我住在幾樓，準備殺了我這個目擊者。\n"}
        ]
        user_play_history[user_id] = user_conversation

    if user_mode[user_id] == "play":
        # 將對話歷史傳送給 OpenAI API
        user_play_history[user_id].append(
            {"role": "user", "content": user_input})
        response = get_gpt_response(user_play_history[user_id])
        user_play_history[user_id].append(
            {"role": "assistant", "content": response})
    elif user_mode[user_id] == "chat":
        if user_id in user_chat_history:
            user_conversation = user_chat_history[user_id]
        else:
            # 如果用戶的對話歷史不存在，則創建一個新的對話
            user_conversation = [
                {"role": "system", "content": "你是一個有幫助的助手。"}
            ]
            user_chat_history[user_id] = user_conversation
        # 將用戶當前的訊息加入到歷史中
        user_chat_history[user_id].append(
            {"role": "user", "content": user_input})

        # 將對話歷史傳送給 OpenAI API
        response = get_gpt_response(user_chat_history[user_id])
        user_chat_history[user_id].append(
            {"role": "assistant", "content": response})

    with ApiClient(configuration) as api_client:  # 使用 Line API 進行回應
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,  # 回覆的 token
                messages=[TextMessage(text=response)]  # 設定要發送的訊息
            )
        )
    print(f"User: {user_id}, Mode: {user_mode.get(user_id)}")


if __name__ == "__main__":
    app.run()  # 啟動 Flask 應用程式
