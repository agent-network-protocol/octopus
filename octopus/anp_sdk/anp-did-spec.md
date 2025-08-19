## ANP DID-WBA 身份认证规范与使用指南

本指南面向需要在工程中集成 ANP 的 DID-WBA（Web-Based Attestation for DID）身份认证的开发者，基于本仓库 `anp_sdk/anp_auth` 中现有实现，说明“请求端（Client）”与“验证端（Server）”如何使用 `agent_connect` 模块完成认证，并给出可直接复制的代码示例。

文档中的示例代码遵循如下约定：
- 代码注释与日志使用英文；
- 示例使用 FastAPI 作为服务端框架，`aiohttp` 作为客户端 HTTP 库；
- JWT 使用 RS256，私钥签发、公网验签；
- 依赖 `agent_connect.authentication` 中的核心能力：
  - `DIDWbaAuthHeader`
  - `verify_auth_header_signature`
  - `resolve_did_wba_document`
  - `extract_auth_header_parts`
  - `create_did_wba_document`


### 1. 名词与流程概览

- DID-WBA Authorization Header：请求端基于 DID 文档与私钥生成的认证头，包含至少以下要素：`did`、`nonce`、`timestamp`、`verification_method`、`signature`（具体串行化由 `DIDWbaAuthHeader` 实现）。
- Nonce：一次性随机数，服务端采用“使用即作废 + 过期清理”的策略防止重放。
- Timestamp：请求时间戳，服务端校验时间窗口（默认 5 分钟）。
- JWT Bearer：服务端在 DID 校验成功后签发的短期访问令牌，后续请求可直接使用 `Authorization: Bearer <token>`。

认证流程（高层次）：
1) 客户端使用 `DIDWbaAuthHeader` 为目标 URL 生成 DID-WBA 认证头发起访问；
2) 服务器检测到非 Bearer 的 Authorization，则进入 DID 校验：解析 header → 校验时间戳与 nonce → 解析 DID 文档并验签；
3) 校验通过后，服务器生成 JWT（RS256）并随响应头返回（`authorization: bearer <token>`）；
4) 客户端保存该 token，后续请求可直接使用 Bearer 访问受保护资源；若 401 失效则清空并回退到 DID-WBA 重新获取。


### 2. 依赖与配置

建议的依赖（以 pip 为例）：
```
fastapi
uvicorn
aiohttp
pyjwt
pydantic-settings
agent_connect  # 提供 DID-WBA 的头部构造与验签、DID 文档解析等
```

核心配置项（参考 `octopus/config/settings.py`）：
- DID 相关
  - `nonce_expiration_minutes`：服务端 nonce 有效期（默认 5）
  - `timestamp_expiration_minutes`：时间戳有效期（默认 5）
  - `did_documents_path`：客户端生成 DID 文档与密钥的目录
  - `did_document_filename`：DID 文档文件名（`did.json`）
  - `local_port`：本地服务端口（用于生成示例 DID 文档中的回链）
- JWT 相关
  - `jwt_algorithm`：JWT 算法（RS256）
  - `access_token_expire_minutes`：JWT 过期时间（建议 30~120 分钟）
  - `jwt_private_key_path`：服务端私钥 PEM 文件路径（签发）
  - `jwt_public_key_path`：服务端公钥 PEM 文件路径（验签）


### 3. 验证端（Server）实现

本仓库提供了完整的 FastAPI 中间件实现，可直接复用：
- `octopus/anp_sdk/anp_auth/auth_middleware.py`
- `octopus/anp_sdk/anp_auth/did_auth.py`
- `octopus/anp_sdk/anp_auth/token_auth.py`
- `octopus/anp_sdk/anp_auth/jwt_keys.py`

要点：
- 统一入口中间件 `auth_middleware`：
  - 放行白名单路径（`EXEMPT_PATHS`）。
  - 非 Bearer 的 Authorization 头按 DID-WBA 流程处理；
  - Bearer 头使用公钥校验 JWT；
  - 通过后把 `authorization` 写回响应头，便于客户端提取。
- DID 校验逻辑（`did_auth.handle_did_auth`）：
  - 解析 header 得到 `did/nonce/timestamp/verification_method/signature`；
  - 验证时间戳窗口（`verify_timestamp`）；
  - 校验并登记 nonce（`is_valid_server_nonce`，一次性）；
  - 解析 DID 文档（`resolve_did_wba_document`）；
  - 使用文档与服务域名验签（`verify_auth_header_signature`）；
  - 生成 JWT 并返回（`token_auth.create_access_token`）。
- JWT 校验逻辑（`token_auth.handle_bearer_auth`）：
  - 提取 Bearer token；
  - 用公钥验签并检查 `sub/iat/exp` 与 DID 前缀；
  - 返回携带 `did` 的身份信息。

示例：将认证中间件接入 FastAPI（其他工程可参考）

```python
# app.py
from fastapi import FastAPI
from octopus.utils.log_base import setup_enhanced_logging
from octopus.anp_sdk.anp_auth.auth_middleware import auth_middleware


def create_app() -> FastAPI:
    # Initialize logging
    setup_enhanced_logging()

    app = FastAPI()

    # Register DID/JWT auth middleware
    app.middleware("http")(auth_middleware)

    @app.get("/v1/status")
    async def status():
        return {"status": "ok"}

    @app.get("/secure/me")
    async def me(request):
        # Example: read headers stored by middleware
        return {"headers": dict(request.state.headers)}

    return app


app = create_app()
```

注意：
- 确保 `settings.jwt_private_key_path` 与 `settings.jwt_public_key_path` 指向有效的 PEM 文件；
- 放行路径应根据自身工程需求调整（例如 `/docs`, `/openapi.json` 等）。


### 4. 请求端（Client）实现

客户端有两种常见方式：
1) 直接使用 `DIDWbaAuthHeader` 生成 DID-WBA 头并发起请求；
2) 复用本仓库提供的轻量封装 `ANPClient`，自动处理 token 缓存与 401 回退。

方式 A：直接使用 `DIDWbaAuthHeader`

```python
# client_direct.py
import asyncio
import aiohttp
from agent_connect.authentication import DIDWbaAuthHeader
from octopus.utils.log_base import setup_enhanced_logging


async def main():
    # Initialize logging
    setup_enhanced_logging()

    # Paths to DID document and private key
    did_document_path = "./did.json"
    private_key_path = "./key-1_private.pem"

    # Initialize DID-WBA client
    auth_client = DIDWbaAuthHeader(
        did_document_path=did_document_path,
        private_key_path=private_key_path,
    )

    url = "https://your-api.example.com/secure/me"

    # Build DID-WBA authorization header for the target URL
    headers = auth_client.get_auth_header(url)

    async with aiohttp.ClientSession() as session:
        # First request with DID-WBA (expect server to return Bearer in response headers)
        async with session.get(url, headers=headers) as resp:
            # Update token from response headers for subsequent calls
            auth_client.update_token(url, dict(resp.headers))
            data = await resp.json()
            print("First call status:", resp.status, "payload:", data)

        # Subsequent request can use Bearer automatically via get_auth_header
        headers2 = auth_client.get_auth_header(url)
        async with session.get(url, headers=headers2) as resp2:
            data2 = await resp2.json()
            print("Second call status:", resp2.status, "payload:", data2)


if __name__ == "__main__":
    asyncio.run(main())
```

方式 B：使用 `ANPClient`（本仓库封装）

```python
# client_anp.py
import asyncio
from octopus.utils.log_base import setup_enhanced_logging
from octopus.anp_sdk.anp_crawler.anp_client import ANPClient


async def main():
    setup_enhanced_logging()

    client = ANPClient(
        did_document_path="./did.json",
        private_key_path="./key-1_private.pem",
    )

    # Auto add DID-WBA header; on 401, ANPClient will clear token and retry with fresh DID
    result = await client.fetch_url("https://your-api.example.com/secure/me")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
```


### 5. DID 文档与私钥生成

可直接使用现成工具方法生成/加载 DID 文档与私钥（参考 `octopus/anp_sdk/anp_auth/did_auth.py` 中的 `generate_or_load_did`）：

```python
# did_bootstrap.py
import asyncio
from octopus.utils.log_base import setup_enhanced_logging
from octopus.anp_sdk.anp_auth.did_auth import generate_or_load_did


async def main():
    setup_enhanced_logging()

    # unique_id 可选，用于区分不同用户的 DID 存储目录
    did_document, keys, did_dir = await generate_or_load_did(unique_id="user01")
    print("DID document saved under:", did_dir)
    print("DID:", did_document.get("id"))


if __name__ == "__main__":
    asyncio.run(main())
```

说明：
- 函数会在配置的 `did_keys/user_<unique_id>/` 下生成 `did.json` 与对应的私钥 PEM；
- 其中私钥 PEM 文件名遵循 `#fragment` 命名（如 `keys-1_private.pem`）。


### 6. 服务端关键实现要点（参考实现）

以下逻辑已在仓库中提供，可直接复用或拷贝到其他工程：

- 路径豁免（`EXEMPT_PATHS`）：放行静态与健康检查；
- 鉴权入口（`verify_auth_header`）：
  - `Authorization` 缺失 → 401；
  - 非 Bearer → `handle_did_auth`；
  - Bearer → `handle_bearer_auth`；
- DID 校验：
  - `extract_auth_header_parts(authorization)` 解析头；
  - `verify_timestamp(ts)` 校验时间窗口；
  - `is_valid_server_nonce(nonce)` 防重放（一次性）；
  - `resolve_did_wba_document(did)` 获取 DID 文档；
  - `verify_auth_header_signature(auth_header, did_document, domain)` 验签；
  - `create_access_token({"sub": did})` 生成 Bearer；
- Bearer 校验：
  - 使用公钥 `jwt.decode(token, public_key, algorithms=["RS256"])`；
  - 校验 `sub/iat/exp` 与 DID 前缀；
  - 拒绝未来时间签发或已过期；
- 响应头透传：将 `authorization` 写回，便于客户端自动学习 token。


### 7. 端到端调用示例（最小可运行片段）

服务端：

```python
# server_minimal.py
from fastapi import FastAPI
from octopus.utils.log_base import setup_enhanced_logging
from octopus.anp_sdk.anp_auth.auth_middleware import auth_middleware


app = FastAPI()
setup_enhanced_logging()
app.middleware("http")(auth_middleware)


@app.get("/secure/ping")
async def secure_ping():
    return {"pong": True}
```

客户端：

```python
# client_minimal.py
import asyncio
import aiohttp
from agent_connect.authentication import DIDWbaAuthHeader


async def main():
    url = "http://127.0.0.1:8000/secure/ping"
    auth = DIDWbaAuthHeader(did_document_path="./did.json", private_key_path="./key-1_private.pem")

    async with aiohttp.ClientSession() as s:
        # First call with DID-WBA header
        h = auth.get_auth_header(url)
        async with s.get(url, headers=h) as r1:
            auth.update_token(url, dict(r1.headers))
            print("first:", r1.status, await r1.json())

        # Second call will use Bearer automatically
        h2 = auth.get_auth_header(url)
        async with s.get(url, headers=h2) as r2:
            print("second:", r2.status, await r2.json())


if __name__ == "__main__":
    asyncio.run(main())
```


### 8. 常见问题（FAQ）

- 时间戳校验失败：确保客户端与服务端时间同步，或适当放宽窗口（默认 5 分钟）。
- Nonce 重放被拒绝：每次请求都应由客户端生成新的 header；服务端会登记并拒绝重复。
- 响应头未返回 authorization：确认服务端在中间件中成功签发并写入响应头；
- JWT 验签失败：检查 `jwt_public_key_path` 与私钥配对是否正确，确认算法一致（RS256）。
- 401 后自动恢复：客户端应在 401 时清空缓存 token 并重新获取 DID-WBA 头（`clear_token(url)`）。


### 9. 安全与最佳实践

- 私钥仅存储在可信环境，避免写入公共仓库或镜像；
- 全程使用 HTTPS 传输；
- Bearer 的有效期要短、可续签；
- Nonce 存储采用“使用即作废 + 定期过期清理”；
- 服务端详细日志请避免记录完整签名内容，仅记录必要诊断信息。


### 10. 参考 API 索引（来自本仓库）

- 请求端
  - `agent_connect.authentication.DIDWbaAuthHeader`
    - `get_auth_header(url: str) -> dict`
    - `update_token(url: str, headers: dict) -> Optional[str]`
    - `clear_token(url: str) -> None`
  - `octopus.anp_sdk.anp_crawler.anp_client.ANPClient.fetch_url(...)`

- 验证端
  - `octopus.anp_sdk.anp_auth.auth_middleware.auth_middleware`
  - `octopus.anp_sdk.anp_auth.did_auth.handle_did_auth(authorization: str, domain: str)`
  - `octopus.anp_sdk.anp_auth.did_auth.get_and_validate_domain(request)`
  - `octopus.anp_sdk.anp_auth.token_auth.handle_bearer_auth(token: str)`
  - `octopus.anp_sdk.anp_auth.token_auth.create_access_token(data: dict, expires_delta: Optional[timedelta] = None)`
  - `octopus.anp_sdk.anp_auth.jwt_keys.get_jwt_private_key(path)` / `get_jwt_public_key(path)`


以上内容可作为其他工程接入 ANP DID-WBA 认证的模板。直接拷贝“服务端中间件 + 客户端最小示例”即可快速运行；如需更强的自动化（401 回退等），推荐使用 `ANPClient` 封装。
