hl.monitor({ output = "", mode = "preferred", position = "auto", scale = "auto" })
hl.monitor({ output = "HDMI-A-1", mode = "1920x1080@100", position = "0x0", scale = 1 })
hl.monitor({ output = "eDP-1", mode = "1920x1080@60.02", position = "160x1080", scale = 1.2 })
hl.env("DESKTOP_PRIMARY_OUTPUT", "HDMI-A-1")
