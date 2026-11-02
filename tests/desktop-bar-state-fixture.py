#!/usr/bin/env python3
"""Synthetic iwd and Elephant state on the smoke test's private bus and socket."""
# D-Bus decorators interpret these annotations as protocol signatures.
# ruff: noqa: F722, F821

import asyncio
import json
import os
from pathlib import Path
import struct

from dbus_next import PropertyAccess, Variant, MessageType, Message
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, dbus_property, method

ROOT = Path(os.environ["DESKTOP_BAR_TEST_ROOT"])
DEVICE = "/net/connman/iwd/0/4"
NETWORK = DEVICE + "/test_network"
PROTECTED = DEVICE + "/protected"
AGENT = None
BUS = None
BLUEZ = None
BT_AGENT = None
BUS_STATS = {"noise_sent": 0, "position_sent": 0, "media_reads": 0}


def bus_stats():
    temporary = ROOT / ".bus-stats.tmp"
    temporary.write_text(json.dumps(BUS_STATS))
    temporary.replace(ROOT / "bus-stats.json")


def stalled(message, provider, interface, member):
    if (message.message_type == MessageType.METHOD_CALL and message.interface == interface
            and message.member == member and (ROOT / ("stall-native-" + provider)).exists()):
        (ROOT / ("stalled-native-" + provider)).touch()
        return True
    return False


class Device(ServiceInterface):
    def __init__(self):
        super().__init__("net.connman.iwd.Device")

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return "wlan-test"

    @dbus_property(access=PropertyAccess.READ)
    def Powered(self) -> "b":
        return True


class Station(ServiceInterface):
    def __init__(self):
        super().__init__("net.connman.iwd.Station")

    @dbus_property(access=PropertyAccess.READ)
    def State(self) -> "s":
        return "connected"

    @dbus_property(access=PropertyAccess.READ)
    def ConnectedNetwork(self) -> "o":
        return NETWORK

    @method()
    def GetOrderedNetworks(self) -> "a(on)":
        return [[NETWORK, -5800], [PROTECTED, -6800]]

    @method()
    def Scan(self): pass


class Network(ServiceInterface):
    def __init__(self, protected=False):
        super().__init__("net.connman.iwd.Network")
        self.protected = protected

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":
        return "Fixture Protected" if self.protected else "Fixture Wi-Fi"
    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> "s": return "psk"
    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b": return not self.protected
    @method()
    async def Connect(self):
        destination, path = AGENT
        tree = await BUS.introspect(destination, path)
        interface = BUS.get_proxy_object(destination, path, tree).get_interface("net.connman.iwd.Agent")
        try:
            password = await interface.call_request_passphrase(PROTECTED)
            accepted = password == "test"
            password = None
            with (ROOT / "wifi-actions.jsonl").open("a") as log: log.write(json.dumps({"accepted": accepted}) + "\n")
        except Exception:
            with (ROOT / "wifi-actions.jsonl").open("a") as log: log.write('{"cancelled": true}\n')


class Manager(ServiceInterface):
    def __init__(self):
        super().__init__("org.freedesktop.DBus.ObjectManager")

    @method()
    def GetManagedObjects(self) -> "a{oa{sa{sv}}}":
        return {
            DEVICE: {
                "net.connman.iwd.Device": {"Name": Variant("s", "wlan-test"), "Powered": Variant("b", True)},
                "net.connman.iwd.Station": {"State": Variant("s", "connected"), "ConnectedNetwork": Variant("o", NETWORK)},
            },
            NETWORK: {"net.connman.iwd.Network": {"Name": Variant("s", "Fixture Wi-Fi")}},
        }


ITEMS = [
    {"identifier": f"item-{index}", "text": f"Text {index}", "subtext": "TEXT · fixture",
     "preview": f"Clipboard fixture {index}\nLiteral text with symbols: <tag> & /path",
     "preview_type": "text", "state": [], "actions": ["pin", "remove"]}
    for index in range(12)
]
ITEMS[1].update(text="Fixture image", preview=str(ROOT / "wallpaper-0.png"), preview_type="file", subtext="PNG · fixture")


async def clipboard(reader, writer):
    try:
        try:
            header = await reader.readexactly(6)
        except asyncio.IncompleteReadError:
            return
        size = struct.unpack(">I", header[2:])[0]
        assert size < 65536 and header[1] == 1
        request = json.loads(await reader.readexactly(size))
        with (ROOT / "clipboard-requests.jsonl").open("a") as stream:
            stream.write(json.dumps({"kind": header[0], **request}) + "\n")
        if header[0] == 0:
            for item in ITEMS:
                body = json.dumps({"item": item}).encode()
                writer.write(b"\0" + struct.pack(">I", len(body)) + body)
            writer.write(b"\xff\0\0\0\0")
            await writer.drain()
        elif header[0] == 1:
            item = next((item for item in ITEMS if item["identifier"] == request["identifier"]), None)
            if item:
                if request["action"] == "pin":
                    item.update(state=["pinned"], actions=["unpin"])
                elif request["action"] == "unpin":
                    item.update(state=[], actions=["pin", "remove"])
                elif request["action"] == "remove":
                    ITEMS.remove(item)
            writer.write(b"\x02\0\0\0\0")
            await writer.drain()
        elif header[0] == 4:
            body = json.dumps({"states": ["show_combined"], "provider": "clipboard"}).encode()
            writer.write(b"\x03" + struct.pack(">I", len(body)) + body + b"\xfd\0\0\0\0")
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


class Player(ServiceInterface):
    def __init__(self):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.playing = True
        self.title = "Fixture Song"

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        return "Playing" if self.playing else "Paused"

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> "x": return 0

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        cover = (ROOT / "media-cover").read_text() if (ROOT / "media-cover").exists() else (ROOT / "wallpaper-0.png").as_uri()
        return {"xesam:title": Variant("s", self.title), "xesam:artist": Variant("as", ["Fixture Artist"]),
                "mpris:artUrl": Variant("s", cover)}

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b": return True
    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b": return True
    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b": return True
    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b": return True
    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b": return True

    def record(self, action):
        with (ROOT / "media-actions.jsonl").open("a") as log:
            log.write(json.dumps(action) + "\n")

    @method()
    def PlayPause(self):
        self.playing = not self.playing
        self.record("PlayPause")
        self.emit_properties_changed({"PlaybackStatus": self.PlaybackStatus})

    @method()
    def Next(self):
        self.title = "Next Fixture Song"
        self.record("Next")
        self.emit_properties_changed({"Metadata": self.Metadata})

    @method()
    def Previous(self):
        self.title = "Fixture Song"
        self.record("Previous")
        self.emit_properties_changed({"Metadata": self.Metadata})


class MediaRoot(ServiceInterface):
    def __init__(self): super().__init__("org.mpris.MediaPlayer2")
    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s": return "Fixture Player"


class Mako(ServiceInterface):
    def __init__(self):
        super().__init__("fr.emersion.Mako")
        self.current = [{"id": Variant("u", 42), "summary": Variant("s", "Fixture Notification"),
                        "body": Variant("s", "<b>Notification body</b>"), "app-name": Variant("s", "Fixture App")}]

    @method()
    def ListNotifications(self) -> "aa{sv}": return self.current
    @method()
    def ListHistory(self) -> "aa{sv}": return []
    @method()
    def InvokeAction(self, identifier: "u", action: "s"):
        with (ROOT / "notification-actions.jsonl").open("a") as log:
            log.write(json.dumps([identifier, action]) + "\n")
    @method()
    def DismissNotifications(self, options: "a{sv}"):
        self.current = []
        with (ROOT / "notification-actions.jsonl").open("a") as log: log.write('"dismiss"\n')


class BluetoothManager(ServiceInterface):
    def __init__(self):
        super().__init__("org.freedesktop.DBus.ObjectManager")
    @method()
    def GetManagedObjects(self) -> "a{oa{sa{sv}}}":
        return {"/org/bluez/hci0": {"org.bluez.Adapter1": {"Powered": Variant("b", True), "Alias": Variant("s", "Test Bluetooth")}},
                "/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF": {"org.bluez.Device1": {
                    "Paired": Variant("b", True), "Connected": Variant("b", False),
                    "Alias": Variant("s", "Fixture Headphones"), "Icon": Variant("s", "audio-headset")}}}


class BluetoothDevice(ServiceInterface):
    def __init__(self, paired=True):
        super().__init__("org.bluez.Device1")
        self.paired = paired
        self.trusted = paired
    @dbus_property(access=PropertyAccess.READ)
    def Alias(self) -> "s": return "Fixture Headphones" if self.paired else "Fixture Keyboard"
    @dbus_property(access=PropertyAccess.READ)
    def Icon(self) -> "s": return "audio-headset"
    @dbus_property(access=PropertyAccess.READ)
    def Paired(self) -> "b": return self.paired
    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b": return False
    @dbus_property(access=PropertyAccess.READWRITE)
    def Trusted(self) -> "b": return self.trusted
    @Trusted.setter
    def Trusted(self, value: "b"): self.trusted = value
    @method()
    async def Pair(self):
        destination, path = BT_AGENT
        tree = await BLUEZ.introspect(destination, path)
        interface = BLUEZ.get_proxy_object(destination, path, tree).get_interface("org.bluez.Agent1")
        await interface.call_request_confirmation("/org/bluez/hci0/dev_11_22_33_44_55_66", 123456)
        self.paired = True
        with (ROOT / "bluetooth-actions.jsonl").open("a") as log: log.write('"paired"\n')
    @method()
    def Connect(self):
        with (ROOT / "bluetooth-actions.jsonl").open("a") as log: log.write('"connect"\n')


class BluetoothAdapter(ServiceInterface):
    def __init__(self): super().__init__("org.bluez.Adapter1")
    @dbus_property(access=PropertyAccess.READ)
    def Powered(self) -> "b": return True
    @dbus_property(access=PropertyAccess.READ)
    def Alias(self) -> "s": return "Test Bluetooth"
    @dbus_property(access=PropertyAccess.READ)
    def Discovering(self) -> "b": return False


class BluetoothAgentManager(ServiceInterface):
    def __init__(self): super().__init__("org.bluez.AgentManager1")
    @method()
    def RegisterAgent(self, agent: "o", capability: "s"): pass


class WirelessAgentManager(ServiceInterface):
    def __init__(self): super().__init__("net.connman.iwd.AgentManager")
    @method()
    def RegisterAgent(self, agent: "o"): pass


async def main():
    global BUS, BLUEZ
    bus = await MessageBus().connect()
    BUS = bus
    def observe(message):
        global AGENT
        if (message.message_type == MessageType.METHOD_CALL
                and message.path == "/org/mpris/MediaPlayer2"
                and message.interface == "org.freedesktop.DBus.Properties" and message.member == "GetAll"):
            BUS_STATS["media_reads"] += 1
            bus_stats()
            if (ROOT / "stall-media").exists():
                (ROOT / "stalled-media").touch()
                return True
        if (stalled(message, "notifications", "fr.emersion.Mako", "ListHistory")
                or stalled(message, "wifi", "net.connman.iwd.Station", "GetOrderedNetworks")):
            return True
        if message.message_type == MessageType.METHOD_CALL and message.interface == "net.connman.iwd.AgentManager" and message.member == "RegisterAgent":
            AGENT = (message.sender, message.body[0])
    bus.add_message_handler(observe)
    bus.export("/", Manager())
    bus.export(DEVICE, Device())
    bus.export(DEVICE, Station())
    bus.export(NETWORK, Network())
    bus.export(PROTECTED, Network(protected=True))
    bus.export("/net/connman/iwd", WirelessAgentManager())
    await bus.request_name("net.connman.iwd")
    player_name = "org.mpris.MediaPlayer2.desktop_fixture"
    player = Player()
    bus.export("/org/mpris/MediaPlayer2", player)
    bus.export("/org/mpris/MediaPlayer2", MediaRoot())
    await bus.request_name(player_name)

    async def media_presence():
        available = True
        network_available = True
        applied_title = None
        while True:
            state = ROOT / "media-state.json"
            if state.exists():
                try:
                    desired = json.loads(state.read_text())["available"]
                except (KeyError, json.JSONDecodeError):
                    desired = available
                if desired != available:
                    if desired:
                        await bus.request_name(player_name)
                    else:
                        await bus.release_name(player_name)
                    available = desired
            state = ROOT / "wifi-presence.json"
            if state.exists():
                try:
                    desired = json.loads(state.read_text())["available"]
                except (KeyError, json.JSONDecodeError):
                    desired = network_available
                if desired != network_available:
                    if desired:
                        await bus.request_name("net.connman.iwd")
                    else:
                        await bus.release_name("net.connman.iwd")
                    network_available = desired
            title = ROOT / "media-title"
            if title.exists() and title.read_text() != applied_title:
                applied_title = title.read_text()
                player.title = applied_title
                player.emit_properties_changed({"Metadata": player.Metadata})
            await asyncio.sleep(0.05)

    asyncio.create_task(media_presence())
    async def bus_load():
        while True:
            mode = (ROOT / "bus-load").read_text() if (ROOT / "bus-load").exists() else ""
            if mode == "noise":
                for _ in range(50):
                    await bus.send(Message.new_signal("/org/example/Noise", "org.example.Noise", "Tick"))
                    BUS_STATS["noise_sent"] += 1
            elif mode == "position":
                player.emit_properties_changed({"Position": BUS_STATS["position_sent"] * 40000})
                BUS_STATS["position_sent"] += 1
            bus_stats()
            await asyncio.sleep(0.04)
    asyncio.create_task(bus_load())
    bus.export("/fr/emersion/Mako", Mako())
    await bus.request_name("org.freedesktop.Notifications")
    bluez = await MessageBus().connect()
    BLUEZ = bluez
    def observe_bluetooth(message):
        global BT_AGENT
        if stalled(message, "bluetooth", "org.freedesktop.DBus.ObjectManager", "GetManagedObjects"):
            return True
        if message.message_type == MessageType.METHOD_CALL and message.interface == "org.bluez.AgentManager1" and message.member == "RegisterAgent":
            BT_AGENT = (message.sender, message.body[0])
    bluez.add_message_handler(observe_bluetooth)
    bluez.export("/org/bluez", BluetoothAgentManager())
    bluez.export("/", BluetoothManager())
    bluez.export("/org/bluez/hci0", BluetoothAdapter())
    bluez.export("/org/bluez/hci0/dev_AA_BB_CC_DD_EE_FF", BluetoothDevice())
    bluez.export("/org/bluez/hci0/dev_11_22_33_44_55_66", BluetoothDevice(paired=False))
    await bluez.request_name("org.bluez")
    directory = Path(os.environ["XDG_RUNTIME_DIR"]) / "elephant"
    directory.mkdir(mode=0o700)
    server = await asyncio.start_unix_server(clipboard, path=str(directory / "elephant.sock"))
    (ROOT / "state-ready").touch()
    async with server:
        await server.serve_forever()


asyncio.run(main())
