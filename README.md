# DMX GPT Image Railway 部署版

## 文件说明

- `app.py`：FastAPI 服务代码
- `requirements.txt`：Python 依赖
- `Procfile`：Railway 启动命令
- `railway.json`：Railway 配置
- `coze_dmx_gpt_image_plugin.openapi.json`：扣子插件导入文件

## Railway 部署步骤

1. 新建一个 GitHub 仓库，例如 `dmx-gpt-image-coze`。
2. 把本文件夹里的所有文件上传到仓库根目录。
3. 打开 Railway，选择 `New Project`。
4. 选择 `Deploy from GitHub repo`。
5. 选择刚才的仓库。
6. 部署完成后，在 Railway 项目里找到 `Variables`，新增：

```text
DMX_API_KEY=你的DMX密钥
```

可选变量：

```text
DMX_BASE_URL=https://www.dmxapi.cn
DMX_MODEL=gpt-image-2-ssvip
```

7. 在 Railway 的 `Settings` 或 `Networking` 里生成公开域名。
8. 浏览器访问：

```text
https://你的Railway域名.up.railway.app/health
```

看到下面内容就成功：

```json
{"ok":true}
```

## 扣子插件导入

1. 打开 `coze_dmx_gpt_image_plugin.openapi.json`。
2. 把里面的：

```text
https://你的Railway域名.up.railway.app
```

替换成你的真实 Railway 域名。

3. 扣子：导入插件 → 本地文件 → 上传 JSON。
4. 授权方式选择：不需要授权。
5. 测试输入：

```json
{
  "prompt": "一只猫在雪山上",
  "size": "1024x1024"
}
```

图生图测试：

```json
{
  "prompt": "参考这张图，改成小红书封面风格",
  "image_url": "https://xxx.com/demo.png",
  "size": "1024x1024"
}
```
