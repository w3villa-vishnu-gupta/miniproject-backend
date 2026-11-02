import asyncio
import uuid

from miniproject.agents.runner_service import chat


async def main():
    response = await chat(
        message="tell me total number of library and students",
        user_id="test-user",
        session_id=str(uuid.uuid4()),
    )
    print("Agent response:", response)


asyncio.run(main())





