import os
import json
import mimetypes
from urllib.parse import urlparse

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="DMX GPT Image for Coze", version="1.0.0")

DMX_API_KEY = os.getenv("DMX_API_KEY", "")
DMX_BASE_URL = os.getenv("DMX_BASE_URL", "https://www.dmxapi.cn")
DMX_MODEL = os.getenv("DMX_MODEL", "gpt-image-2-ssvip")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="图片生成/修改提示词")
    image_url: str | None = Field(default="", description="原图链接，不传则文生图，传则图生图/图片编辑")
    size: str | None = Field(default="1024x1024", description="图片尺寸，如 1024x1024、1536x1024、1024x1536、2048x1152")
    quality: str | None = Field(default="high", description="图片质量")
    output_format: str | None = Field(default="png", description="输出格式：png/jpeg/webp")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/generate")
def generate(req: GenerateRequest):
    if not DMX_API_KEY:
        return {"success": False, "image_url": "", "error": "服务器未配置 DMX_API_KEY"}

    prompt = (req.prompt or "").strip()
    image_url = (req.image_url or "").strip()
    size = req.size or "1024x1024"
    quality = req.quality or "high"
    output_format = req.output_format or "png"

    if not prompt:
        return {"success": False, "image_url": "", "error": "prompt不能为空"}

    try:
        if not image_url:
            url = f"{DMX_BASE_URL}/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {DMX_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": DMX_MODEL,
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": quality,
                "output_format": output_format
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=180)
            mode = "text_to_image"
        else:
            img_resp = requests.get(image_url, timeout=60)
            img_resp.raise_for_status()

            filename = urlparse(image_url).path.split("/")[-1] or "image.png"
            mime_type = mimetypes.guess_type(filename)[0] or "image/png"

            url = f"{DMX_BASE_URL}/v1/images/edits"
            headers = {"Authorization": f"Bearer {DMX_API_KEY}"}
            data = {
                "model": DMX_MODEL,
                "prompt": prompt,
                "n": "1",
                "size": size,
                "quality": quality,
                "output_format": output_format
            }
            files = {"image": (filename, img_resp.content, mime_type)}
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=180)
            mode = "image_to_image"

        try:
            result = resp.json()
        except Exception:
            return {
                "success": False,
                "image_url": "",
                "error": "DMX返回不是JSON：" + resp.text[:1000],
                "status_code": resp.status_code,
            }

        if resp.status_code >= 400:
            return {
                "success": False,
                "image_url": "",
                "error": json.dumps(result, ensure_ascii=False),
                "status_code": resp.status_code,
            }

        image_result_url = ""
        if isinstance(result, dict) and result.get("data"):
            item = result["data"][0]
            image_result_url = item.get("url") or item.get("b64_json") or ""

        if image_result_url:
            return {"success": True, "image_url": image_result_url, "error": "", "mode": mode}

        return {
            "success": False,
            "image_url": "",
            "error": "没有拿到图片URL：" + json.dumps(result, ensure_ascii=False),
        }

    except Exception as e:
        return {"success": False, "image_url": "", "error": str(e)}
