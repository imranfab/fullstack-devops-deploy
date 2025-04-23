from dataclasses import dataclass
import openai
import os
from src.libs import openai

GPT_40_PARAMS = dict(
    temperature=0.7,
    top_p=0.95,
    frequency_penalty=0,
    presence_penalty=0,
    stop=None,
    stream=True, #Previously False

)


@dataclass
class GPTVersion:
    name: str
    engine: str



GPT_VERSIONS = {
    "gpt35": GPTVersion("gpt35", "gpt-35-turbo-0613"),
    "gpt35-16k": GPTVersion("gpt35-16k", "gpt-35-turbo-16k"),
    "gpt4": GPTVersion("gpt4", "gpt-4-0613"),
    "gpt4-32k": GPTVersion("gpt4-32k", "gpt4-32k-0613"),
}


openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_BASE")
openai.api_type = os.getenv("OPENAI_API_TYPE", "openai")  # fallback to 'openai'

def get_simple_answer(prompt: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}

    for resp in openai.ChatCompletion.create(
        #engine=GPT_VERSIONS["gpt35"].engine,
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        messages=[{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": prompt}],
        **kwargs,
    ):
        choices = resp.get("choices", [])
        if not choices:
            continue
        chunk = choices.pop()["delta"].get("content")
        if chunk:
            yield chunk


def get_gpt_title(prompt: str, response: str):
    sys_msg: str = (
        "As an AI Assistant your goal is to make very short title, few words max for a conversation between user and "
        "chatbot. You will be given the user's question and chatbot's first response and you will return only the "
        "resulting title. Always return some raw title and nothing more."
    )
    usr_msg = f'user_question: "{prompt}"\n' f'chatbot_response: "{response}"'

    response = openai.ChatCompletion.create(
        #engine=GPT_VERSIONS["gpt35"].engine,
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": usr_msg}],
        #**GPT_40_PARAMS,
        **{**GPT_40_PARAMS, "stream": False},
    )

    result = response["choices"][0]["message"]["content"].replace('"', "")
    return result


def get_conversation_answer(conversation: list[dict[str, str]], model: str, stream: bool = True):
    kwargs = {**GPT_40_PARAMS, **dict(stream=stream)}
    engine = GPT_VERSIONS[model].engine

    for resp in openai.ChatCompletion.create(
        #engine=engine,
        model=os.getenv("OPENAI_MODEL", "gpt-4"),
        messages=[{"role": "system", "content": "You are a helpful assistant."}, *conversation],
        **kwargs,
    ):
        choices = resp.get("choices", [])
        if not choices:
            continue
        chunk = choices.pop()["delta"].get("content")
        if chunk:
            yield chunk

# generate summary
# def generate_summary(conversation: list[dict[str, str]], model: str):
#     #Added this
#     from chat.models import Conversation 
#     sys_msg = "You are an AI that summarizes conversations concisely. Your task is to create a brief summary of the conversation."
#     messages = [{"role": "system", "content": sys_msg}] + conversation

#     model_name = GPT_VERSIONS[model].model

#     response = openai.ChatCompletion.create(
#         model=model_name,
#         messages=messages,
#         **GPT_40_PARAMS,
#     )

#     summary = response["choices"][0]["message"]["content"].strip()

#     return summary


#This is IMP
# def generate_summary(conversation: list[dict[str, str]], model: str):
#     from chat.models import Conversation  # Import if needed
#     # model_name = GPT_VERSIONS.get(model, None)  # Safely get model version
#     model_name = GPT_VERSIONS[model].engine
#     if model_name:
#         model_name = model_name.engine
#     else:
#         raise ValueError(f"Invalid model name: {model}")
    
#     sys_msg = "You are an AI that summarizes conversations concisely. Your task is to create a brief summary of the conversation."
#     messages = [{"role": "system", "content": sys_msg}] + conversation

#     response = openai.ChatCompletion.create(
#         model=model_name,
#         messages=messages,
#         **GPT_40_PARAMS,
#     )

#     summary = response["choices"][0]["message"]["content"].strip()

#     return summary

def generate_summary(conversation: list[dict[str, str]], model: str):
    from chat.models import Conversation  # Import if needed

    model_name = GPT_VERSIONS[model].engine  # ✅ this is enough

    sys_msg = "You are an AI that summarizes conversations concisely. Your task is to create a brief summary of the conversation."
    messages = [{"role": "system", "content": sys_msg}] + conversation

    response = openai.ChatCompletion.create(
        model=model_name,
        messages=messages,
        # **GPT_40_PARAMS,
        **{**GPT_40_PARAMS, "stream": False},
    )

    summary = response["choices"][0]["message"]["content"].strip()
    return summary



# Function to update the conversation with the summary
def update_conversation_summary(conversation_id: str, model: str):
    conversation = Conversation.objects.get(id=conversation_id)  # Fetch the conversation
    # Assuming that conversation.messages is a list of message dictionaries
    conversation_summary = generate_summary(conversation.messages, model)  # Generate the summary
    conversation.summary = conversation_summary  # Update the summary field
    conversation.save()  # Save the updated conversation
    print(conversation)


def get_conversation_summary(conversation_id: str):
    from chat.models import Conversation
    try:
        conversation = Conversation.objects.get(id=conversation_id)  # Fetch the conversation by its ID
        if conversation.summary:
            print(conversation.summary)
            return conversation.summary  # Return the summary if available
        else:
            return "No summary available."  # Return a default message if no summary exists
    except Conversation.DoesNotExist:
        return "Conversation not found."  # Return an error message if the conversation is not found