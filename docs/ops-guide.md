# 运维与故障排查

> 最后更新: 2026-04-03

## 日常运维

### 查看推送记录
```bash
# 查看已推送文章数量
python -c "import json; d=json.load(open('seen.json')); print(f'已记录 {len(d[\"seen\"])} 篇')"
```

### 手动触发推送
```bash
.\.venv\Scripts\activate
python -m src.main
```

### 重置去重记录
删除 `seen.json` 文件，下次推送会当作全新处理。

---

## 定时任务管理

### 查看当前任务
```powershell
Get-ScheduledTask | Where-Object { $_.TaskName -like "AI-News*" }
```

### 暂停任务 (不禁用)
```powershell
Disable-ScheduledTask -TaskName "AI-News-Morning"
Disable-ScheduledTask -TaskName "AI-News-Evening"
```

### 恢复任务
```powershell
Enable-ScheduledTask -TaskName "AI-News-Morning"
Enable-ScheduledTask -TaskName "AI-News-Evening"
```

### 删除任务
```powershell
.\stop-tasks.bat
```

### 重新注册
```powershell
.\start-tasks.bat
```

---

## 常见问题

### 推送失败

**症状**: 飞书群收到告警消息，或日志显示错误。

**排查步骤**:
1. 检查 `.env` 中 `FEISHU_WEBHOOK_URL` 是否正确
2. 检查网络是否能访问 `open.feishu.cn`
3. 检查飞书机器人是否被群主删除

### AI 摘要生成失败

**症状**: 日志显示 `LLM 调用失败` 或超时。

**排查步骤**:
1. 检查 `.env` 中 `NVIDIA_API_KEY` 是否正确
2. 检查网络是否能访问 `integrate.api.nvidia.com`
3. NVIDIA 免费额度是否用完 (登录 build.nvidia.com 查看)

### RSS 源抓不到内容

**症状**: 日志显示 `→ 无内容` 或 `→ 网络错误`。

**排查步骤**:
1. 浏览器直接访问 RSS URL，确认是否可用
2. 检查是否是 DNS 解析问题 (`ping 域名`)
3. 如果是境外源，可能是网络问题，考虑替换

### 电脑关机导致任务跳过

**症状**: 某天没有收到推送。

**原因**: Windows 任务计划依赖开机状态。

**解决方案**:
- 保持电脑在推送时间点开机
- 或迁移到 GitHub Actions / 云服务器 (24/7 运行)

### seen.json 文件过大

**症状**: 文件超过几 MB。

**解决**: 去重模块自动限制最多 2000 条，一般不会过大。如果确实过大，删除后重新生成即可。

---

## 日志查看

Windows 任务计划执行日志：
1. 打开 `taskschd.msc`
2. 找到 `AI-News-Morning` 任务
3. 点击右侧 **历史记录** 标签

手动运行的日志直接输出到终端。
