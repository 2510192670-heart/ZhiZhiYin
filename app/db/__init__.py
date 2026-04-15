"""
智知因 - 数据初始化脚本
"""
import sys
sys.path.insert(0, '.')

from app.db.database import db_manager
from loguru import logger


def init_sample_data():
    """初始化示例数据"""

    # Python课程知识库示例
    python_knowledge = [
        {
            "course": "Python",
            "chapter": 1,
            "title": "变量与数据类型",
            "content": '''
## Python变量与数据类型

Python是一种动态类型语言，不需要显式声明变量类型。

### 基本数据类型
1. **整数(int)**：如 1, 42, -10
2. **浮点数(float)**：如 3.14, -0.5
3. **字符串(str)**：如 "Hello", 'World'
4. **布尔值(bool)**：True, False

### 变量命名规则
- 变量名只能包含字母、数字和下划线
- 变量名不能以数字开头
- 变量名区分大小写
- 不能使用Python关键字作为变量名

### 示例代码
```python
name = "Alice"  # 字符串
age = 20        # 整数
height = 1.65   # 浮点数
is_student = True  # 布尔值
```
'''
        },
        {
            "course": "Python",
            "chapter": 2,
            "title": "控制流",
            "content": '''
## Python控制流

### 条件语句
```python
if condition:
    # 满足条件时执行
elif another_condition:
    # 另一个条件满足时执行
else:
    # 以上都不满足时执行
```

### 循环语句

#### for循环
```python
for item in iterable:
    print(item)
```

#### while循环
```python
while condition:
    # 循环体
```

### break和continue
- **break**：立即退出循环
- **continue**：跳过当前迭代，进入下一次循环
'''
        },
        {
            "course": "Python",
            "chapter": 3,
            "title": "函数",
            "content": '''
## Python函数

### 函数定义
```python
def function_name(parameters):
    # 函数文档字符串
    # 函数体
    return result
```

### 参数类型
1. **位置参数**：按位置传递
2. **关键字参数**：按名称传递
3. **默认参数**：有默认值的参数
4. **可变参数**：*args, **kwargs

### 函数返回值
- 使用return语句返回值
- 没有return时返回None

### 示例
```python
def greet(name, greeting="Hello"):
    return f"{greeting}, {name}!"

result = greet("Alice")  # Hello, Alice!
```
'''
        },
        {
            "course": "Python",
            "chapter": 4,
            "title": "装饰器",
            "content": '''
## Python装饰器 (Decorator)

### 什么是装饰器
装饰器是一种高级Python特性，允许我们在不修改原函数的情况下，为函数添加新的功能。

### 简单装饰器
```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("函数执行前")
        result = func(*args, **kwargs)
        print("函数执行后")
        return result
    return wrapper

@my_decorator
def say_hello():
    print("Hello!")

say_hello()
# 输出:
# 函数执行前
# Hello!
# 函数执行后
```

### 带参数的装饰器
```python
def repeat(times):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for _ in range(times):
                func(*args, **kwargs)
        return wrapper
    return decorator

@repeat(3)
def greet():
    print("Hi!")

greet()  # 输出3次"Hi!"
```

### functools.wraps
使用@functools.wraps保留原函数的元信息：
```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper
```

### 装饰器的应用场景
1. 日志记录
2. 性能计时
3. 权限检查
4. 缓存
5. 输入验证
'''
        },
        {
            "course": "Python",
            "chapter": 5,
            "title": "闭包",
            "content": '''
## Python闭包 (Closure)

### 什么是闭包
闭包是指内部函数引用了外部函数的变量，即使外部函数已经执行完毕，这些变量依然被内部函数引用。

### 闭包示例
```python
def outer_function(msg):
    message = msg

    def inner_function():
        print(message)  # 引用外部变量

    return inner_function

# 创建闭包
my_func = outer_function("Hello")
my_func()  # 输出: Hello
```

### 闭包的条件
1. 必须有一个嵌套函数
2. 嵌套函数必须引用外部作用域的变量
3. 外部函数必须返回内部函数

### 闭包与装饰器的关系
装饰器本质上是闭包的一种应用。装饰器函数接收一个函数作为参数，并返回一个新函数。

```python
# 装饰器就是闭包的典型应用
def decorator(func):
    def wrapper(*args, **kwargs):
        # 可以在调用前添加功能
        result = func(*args, **kwargs)
        # 可以在调用后添加功能
        return result
    return wrapper
```

### 闭包与lambda
闭包可以与lambda表达式结合使用：
```python
def make_power_func(n):
    return lambda x: x ** n

square = make_power_func(2)
cube = make_power_func(3)

print(square(5))  # 25
print(cube(5))    # 125
```
'''
        }
    ]

    # 添加知识到向量库
    for item in python_knowledge:
        db_manager.add_knowledge(
            course=item["course"],
            chapter=item["chapter"],
            content=item["content"],
            source=f"Python基础教程 - {item['title']}",
            doc_type="concept",
            importance="核心"
        )

    logger.info("Python课程知识库初始化完成")


def create_demo_user():
    """创建演示用户"""
    demo_users = [
        {"student_id": "2024001", "name": "张三", "major": "计算机科学", "grade": "大二"},
        {"student_id": "2024002", "name": "李四", "major": "软件工程", "grade": "大一"},
        {"student_id": "2024003", "name": "王五", "major": "数据科学", "grade": "大三"},
    ]

    for user in demo_users:
        existing = db_manager.get_user_by_student_id(user["student_id"])
        if not existing:
            import uuid
            db_manager.create_user(
                user_id=str(uuid.uuid4()),
                **user
            )
            logger.info(f"创建演示用户: {user['name']}")


if __name__ == "__main__":
    print("=" * 50)
    print("智知因 - 数据初始化")
    print("=" * 50)

    print("\n1. 初始化知识库...")
    init_sample_data()

    print("\n2. 创建演示用户...")
    create_demo_user()

    print("\n初始化完成!")
    print("\n演示用户:")
    print("  学号: 2024001, 姓名: 张三")
    print("  学号: 2024002, 姓名: 李四")
    print("  学号: 2024003, 姓名: 王五")
