This is a [LlamaIndex](https://www.llamaindex.ai/) project using [FastAPI](https://fastapi.tiangolo.com/) bootstrapped with [`create-llama`](https://github.com/run-llama/LlamaIndexTS/tree/main/packages/create-llama).

## Getting Started

First, setup the environment:

```
poetry install
poetry shell
```

By default, we use the OpenAI LLM (though you can customize, see `app/context.py`). As a result you need to specify an `OPENAI_API_KEY` in an .env file in this directory.

Example `.env` file:

```
OPENAI_API_KEY=<openai_api_key>
```

Second, generate the embeddings of the documents in the `./data` directory (if this folder exists - otherwise, skip this step):

```
python app/engine/generate.py
```

Third, run the development server:

```
python main.py
```

Then call the API endpoint `/api/chat` to see the result:

```
curl --location 'localhost:8000/api/chat' \
--header 'Content-Type: application/json' \
--data '{ "messages": [{ "role": "user", "content": "Hello" }] }'
```

You can start editing the API by modifying `app/api/routers/chat.py`. The endpoint auto-updates as you save the file.

Open [http://localhost:8000/docs](http://localhost:8000/docs) with your browser to see the Swagger UI of the API.

The API allows CORS for all origins to simplify development. You can change this behavior by setting the `ENVIRONMENT` environment variable to `prod`:

```
ENVIRONMENT=prod uvicorn main:app
```

## Chat 🦙
The script at `scripts/chat_llama.py` spins up a repl interface to start a chat within your terminal by interacting with the API directly. This is useful for debugging issues without having to interact with a full frontend.

The script takes an optional `--base_url` argument that defaults to `http://localhost:8000` but can be specified to make the script point to the prod or preview servers. The `Makefile` contains `chat` & `chat_prod` commands that specify this arg for you.

Usage is as follows:

```
$ poetry shell  # if you aren't already in your poetry shell
$ make chat
poetry run python -m scripts.chat_llama
(Chat🦙) message Hi


=== Message 0 ===
{'id': '05db08be-bbd5-4908-bd68-664d041806f6', 'created_at': None, 'updated_at': None, 'conversation_id': '8371bbc8-a7fd-4b1f-889b-d0bc882df2a5', 'content': 'Hello! How can I assist you today?', 'role': 'assistant', 'status': 'PENDING', 'sub_processes': [{'id': None, 'created_at': None, 'updated_at': None, 'message_id': '05db08be-bbd5-4908-bd68-664d041806f6', 'content': 'Starting to process user message', 'source': 'constructed_query_engine'}]}


=== Message 1 ===
{'id': '05db08be-bbd5-4908-bd68-664d041806f6', 'created_at': '2023-06-29T20:50:36.659499', 'updated_at': '2023-06-29T20:50:36.659499', 'conversation_id': '8371bbc8-a7fd-4b1f-889b-d0bc882df2a5', 'content': 'Hello! How can I assist you today?', 'role': 'assistant', 'status': 'SUCCESS', 'sub_processes': [{'id': '75ace83c-1ebd-4756-898f-1957a69eeb7e', 'created_at': '2023-06-29T20:50:36.659499', 'updated_at': '2023-06-29T20:50:36.659499', 'message_id': '05db08be-bbd5-4908-bd68-664d041806f6', 'content': 'Starting to process user message', 'source': 'constructed_query_engine'}]}


====== Final Message ======
Hello! How can I assist you today?
