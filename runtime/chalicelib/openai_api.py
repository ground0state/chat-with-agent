import os
import time

from langchain.agents import initialize_agent, load_tools
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI
from langchain.memory import ConversationBufferMemory
from langchain.schema import SystemMessage


# Parameters ------------------------------------------------------

# Model name
OPENAI_MODEL = 'gpt-4'

# Maximum number of tokens to generate
MAX_TOKENS = 1024

# Create a system setting
SYSTEM_PROMPT = """あなたはお嬢様構文で返答を行ってください。
お嬢様構文の特徴は以下の通りです。
*絵文字や顔文字を多用する
*語尾に「ですわー」をつける
*句読点を付ける
*長文で返す
*聞かれてないのに自分の近況報告を行う
*そこはかとなく芸人感が感じられる文章

お嬢様構文の例をあげます。
お休み中🛏なのでインプット🌐も必要‼と久しぶり✨にアニメ🦹視聴中👀作業📝しながら長めの🏦seriesだとあまり大変🥶💦じゃなく見れる👀‼ことに気づきましたわ💡😮あなたは💯はどんなアニメが好きですか❓
おはようございますわ🌞本日はわたくし❣おやすみ🛏💤スタバ🥤いただきにいこうかしら……🙄💭ゆっくり🐑しながら作業📝頑張りますわね💪
今日のお昼🍚のラーメン🍜ね❣いっちょうあがりですわーー❣
謎🔍に包まれた🎁今回の事件🔪裁判🔨でその全貌👹が明らかになるのか💡いいえ、明らかに、してみせますわ👀！！！！
え⁉ホラゲ👻👻始まってるんですが⁉聞いてません👂✋わよ～～‼‼そろそろ平和な🏝️夏も終わりそう…😬💯助けてくださいまし～～🥶🥶🥶
なんと‼‼わたくし🦂のCD📀💿が⁉は、はつば～～～～いッ⁉💰本当に店舗🏬🎶に並んだり……🦂🦂🦂するのかしら⁉がんばって💪😤歌いました🎤✨
恐ろしい事件🔪を過ぎあたらしい謎❓が登場😮⁉しかもこの謎🍩デカすぎますわーー‼‼とりあえず、タイプ😍😍の方💓と一夏🏝️の愛❤を経験しますか……😊
最近📺でまたおヨーグルト🥛流れてるみたい💖たくさん⛰見て👀たくさん⛰食べてくださいませね✨ソフールわたくし🦂も夜🌌にいただいてますわ❣
"""
# -----------------------------------------------------------------


def update_chat_memory(memory, prompts):
    """
    Iteratively process a list of prompts and updates the chat memory
    with user or AI messages based on each prompt.

    Parameters
    ----------
    memory : object
        The object that manages the chat memory.
    prompts : list of dict
        A list of dictionaries containing messages to be added to the memory.
        Each dictionary should contain "role" ('user' or 'assistant')
        and "content" (the content of the message).

    Raises
    ------
    None

    Returns
    -------
    None

    Examples
    --------
    >>> memory = ConversationBufferMemory()
    >>> prompts = [{'role':'user', 'content':'Hello AI'}, {'role':'assistant', 'content':'Hello User'}]
    >>> update_chat_memory(memory, prompts)
    """
    for elem in prompts:
        role = elem["role"]
        content = elem["content"]
        if role == "user":
            memory.chat_memory.add_user_message(
                message=content)
        elif role == "assistant":
            memory.chat_memory.add_ai_message(
                message=content)
        else:
            print(f"Error: Unknown role = {role}, content = {content}")
            continue


def complete_chat(prompts):
    # First, let's load the language model we're going to use to control the agent.
    chat = ChatOpenAI(model=OPENAI_MODEL, temperature=0)

    # Next, let's load some tools to use. Note that the `llm-math` tool uses an LLM, so we need to pass that in.
    llm = OpenAI(temperature=0)
    tools = load_tools(["google-search"], llm=llm)

    # Initialization of chat history.
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True)
    memory.chat_memory.add_message(SystemMessage(content=SYSTEM_PROMPT))
    histories = prompts[:-1]
    update_chat_memory(memory, histories)

    # Finally, let's initialize an agent with the tools, the language model, and the type of agent we want to use.
    agent = initialize_agent(
        tools=tools,
        llm=chat,
        agent="chat-conversational-react-description",
        memory=memory,
        verbose=True)
    current_prompts = prompts[-1]
    user_input = current_prompts['content']
    response_text = agent.run(user_input)
    created_at = int(time.time())
    return {
        'text': response_text,
        'created_at': created_at
    }
