# ==================== 文件说明 ====================
# 这是缓存模块，提供内存缓存功能
# 使用抽象基类定义接口，方便未来扩展为 Redis 缓存等
# 缓存的作用：保存已经回答过的问题，避免重复计算，提高响应速度
#
# 本版关键变化：
# 1. 淘汰策略从"按 expire_at 最小"改为真正的 LRU（最近最少使用）
# 2. 不再在内部做 md5：调用方传入的字符串直接作为 key。
#    此前 GraphNodes._make_cache_key 已经 md5 过一次，
#    本模块又 md5 一次，造成双重 hash 和语义混淆。
# 3. 过期条目仍然是"惰性删除"：get 时发现过期才删，
#    另外 set 满了触发淘汰时，会顺带清理已过期条目。

# ==================== 导入依赖 ====================
import threading
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional

from core.logger import logger

# ==================== 抽象基类（接口定义） ====================
class BaseCache(ABC):
    """缓存抽象基类：定义缓存必须实现的方法"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        pass

# ==================== 内存缓存实现 ====================
class MemoryCache(BaseCache):
    """内存缓存实现：使用 OrderedDict 实现 LRU

    特点：
    1. 线程安全：使用锁保护并发访问
    2. 有限容量：超过最大容量时淘汰最久未使用的条目（LRU）
    3. 支持过期：每个缓存条目都有过期时间，get 时惰性删除
    """

    def __init__(self, max_size: int = 1000):
        """初始化内存缓存

        参数：
            max_size: 缓存最大条目数，超过后按 LRU 淘汰
        """
        self._store: "OrderedDict[str, dict]" = OrderedDict()
        self.max_size = max_size
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值

        命中时把条目移到末尾（标记为"最近使用"）；
        发现过期则删除并返回 None。

        参数：
            key: 缓存键（调用方负责保证唯一性）

        返回：
            缓存的 value（如果存在且未过期），否则 None
        """
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None

            if item["expire_at"] <= time.time():
                # 过期：删除并返回 None
                del self._store[key]
                return None

            # 命中：移到末尾，标记为最近使用
            self._store.move_to_end(key)
            return item["value"]

    def set(self, key: str, value: Any, ttl: int = 3600) -> None:
        """设置缓存值

        参数：
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认 1 小时
        """
        with self._lock:
            # 如果 key 已存在，先删掉，保证新插入在末尾
            if key in self._store:
                del self._store[key]

            # 容量已满：先清理过期条目，仍然满则按 LRU 淘汰最旧的
            if len(self._store) >= self.max_size:
                self._evict_locked()

            self._store[key] = {
                "value": value,
                "expire_at": time.time() + ttl,
            }

    def _evict_locked(self) -> None:
        """淘汰条目。调用方必须持有锁。

        策略：
        1. 遍历全部条目，删掉所有已过期的
        2. 如果仍然满，从头部（最久未使用）淘汰一个
        """
        now = time.time()

        # 遍历全部清理过期条目。
        # OrderedDict 的 expire_at 不保证单调递增，所以不能只扫头部。
        # 代价 O(n)，但只在 set 满容量时触发，可接受。
        expired_keys = [k for k, v in self._store.items() if v["expire_at"] <= now]
        for k in expired_keys:
            del self._store[k]

        if expired_keys:
            logger.info("cache_evicted_expired", count=len(expired_keys))

        # 仍然满，淘汰最久未使用（头部）
        if len(self._store) >= self.max_size and self._store:
            key, _ = self._store.popitem(last=False)
            logger.info("cache_eviction_lru", removed_key_prefix=key[:16])

    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self._store.clear()
            logger.info("cache_cleared")

    # -------------------- 观测辅助（可选） --------------------
    def stats(self) -> dict:
        """返回当前缓存统计，供 /health 或日志使用"""
        with self._lock:
            now = time.time()
            expired = sum(1 for v in self._store.values() if v["expire_at"] <= now)
            return {
                "size": len(self._store),
                "max_size": self.max_size,
                "expired": expired,
            }