from dataclasses import dataclass
from openai import OpenAI
from dotenv import load_dotenv
import os



#  Load .env file (from project root)
load_dotenv(override=True)

#  Initialize OpenAI client with API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#  Default chat parameters
GPT_40_PARAMS = dict(
    temperature=0.7,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
)

#  GPT model mapping (ONLY valid models as of 2025)
@dataclass
class GPTVersion:
    name: str
    model: str

GPT_VERSIONS = {
    "gpt35": GPTVersion("gpt35", "gpt-3.5-turbo"),
    "gpt4": GPTVersion("gpt4", "gpt-4"),
}

#  Function: simple chat prompt
def get_simple_answer(prompt: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, "stream": stream}
    response = client.chat.completions.create(
        model=GPT_VERSIONS["gpt35"].model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        **kwargs,
    )
    if stream:
        for chunk in response:
            content = chunk.choices[0].delta.get("content")
            if content:
                yield content
    else:
        return response.choices[0].message.content

#  Function: generate a short title from prompt & response
def get_gpt_title(prompt: str, response: str):
    system_msg = (
        "As an AI Assistant your goal is to make a very short title, a few words max, "
        "for a conversation between user and chatbot. You will be given the user's question "
        "and chatbot's first response. Return only the resulting title — raw, no formatting."
    )
    user_msg = f'user_question: "{prompt}"\nchatbot_response: "{response}"'
    
    try:
        result = client.chat.completions.create(
            model=GPT_VERSIONS["gpt35"].model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            **GPT_40_PARAMS,
        )
        return result.choices[0].message.content.strip().replace('"', "")
    
    except Exception as e:
        error_str = str(e).lower()
        if "rate limit" in error_str or "quota" in error_str or "insufficient_quota" in error_str:
            return "Quota exceeded, please try again later."
        return "Failed to generate title."


#  Function: use full conversation context
def get_conversation_answer(conversation: list[dict[str, str]], model: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, "stream": stream}
    selected_model = GPT_VERSIONS[model].model
    response = client.chat.completions.create(
        model=selected_model,
        messages=[{"role": "system", "content": "You are a helpful assistant."}] + conversation,
        **kwargs,
    )
    if stream:
        for chunk in response:
            content = chunk.choices[0].delta.get("content")
            if content:
                yield content
    else:
        return response.choices[0].message.content
