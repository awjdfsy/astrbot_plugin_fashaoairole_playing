"""Fevers AI - Multi-persona role-playing plugin for AstrBot.

This plugin provides a persona switching system with 5 character roles,
compliance verification, age verification, content safety filtering,
and a unified output format.
"""

import asyncio
import json
import time
from pathlib import Path

from personas import PERSONAS

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api.web import (
    error_response,
    json_response,
    request,
    stream_response,
)
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

PLUGIN_NAME = "astrbot_plugin_fashaoairole_playing"
_LOG_SUBSCRIBERS: list[asyncio.Queue] = []


@register(
    PLUGIN_NAME,
    "awjdfsy",
    "多角色人格扮演系统，支持5种人格一键切换，含合规验证与安全过滤。",
    "v1.0.0",
)
class FeversPlugin(Star):
    """Main plugin class for Fevers AI persona system."""

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.plugin_data_path = (
            Path(get_astrbot_data_path()) / "plugin_data" / PLUGIN_NAME
        )
        self.plugin_data_path.mkdir(parents=True, exist_ok=True)
        self._state_cache: dict[str, str] = {}
        self._safety_keywords = self._load_safety_keywords()

        # Register plugin page backend APIs
        context.register_web_api(
            f"/{PLUGIN_NAME}/api/stats",
            self.api_stats,
            ["GET"],
            "Get FeversAI usage statistics",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/api/users",
            self.api_users,
            ["GET"],
            "List active FeversAI users",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/api/users/reset",
            self.api_user_reset,
            ["POST"],
            "Reset a single user's FeversAI state",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/api/users/reset-all",
            self.api_reset_all,
            ["POST"],
            "Reset all users' FeversAI state",
        )
        context.register_web_api(
            f"/{PLUGIN_NAME}/api/logs",
            self.api_logs,
            ["GET"],
            "SSE log stream for FeversAI",
        )

    # ────────────────────────────────────────────────
    # Safety filter
    # ────────────────────────────────────────────────

    def _load_safety_keywords(self) -> list[str]:
        """Load safety filter keywords."""
        return [
            "自杀",
            "自残",
            "自杀方法",
            "怎么自杀",
            "贩卖毒品",
            "制作炸弹",
            "恐怖袭击",
            "儿童色情",
            "幼女",
            "未成年人色情",
        ]

    def _check_safety(self, text: str) -> str | None:
        """Check text against safety filter. Returns matched keyword or None."""
        if not self.config.get("enable_safety_filter", True):
            return None
        for keyword in self._safety_keywords:
            if keyword.lower() in text.lower():
                return keyword
        return None

    # ────────────────────────────────────────────────
    # State management
    # ────────────────────────────────────────────────

    async def _get_user_state(self, user_id: str) -> str:
        """Get user's current state from KV cache or storage."""
        if user_id in self._state_cache:
            return self._state_cache[user_id]
        state = await self.get_kv_data(f"state_{user_id}", "none")
        self._state_cache[user_id] = state
        return state

    async def _set_user_state(self, user_id: str, state: str):
        """Set user's state and update cache."""
        await self.put_kv_data(f"state_{user_id}", state)
        self._state_cache[user_id] = state

    async def _has_compliance(self, user_id: str) -> bool:
        """Check if user has completed compliance verification."""
        val = await self.get_kv_data(f"compliance_{user_id}", "false")
        return val == "true"

    async def _set_compliance(self, user_id: str):
        """Mark user as having completed compliance (permanent)."""
        await self.put_kv_data(f"compliance_{user_id}", "true")

    async def _update_activity(self, user_id: str):
        """Update user's last activity timestamp for timeout tracking."""
        await self.put_kv_data(f"activity_{user_id}", str(int(time.time())))

    async def _check_timeout(self, user_id: str) -> bool:
        """Check if user session has timed out. Returns True if timed out."""
        timeout_min = self.config.get("session_timeout_minutes", 30)
        if timeout_min <= 0:
            return False
        activity_str = await self.get_kv_data(f"activity_{user_id}", "0")
        if activity_str == "0":
            return False
        elapsed = int(time.time()) - int(activity_str)
        return elapsed > timeout_min * 60

    # ────────────────────────────────────────────────
    # Command groups
    # ────────────────────────────────────────────────

    @filter.command_group("fevers")
    def fevers(self):
        """发烧AI角色扮演系统"""

    @fevers.command("help")
    async def fevers_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)

        msg = (
            "[发烧AI] 发烧AI角色扮演系统\n\n"
            "可用命令：\n"
            "/fevers help   - 显示此帮助\n"
            "/fevers start  - 开始设置（合规验证→选择人格→聊天）\n"
            "/fevers list   - 列出所有人格\n"
            "/fevers select <编号或名称> - 选择/切换人格\n"
            "/fevers status - 查看当前状态\n"
            "/fevers exit   - 退出发烧模式\n\n"
        )

        if state.startswith("active:"):
            persona_id = state.split(":", 1)[1]
            persona = PERSONAS.get(persona_id, {})
            msg += f"当前状态：已激活（{persona.get('name', '未知')}）"
        elif state != "none":
            msg += "当前状态：设置流程中"
        else:
            msg += "当前状态：未激活"

        yield event.plain_result(msg)
        event.stop_event()

    @fevers.command("start")
    async def fevers_start(self, event: AstrMessageEvent):
        """开始发烧AI模式设置"""
        user_id = event.get_sender_id()

        if await self._check_timeout(user_id):
            await self._set_user_state(user_id, "none")

        has_compliance = await self._has_compliance(user_id)

        if not has_compliance:
            compliance_text = self.config.get(
                "compliance_text",
                "此账号内容由AI生成，内容仅供参考，请仔细甄别。",
            )
            age_required = self.config.get("age_verification_required", True)

            msg = f"[发烧AI] {compliance_text}\n\n"
            if age_required:
                msg += (
                    "在使用本服务前，请确认：\n"
                    "1. 你已年满18周岁\n"
                    "2. 你已知悉并同意遵守《人工智能拟人化互动服务管理暂行办法》\n"
                    "3. 你理解所有输出内容均为AI生成，不构成专业建议\n\n"
                    "回复「已确认」以继续，回复「退出」取消。"
                )
            else:
                msg += "回复「已确认」以继续，回复「退出」取消。"

            await self._set_user_state(user_id, "awaiting_compliance")
            yield event.plain_result(msg)
        else:
            await self._set_user_state(user_id, "awaiting_persona")
            yield event.plain_result(
                "[发烧AI] 请选择人格（回复编号）：\n\n"
                "1. 病娇          - 极端占有欲，温柔与阴森切换\n"
                "2. 绿茶          - 表面温柔体贴，话里藏话\n"
                "3. 傲娇小萝莉    - 嘴硬心软，口是心非\n"
                "4. 知心姐姐      - 温柔治愈，包容倾听\n"
                "5. 喊杂鱼的妹妹  - 毒舌得意又黏人"
            )
        event.stop_event()

    @fevers.command("list")
    async def fevers_list(self, event: AstrMessageEvent):
        """列出所有人格"""
        msg = "[发烧AI] 可用人格列表：\n\n"
        for pid, persona in PERSONAS.items():
            msg += f"{pid}. {persona['name']} - {persona['description']}\n"
        msg += "\n使用 /fevers select <编号或名称> 切换人格"
        yield event.plain_result(msg)
        event.stop_event()

    @fevers.command("select")
    async def fevers_select(self, event: AstrMessageEvent, persona: str):
        """切换人格。用法：/fevers select <编号或名称>"""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)
        transition_texts = {
            "1": "（切换至病娇人格）（双手托腮对你微笑，眼神却让人脊背发凉）",
            "2": "（切换至绿茶人格）（歪头露出人畜无害的笑容）",
            "3": "（切换至傲娇小萝莉人格）（双手叉腰别过脸去）",
            "4": "（切换至知心姐姐人格）（温柔地看着你，目光柔和）",
            "5": "（切换至杂鱼妹妹人格）（踮起脚尖俯视你，一脸得意）",
        }
        persona_id = self._resolve_persona(persona)
        if persona_id is None:
            yield event.plain_result(
                "[发烧AI] 未找到对应人格。请使用 /fevers list 查看可用人格。"
            )
            event.stop_event()
            return

        persona = PERSONAS[persona_id]

        if state.startswith("active:") and self.config.get(
            "persona_transition_enabled", True
        ):
            transition = transition_texts.get(persona_id, "")
            yield event.plain_result(f"{transition}\n{persona['name']}：")

        await self._set_user_state(user_id, f"active:{persona_id}")
        await self._update_activity(user_id)

        if not state.startswith("active:"):
            yield event.plain_result(
                f"[发烧AI] 已切换至「{persona['name']}」。\n"
                "现在你可以和我聊天了。发送 /fevers exit 退出发烧模式。"
            )
        event.stop_event()

    @fevers.command("status")
    async def fevers_status(self, event: AstrMessageEvent):
        """查看当前状态"""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)

        if state.startswith("active:"):
            persona_id = state.split(":", 1)[1]
            persona = PERSONAS.get(persona_id, {})
            yield event.plain_result(
                f"[发烧AI] 当前状态：已激活\n"
                f"当前人格：{persona.get('name', '未知')}\n"
                f"使用 /fevers select <编号> 切换人格\n"
                f"使用 /fevers exit 退出发烧模式"
            )
        elif state == "none":
            yield event.plain_result("[发烧AI] 当前未激活。发送 /fevers start 开始。")
        else:
            yield event.plain_result("[发烧AI] 正在进行设置流程，请按提示操作。")
        event.stop_event()

    @fevers.command("exit")
    async def fevers_exit(self, event: AstrMessageEvent):
        """退出发烧AI模式"""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)

        if state.startswith("active:"):
            persona_id = state.split(":", 1)[1]
            persona_name = PERSONAS.get(persona_id, {}).get("name", "")

            await self._set_user_state(user_id, "none")
            if persona_name:
                yield event.plain_result(
                    f"（{persona_name}轻轻挥手）再见啦，下次再来找我玩哦。\n"
                    "[发烧AI] 已退出发烧模式。发送 /fevers start 重新开始。"
                )
            else:
                yield event.plain_result(
                    "[发烧AI] 已退出发烧模式。发送 /fevers start 重新开始。"
                )
        else:
            await self._set_user_state(user_id, "none")
            yield event.plain_result(
                "[发烧AI] 已退出发烧模式。发送 /fevers start 重新开始。"
            )
        event.stop_event()

    # ────────────────────────────────────────────────
    # Message interceptor for setup flow
    # ────────────────────────────────────────────────

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_message(self, event: AstrMessageEvent):
        """Intercept messages during setup flow (compliance, persona selection)."""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)
        text = event.message_str.strip()

        if text.startswith("/"):
            return

        if state == "awaiting_compliance":
            confirm_words = ["已确认", "确认", "是", "好的", "同意", "嗯"]
            cancel_words = ["退出", "取消", "不", "否", "不要"]

            if any(w in text for w in confirm_words):
                await self._set_compliance(user_id)
                await self._set_user_state(user_id, "awaiting_persona")
                yield event.plain_result(
                    "[发烧AI] 感谢你的确认！请选择人格（回复编号）：\n\n"
                    "1. 病娇          - 极端占有欲，温柔与阴森切换\n"
                    "2. 绿茶          - 表面温柔体贴，话里藏话\n"
                    "3. 傲娇小萝莉    - 嘴硬心软，口是心非\n"
                    "4. 知心姐姐      - 温柔治愈，包容倾听\n"
                    "5. 喊杂鱼的妹妹  - 毒舌得意又黏人"
                )
            elif any(w in text for w in cancel_words):
                await self._set_user_state(user_id, "none")
                yield event.plain_result(
                    "[发烧AI] 已取消。发送 /fevers start 重新开始。"
                )
            else:
                yield event.plain_result(
                    "[发烧AI] 请回复「已确认」以同意服务条款并继续，"
                    "或回复「退出」取消。"
                )
            event.stop_event()
            return

        if state == "awaiting_persona":
            persona_id = self._resolve_persona(text)
            if persona_id is None:
                yield event.plain_result(
                    "[发烧AI] 请输入有效的编号（1-5）或人格名称。\n"
                    "使用 /fevers list 查看可用人格。"
                )
                event.stop_event()
                return

            persona = PERSONAS[persona_id]
            await self._set_user_state(user_id, f"active:{persona_id}")
            await self._update_activity(user_id)

            transition_texts = {
                "1": "（切换至病娇人格）（双手托腮对你微笑，眼神却让人脊背发凉）",
                "2": "（切换至绿茶人格）（歪头露出人畜无害的笑容）",
                "3": "（切换至傲娇小萝莉人格）（双手叉腰别过脸去）",
                "4": "（切换至知心姐姐人格）（温柔地看着你，目光柔和）",
                "5": "（切换至杂鱼妹妹人格）（踮起脚尖俯视你，一脸得意）",
            }
            yield event.plain_result(
                f"[发烧AI] 已选择「{persona['name']}」\n"
                f"{transition_texts.get(persona_id, '')}"
            )
            event.stop_event()
            return

        if state.startswith("active:"):
            if await self._check_timeout(user_id):
                await self._set_user_state(user_id, "none")
                yield event.plain_result(
                    "[发烧AI] 会话已超时，已自动退出发烧模式。\n"
                    "发送 /fevers start 重新开始。"
                )
                event.stop_event()
                return
            await self._update_activity(user_id)

    # ────────────────────────────────────────────────
    # Persona prompt injection via on_llm_request
    # ────────────────────────────────────────────────

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """Inject persona prompt into LLM request for active fever mode users."""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)

        if not state.startswith("active:"):
            return

        persona_id = state.split(":", 1)[1]
        persona = PERSONAS.get(persona_id)
        if persona is None:
            return

        req.system_prompt += f"\n\n{persona['prompt']}"

        configured_provider = self.config.get("provider", "")
        if configured_provider:
            try:
                current_provider = await self.context.get_current_chat_provider_id(
                    event.unified_msg_origin
                )
                if current_provider != configured_provider:
                    logger.warning(
                        f"User {user_id} in fever mode but active provider "
                        f"({current_provider}) differs from configured "
                        f"provider ({configured_provider})"
                    )
            except Exception as e:
                logger.debug(f"Provider check failed: {e}")

    # ────────────────────────────────────────────────
    # Output formatting via on_decorating_result
    # ────────────────────────────────────────────────

    @filter.on_decorating_result()
    async def on_decorating_result(self, event: AstrMessageEvent):
        """Format AI output with persona name prefix for fever mode users."""
        user_id = event.get_sender_id()
        state = await self._get_user_state(user_id)

        if not state.startswith("active:"):
            return

        persona_id = state.split(":", 1)[1]
        persona = PERSONAS.get(persona_id)
        if persona is None:
            return

        result = event.get_result()
        if not result or not result.chain:
            return

        persona_name = persona["name"]

        if self.config.get("enable_safety_filter", True):
            for comp in result.chain:
                if hasattr(comp, "text") and comp.text:
                    matched = self._check_safety(comp.text)
                    if matched:
                        comp.text = "[内容已被安全策略拦截]"
                        logger.warning(
                            f"Safety filter blocked output for user "
                            f"{user_id}: matched '{matched}'"
                        )
                        break

        max_length = self.config.get("output_max_length", 200)
        for comp in result.chain:
            if hasattr(comp, "text") and comp.text:
                comp.text = f"{persona_name}：{comp.text}"
                if len(comp.text) > max_length:
                    comp.text = comp.text[:max_length] + "……"

    # ────────────────────────────────────────────────
    # Utility
    # ────────────────────────────────────────────────

    def _resolve_persona(self, identifier: str) -> str | None:
        """Resolve a persona identifier (number or name) to a persona ID."""
        identifier = identifier.strip().replace(" ", "")
        if identifier in PERSONAS:
            return identifier
        for pid, p in PERSONAS.items():
            if p["name"] == identifier or identifier in p["name"]:
                return pid
        return None

    # ────────────────────────────────────────────────
    # Plugin Page APIs
    # ────────────────────────────────────────────────

    async def _publish_log(self, level: str, message: str):
        """Publish a log entry to SSE subscribers."""
        entry = json.dumps({"level": level, "message": message}, ensure_ascii=False)
        dead: list[asyncio.Queue] = []
        for q in _LOG_SUBSCRIBERS:
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            _LOG_SUBSCRIBERS.remove(q)

    async def api_stats(self):
        """GET /api/stats - Return usage statistics."""
        try:
            active_count = sum(
                1 for s in self._state_cache.values() if s.startswith("active:")
            )
            total = len(self._state_cache)
            today_msgs = 0
            today = time.strftime("%Y-%m-%d")
            msg_log = self.plugin_data_path / "message_log.json"
            if msg_log.exists():
                try:
                    with open(msg_log, encoding="utf-8") as f:
                        log_data = json.load(f)
                    today_msgs = log_data.get(today, 0)
                except (json.JSONDecodeError, OSError):
                    pass
            return json_response(
                {
                    "active_users": active_count,
                    "total_users": total,
                    "today_messages": today_msgs,
                }
            )
        except Exception as e:
            logger.error(f"api_stats error: {e}")
            return error_response("Internal error", 500)

    async def api_users(self):
        """GET /api/users - List users and their states."""
        try:
            users = []
            for uid, state in self._state_cache.items():
                persona_name = ""
                if state.startswith("active:"):
                    pid = state.split(":", 1)[1]
                    p = PERSONAS.get(pid)
                    persona_name = p["name"] if p else pid
                users.append(
                    {
                        "user_id": uid,
                        "state": "active" if state.startswith("active:") else state,
                        "persona": persona_name,
                    }
                )
            users.sort(key=lambda u: u["user_id"])
            return json_response(users)
        except Exception as e:
            logger.error(f"api_users error: {e}")
            return error_response("Internal error", 500)

    async def api_user_reset(self):
        """POST /api/users/reset - Reset a single user's state."""
        try:
            payload = await request.json(default={})
            user_id = payload.get("user_id", "")
            if not user_id:
                return error_response("Missing user_id", 400)
            await self._set_user_state(user_id, "none")
            await self._publish_log("info", f"User {user_id} reset via WebUI")
            return json_response({"reset": True, "user_id": user_id})
        except Exception as e:
            logger.error(f"api_user_reset error: {e}")
            return error_response("Internal error", 500)

    async def api_reset_all(self):
        """POST /api/users/reset-all - Reset all users."""
        try:
            count = 0
            for uid in list(self._state_cache.keys()):
                await self._set_user_state(uid, "none")
                count += 1
            await self._publish_log("warn", f"All users reset via WebUI ({count})")
            return json_response({"reset": True, "count": count})
        except Exception as e:
            logger.error(f"api_reset_all error: {e}")
            return error_response("Internal error", 500)

    async def api_logs(self):
        """GET /api/logs (SSE) - Stream plugin logs."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        _LOG_SUBSCRIBERS.append(queue)

        async def event_stream():
            try:
                yield 'data: {"level": "info", "message": "日志连接已建立"}\n\n'
                while True:
                    try:
                        data = await asyncio.wait_for(queue.get(), timeout=30)
                        yield f"data: {data}\n\n"
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                if queue in _LOG_SUBSCRIBERS:
                    _LOG_SUBSCRIBERS.remove(queue)

        return stream_response(event_stream())

    # ────────────────────────────────────────────────
    # Lifecycle
    # ────────────────────────────────────────────────

    async def terminate(self):
        """Clean up when plugin is unloaded."""
        self._state_cache.clear()
        _LOG_SUBSCRIBERS.clear()
        logger.info("FeversAI plugin terminated.")
