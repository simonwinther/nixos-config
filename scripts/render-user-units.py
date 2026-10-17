#!/usr/bin/env python3
"""Render portable systemd user units into a NEW Stow staging directory; never enable them."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('target',type=Path)
p.add_argument('--laptop',action='store_true',help='Include the minimal second bar')
a=p.parse_args()
if a.target.exists() and any(a.target.iterdir()):p.error('Use an empty staging directory')
units=a.target/'desktop-services/.config/systemd/user'
units.mkdir(parents=True,exist_ok=True)
( units/'desktop-session.target').write_text('''[Unit]
Description=Personal Hyprland desktop
Requires=desktop-prepare.service
After=desktop-prepare.service
BindsTo=graphical-session.target
PartOf=graphical-session.target
''')
base='''[Unit]
Description={description}
PartOf=desktop-session.target
After=desktop-prepare.service

[Service]
Type={kind}
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart={command}
{extra}
[Install]
WantedBy=desktop-session.target
'''
services={
 'desktop-prepare':('Prepare writable desktop state','%h/.local/bin/desktopctl prepare','oneshot','RemainAfterExit=yes'),
 'desktop-elephant':('Search providers','elephant','exec','Restart=on-failure'),
 'desktop-walker':('Launcher','%h/.local/bin/desktopctl run walker -- --gapplication-service','exec','Restart=on-failure'),
 'desktop-waybar':('Main bar','%h/.local/bin/desktopctl run waybar -- --config %h/.config/waybar/config.jsonc --style %h/.config/waybar/style.css','exec','Restart=on-failure'),
 'desktop-workspaces':('Workspace sliders','%h/.local/bin/workspaces-slider','exec','Restart=on-failure'),
 'desktop-mako':('Notifications','%h/.local/bin/desktopctl run mako','exec','Restart=on-failure'),
 'desktop-monitor-watch':('Recover disconnected laptop displays','%h/.local/bin/desktopctl monitor-watch','exec','Restart=on-failure'),
 'desktop-awww':('Wallpaper daemon','awww-daemon --no-cache','exec','Restart=on-failure'),
 'desktop-swayosd':('Volume and brightness display','%h/.local/bin/desktopctl run swayosd-server','exec','Restart=on-failure'),
 'desktop-hypridle':('Idle handling','hypridle','exec','Restart=on-failure'),
 'desktop-wallpaper':('Restore wallpapers','%h/.local/bin/desktopctl wallpaper restore','oneshot',''),
 'desktop-file-picker':('Prepare file picker','%h/.local/bin/file-picker --warm','oneshot','RemainAfterExit=yes\nTimeoutStartSec=20'),
 'desktop-pdf-picker':('Prepare PDF picker','%h/.local/bin/file-picker --warm --pdf','oneshot','RemainAfterExit=yes\nTimeoutStartSec=20'),
}
if a.laptop:services['desktop-waybar-minimal']=('Minimal bar','%h/.local/bin/desktopctl run waybar -- --config %h/.config/waybar/config-minimal.jsonc --style %h/.config/waybar/style-minimal.css','exec','Restart=on-failure')
for name,(description,command,kind,extra) in services.items():
 text=base.format(description=description,command=command,kind=kind,extra=extra)
 if name=='desktop-prepare':text=text.replace('After=desktop-prepare.service','Before=desktop-session.target')
 if name=='desktop-walker':text=text.replace('After=desktop-prepare.service','After=desktop-prepare.service desktop-elephant.service\nRequires=desktop-elephant.service')
 if name=='desktop-wallpaper':text=text.replace('After=desktop-prepare.service','After=desktop-prepare.service desktop-awww.service\nRequires=desktop-awww.service')
 (units/(name+'.service')).write_text(text)
for name,command in {'desktop-lock':'desktopctl lock-worker','desktop-lock-only':'desktopctl lock-worker --only','desktop-hyprsunset':'hyprsunset'}.items():
 (units/(name+'.service')).write_text('[Unit]\nDescription='+name+'\n\n[Service]\nType=exec\nEnvironment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin\nExecStart='+command+'\n')
print(a.target/'desktop-services')
print('Rendered only. Review, Stow to the target home, reload the target user manager, then start desktop-session.target.')
