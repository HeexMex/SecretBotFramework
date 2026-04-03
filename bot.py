#!/usr/bin/env python3
"""
Matrix Bot Framework.

Фреймворк для ботов Matrix. Этот файл не нужно редактировать.
Команды добавляются в commands.py.
"""

import asyncio
import json
import logging
import os
import sys
import time

from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LoginResponse,
    MatrixRoom,
    MegolmEvent,
    RoomMessageText,
)

from config import (
    BOT_DISPLAY_NAME,
    BOT_PASSWORD,
    BOT_USER_ID,
    CREDENTIALS_FILE,
    HOMESERVER_URL,
    STORE_PATH,
)
from commands import COMMANDS

PREFIX = "!"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("matrix-bot")


class MatrixBot:
    def __init__(self):
        self.client: AsyncClient | None = None
        self.start_time = time.time()

    # ── Client setup ──────────────────────────────────────────

    async def init_client(self) -> AsyncClient:
        config = AsyncClientConfig(
            max_limit_exceeded=0,
            max_timeouts=0,
            store_sync_tokens=True,
            encryption_enabled=True,
        )
        if not os.path.exists(STORE_PATH):
            os.makedirs(STORE_PATH)

        self.client = AsyncClient(
            HOMESERVER_URL,
            BOT_USER_ID,
            store_path=STORE_PATH,
            config=config,
        )
        return self.client

    async def login(self) -> None:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE) as f:
                creds = json.load(f)
            log.info("Restoring session from %s", CREDENTIALS_FILE)
            self.client.restore_login(
                user_id=creds["user_id"],
                device_id=creds["device_id"],
                access_token=creds["access_token"],
            )
        else:
            log.info("Logging in as %s with password", BOT_USER_ID)
            resp = await self.client.login(
                password=BOT_PASSWORD,
                device_name=BOT_DISPLAY_NAME,
            )
            if not isinstance(resp, LoginResponse):
                log.error("Login failed: %s", resp)
                sys.exit(1)
            log.info("Login successful, saving credentials")
            with open(CREDENTIALS_FILE, "w") as f:
                json.dump({
                    "homeserver": HOMESERVER_URL,
                    "user_id": resp.user_id,
                    "device_id": resp.device_id,
                    "access_token": resp.access_token,
                }, f, indent=2)

    def _trust_all_devices(self) -> None:
        for user_id in self.client.device_store.users:
            for device_id, olm_device in self.client.device_store[user_id].items():
                if user_id == self.client.user_id and device_id == self.client.device_id:
                    continue
                self.client.verify_device(olm_device)

    def register_callbacks(self) -> None:
        self.client.add_event_callback(self.on_message, RoomMessageText)
        self.client.add_event_callback(self.on_megolm, MegolmEvent)
        self.client.add_event_callback(self.on_invite, InviteMemberEvent)

    # ── Callbacks ─────────────────────────────────────────────

    async def on_invite(self, room: MatrixRoom, event: InviteMemberEvent) -> None:
        if event.state_key != self.client.user_id:
            return
        log.info("Invited to %s by %s — joining", room.room_id, event.sender)
        await self.client.join(room.room_id)

    async def on_megolm(self, room: MatrixRoom, event: MegolmEvent) -> None:
        log.warning(
            "Can't decrypt in %s from %s (session: %s)",
            room.display_name, event.sender, event.session_id,
        )

    async def on_message(self, room: MatrixRoom, event: RoomMessageText) -> None:
        if event.sender == self.client.user_id:
            return

        body = event.body.strip()
        if not body.startswith(PREFIX):
            return

        parts = body[len(PREFIX):].split(maxsplit=1)
        cmd_name = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd_name == "help":
            await self._send_help(room)
            return

        entry = COMMANDS.get(cmd_name)
        if entry:
            handler, _ = entry
            log.info("%s | %s -> !%s", room.display_name, event.sender, cmd_name)
            await handler(self, room, event, args)

    # ── Helpers ───────────────────────────────────────────────

    async def _send(self, room: MatrixRoom, text: str) -> None:
        await self.client.room_send(
            room_id=room.room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )

    async def _send_help(self, room: MatrixRoom) -> None:
        lines = [f"{BOT_DISPLAY_NAME} — команды:\n"]
        for name, (_, desc) in COMMANDS.items():
            lines.append(f"  !{name}  — {desc}")
        lines.append(f"  !help  — список команд")
        await self._send(room, "\n".join(lines))

    # ── Main loop ─────────────────────────────────────────────

    async def run(self) -> None:
        await self.init_client()
        await self.login()
        self.register_callbacks()

        log.info(
            "Bot %s running with %d commands. Ctrl+C to stop.",
            BOT_USER_ID, len(COMMANDS),
        )

        async def after_first_sync():
            await self.client.synced.wait()
            self._trust_all_devices()
            log.info("Trusted all known devices")
            if self.client.should_upload_keys:
                await self.client.keys_upload()
                log.info("Uploaded encryption keys")

        sync_task = asyncio.ensure_future(
            self.client.sync_forever(timeout=30000, full_state=True)
        )
        trust_task = asyncio.ensure_future(after_first_sync())

        try:
            await asyncio.gather(sync_task, trust_task)
        except (asyncio.CancelledError, KeyboardInterrupt):
            log.info("Shutting down...")
        finally:
            await self.client.close()


async def main():
    bot = MatrixBot()
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
