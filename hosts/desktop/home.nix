{ ... }:
{
  # Preserve the reference settings; compositor scaling belongs to each display.
  desktop.appearance = {
    barScale = 1.0;
    terminalScale = 1.0;
  };
  # The portrait ASUS keeps its compact bar, identified by hardware, not a port.
  desktop.outputs = {
    full = [
      "!Ancor Communications Inc VG248 J5LMQS024117"
      "*"
    ];
    minimal = [ "Ancor Communications Inc VG248 J5LMQS024117" ];
  };
}
