# Efficient Thread Pool Usage in Python

## Overview
This guide demonstrates best practices for creating and using thread pools efficiently, based on optimizations made to your `LabellingModelOrchestrator` class.

## Key Principles

### 1. **Reuse Thread Pools Instead of Creating New Ones**
```python
# ❌ Bad - Creates new thread pools repeatedly
def process_files(files):
    for file in files:
        with ThreadPoolExecutor(max_workers=4) as executor:
            # Process file...

# ✅ Good - Reuse persistent thread pools
class Processor:
    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=4)
    
    def __del__(self):
        self._pool.shutdown(wait=True)
```

### 2. **Optimal Worker Count Selection**
```python
import os

# For CPU-bound tasks
cpu_workers = min(32, os.cpu_count() or 1)

# For I/O-bound tasks (network, file I/O, ML inference)
io_workers = min(32, (os.cpu_count() or 1) * 2)

# For mixed workloads
mixed_workers = os.cpu_count() or 1
```

### 3. **Use Multiple Specialized Thread Pools**
```python
class OptimizedProcessor:
    def __init__(self):
        # Different pools for different types of work
        self._main_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="main")
        self._inference_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="inference")
        self._io_pool = ThreadPoolExecutor(max_workers=16, thread_name_prefix="io")
```

## Advanced Patterns

### 1. **Pipeline Processing**
```python
def pipeline_process(self, data):
    # Phase 1: Data loading
    main_pool = self.get_main_pool()
    load_future = main_pool.submit(self._load_data, data)
    processed_data = load_future.result()
    
    # Phase 2: Parallel inference
    inference_pool = self.get_inference_pool()
    inference_tasks = [
        ('task1', self._inference_func1),
        ('task2', self._inference_func2),
        # ... more tasks
    ]
    
    futures = {
        name: inference_pool.submit(func, processed_data)
        for name, func in inference_tasks
    }
    
    # Collect results efficiently
    results = {}
    for name, future in futures.items():
        results[name] = future.result()
    
    return results
```

### 2. **Batch Processing with as_completed**
```python
def batch_process(self, items, max_workers=None):
    if max_workers is None:
        max_workers = min(len(items), os.cpu_count() or 1)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        futures = {
            item: executor.submit(self._process_item, item)
            for item in items
        }
        
        # Process results as they complete (more efficient)
        results = {}
        for future in concurrent.futures.as_completed(futures.values()):
            for item, item_future in futures.items():
                if item_future == future:
                    try:
                        results[item] = future.result()
                    except Exception as e:
                        logger.error(f"Error processing {item}: {e}")
                        results[item] = None
                    break
        
        return results
```

### 3. **Thread-Safe Operations**
```python
class ThreadSafeProcessor:
    def __init__(self):
        self._data_lock = threading.Lock()
        self._shared_resource = None
    
    def _safe_operation(self, data):
        with self._data_lock:
            # Thread-safe access to shared resources
            self._shared_resource = self._load_resource(data)
        
        # Process without lock
        return self._process(self._shared_resource)
```

## Performance Optimization Tips

### 1. **Submit All Tasks Before Collecting Results**
```python
# ✅ Good - Submit all first, then collect
futures = [executor.submit(func, arg) for arg in args]
results = [future.result() for future in futures]

# ❌ Bad - Submit and wait one by one
results = []
for arg in args:
    future = executor.submit(func, arg)
    results.append(future.result())  # Blocks here
```

### 2. **Use Thread Naming for Debugging**
```python
executor = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="my_pool"  # Helps with debugging
)
```

### 3. **Graceful Shutdown**
```python
class ProcessorWithCleanup:
    def __init__(self):
        self._pool = ThreadPoolExecutor(max_workers=4)
    
    def shutdown(self, wait=True):
        """Explicitly shutdown thread pool"""
        if self._pool:
            self._pool.shutdown(wait=wait)
    
    def __del__(self):
        self.shutdown(wait=True)
```

### 4. **Error Handling in Parallel Processing**
```python
def robust_parallel_process(self, items):
    with ThreadPoolExecutor() as executor:
        futures = {
            item: executor.submit(self._process_item, item)
            for item in items
        }
        
        results = {}
        for item, future in futures.items():
            try:
                results[item] = future.result(timeout=30)  # Add timeout
            except TimeoutError:
                logger.error(f"Timeout processing {item}")
                results[item] = None
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                results[item] = None
        
        return results
```

## Memory and Resource Management

### 1. **Limit Concurrent Memory Usage**
```python
def memory_efficient_batch(self, large_items, max_concurrent=4):
    """Process large items with memory constraints"""
    results = []
    
    # Process in chunks to limit memory usage
    for i in range(0, len(large_items), max_concurrent):
        chunk = large_items[i:i + max_concurrent]
        
        with ThreadPoolExecutor(max_workers=len(chunk)) as executor:
            futures = [executor.submit(self._process_large_item, item) for item in chunk]
            chunk_results = [future.result() for future in futures]
            results.extend(chunk_results)
    
    return results
```

### 2. **Resource Pooling**
```python
from queue import Queue

class ResourcePool:
    def __init__(self, create_resource_func, pool_size=4):
        self._pool = Queue()
        for _ in range(pool_size):
            self._pool.put(create_resource_func())
    
    def get_resource(self):
        return self._pool.get()
    
    def return_resource(self, resource):
        self._pool.put(resource)

# Usage
resource_pool = ResourcePool(lambda: expensive_model_loader(), pool_size=4)

def process_with_pooled_resource(self, data):
    resource = resource_pool.get_resource()
    try:
        return resource.process(data)
    finally:
        resource_pool.return_resource(resource)
```

## Benchmarking and Monitoring

### 1. **Performance Measurement**
```python
import time
from contextlib import contextmanager

@contextmanager
def timer(description):
    start = time.time()
    yield
    end = time.time()
    print(f"{description} took {end - start:.2f} seconds")

# Usage
with timer("Parallel processing"):
    results = self.batch_process(items)
```

### 2. **Thread Pool Monitoring**
```python
def monitor_thread_pool(self):
    """Get thread pool statistics"""
    if hasattr(self._pool, '_threads'):
        active_threads = len([t for t in self._pool._threads if t.is_alive()])
        return {
            'active_threads': active_threads,
            'max_workers': self._pool._max_workers,
            'queue_size': self._pool._work_queue.qsize()
        }
    return None
```

## Real-World Example: Your Optimized Implementation

Your updated `LabellingModelOrchestrator` demonstrates several best practices:

1. **Reusable Thread Pools**: `_main_pool` and `_inference_pool` are created once and reused
2. **Specialized Pools**: Different pools for different types of work (main processing vs inference)
3. **Thread Safety**: `_audio_lock` protects shared audio data
4. **Efficient Batching**: `batch_label_audio_optimized` processes multiple files efficiently
5. **Proper Cleanup**: `__del__` method ensures thread pools are shut down

The optimized version should show significant performance improvements, especially when processing multiple files, because:
- Thread pool creation overhead is eliminated
- Better resource utilization with specialized pools
- More efficient task scheduling and result collection

## When NOT to Use Thread Pools

- **CPU-bound tasks in CPython**: Use `ProcessPoolExecutor` instead due to GIL
- **Very short tasks**: Thread overhead might exceed task duration
- **Memory-intensive tasks**: May cause memory pressure with too many concurrent tasks
- **Tasks requiring strict ordering**: Consider serial processing or use queues

## Summary

Efficient thread pool usage requires:
1. Reusing thread pools instead of creating them repeatedly
2. Choosing appropriate worker counts based on task type
3. Using specialized pools for different workloads
4. Implementing proper error handling and resource management
5. Monitoring performance and adjusting based on real-world usage

Your optimized implementation demonstrates these principles and should provide significant performance improvements for your ML inference workloads.
