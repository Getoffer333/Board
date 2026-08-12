#!/bin/bash
# 注册 macOS 开机自启（launchd LaunchAgent），服务常驻后台，避免进程被回收。
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/com.jobseeker.workbench.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.jobseeker.workbench</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SCRIPT_DIR/start.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$SCRIPT_DIR/..</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$SCRIPT_DIR/../data/server.log</string>
  <key>StandardErrorPath</key>
  <string>$SCRIPT_DIR/../data/server.log</string>
</dict>
</plist>
EOF

launchctl load "$PLIST" 2>/dev/null || launchctl bootstrap gui/$(id -u) "$PLIST" 2>/dev/null || true
echo "已安装开机自启。浏览器打开 http://localhost:7788 即可使用。"
echo "停止：launchctl unload $PLIST"
