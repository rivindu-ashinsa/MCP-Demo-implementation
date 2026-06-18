import asyncio
from langchain_groq import ChatGroq
from mcp_use import MCPClient, MCPAgent

import os

from posthog import flush


async def run_memory_chat():
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")



    config_file = "server.json"
    print("initialiing chat..")


    client = MCPClient.from_config_file(config_file)
    llm = ChatGroq(groq_api_key=groq_api_key, model="llama-3.1-8b-instant")

    agent = MCPAgent(
        client=client,
        llm=llm, 
        max_steps=10, 
        memory_enabled=True
    )


    print("Chat initialized.")
    print("type quit to exit")
    try:
        while True:
            user_input = input("\nyou: ")
            if user_input.lower() == "quit":
                print("Ending conversation")
                break

            if user_input.lower() == "clear": 
                agent.clear_conversation_history()
                print("history cleared")
                continue
            
            print("Assistant: ", end="", flush=True)
            try:
                response = await agent.run(user_input)
                print(response)
            except Exception as e:
                print(f"error occured : {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        if client and client.sessions:
            await client.close_all_sessions()




async def main():
    await run_memory_chat()

if __name__ == "__main__":
    asyncio.run(main())