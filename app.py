import os
import json
import mimetypes
import base64
import uuid
from urllib.parse import urlparse
from typing import Optional

import requests
import oss2
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="DMX GPT Image for Coze", version="1.0.0")

# DMX 绘图接口配置
DMX_API_KEY = os.getenv("DMX_API_KEY", "")
DMX_BASE_URL = os.getenv("DMX_BASE_URL", "https://www.dmxapi.cn")
DMX_MODEL = os.getenv("DMX_MODEL", "gpt-image-2-ssvip")

# 阿里云 OSS 配置
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")


# 请求参数模型
class GenerateRequest(BaseModel):
    prompt: str = Field(..., description="图片生成/修改提示词")
    image_url: Optional[str] = Field(default="", description="原图链接，不传则文生图，传则图生图/图片编辑")
    size: Optional[str] = Field(default="1024x1024", description="图片尺寸，如 1024x1024、1536x1024、1024x1536、2048x1152")


# 健康检测接口
@app.get("/health")
def health():
    return {"ok": True}


# 核心工具：base64 上传OSS，兼容低版本oss2，强制HTTPS
def upload_b64_to_oss(b64_str: str) -> str:
    if not all([OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, OSS_BUCKET_NAME]):
        raise Exception("服务未完整配置阿里云OSS环境变量，无法转换base64图片链接")

    auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
    # 兼容低版本oss2，拼接https://强制走443端口HTTPS，移除secure参数
    full_endpoint = f"https://{OSS_ENDPOINT}"
    bucket = oss2.Bucket(auth, full_endpoint, OSS_BUCKET_NAME)

    img_bytes = base64.b64decode(b64_str)
    file_key = f"draw/{uuid.uuid4()}.png"

    bucket.put_object(file_key, img_bytes, headers={"Content-Type": "image/png"})

    full_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{file_key}"
    return full_url


# 绘图主接口
@app.post("/generate")
def generate(req: GenerateRequest):
    if not DMX_API_KEY:
        return {"success": False, "image_url": "", "error": "服务器未配置 DMX_API_KEY"}

    prompt = (req.prompt or "").strip()
    image_url = (req.image_url or "").strip()
    size = req.size or "1024x1024"

    if not prompt:
        return {"success": False, "image_url": "", "error": "prompt不能为空"}

    try:
        # 文生图
        if not image_url:
            api_url = f"{DMX_BASE_URL}/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {DMX_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": DMX_MODEL,
                "prompt": prompt,
                "n": 1,
                "size": size
            }
            resp = requests.post(api_url, headers=headers, json=payload, timeout=600)
            run_mode = "text_to_image"

        # 图生图编辑
        else:
            img_download_resp = requests.get(image_url, timeout=60)
            img_download_resp.raise_for_status()

            filename = urlparse(image_url).path.split("/")[-1] or "input.png"
            mime_type = mimetypes.guess_type(filename)[0] or "image/png"

            api_url = f"{DMX_BASE_URL}/v1/images/edits"
            headers = {"Authorization": f"Bearer {DMX_API_KEY}"}
            form_data = {
                "model": DMX_MODEL,
                "prompt": prompt,
                "n": "1",
                "size": size
            }
            upload_files = {"image": (filename, img_download_resp.content, mime_type)}
            resp = requests.post(api_url, headers=headers, data=form_data, files=upload_files, timeout=600)
            run_mode = "image_to_image"

        # 解析DMX返回
        try:
            result = resp.json()
            print("====== DMX 原始返回数据 ======")
            print(result)
            print("============================")
        except Exception:
            return {
                "success": False,
                "image_url": "",
                "error": f"DMX接口返回非JSON格式：{resp.text[:1000]}",
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
        if isinstance(result, dict):
            if result.get("data") and len(result["data"]) > 0:
                item = result["data"][0]
                base64_data = item.get("b64_json")

                # 优先使用DMX原生直链
                if item.get("url"):
                    image_result_url = item["url"]
                elif item.get("image_url"):
                    image_result_url = item["image_url"]
                elif item.get("output_url"):
                    image_result_url = item["output_url"]
                # 只有base64时上传OSS转https链接
                elif base64_data:
                    image_result_url = upload_b64_to_oss(base64_data)
            else:
                image_result_url = (
                    result.get("url")
                    or result.get("image_url")
                    or result.get("output_url")
                    or ""
                )

        return {
            "success": bool(image_result_url),
            "image_url": image_result_url,
            "error": "" if image_result_url else "未获取到有效图片链接",
            "mode": run_mode,
            "raw": result
        }

    except Exception as e:
        return {"success": False, "image_url": "", "error": str(e)}
