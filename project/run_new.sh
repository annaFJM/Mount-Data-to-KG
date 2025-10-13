#!/bin/bash

# 材料知识图谱自动挂载系统 - 运行脚本 (Function Call 版本)

echo "======================================================================"
echo "材料知识图谱自动挂载系统 (Function Call 版本)"
echo "======================================================================"
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
    echo "❌ 错误：未设置 DEEPSEEK_API_KEY 环境变量"
    echo "   请运行: export DEEPSEEK_API_KEY='your_api_key'"
    exit 1
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

# 创建必要的目录
mkdir -p logs
mkdir -p results

echo "✅ 已创建日志和结果目录"
echo ""

# 运行主程序
echo "======================================================================"
echo "开始执行主程序..."
echo "======================================================================"
echo ""

python3 main.py

exit_code=$?

echo ""
echo "======================================================================"
if [ $exit_code -eq 0 ]; then
    echo "✅ 程序执行完成"
    echo ""
    echo "输出文件："
    echo "  - 日志目录: logs/"
    echo "  - 结果目录: results/"
    echo ""
    echo "最新文件："
    latest_log=$(ls -t logs/mount_log_*.log 2>/dev/null | head -1)
    latest_result=$(ls -t results/mount_result_*.json 2>/dev/null | head -1)
    if [ -n "$latest_log" ]; then
        echo "  - 日志: $latest_log"
    fi
    if [ -n "$latest_result" ]; then
        echo "  - 结果: $latest_result"
    fi
else
    echo "❌ 程序执行出错（退出码: $exit_code）"
    echo "   请查看日志文件获取详细信息"
fi
echo "======================================================================"

exit $exit_code