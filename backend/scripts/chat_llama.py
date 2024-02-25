import cmd
import requests
import json
import random
import dotenv
from urllib.parse import quote
from dotenv import load_dotenv
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler
from llama_index.core import Settings

from app.engine.engine import get_index, get_query_engine

load_dotenv()

llama_debug = LlamaDebugHandler(print_trace_on_end=True)
callback_manager = CallbackManager([llama_debug])

Settings.callback_manager = callback_manager


class ConversationCmd(cmd.Cmd):
    prompt = "(Chat🦙) "

    def __init__(self):
        super().__init__()
        self._index = get_index()

    def do_message(self, message):
        print(message)

        vector_query_engine = self._index.as_query_engine()

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
            use_async=True,
        )

        response = query_engine.query(message)

        print(response)

        # QUERY = "Can I get communion if I haven't been to confession in a while?"
        # QUERY = "How should the sharing of the sign of peace be celebrated?"
        # QUERY = "Is the Eucharist a re-enactment of the upper room or Calvary?"

        # message = quote(message.strip())  # URI encode the message
        # url = f"{self.base_url}/api/conversation/{self.conversation_id}/message?user_message={message}"
        # headers = {"Accept": "text/event-stream"}
        # response = sse_with_requests(url, headers)
        # messages = SSEClient(response).events()
        # message_idx = 0
        # final_message = None
        # for msg in messages:
        #     print(f"\n\n=== Message {message_idx} ===")
        #     msg_json = json.loads(msg.data)
        #     print(msg_json)
        #     final_message = msg_json.get("content")
        #     message_idx += 1

        # if final_message is not None:
        #     print(f"\n\n====== Final Message ======")
        #     print(final_message)

    def do_quit(self, args):
        "Quits the program."
        print("Quitting.")
        raise SystemExit


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Start the chat terminal.")
    args = parser.parse_args()

    cmd = ConversationCmd()
    try:
        cmd.cmdloop()
    except KeyboardInterrupt:
        cmd.do_quit("")
    except Exception as e:
        print(e)
        cmd.do_quit("")



