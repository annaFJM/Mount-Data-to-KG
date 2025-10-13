#!/bin/bash

# 快速清理测试节点脚本（新版）

echo "======================================================================"
echo "材料知识图谱 - 节点清理工具"
echo "======================================================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3"
    exit 1
fi

# 查找最新的 result 文件
latest_result=$(ls -t results/mount_result_*.json 2>/dev/null | head -1)

if [ -n "$latest_result" ]; then
    echo "找到最新的 result 文件:"
    echo "  $latest_result"
    echo ""
    echo "选择删除模式："
    echo "  1. 从 result 文件删除（推荐）"
    echo "  2. 从 cleanup 文件删除（旧版兼容）"
    echo ""
    read -p "请选择 (1/2，默认1): " choice
    
    if [ "$choice" = "2" ]; then
        # 使用旧版 cleanup 文件
        if [ ! -f "cleanup/new_data1.json" ]; then
            echo "ℹ️  没有找到挂载记录文件"
            echo "   文件位置: cleanup/new_data1.json"
            exit 0
        fi
        
        record_count=$(python3 -c "import json; print(len(json.load(open('cleanup/new_data1.json'))))" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo ""
            echo "找到 $record_count 条挂载记录（从 cleanup 文件）"
            echo ""
        fi
    fi
    
    echo ""
fi

# 运行删除脚本
python3 cleanup/delete_mounted_nodes.py

exit_code=$?

echo ""
if [ $exit_code -eq 0 ]; then
    echo "✅ 清理完成"
    echo ""
    echo "日志文件保存在: results/cleanup_log_*.txt"
    echo "删除记录保存在: results/deletion_record_*.json"
else
    echo "❌ 清理过程出现错误"
fi

exit $exit_code