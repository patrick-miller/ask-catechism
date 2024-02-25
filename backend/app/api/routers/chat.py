from typing import List

from fastapi.responses import StreamingResponse
from llama_index.core.query_engine import BaseQueryEngine

from app.engine.engine import get_query_engine
from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_index.core.llms import ChatMessage
from llama_index.core.llms import MessageRole
from pydantic import BaseModel

chat_router = r = APIRouter()


class _Message(BaseModel):
    role: MessageRole
    content: str


class _ChatData(BaseModel):
    messages: List[_Message]


@r.post("")
async def chat(
    request: Request,
    data: _ChatData,
    query_engine: BaseQueryEngine = Depends(get_query_engine),
):
    # check preconditions and get last message
    if len(data.messages) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided",
        )
    lastMessage = data.messages.pop()
    if lastMessage.role != MessageRole.USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user",
        )
    # convert messages coming from the request to type ChatMessage
    messages = [
        ChatMessage(
            role=m.role,
            content=m.content,
        )
        for m in data.messages
    ]

    # query chat engine
    response = await query_engine.aquery(lastMessage.content) # , messages)

    return response.response
