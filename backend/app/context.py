import os

from llama_index.core import ServiceContext
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI


def create_base_context():
    model = os.getenv("MODEL", "gpt-3.5-turbo")
    embed_model = OpenAIEmbedding()
    return ServiceContext.from_defaults(
        llm=OpenAI(model=model),
        embed_model=embed_model
    )
