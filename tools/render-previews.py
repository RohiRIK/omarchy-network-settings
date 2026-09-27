#!/usr/bin/env python3
"""Render the actual plugin QML with synthetic data in an offscreen window."""
import atexit, json, os, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = Path(os.environ.get("OMARCHY_PATH", "/usr/share/omarchy")) / "shell"
work = Path(tempfile.mkdtemp(prefix="network-settings-preview-"))
atexit.register(shutil.rmtree, work, ignore_errors=True)
for name in ["Ui", "Commons", "services"]:
    shutil.copytree(SHELL / name, work / name)
shutil.copytree(ROOT, work / "Plugin", ignore=shutil.ignore_patterns(".git", "docs", "tools", "tests"))
# Replace only the platform window adapter; the plugin's UI stays intact.
(work / "Ui" / "KeyboardPanel.qml").write_text("""
import QtQuick
import Quickshell
import qs.Commons
FloatingWindow {
 id: root
 property var anchorItem
 property var owner
 property var bar
 property bool open: false
 property var focusTarget
 property bool blocked: false
 property int contentWidth: 480
 property int contentHeight: 560
 default property alias contents: body.data
 function fittedContentWidth(w) { return w }
 function fittedContentHeight(h, cap) { return cap === undefined ? h : Math.min(h, cap) }
 implicitWidth: contentWidth + 40
 implicitHeight: contentHeight + 40
 visible: open
 color: Color.background
 Rectangle {
   id: frame
   width: root.contentWidth + 40
   height: root.contentHeight + 40
   color: Color.background
   border.color: Color.foreground
   border.width: 1
   Item { id: body; anchors.fill: parent; anchors.margins: 20 }
 }
 Timer {
   interval: 1200; running: root.open; repeat: false
   onTriggered: { frame.grabToImage(function(result) {
     if (!result.saveToFile(Qt.resolvedUrl("OUTPUT").toString().replace("file://", ""))) Qt.exit(1)
     else Qt.quit()
   }, Qt.size(frame.width * 2, frame.height * 2)); }
 }
}
""")

# Static demo: cut every live source (NetworkManager, nmcli, ipify, polling)
# in this copy so no real SSID, profile or address can reach a screenshot.
p = work / "Plugin" / "Panel.qml"
s = p.read_text()
for old, new in [
    ('running: root.opened', 'running: false'),
    ('Component.onCompleted: refresh()', 'Component.onCompleted: {}'),
    ('function refresh(scanWifi) {', 'function refresh(scanWifi) { return'),
    ('publicIpProc.running = true', 'return'),
    ('ipProc.running = true', 'return'),
    ('Networking.devices ? Networking.devices.values : []', '[]'),
    ('wifiNetworks = Model.sortWifiRows(nets)', 'return'),
    ('if (wiredDevice && wiredDevice.connected) return "ethernet"', 'return "wifi"'),
    ('ipcTarget: "omarchy.network"', 'ipcTarget: ""'),
]:
    if old not in s:
        raise SystemExit("Panel.qml changed; update preview patch: " + old)
    s = s.replace(old, new)
p.write_text(s)

info = dict(iface="wlan0", type="wifi", ssid="Home Network", ip="192.168.1.50", prefix="24",
            gateway="192.168.1.1", signal="-48", freq="5180", bitrate="866.7",
            rx_bytes="1843200000", tx_bytes="265400000", router_ping_ms="2.1", internet_ping_ms="14.6")
networks = [
    dict(connected=True, known=True, ssid="Home Network", signal=86, security="WPA2"),
    dict(connected=False, known=True, ssid="Office", signal=58, security="WPA2"),
    dict(connected=False, known=False, ssid="Cafe Guest", signal=71, security="Open"),
    dict(connected=False, known=False, ssid="Neighbor 5G", signal=34, security="WPA3"),
]
profiles = [dict(value="demo-home", label="Home Network"), dict(value="demo-wired", label="Wired connection 1"),
            dict(value="demo-office", label="Office")]
auto = dict(uuid="demo-home", method="auto", addresses="", gateway="", dns="")
manual = dict(uuid="demo-home", method="manual", addresses="192.168.1.50/24", gateway="192.168.1.1",
              dns="192.168.1.1,1.1.1.1")

views = {
    "wifi": "",
    "ip-dhcp": f'plugin.ipEditing = true; plugin.ipProfiles = {json.dumps(profiles)}; plugin.ipLoad({json.dumps(auto)});',
    "ip-manual": f'plugin.ipEditing = true; plugin.ipProfiles = {json.dumps(profiles)}; plugin.ipLoad({json.dumps(manual)});'
                 'plugin.ipMessage = "Filled from current subnet 192.168.1.0/24. Review, then save.";'
                 'plugin.publicIp = "203.0.113.42";',
}
adapter = (work / "Ui" / "KeyboardPanel.qml").read_text()
(ROOT / "docs").mkdir(exist_ok=True)
for view, selection in views.items():
    out = ROOT / "docs" / (view + ".png")
    out.unlink(missing_ok=True)
    (work / "Ui" / "KeyboardPanel.qml").write_text(adapter.replace("OUTPUT", str(out)))
    (work / "shell.qml").write_text("""
import QtQuick
import Quickshell
import qs.Commons
import "Plugin" as Plugin
ShellRoot {
 QtObject {
  id: fakeBar
  property color foreground: Color.foreground
  property color barForeground: Color.foreground
  property color background: Color.background
  property color urgent: Color.urgent
  property string fontFamily: Style.font.family
  property bool vertical: false
  property int barSize: 32
  property string position: "top"
  property bool foregroundAnimationEnabled: false
  function hideTooltip() {}
  function showTooltip() {}
  function registerClickTarget() {}
  function unregisterClickTarget() {}
 }
 Plugin.Panel { id: plugin; bar: fakeBar }
 Timer {
  interval: 200; running: true; repeat: false
  onTriggered: {
    plugin.open();
    plugin.info = INFO;
    plugin.wifiNetworks = NETWORKS;
    plugin.wifiStationAvailable = true;
    plugin.scanning = false;
    plugin.dnsProvider = "Cloudflare";
    plugin.bandCurrent = "5";
    plugin.bandSelected = "auto";
    plugin.bandAvailable = ["2.4", "5"];
    plugin.downloadRate = 2457600;
    plugin.uploadRate = 312000;
    plugin.routerPingLatency = 2.1;
    plugin.internetPingLatency = 14.6;
    plugin.internetPingSamples = [14.2, 15.1, 14.6];
    SELECTION
  }
 }
}
""".replace("INFO", json.dumps(info)).replace("NETWORKS", json.dumps(networks)).replace("SELECTION", selection))
    runtime = work / "runtime"
    runtime.mkdir(mode=0o700, exist_ok=True)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="basic",
               QT_QUICK_BACKEND="software", QT_SCALE_FACTOR="1", XDG_RUNTIME_DIR=str(runtime))
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    result = subprocess.run(["quickshell", "-p", str(work), "--no-color"], env=env,
                            capture_output=True, text=True, timeout=20)
    if result.returncode or not out.exists():
        raise SystemExit(result.stdout + result.stderr)
    print(out)
shutil.copy2(ROOT / "docs" / "ip-manual.png", ROOT / "preview.png")
shutil.rmtree(work)
