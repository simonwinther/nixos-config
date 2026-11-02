#!/usr/bin/env python3
"""A private-bus SNI/dbusmenu fixture for the compositor smoke test (dbus-next)."""
# D-Bus decorators interpret these annotations as protocol signatures.
# ruff: noqa: F722, F821

import asyncio
import json
from pathlib import Path
import sys

from dbus_next import PropertyAccess, Variant, Message, MessageType
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method, signal

NAME = "org.example.DesktopBarSmokeTray"
WATCHER = "org.kde.StatusNotifierWatcher"
log = Path(sys.argv[1])


def record(action, **values):
    with log.open("a") as stream:
        stream.write(json.dumps({"action": action, **values}) + "\n")


class Item(ServiceInterface):
    def __init__(self):
        super().__init__("org.kde.StatusNotifierItem")
        self.status = "Active"

    @dbus_property(access=PropertyAccess.READ)
    def Title(self) -> "s":
        return "Private tray fixture"

    @dbus_property(access=PropertyAccess.READ)
    def Status(self) -> "s":
        record("StatusRead", status=self.status)
        return self.status

    @signal()
    def NewStatus(self, status) -> "s":
        return status

    @dbus_property(access=PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        return [[24, 24, bytes([255, 96, 165, 250]) * 576]]

    @dbus_property(access=PropertyAccess.READ)
    def Menu(self) -> "o":
        return "/Menu"

    @dbus_property(access=PropertyAccess.READ)
    def ItemIsMenu(self) -> "b":
        return False

    @method()
    def Activate(self, x: "i", y: "i"):
        record("Activate", x=x, y=y)


def node(identifier, label, **attributes):
    props = {"label": Variant("s", label), "enabled": Variant("b", True)}
    props.update(
        {
            key: Variant(signature, value)
            for key, (signature, value) in attributes.items()
        }
    )
    return Variant("(ia{sv}av)", [identifier, props, []])


class Menu(ServiceInterface):
    def __init__(self):
        super().__init__("com.canonical.dbusmenu")

    @method()
    def GetLayout(self, parent: "i", depth: "i", properties: "as") -> "u(ia{sv}av)":
        children = (
            [node(21, "Submenu action")]
            if parent == 20
            else [
                node(7, "_Connect", **{"toggle-state": ("i", 1)}),
                node(8, "", type=("s", "separator")),
                node(9, "Disabled", enabled=("b", False)),
                node(20, "Settings", **{"children-display": ("s", "submenu")}),
            ]
        )
        return [1, [parent, {}, children]]

    @method()
    def AboutToShow(self, parent: "i") -> "b":
        record("AboutToShow", parent=parent)
        self.LayoutUpdated(1, parent)
        return False

    @signal()
    def LayoutUpdated(self, revision, parent) -> "ui":
        return [revision, parent]

    @method()
    def Event(self, identifier: "i", event: "s", data: "v", timestamp: "u"):
        record("Event", id=identifier, time=timestamp)


async def main():
    bus = await MessageBus().connect()
    item = Item()
    bus.export("/StatusNotifierItem", item)
    bus.export("/Menu", Menu())
    await bus.request_name(NAME)
    introspection = await bus.introspect(WATCHER, "/StatusNotifierWatcher")
    watcher = bus.get_proxy_object(
        WATCHER, "/StatusNotifierWatcher", introspection
    ).get_interface(WATCHER)
    await watcher.call_register_status_notifier_item(NAME)
    async def register_again():
        await watcher.call_register_status_notifier_item(NAME)
        record("Reregistered")
    def owner_changed(message):
        if (message.message_type == MessageType.SIGNAL and message.interface == "org.freedesktop.DBus"
                and message.member == "NameOwnerChanged" and message.body[0] == WATCHER and message.body[2]):
            asyncio.create_task(register_again())
    bus.add_message_handler(owner_changed)
    await bus.call(Message(destination="org.freedesktop.DBus", path="/org/freedesktop/DBus",
        interface="org.freedesktop.DBus", member="AddMatch", signature="s",
        body=["type='signal',sender='org.freedesktop.DBus',interface='org.freedesktop.DBus',member='NameOwnerChanged',arg0='org.kde.StatusNotifierWatcher'"]))
    record("ready")
    async def update_status():
        path = log.parent / "tray-status"
        while True:
            status = path.read_text() if path.exists() else "Active"
            if status in ("Active", "Passive") and status != item.status:
                item.status = status
                item.NewStatus(status)
            await asyncio.sleep(0.05)
    asyncio.create_task(update_status())
    await bus.wait_for_disconnect()


asyncio.run(main())
