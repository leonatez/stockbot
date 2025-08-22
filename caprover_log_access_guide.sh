#!/bin/bash
# CapRover Log File Access Guide
# Replace YOUR_APP_NAME with your actual app name

APP_NAME="your-stockbot-app-name"  # Change this to your actual app name

echo "=== CapRover Log File Access Guide ==="
echo ""

echo "1. SSH into your CapRover server:"
echo "   ssh root@your-caprover-server.com"
echo ""

echo "2. Find your app container:"
echo "   docker ps | grep $APP_NAME"
echo ""

echo "3. Get container ID and exec into it:"
echo "   CONTAINER_ID=\$(docker ps | grep $APP_NAME | awk '{print \$1}')"
echo "   docker exec -it \$CONTAINER_ID /bin/bash"
echo ""

echo "4. Navigate to logs directory:"
echo "   cd /app/logs"
echo "   ls -la"
echo ""

echo "5. Check available log directories:"
echo "   ls -la debug/ holistic_analysis/"
echo ""

echo "6. Read latest JSON files:"
echo "   # Debug logs"
echo "   ls -t debug/*.json | head -1 | xargs cat | jq ."
echo ""
echo "   # Holistic analysis logs"
echo "   ls -t holistic_analysis/*.json | head -1 | xargs cat | jq ."
echo ""

echo "7. Copy files to host (from CapRover server, not inside container):"
echo "   docker cp \$CONTAINER_ID:/app/logs/debug/ ./debug_logs/"
echo "   docker cp \$CONTAINER_ID:/app/logs/holistic_analysis/ ./holistic_logs/"
echo ""

echo "=== Quick Commands ==="
echo ""
echo "# One-liner to read latest debug JSON:"
echo "docker exec \$(docker ps | grep $APP_NAME | awk '{print \$1}') sh -c 'ls -t /app/logs/debug/*.json 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo \"No debug logs found\"'"
echo ""

echo "# One-liner to read latest holistic analysis JSON:"
echo "docker exec \$(docker ps | grep $APP_NAME | awk '{print \$1}') sh -c 'ls -t /app/logs/holistic_analysis/*.json 2>/dev/null | head -1 | xargs cat 2>/dev/null || echo \"No holistic logs found\"'"
echo ""

echo "# Download all logs to local machine:"
echo "mkdir -p ./downloaded_logs"
echo "docker cp \$(docker ps | grep $APP_NAME | awk '{print \$1}'):/app/logs/ ./downloaded_logs/"