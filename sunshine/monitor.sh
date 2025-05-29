#!/bin/bash
echo "📊 Monitoring Sunshine processes..."
echo ""

while true; do
    clear
    echo "🌞 SUNSHINE PROCESS MONITOR"
    echo "=========================="
    echo ""
    
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        # Windows
        echo "Active Sunshine Processes:"
        tasklist | grep -E "(message_proxy|control_panel|test_subprocess)" | awk '{printf "  %-20s PID: %s\n", $1, $2}'
    else
        # Unix/Linux/Mac
        echo "Active Sunshine Processes:"
        ps aux | grep -E "(message_proxy|control_panel|test_subprocess)" | grep -v grep | awk '{printf "  %-20s PID: %s\n", $11, $2}'
    fi
    
    echo ""
    echo "Press Ctrl+C to exit monitor"
    sleep 2
done
