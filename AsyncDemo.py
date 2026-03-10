
import random
import time
import asyncio

## =========================================================
## 同步操作

def sync_process_item(item: str):
    """
    模拟耗时的操作
    """
    print(f"处理中: {item}")
    process_time = random.uniform(0.5, 2.0)
    time.sleep(process_time)
    return f"处理完成: {item}, 处理时长: {process_time:.2f}s"

def sync_process_all_items():
    """
    模拟同步串行执行耗时操作
    """
    items = ["任务1", "任务2", "任务3", "任务4"]
    results = []
    for item in items:
        result = sync_process_item(item)
        results.append(result)
    return results

def unit_test_sync_sequence_operation():
    """
    同步串行执行操作的测试用例
    """
    startTime = time.time()
    results = sync_process_all_items()
    print("\n".join(results))
    endTime = time.time()
    print(f"总耗时: {endTime - startTime:.2f}s")

## =========================================================
## async/await 基于协程实现异步

async def async_process_item(item):
    """
    模拟异步执行耗时的操作
    """
    print(f"处理中: {item}")
    process_time = random.uniform(0.5, 2.0)
    try:
        await asyncio.wait_for( ## 设置超时
            asyncio.sleep(process_time), ## await 等待异步操作完成
            1.0
        )
        return f"处理完成: {item}, 处理时长: {process_time:.2f}s"
    except TimeoutError as e:
        return f"处理超时: {item}, 异常信息: {e}"

async def async_process_all_items():
    """
    模拟异步串行执行耗时操作
    """
    items = ["任务1", "任务2", "任务3", "任务4"]
    tasks = [asyncio.create_task(async_process_item(item)) for item in items]
    results = await asyncio.gather(*tasks)
    return results

async def unit_test_async_sequence_operation():
    """
    异步执行操作的测试用例
    """
    startTime = time.time()
    results = await async_process_all_items()
    print("\n".join(results))
    endTime = time.time()
    print(f"总耗时: {endTime - startTime:.2f}s")

## =========================================================
## 异步上下文

class AsyncResource():
    """
    异步上下文
    """
    async def __aenter__(self):
        """
        异步初始化资源
        """
        print("初始化异步资源...")
        await asyncio.sleep(0.1)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """
        异步清理资源
        """
        print("清理异步资源...")
        await asyncio.sleep(0.1)

    async def process(self, item):
        """
        模拟异步执行耗时的操作
        """
        print(f"处理中: {item}")
        process_time = random.uniform(0.5, 2.0)
        try:
            await asyncio.wait_for( ## 设置超时
                asyncio.sleep(process_time), ## await 等待异步操作完成
                2.0
            )
            return f"处理完成: {item}, 处理时长: {process_time:.2f}s"
        except TimeoutError as e:
            return f"处理超时: {item}, 异常信息: {e}" 
        
async def unit_test_async_context():
    items = ["任务1", "任务2", "任务3", "任务4"]
    startTime = time.time()
    async with AsyncResource() as resource:
        tasks = [asyncio.create_task(resource.process(item)) for item in items] 
        results = await asyncio.gather(*tasks)
    endTime = time.time()
    print("\n".join(results))
    print(f"总耗时: {endTime - startTime:.2f}s")

if __name__ == "__main__":
    ## 同步执行耗时操作，等于所有任务执行的总时长
    unit_test_sync_sequence_operation()
    print("=" * 40)
    ## 协程执行耗时操作，基于近似于最长执行任务的时长
    asyncio.run(unit_test_async_sequence_operation())
    print("=" * 40)
    ## 异步上下文资源管理器
    asyncio.run(unit_test_async_context())
    print("=" * 40)

