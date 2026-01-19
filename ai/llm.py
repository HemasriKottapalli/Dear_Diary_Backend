import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

load_dotenv()

def get_llm():
    #LLAMA 3.1 8B (Good alternative)
    llm = HuggingFaceEndpoint(
        repo_id="meta-llama/Meta-Llama-3.1-8B-Instruct",
        task="text-generation",
        huggingfacehub_api_token=os.getenv("HF_API_TOKEN"),
        max_new_tokens=400,
        temperature=0.3,
        timeout=120
    )
    return ChatHuggingFace(llm=llm)
