#!/bin/bash

# 快速清理测试节点脚本

echo "=================================="
echo "清理测试挂载的节点"
echo "=================================="
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    exit 1
fi

# 检查记录文件是否存在
if [ ! -f "cleanup/new_data1.json" ]; then
    echo "ℹ️  没有找到挂载记录文件"
    echo "   文件位置: cleanup/new_data1.json"
    exit 0
fi

# 显示记录数量
record_count=$(python3 -c "import json; print(len(json.load(open('cleanup/new_data1.json'))))" 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "找到 $record_count 条挂载记录"
    echo ""
else
    echo "⚠️  无法读取记录文件"
    exit 1
fi

# 运行删除脚本
python3 cleanup/delete_mounted_nodes.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ 清理完成"
else
    echo "❌ 清理过程出现错误"
fi

exit $exit_code