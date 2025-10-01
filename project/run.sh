#!/bin/bash

# 材料知识图谱挂载系统 - 运行脚本

echo "=================================="
echo "材料知识图谱挂载系统"
echo "=================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    exit 1
fi

echo "✅ 检测到 Python: $(python3 --version)"
echo ""

# 检查环境变量
if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo "⚠️  警告：未设置 DEEPSEEK_API_KEY 环境变量"
    echo "   请运行: export DEEPSEEK_API_KEY='your_api_key'"
    echo "   或继续运行（将使用默认Prompt）"
    echo ""
    read -p "是否继续？(y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✅ 检测到 DEEPSEEK_API_KEY"
    echo ""
fi

# 检查必需的Python包
echo "检查依赖包..."
python3 -c "import neo4j" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少 neo4j 包"
    echo "   请运行: pip install neo4j"
    exit 1
fi

python3 -c "import openai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ 缺少 openai 包"
    echo "   请运行: pip install openai"
    exit 1
fi

echo "✅ 所有依赖包已安装"
echo ""

# 运行主程序
echo "=================================="
echo "开始执行主程序..."
echo "=================================="
echo ""

python3 main.py

echo ""
echo "=================================="
echo "程序执行完毕"
echo "=================================="