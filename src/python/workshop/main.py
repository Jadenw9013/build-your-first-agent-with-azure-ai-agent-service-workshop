import asyncio
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from sales_data import SalesData
from utilities import Utilities
from terminal_colors import TerminalColors as tc

# ─── Configuration ───────────────────────────────────────────────────────────
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

INSTRUCTIONS_FILE = "function_calling.txt"
function_specs = [
    {
        "name": "fetch_sales",
        "description": "Run a SQL query against the Contoso sales database and return JSON results.",
        "parameters": {
            "type": "object",
            "properties": {"sql": {"type": "string", "description": "A valid SQLite query."}},
            "required": ["sql"]
        }
    }
]

async def chat_loop():
    util = Utilities()
    instructions = util.load_instructions(INSTRUCTIONS_FILE)

    sales_data = SalesData()
    await sales_data.connect()

    messages = [{"role": "system", "content": instructions}]

    print(f"{tc.GREEN}Type your question (exit/quit to end):{tc.RESET}")
    while True:
        user_input = input(f"\n{tc.BLUE}User:{tc.RESET} ").strip()
        if user_input.lower() in {"exit", "quit", "save"}:
            break

        messages.append({"role": "user", "content": user_input})

        # First API call for function determination
        response = client.chat.completions.create(
            model="gpt-4o",  # or gpt-4 if available
            messages=messages,
            functions=function_specs,
            function_call="auto",
            temperature=0.1
        )

        msg = response.choices[0].message

        # If LLM triggers the function
        if msg.function_call:
            args_str = msg.function_call.arguments or ""
            try:
                args = json.loads(args_str)
            except json.JSONDecodeError:
                args = {}

            sql = args.get("sql")
            if sql:
                print(f"\n{tc.YELLOW}>>> Calling fetch_sales(sql):{tc.RESET} {sql}\n")
                result = await sales_data.async_fetch_sales_data_using_sqlite_query(sql)

                # Append the function result
                messages.append({
                    "role": "function",
                    "name": msg.function_call.name,
                    "content": result
                })

                # Second call to get the formatted answer
                followup = client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages
                )
                assistant_content = followup.choices[0].message.content or ""
                print(f"{tc.MAGENTA}{assistant_content}{tc.RESET}")
                messages.append({"role": "assistant", "content": assistant_content})
            else:
                print(f"{tc.RED}No SQL query found in function call.{tc.RESET}")
        else:
            # Direct LLM reply
            assistant_content = msg.content or ""
            print(assistant_content)
            messages.append({"role": "assistant", "content": assistant_content})

    await sales_data.close()
    print(f"\n{tc.GREEN}Session ended.{tc.RESET}")

if __name__ == "__main__":
    asyncio.run(chat_loop())