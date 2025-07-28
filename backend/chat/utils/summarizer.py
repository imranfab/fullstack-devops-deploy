from transformers import pipeline

# Load once and reuse
summarizer = pipeline("summarization", model="t5-small", tokenizer="t5-small")

def generate_summary(text: str) -> str:
    if not text.strip():
        return "No content available for summary."
    try:
        # Truncate if too long for small model
        text = text[:1000]
        summary = summarizer(text, max_length=60, min_length=20, do_sample=False)
        return summary[0]['summary_text']
    except Exception as e:
        return f"Summary error: {str(e)}"
