<div align="center">

# 🔥 发烧AI · 角色扮演插件

✨ **将多个角色融入一个QQ账号，支持人格切换、合规验证、安全过滤** ✨

![License](https://img.shields.io/badge/license-AGPL--3.0-green?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python&logoColor=white)
![AstrBot](https://img.shields.io/badge/framework-AstrBot-ff6b6b?style=flat-square)
![Version](https://img.shields.io/github/v/release/awjdfsy/astrbot_plugin_fashaoairole_playing?style=flat-square)

</div>

---

## 📖 简介

**发烧AI角色切换器** 是一款为 [AstrBot](https://astrbot.app) 设计的角色扮演插件。它允许你将 **5种不同人格** 融入同一个QQ账号，用户可以通过简单指令自由切换人格，获得沉浸式的角色扮演体验。

内置 **合规验证**（含年龄验证）、**内容安全过滤**、**会话超时管理** 等功能，并提供了 **WebUI 管理页面**，方便查看用户数据和运行状态。

---

## 🚀 特性

- 🎭 **5种预设人格**：病娇、绿茶、傲娇小萝莉、知心姐姐、喊杂鱼的妹妹，各具特色的对话风格
- 🔄 **一键切换人格**：使用 `/fevers select` 指令随时切换
- 📋 **引导式设置流程**：首次使用自动进入交互式设置，引导用户完成合规验证
- 🛡️ **合规验证系统**：含用户协议确认 + 年龄验证，未通过则无法使用
- 🔒 **内容安全过滤**：可选的敏感内容过滤，保护对话安全
- ⏱️ **会话超时管理**：可配置超时时间，超时后自动退出当前人格
- 🌐 **WebUI 管理页面**：浏览器查看用户统计、活跃人格、运行日志（SSE 实时推送）
- ⚙️ **灵活配置**：支持选择 LLM 提供商、设置输出长度上限等

---

## 📋 人格列表

| # | 人格名称 | 风格描述 |
|:-:|:--------:|:---------|
| 1 | 🩸 **病娇** | 执着、偏激、占有欲强，对主人极度依恋 |
| 2 | 🍵 **绿茶** | 温柔体贴中带着心机，说话总是含沙射影 |
| 3 | 👸 **傲娇小萝莉** | 口是心非、傲娇可爱，明明关心你却嘴硬 |
| 4 | 💝 **知心姐姐** | 成熟温柔、善解人意，像大姐姐一样开导你 |
| 5 | 😈 **喊杂鱼的妹妹** | 毒舌抖S，一口一个"杂鱼"，把你踩在脚下 |

---

## 🔧 安装

### 方法一：通过 AstrBot 插件市场安装（推荐）

1. 打开 AstrBot WebUI → **插件市场**
2. 搜索 `发烧AI角色切换器` 或 `fashaoairole`
3. 点击 **安装**

### 方法二：手动安装

1. 克隆本仓库到 AstrBot 的 `data/plugins/` 目录：
   ```bash
   cd data/plugins/
   git clone https://github.com/awjdfsy/astrbot_plugin_fashaoairole_playing.git
   ```
2. 重启 AstrBot

### 方法三：直接下载 ZIP

1. 下载 [最新 Release](https://github.com/awjdfsy/astrbot_plugin_fashaoairole_playing/releases) 的 ZIP 包
2. 在 AstrBot WebUI → **插件管理** → **上传安装**

---

## ⚙️ 配置

在 AstrBot WebUI → **插件配置** 中找到本插件，可配置以下选项：

| 配置项 | 说明 | 默认值 |
|:-------|:-----|:-------|
| `select_provider` | 选择 LLM 提供商 | — |
| `output_max_length` | 输出最大 token 数 | `2048` |
| `session_timeout_minutes` | 会话超时时间（分钟） | `30` |
| `enable_safety_filter` | 启用内容安全过滤 | `true` |
| `compliance_text` | 用户协议文本 | 见默认配置 |
| `age_verification_required` | 是否要求年龄验证 | `true` |
| `persona_transition_enabled` | 允许人格过渡对话 | `true` |

---

## 💬 使用方法

### 指令列表

| 指令 | 说明 |
|:-----|:------|
| `/fevers help` | 查看帮助信息 |
| `/fevers start` | 开始人格选择流程 |
| `/fevers list` | 列出所有人格 |
| `/fevers select 1` | 选择指定人格（1-5） |
| `/fevers status` | 查看当前状态 |
| `/fevers exit` | 退出当前人格对话 |

### 首次使用流程

1. 发送 `/fevers start` 或直接与机器人对话
2. 阅读并同意 **用户协议**
3. 完成 **年龄验证**
4. 选择一个人格（1-5）
5. 开始角色扮演对话 ✨

### 使用提示

- 切换人格时，当前会话将自动保存
- 长时间不对话，会话会自动退出（超时时间可配置）
- 发送 `/fevers status` 查看当前激活的人格和超时倒计时

---

## 🖥️ WebUI 管理页面

安装后，在 AstrBot WebUI → **插件** 中找到本插件，点击 **管理** 即可进入。

管理页面提供以下功能：

- 📊 **运行统计**：总用户数、活跃用户数、今日对话次数
- 👥 **用户列表**：查看所有用户及其当前人格、会话状态
- 📝 **实时日志**：SSE 实时推送的系统运行日志

---

## 🗺️ 路线图

- [ ] 自定义人格创建（用户自行编写提示词）
- [ ] 更多预设人格
- [ ] 人格对话历史导出
- [ ] 多语言支持
- [ ] 群聊模式

---

## 📄 许可证

本项目基于 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源。

```
Copyright (C) 2024 awjdfsy

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

---

## 🙏 鸣谢

- [AstrBot](https://github.com/AstrBotDevs/AstrBot) — 强大的 AI 助手框架
- 所有参与测试和建议的朋友们 ❤️
