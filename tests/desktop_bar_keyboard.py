"""Keyboard acceptance through real input in the bar's private compositor."""
import json
from pathlib import Path
import time


def exercise(context):
    def tap(key):
        context.send(f"key {key} 1")
        context.send(f"key {key} 0")

    def chord(modifiers, key):
        for modifier in modifiers:
            context.send(f"key {modifier} 1")
        tap(key)
        for modifier in reversed(modifiers):
            context.send(f"key {modifier} 0")

    def help_page():
        chord([42], 53)  # ?

    def dashboard():
        chord([125, 29], 32)  # Super+Ctrl+D

    # Exercise the shipped clipboard shortcut in both styles.
    source = Path(__file__).resolve().parent.parent / "dotfiles/hypr/.config/hypr/defaults/bindings/clipboard.lua"
    context.control("eval", "dofile(" + json.dumps(str(source)) + ")")
    context.control("eval", 'hl.bind("SUPER + CTRL + D", hl.dsp.exec_cmd(' + json.dumps(str(context.binary) + " --panel controls") + '), {description="Toggle dashboard"})')
    context.move(context.width - 100, context.height - 100)
    dashboard()
    context.wait_for(lambda: context.settled_height(312))
    time.sleep(0.2)
    layers = context.control("-j", "layers")
    first = lambda: context.pixel("WAYLAND-1", context.width // 2 - 250, 70)
    selected = first()
    for down, up in [(36, 37), (38, 35)]:  # j/k, then l/h.
        tap(down)
        context.wait_for(lambda: first() != selected)
        tap(up)
        context.wait_for(lambda: first() == selected)
    tap(36)
    context.capture("dashboard-hjkl")
    help_page()
    context.wait_for(lambda: context.settled_height(252))
    context.capture("dashboard-help")
    help_page()
    context.wait_for(lambda: context.settled_height(312))
    assert first() != selected, "Help lost the dashboard selection"
    tap(37)
    context.wait_for(lambda: first() == selected)

    chord([29], 38)  # Ctrl+L: a literal l must be searchable.
    tap(38)
    time.sleep(0.12)
    context.wait_for(lambda: first() == selected)
    context.capture("dashboard-search-literal-l")
    tap(1)  # Leave search while retaining the filter.
    tap(14)
    tap(53)  # /: search for Bluetooth, including literal l and h.
    for key in (48, 38, 22, 18, 20, 24, 24, 20, 35):
        tap(key)
    tap(28)
    context.wait_for(lambda: context.settled_height(352))
    tap(1)
    context.wait_for(lambda: context.settled_height(312))
    help_page()
    context.wait_for(lambda: context.settled_height(252))
    tap(1)
    context.wait_for(lambda: context.settled_height(312))
    assert context.control("-j", "layers") == layers
    dashboard()
    context.wait_for(context.no_backdrop)

    chord([56], 47)  # Alt+V follows the shipped binding into the current bar.
    context.wait_for(lambda: context.settled_height(464))
    time.sleep(0.2)
    border = lambda: context.pixel("WAYLAND-1", context.width // 2 - 360, 125)
    grid = border()
    for down, up in [(38, 35), (36, 37)]:  # Ctrl+L/H across cards, Ctrl+J/K across rows.
        chord([29], down)
        context.wait_for(lambda: border() != grid)
        chord([29], up)
        context.wait_for(lambda: border() == grid)
    tap(25)  # p previews immediately, without Escape.
    context.wait_for(lambda: border() != grid)
    context.capture("clipboard-immediate-preview")
    help_page()
    context.wait_for(lambda: context.settled_height(252))
    context.capture("clipboard-preview-help")
    tap(1)
    context.wait_for(lambda: context.settled_height(464))
    assert border() != grid, "Help lost the preview"
    tap(1)
    context.wait_for(lambda: border() == grid)
    help_page()
    context.wait_for(lambda: context.settled_height(304))
    context.capture("clipboard-help")
    tap(1)
    context.wait_for(lambda: context.settled_height(464))
    tap(53)  # / enters clipboard search; Ctrl+L now moves right.
    tap(25)  # p remains literal text while editing a search.
    help_page()
    context.wait_for(lambda: context.settled_height(304))
    tap(1)
    context.wait_for(lambda: context.settled_height(464))
    tap(1)
    assert not context.no_backdrop(), "Help lost search focus"
    tap(1)
    context.wait_for(context.no_backdrop)

    context.style("native-clean")
    # Menus must paint above a fullscreen application, not just acquire focus.
    context.control("eval", 'hl.window_rule({match={class="hs-capture-fixture"},fullscreen=true})')
    client = context.start([str(context.fullscreen_client), "Native menu fullscreen fixture"], "fullscreen")
    try:
        context.wait_for(lambda: any(window.get("class") == "hs-capture-fixture" and window.get("fullscreen") == 2
                                    for window in json.loads(context.control("-j", "clients"))))
        context.control("eval", 'hl.bind("CTRL + K", hl.dsp.exec_cmd(' +
                        json.dumps(str(context.binary) + " --menu keybindings") +
                        '), {description="Open keybindings"})')
        first_row = lambda: context.pixel("WAYLAND-1", context.width // 2 - 210,
                                           context.height // 2 - 90)
        chord([29], 37)
        context.wait_for(lambda: context.settled_height(352))
        time.sleep(0.1)
        selected = first_row()
        context.move(context.width // 2, context.height // 2)
        # Reopen both during the close and after its surfaces have gone away.
        # Exercise navigation too: a visible stale frame must not pass.
        for delay in (0.0, 0.04, 0.12, 0.4):
            tap(1)
            time.sleep(delay)
            chord([29], 37)
            context.wait_for(lambda: context.settled_height(352), timeout=2)
            context.wait_for(lambda: first_row() == selected, timeout=2)
            chord([29], 36)
            context.wait_for(lambda: first_row() != selected, timeout=2)
            tap(103)  # Up restores the first row without toggling the shortcut.
            context.wait_for(lambda: first_row() == selected, timeout=2)
        context.capture("clean-rapid-reopen")
        tap(1)
        context.wait_for(context.no_backdrop, timeout=2)
        position = ("WAYLAND-1", context.width // 2, context.height // 2)
        background = context.pixel(*position)
        for name, modifiers, key, panel in (
            ("apps", [125], 57, "apps"),
            ("keybindings", [125], 37, "keybindings"),
            ("clipboard", [56], 47, "clipboard"),
            ("notifications", [125], 49, "notifications"),
        ):
            key_name = {"apps": "SUPER + SPACE", "keybindings": "SUPER + K",
                        "clipboard": "ALT + V", "notifications": "SUPER + N"}[name]
            if name != "clipboard":
                context.control("eval", "hl.bind(" + json.dumps(key_name) + ", hl.dsp.exec_cmd(" +
                                json.dumps(str(context.binary) + " --menu " + panel) + "))")
            chord(modifiers, key)
            context.wait_for(lambda: context.pixel(*position) != background)
            time.sleep(0.2)
            context.capture("clean-fullscreen-" + name)
            if name == "notifications":
                context.move(50, context.height - 50)
                context.send("272 1")
                context.send("272 0")
            else:
                tap(1)
            context.wait_for(context.no_backdrop)
            context.wait_for(lambda: context.pixel(*position) == background)
    finally:
        client.terminate()
        client.wait(timeout=3)

    dashboard()
    context.wait_for(lambda: context.settled_height(312))
    help_page()
    context.wait_for(lambda: context.settled_height(252))
    context.capture("dashboard-help-clean")
    tap(1)
    context.wait_for(lambda: context.settled_height(312))
    tap(1)
    context.wait_for(context.no_backdrop)
