import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse, Response

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

load_dotenv()
app = FastAPI()
BASE_URL = "https://finechatserver.erweima.ai"
headers = {
    "accept": "*/*",
    "accept-language": "zh-CN,zh;q=0.9",
    "authorization": "",
    # Already added when you pass json=
    # 'content-type': 'application/json',
    "origin": "https://www.yeschat.ai",
    "priority": "u=1, i",
    "referer": "https://www.yeschat.ai/",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
}
APP_SECRET = os.getenv("APP_SECRET")
ALLOWED_MODELS = [
    {"id": "gpt-4o", "name": "gpt-4o"},
    {"id": "gpt-4o-mini", "name": "gpt-4o-mini"},
]
# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，您可以根据需要限制特定源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头
)
security = HTTPBearer()


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False


def simulate_data(content, model):
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content, "role": "assistant"},
                "finish_reason": None,
            }
        ],
        "usage": None,
    }


def stop_data(content, model):
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content, "role": "assistant"},
                "finish_reason": "stop",
            }
        ],
        "usage": None,
    }
    
    
def create_chat_completion_data(content: str, model: str, finish_reason: Optional[str] = None) -> Dict[str, Any]:
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion.chunk",
        "created": int(datetime.now().timestamp()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"content": content, "role": "assistant"},
                "finish_reason": finish_reason,
            }
        ],
        "usage": None,
    }


def verify_app_secret(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != APP_SECRET:
        raise HTTPException(status_code=403, detail="Invalid APP_SECRET")
    return credentials.credentials


@app.options("/v1/chat/completions")
async def chat_completions_options():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


def replace_escaped_newlines(input_string: str) -> str:
    return input_string.replace("\\n", "\n")


@app.get("/v1/models")
async def list_models():
    return {"object": "list", "data": ALLOWED_MODELS}


@app.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest, app_secret: str = Depends(verify_app_secret)
):
    logger.info(f"Received chat completion request for model: {request.model}")

    if request.model not in [model['id'] for model in ALLOWED_MODELS]:
        raise HTTPException(
            status_code=400,
            detail=f"Model {request.model} is not allowed. Allowed models are: {', '.join(model['id'] for model in ALLOWED_MODELS)}",
        )
    # 生成一个UUID
    original_uuid = uuid.uuid4()
    uuid_str = str(original_uuid).replace("-", "")

    # 使用 OpenAI API
    json_data = {
        "sessionId": uuid_str,
        "prompt": "\n".join(
            [
                f"{'User' if msg.role == 'user' else 'Assistant'}: {msg.content}"
                for msg in request.messages
            ]
        ),
    }

    headers["uniqueid"] = uuid_str

    async def generate():
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream('POST', f'{BASE_URL}/api/v1/gpt2/free-gpt2/chat', headers=headers, json=json_data, timeout=120.0) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line and line != "[DONE]":
                            content = json.loads(line)["data"]
                            if 'url' in content:
                                markdown_url = "\n ![](" + content['url'] + ") \n"
                                yield f"data: {json.dumps(create_chat_completion_data(markdown_url, request.model))}\n\n"
                            yield f"data: {json.dumps(create_chat_completion_data(content['message'], request.model))}\n\n"
                    yield f"data: {json.dumps(create_chat_completion_data('', request.model, 'stop'))}\n\n"
                    yield "data: [DONE]\n\n"
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e}")
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
            except httpx.RequestError as e:
                logger.error(f"An error occurred while requesting: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    if request.stream:
        logger.info("Streaming response")
        return StreamingResponse(generate(), media_type="text/event-stream")
    else:
        logger.info("Non-streaming response")
        full_response = ""
        async for chunk in generate():
            if chunk.startswith("data: ") and not chunk[6:].startswith("[DONE]"):
                # print(chunk)
                data = json.loads(chunk[6:])
                if data["choices"][0]["delta"].get("content"):
                    full_response += data["choices"][0]["delta"]["content"]
        
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(datetime.now().timestamp()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": full_response},
                    "finish_reason": "stop",
                }
            ],
            "usage": None,
        }



if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
