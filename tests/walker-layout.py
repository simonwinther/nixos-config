"""Render the actual GTK templates using synthetic history in a disposable display.

Run through the walker-layout Nix check. This validates layout/CSS, not Wayland
focus or real clipboard capture. The native provider has separate Go tests.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gsk", "4.0")
gi.require_version("Graphene", "1.0")
from gi.repository import Gdk, GLib, Graphene, Gsk, Gtk

ROOT, OUTPUT = map(Path, sys.argv[1:])
OUTPUT.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("desktopctl", ROOT / "dotfiles/desktop-tools/.local/share/desktop-tools/desktopctl.py")
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)
Gtk.init()


def settle():
    deadline = time.monotonic() + 0.2
    while time.monotonic() < deadline:
        while GLib.MainContext.default().iteration(False):
            pass
        time.sleep(0.01)


def menu_entries(group):
    captured = []
    def fixture_run(argv, **kwargs):
        if "--dmenu" in argv:
            captured.extend(kwargs["input"].splitlines())
            return subprocess.CompletedProcess(argv, 130, "")
        if argv[0] == "fc-list":
            return subprocess.CompletedProcess(argv, 0, "JetBrainsMono Nerd Font\nAdwaita Mono\n")
        if argv[0] == "powerprofilesctl":
            return subprocess.CompletedProcess(argv, 0, "  power-saver:\n* balanced:\n  performance:\n")
        if argv[0] == "hyprctl":
            return subprocess.CompletedProcess(argv, 0, '{"mice": []}')
        raise AssertionError(argv)
    with patch.object(ctl, "run", side_effect=fixture_run), patch.object(ctl, "executable", return_value="fixture-walker"):
        ctl.menu([group])
    assert captured, group
    return captured


def render(view, width, height, palette="tokyoled", image=False, group="main"):
    ctl.prepare_theme(palette)
    folder = ctl.RUNTIME / "walker/themes" / ("desktop-" + view)
    errors = []
    css = Gtk.CssProvider()
    css.connect("parsing-error", lambda _, section, error: errors.append(str(error)))
    css.load_from_path(str(folder / "style.css"))
    Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    builder = Gtk.Builder.new_from_file(str(folder / "layout.xml"))
    window = builder.get_object("Window")
    window.set_decorated(False)
    builder.get_object("BoxWrapper").set_size_request(width, height if view != "menu" else -1)
    window.set_default_size(width, height)
    for name in ("ElephantHint", "Placeholder", "Keybinds", "Error"):
        builder.get_object(name).set_visible(False)
    if view == "menu":
        title = ctl.read_json(ctl.CONFIG / "desktop/menus.json")[group].get("title") if group in ctl.read_json(ctl.CONFIG / "desktop/menus.json") else None
        builder.get_object("Input").set_placeholder_text(title or group.replace("-", " ").title() + "…")
    entries = menu_entries(group) if view == "menu" else [
        "Image", "Meeting notes — next steps", "1. Path Parametrization & Instantaneous Velocity",
        "https://example.com/" + "very-long-path-" * 30, "Email address", "Pinned code snippet",
    ]
    selection = Gtk.SingleSelection.new(Gtk.StringList.new(entries))
    selection.set_selected(0 if image else 2)
    factory = Gtk.SignalListItemFactory()

    def setup(_, item):
        if view == "menu":
            box, text, label = Gtk.Box(), Gtk.Box(), Gtk.Label(xalign=0)
            box.add_css_class("item-box")
            text.add_css_class("item-text-box")
            text.set_hexpand(True)
            label.add_css_class("item-text")
            # Match Walker's built-in item_dmenu.xml label behavior.
            label.set_ellipsize(3)
            label.set_single_line_mode(True)
            text.append(label)
            box.append(text)
            item.set_child(box)
            item.label = label
        else:
            template = Gtk.Builder.new_from_file(str(folder / "item_clipboard.xml"))
            item.set_child(template.get_object("ItemBox"))
            item.label = template.get_object("ItemText")
            template.get_object("ItemSubtext").set_text("2 minutes ago  ✦" if item.get_position() == 5 else "Just now")

    factory.connect("setup", setup)
    factory.connect("bind", lambda _, item: item.label.set_text(item.get_item().get_string()))
    builder.get_object("List").set_factory(factory)
    builder.get_object("List").set_model(selection)
    preview = builder.get_object("Preview")
    if view != "menu":
        template = Gtk.Builder.new_from_file(str(folder / "preview.xml"))
        if image:
            content = Gtk.Picture.new_for_filename(str(ROOT / "dotfiles/wallpapers/.local/share/wallpapers/tokyoled/digital-art/background.png"))
            content.set_can_shrink(True)
            content.set_content_fit(Gtk.ContentFit.CONTAIN)
        else:
            content = Gtk.Label(label="1. Path Parametrization & Instantaneous Velocity\n\nCopied text stays readable, with line breaks and punctuation preserved.\n\nz(t) = t × source + (1 − t) × target\n\nLong URLs wrap within this pane:\nhttps://example.com/" + "continuous-long-path-" * 14)
            content.set_selectable(True)
            content.set_wrap(True)
            content.set_wrap_mode(2)  # Pango WordChar, matching the patched native preview.
            content.set_max_width_chars(48)
            content.set_halign(Gtk.Align.FILL)
            content.set_xalign(0)
            content.set_valign(Gtk.Align.START)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.set_child(content)
        template.get_object("PreviewStack").add_child(scrolled)
        preview.append(template.get_object("PreviewBox"))
    window.present()
    settle()
    assert not errors, errors
    actual_width, actual_height = window.get_width(), window.get_height()
    assert actual_width == width, (view, actual_width, width)
    if view == "menu":
        assert actual_height <= 700, (group, actual_height)
    if view != "menu":
        assert actual_height == height, (view, actual_height, height)
        assert preview.get_width() >= 250 and preview.get_height() >= 70, (view, "preview is unusable")
    paint = Gtk.WidgetPaintable.new(window)
    snapshot = Gtk.Snapshot.new()
    paint.snapshot(snapshot, actual_width, actual_height)
    renderer = Gsk.CairoRenderer.new()
    renderer.realize(window.get_surface())
    rectangle = Graphene.Rect()
    rectangle.init(0, 0, actual_width, actual_height)
    texture = renderer.render_texture(snapshot.to_node(), rectangle)
    tag = "-" + group if view == "menu" else ""
    texture.save_to_png(str(OUTPUT / f"{view}{tag}-{palette}{'-image' if image else ''}.png"))
    renderer.unrealize()
    print(f"{view}{tag} / {palette}: {actual_width} × {actual_height}; CSS and geometry pass")
    window.destroy()
    Gtk.StyleContext.remove_provider_for_display(Gdk.Display.get_default(), css)
    settle()


with tempfile.TemporaryDirectory(prefix="desktop-ui-") as directory:
    sandbox = Path(directory)
    ctl.HOME, ctl.CONFIG, ctl.STATE = sandbox, sandbox / ".config", sandbox / "state/desktop"
    ctl.DATA, ctl.RUNTIME = sandbox / "data", sandbox / "runtime/desktop"
    for source, target in [("appearance/.config/desktop/themes", "desktop/themes"), ("walker/.config/walker/templates", "walker/templates")]:
        path = ctl.CONFIG / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(ROOT / "dotfiles" / source)
    (ctl.CONFIG / "desktop/menus.json").symlink_to(ROOT / "dotfiles/desktop-settings/.config/desktop/menus.json")
    menus = json.loads((ctl.CONFIG / "desktop/menus.json").read_text())
    for group in [*menus, "theme", "font", "config", "power-profile"]:
        render("menu", 350, 0, group=group)
    render("clipboard", 1000, 520)
    render("clipboard", 1000, 520, image=True)
    render("clipboard-compact", 880, 380)
    render("clipboard-compact", 480, 380)
    render("clipboard", 1000, 520, "catppuccin-latte")
