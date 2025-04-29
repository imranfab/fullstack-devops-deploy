from dataclasses import dataclass
import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_type = "open_ai"

GPT_40_PARAMS = dict(
    temperature=0.7,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=False,
)


@dataclass
class GPTVersion:
    name: str
    model: str


GPT_VERSIONS = {
    "gpt35": GPTVersion("gpt35", "gpt-3.5-turbo"),
    "gpt35-16k": GPTVersion("gpt35-16k", "gpt-3.5-turbo-16k"),
    "gpt4": GPTVersion("gpt4", "gpt-4"),
    "gpt4-32k": GPTVersion("gpt4-32k", "gpt4-32k"),
}


def get_simple_answer(prompt: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}

    response = openai.chat.completions.create(
        model=GPT_VERSIONS["gpt35"].model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        **kwargs
    )

    if stream:
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    else:
        return response.choices[0].message.content


def get_gpt_title(prompt: str, response_text: str):
    sys_msg = (
        "As an AI Assistant your goal is to make a very short title — a few words max — for a conversation between "
        "a user and chatbot. You will be given the user's question and chatbot's first response. Return ONLY the raw title."
    )
    usr_msg = f'user_question: "{prompt}"\nchatbot_response: "{response_text}"'

    response = openai.chat.completions.create(
        model=GPT_VERSIONS["gpt35"].model,
        messages=[
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": usr_msg}
        ]
    )

    return response.choices[0].message.content.strip().replace('"', "")


def get_conversation_answer(conversation: list[dict[str, str]], model: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}

    response = openai.chat.completions.create(
        model=GPT_VERSIONS[model].model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            *conversation
        ],
        **kwargs
    )

    if stream:
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    else:
        return response.choices[0].message.content