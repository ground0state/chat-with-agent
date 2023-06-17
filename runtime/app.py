import os
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key
from chalice import Chalice, Response
from chalicelib import complete_chat
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# Parameters ------------------------------------------------------
QUERY_LIMIT = 6
EXIT_COMMAND = "EXIT"
# -----------------------------------------------------------------


app = Chalice(app_name='gpt-with-agent')
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
dynamodb_table = dynamodb.Table(os.environ['APP_TABLE_NAME'])

line_bot_api = LineBotApi(
    channel_access_token=os.environ['LINE_CHANNEL_ACCESS_TOKEN']
)
handler = WebhookHandler(
    channel_secret=os.environ['LINE_CHANNEL_SECRET']
)


@app.route('/callback', methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = app.current_request.headers.get('X-Line-Signature')

    # get request body as text
    request_body = app.current_request.raw_body.decode()

    try:
        # forward body to GPT
        handler.handle(body=request_body, signature=signature)
    except InvalidSignatureError:
        error_text = "ERROR: Invalid signature. Please check your channel access token / channel secret."
        app.log.error(error_text)
        return Response(body=error_text, status_code=400)

    return Response(
        body='OK',
        headers={'Content-Type': 'text/plain'},
        status_code=200
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # extract info
    line_user_id = event.source.user_id
    line_timestamp = int(event.timestamp)

    prompt_text = event.message.text
    # special command
    if prompt_text == EXIT_COMMAND:
        delete_all_message(line_user_id)
        info_text = "INFO: 今までの会話を削除しました。"
        reply_message(event, info_text)
        app.log.info(info_text)
        return

    # ChatGPT
    current_prompts = [{"role": "user", "content": prompt_text}]
    try:
        chat_histories = get_chat_history(line_user_id, QUERY_LIMIT)
    except:
        reply_message(event, "DB Error")
        error_text = "ERROR: Cannot get chat histories"
        app.log.error(error_text)
        return

    prompts = chat_histories + current_prompts
    try:
        response = forward_message(prompts)
        response_text = response['text']
        response_timestamp = int(response['timestamp'])
    except:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="GPT Error"))
        error_text = "ERROR: GPT is bussy"
        app.log.error(error_text)
        return
    # save message
    try:
        insert_message(line_user_id, prompt_text, "user", line_timestamp)
        insert_message(line_user_id, response_text,
                       "assistant", response_timestamp)
    except:
        reply_message(event, "Failed to save message to DB")
        error_text = "ERROR: Failed to save message to DB"
        app.log.error(error_text)
    # returm message to line
    reply_message(event, response_text)


def forward_message(prompts):
    response = complete_chat(prompts)
    ret = {'text': response['text'],
           'timestamp': response['created_at']}
    return ret


def insert_message(
    user_id: str,
    content: str,
    role: str,
    timestamp: int = None
):
    if timestamp is None:
        timestamp = int(datetime.now().timestamp()) * 1000

    item = {
        'userId': user_id,
        'unixTimestamp': int(timestamp),
        'content': content,
        'role': role
    }
    try:
        ret = dynamodb_table.put_item(Item=item)
    except Exception as e:
        raise e
    return ret


def get_chat_history(user_id: str, limit: int = 1):
    try:
        response = dynamodb_table.query(
            KeyConditionExpression=Key('userId').eq(user_id),
            Limit=limit,
            ScanIndexForward=False  # Sort the results in descending order by sort key
        )
    except Exception as e:
        raise e

    history = []
    for item in reversed(response['Items']):
        history.append({
            "role": item["role"],
            "content": item["content"]
        })
    return history


def delete_all_message(user_id: str):
    response = dynamodb_table.scan(
        ProjectionExpression='userId, unixTimestamp',
        FilterExpression=Key('userId').eq(user_id)
    )
    data = response['Items']
    if len(data) == 0:
        return

    while 'LastEvaluatedKey' in response:
        response = dynamodb_table.scan(
            ExclusiveStartKey=response['LastEvaluatedKey'])
        data.extend(response['Items'])

    with dynamodb_table.batch_writer() as batch:
        for each in data:
            batch.delete_item(Key=each)


def reply_message(event, text):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text))
