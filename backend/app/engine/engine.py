import logging
import os
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine

from app.engine.constants import STORAGE_DIR
from app.engine.context import create_service_context


def get_index():
    service_context = create_service_context()
    # check if storage already exists
    if not os.path.exists(STORAGE_DIR):
        raise Exception(
            "StorageContext is empty - call 'python app/engine/generate.py' to generate the storage first"
        )
    logger = logging.getLogger("uvicorn")
    # load the existing index (VectorStoreIndex)
    logger.info(f"Loading index from {STORAGE_DIR}...")
    storage_context = StorageContext.from_defaults(persist_dir=STORAGE_DIR)
    index = load_index_from_storage(storage_context, service_context=service_context)
    logger.info(f"Finished loading index from {STORAGE_DIR}")
    return index


def get_query_engine():
    index = get_index()

    vector_query_engine = index.as_query_engine()

    query_engine_tools = [
        QueryEngineTool(
            query_engine=vector_query_engine,
            metadata=ToolMetadata(
                name="catechism",
                description="The Catechism of the Catholic church which has information about creed, sacraments, prayer, morals.",
            ),
        ),
    ]

    query_engine = SubQuestionQueryEngine.from_defaults(
        query_engine_tools=query_engine_tools,
    )

    return query_engine
