import os
# import openai
# from dotenv import load_dotenv

# load_dotenv()
# openai.api_key = os.getenv("OPENAI_API_KEY")

# chat/utils/summarizer.py

import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

def generate_conversation_summary(conversation_text):
    prompt = f"Summarize this conversation:\n\n{conversation_text}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"[Error generating summary: {str(e)}]"



# def generate_conversation_summary(conversation):
#     messages = (
#         conversation.versions
#         .prefetch_related("messages")
#         .values_list("messages__content", flat=True)
#     )
#     conversation_text = "\n".join(messages)

#     if not conversation_text.strip():
#         return "No content to summarize."

#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "Summarize this conversation in 3-5 lines."},
#             {"role": "user", "content": conversation_text},
#         ],
#         temperature=0.7,
#         max_tokens=150
#     )

#     summary = response.choices[0].message.content.strip()
#     return summary
