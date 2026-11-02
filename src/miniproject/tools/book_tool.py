import os
import httpx
from google.adk.tools import ToolContext

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001").rstrip("/")


async def get_all_books(tool_context:ToolContext, library_id: int | None = None) -> dict :
    token=tool_context.state.get('access_token')
    print(f'this is your token {token}')
    
    if not token:
        print("bhai token leke aa na")
        return {"error":"token not found"}
    
    params={}
    
    if library_id is not None:
        params['library_id']=library_id
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/books", params=params, headers={'Authorization': f'Bearer {token}'})
        return response.json()