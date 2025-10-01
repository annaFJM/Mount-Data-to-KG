#!/bin/bash

# 材料知识图谱挂载系统 - 依赖安装脚本

echo "=================================="
echo "材料知识图谱挂载系统 - 依赖安装"
echo "=================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    echo "   请先安装 Python 3"
    exit 1
fi

echo "✅ 检测到 Python: $(python3 --version)"
echo ""

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ 错误：未找到 pip3"
    echo "   请先安装 pip"
    exit 1
fi

echo "✅ 检测到 pip: $(pip3 --version)"
echo ""

# 安装依赖包
echo "开始安装依赖包..."
echo ""

echo "1. 安装 neo4j..."
pip3 install neo4j
if [ $? -ne 0 ]; then
    echo "❌ neo4j 安装失败"
    exit 1
fi
echo "✅ neo4j 安装成功"
echo ""

echo "2. 安装 openai..."
pip3 install openai
if [ $? -ne 0 ]; then
    echo "❌ openai 安装失败"
    exit 1
fi
echo "✅ openai 安装成功"
echo ""

echo "=================================="
echo "所有依赖安装完成！"
echo "=================================="
echo ""
echo "下一步："
echo "1. 设置环境变量："
echo "   export DEEPSEEK_API_KEY='your_api_key'"
echo ""
echo "2. 修改 config.py 中的配置"
echo ""
echo "3. 运行程序："
echo "   bash run.sh"
echo "   或"
echo "   python3 main.py"
echo ""