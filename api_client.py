"""
通用 API 客户端模块
提供带有重试机制、异常处理和日志记录的 HTTP 请求封装
从 .env 文件读取第三方API配置
"""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional
import aiohttp
import json
from dataclasses import dataclass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logger = logging.getLogger(__name__)


@dataclass
class ApiResponse:
    """API 响应数据类"""

    success: bool
    data: Any = None
    error: str = None
    status_code: int = None
    response_time: float = None


class ThirdPartyApiClient:
    """
    第三方 API 客户端
    从 .env 文件读取配置
    """

    def __init__(self, base_url: str = None):
        # 从 .env 读取配置
        self.base_url = (
            base_url or os.getenv("THIRD_PARTY_API_URL", "https://api.zmone.me/v1")
        ).rstrip("/")
        self.api_key = os.getenv("THIRD_PARTY_API_KEY", "")
        self.timeout = int(os.getenv("THIRD_PARTY_API_TIMEOUT", "30"))
        self.max_retries = int(os.getenv("THIRD_PARTY_API_MAX_RETRIES", "3"))
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """获取或创建 aiohttp 会话"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """
        执行 HTTP 请求

        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE)
            endpoint: API 端点
            headers: 请求头
            data: 请求体数据
            params: URL 参数

        Returns:
            ApiResponse: 封装的响应结果
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        session = await self._get_session()

        # 默认请求头
        default_headers = {
            "Content-Type": "application/json",
            "User-Agent": "KHL-Bot-ApiClient/1.0",
        }

        # 如果有API密钥，添加认证头
        if self.api_key:
            default_headers["Authorization"] = f"Bearer {self.api_key}"

        # 合并用户提供的请求头
        if headers:
            default_headers.update(headers)

        start_time = time.time()

        try:
            async with session.request(
                method=method,
                url=url,
                headers=default_headers,
                json=data if data else None,
                params=params,
            ) as response:
                response_time = time.time() - start_time

                try:
                    response_data = await response.json()
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    response_data = await response.text()

                if response.status == 200:
                    logger.info(
                        f"API 请求成功: {method} {url} (耗时: {response_time:.2f}s)"
                    )
                    return ApiResponse(
                        success=True,
                        data=response_data,
                        status_code=response.status,
                        response_time=response_time,
                    )
                else:
                    error_msg = f"HTTP {response.status}: {response_data}"
                    logger.warning(f"API 请求失败: {error_msg}")
                    return ApiResponse(
                        success=False,
                        error=error_msg,
                        status_code=response.status,
                        response_time=response_time,
                    )

        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            error_msg = f"请求超时 (>{self.timeout}s)"
            logger.error(f"API 请求超时: {method} {url}")
            return ApiResponse(
                success=False, error=error_msg, response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = f"请求异常: {str(e)}"
            logger.error(f"API 请求异常: {method} {url} - {error_msg}")
            return ApiResponse(
                success=False, error=error_msg, response_time=response_time
            )

    async def _make_request_with_retry(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """
        带重试机制的请求方法
        对 HTTP 500 错误进行最多 3 次重试，使用指数退避策略
        """
        last_response = None

        for attempt in range(self.max_retries + 1):
            response = await self._make_request(method, endpoint, headers, data, params)

            # 请求成功或非 500 错误，直接返回
            if response.success or (
                response.status_code and response.status_code != 500
            ):
                return response

            last_response = response

            # 如果是最后一次尝试，不再重试
            if attempt == self.max_retries:
                break

            # 指数退避：2^attempt 秒
            wait_time = 2**attempt
            logger.warning(
                f"HTTP 500 错误，{wait_time}秒后进行第{attempt + 2}次重试..."
            )
            await asyncio.sleep(wait_time)

        # 所有重试都失败
        logger.error(f"API 请求在 {self.max_retries + 1} 次尝试后仍然失败")
        return last_response or ApiResponse(success=False, error="所有重试尝试都失败")

    async def get(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """GET 请求"""
        return await self._make_request_with_retry(
            "GET", endpoint, headers, None, params
        )

    async def post(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """POST 请求"""
        return await self._make_request_with_retry(
            "POST", endpoint, headers, data, params
        )

    async def put(
        self,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """PUT 请求"""
        return await self._make_request_with_retry(
            "PUT", endpoint, headers, data, params
        )

    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict] = None,
    ) -> ApiResponse:
        """DELETE 请求"""
        return await self._make_request_with_retry(
            "DELETE", endpoint, headers, None, params
        )

    async def close(self):
        """关闭 HTTP 会话"""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("API 客户端会话已关闭")


# 全局 API 客户端实例
_api_client = ThirdPartyApiClient()


async def third_party_api_call(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict] = None,
) -> ApiResponse:
    """
    统一的第三方 API 调用函数

    Args:
        endpoint: API 端点 (如: '/users', '/data')
        method: HTTP 方法
        data: 请求数据
        headers: 请求头
        params: URL 参数

    Returns:
        ApiResponse: 响应结果

    Example:
        >>> response = await third_party_api_call('/users', 'GET')
        >>> if response.success:
        >>>     print(response.data)
        >>> else:
        >>>     print(f"错误: {response.error}")
    """
    method = method.upper()

    if method == "GET":
        return await _api_client.get(endpoint, headers, params)
    elif method == "POST":
        return await _api_client.post(endpoint, data, headers, params)
    elif method == "PUT":
        return await _api_client.put(endpoint, data, headers, params)
    elif method == "DELETE":
        return await _api_client.delete(endpoint, headers, params)
    else:
        return ApiResponse(success=False, error=f"不支持的 HTTP 方法: {method}")


# 便捷函数
async def get_user_info(user_id: str) -> ApiResponse:
    """获取用户信息"""
    return await third_party_api_call(f"/users/{user_id}")


async def create_user(user_data: Dict) -> ApiResponse:
    """创建用户"""
    return await third_party_api_call("/users", "POST", data=user_data)


async def update_user(user_id: str, user_data: Dict) -> ApiResponse:
    """更新用户信息"""
    return await third_party_api_call(f"/users/{user_id}", "PUT", data=user_data)


async def delete_user(user_id: str) -> ApiResponse:
    """删除用户"""
    return await third_party_api_call(f"/users/{user_id}", "DELETE")


# 资源清理函数
async def cleanup_api_client():
    """清理 API 客户端资源"""
    await _api_client.close()


# === LLM专用API调用函数 ===


async def llm_chat_completion(
    model: str, messages: list, api_key: str, **kwargs
) -> ApiResponse:
    """
    LLM聊天完成API调用

    Args:
        model: 模型名称
        messages: 消息列表
        api_key: API密钥
        **kwargs: 其他参数(temperature, max_tokens等)

    Returns:
        ApiResponse: LLM响应结果
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    data = {"model": model, "messages": messages, **kwargs}

    return await third_party_api_call(
        endpoint="/chat/completions", method="POST", data=data, headers=headers
    )


async def llm_embeddings(model: str, input_text: str, api_key: str) -> ApiResponse:
    """
    获取文本嵌入向量

    Args:
        model: 嵌入模型名称
        input_text: 输入文本
        api_key: API密钥

    Returns:
        ApiResponse: 嵌入向量响应
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    data = {"model": model, "input": input_text}

    return await third_party_api_call(
        endpoint="/embeddings", method="POST", data=data, headers=headers
    )


# === 通用第三方服务API ===


async def webhook_call(
    webhook_url: str, data: dict, headers: dict = None
) -> ApiResponse:
    """
    通用Webhook调用

    Args:
        webhook_url: Webhook完整URL
        data: 发送数据
        headers: 请求头

    Returns:
        ApiResponse: Webhook响应
    """
    # 创建临时客户端实例，使用自定义URL
    temp_client = ThirdPartyApiClient(base_url=webhook_url.rsplit("/", 1)[0])
    endpoint = "/" + webhook_url.rsplit("/", 1)[1]

    try:
        return await temp_client.post(endpoint, data, headers)
    finally:
        await temp_client.close()


async def health_check() -> ApiResponse:
    """
    API健康检查

    Returns:
        ApiResponse: 健康状态响应
    """
    return await third_party_api_call("/health", "GET")
