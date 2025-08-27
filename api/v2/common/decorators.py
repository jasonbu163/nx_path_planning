# api/v2/wcs/decorators.py

from functools import wraps
from fastapi import HTTPException
from .response import StandardResponse

def standard_response(func):
    """将路由函数返回值包装为标准响应格式的装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            # 如果已经返回了 StandardResponse，直接返回
            if isinstance(result, StandardResponse):
                return result
                
            # 否则包装为标准格式
            return StandardResponse.isSuccess(data=result)
        except HTTPException as e:
            raise e  # HTTPException 会让自定义处理器处理
        except Exception as e:
            # 处理其他未捕获异常
            return StandardResponse.isError(
                message="处理请求时发生错误",
                code=500,
                status="internal_server_error",
                data={"detail": str(e)}
            )
    return wrapper

def standard_response_sync(func):
    """将路由函数返回值包装为标准响应格式的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 如果已经返回了 StandardResponse，直接返回
            if isinstance(result, StandardResponse):
                return result
                
            # 否则包装为标准格式
            return StandardResponse.isSuccess(data=result)
        except HTTPException as e:
            raise e  # HTTPException 会让自定义处理器处理
        except Exception as e:
            # 处理其他未捕获异常
            return StandardResponse.isError(
                message="处理请求时发生错误",
                code=500,
                status="internal_server_error",
                data={"detail": str(e)}
            )
    return wrapper