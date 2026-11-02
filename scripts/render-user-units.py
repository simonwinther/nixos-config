#!/usr/bin/env python3
"""Render portable systemd user units into a NEW Stow staging directory; never enable them."""
import argparse
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('target',type=Path)
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
 'desktop-search':('Search and clipboard providers','%h/.local/bin/desktop-search serve','exec','Restart=on-failure'),
 'desktop-bar':('Morphing Notch Bar','%h/.local/bin/desktop-bar','exec','Restart=on-failure\nExecReload=kill -USR2 $MAINPID'),
 'desktop-mako':('Notifications','%h/.local/bin/desktopctl run mako','exec','Restart=on-failure'),
 # Keeps Chromium warm (about 650 MB idle) so project windows open in about 0.6 s.
 'desktop-browser':('Background browser','chromium --no-startup-window','exec',''),
 'desktop-monitor-watch':('Recover disconnected laptop displays','%h/.local/bin/desktopctl monitor-watch','exec','Restart=on-failure'),
 'desktop-awww':('Wallpaper daemon','awww-daemon --no-cache','exec','Restart=on-failure'),
 'desktop-swayosd':('Volume and brightness display','%h/.local/bin/desktopctl run swayosd-server','exec','Restart=on-failure'),
 'desktop-hypridle':('Idle and suspend coordination','%h/.local/bin/desktopctl idle-worker','exec','Restart=on-failure'),
 'desktop-fcitx5':('Keyboard input method','fcitx5 --disable notificationitem','exec','Restart=on-failure'),
 'desktop-wallpaper':('Restore wallpapers','%h/.local/bin/desktopctl wallpaper restore','oneshot',''),
 'desktop-file-picker':('Prepare windowless file and PDF picker terminal','%h/.local/bin/file-picker --prepare-terminal','oneshot','RemainAfterExit=yes\nTimeoutStartSec=20'),
}
for name,(description,command,kind,extra) in services.items():
 text=base.format(description=description,command=command,kind=kind,extra=extra)
 if name=='desktop-prepare':text=text.replace('After=desktop-prepare.service','Before=desktop-session.target')
 if name=='desktop-bar':
  text=text.replace('After=desktop-prepare.service','After=desktop-prepare.service desktop-search.service\nWants=desktop-search.service')
 if name=='desktop-wallpaper':text=text.replace('After=desktop-prepare.service','After=desktop-prepare.service desktop-awww.service\nRequires=desktop-awww.service')
 if name == 'desktop-bar':text=text.replace('PartOf=desktop-session.target','PartOf=desktop-session.target\nConditionPathExists=!%h/.local/state/desktop/toggles/bar-off')
 (units/(name+'.service')).write_text(text)
for name,command in {'desktop-lock':'desktopctl lock-worker','desktop-lock-only':'desktopctl lock-worker --only','desktop-hyprsunset':'hyprsunset'}.items():
 (units/(name+'.service')).write_text('[Unit]\nDescription='+name+'\n\n[Service]\nType=exec\nEnvironment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin\nExecStart='+command+'\n')
print(a.target/'desktop-services')
print('Rendered only. Review, Stow to the target home, reload the target user manager, then start desktop-session.target.')
