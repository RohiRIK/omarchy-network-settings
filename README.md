# Omarchy Network Settings

Native Wi-Fi and IPv4 configuration inside the Omarchy network panel. Uses the shell's own controls, colors, and fonts.

- Connect to Wi-Fi using Omarchy's existing network panel.
- Edit saved Wi-Fi and Ethernet profiles, with the active connection selected automatically.
- Choose DHCP or a manual IPv4 address, prefix, gateway, and DNS servers.
- **Use current IP as fixed** fills the current connection's address, subnet prefix, gateway, and DNS into a manual configuration.
- Save a profile without interrupting the active connection. Reconnect to apply it.

## Requirements

Tested on Omarchy **4.0.3**, with its Quickshell plugin system, NetworkManager (`nmcli`), and Python 3. Uses Omarchy internal UI components; compatibility with future shell releases may require updates.

## Install

```bash
omarchy plugin add https://github.com/RohiRIK/omarchy-network-settings.git --enable
```

The plugin replaces the built-in network widget through Omarchy's `clonedFrom` mechanism. Click the network icon, then **IP settings**. NetworkManager handles authorization when a profile is saved.

If you already use a custom clone of `omarchy.network`, disable that clone before enabling this plugin.

### Optional Setup → Network menu

Merge the entries in [menu.jsonc](menu.jsonc) into `~/.config/omarchy/extensions/omarchy-menu.jsonc`. Keep your other entries. Omarchy reloads this menu automatically.

This adds separate **Wi-Fi** and **IP settings** actions under **Network**, alongside Omarchy's existing network options. The plugin also works directly from the bar without this menu customization.

## Set a fixed IP

1. Open **IP settings** and select the connection.
2. Choose **Manual (choose an IP)** and enter an address with prefix, such as `192.168.1.50/24`; or click **Use current IP as fixed** to fill the active connection's values.
3. Review the gateway and DNS servers, then click **Save settings**.
4. Reconnect that connection to apply the saved profile.

The current-IP button only fills the form. It does not choose a new unused address or create a DHCP reservation on your router. Reserve or exclude the address in the router's DHCP configuration to prevent it being leased to another device.

Only IPv4 settings are edited. Existing IPv6 settings and other profile properties remain as configured. The current-IP shortcut requires the selected connection to be active and have an IPv4 address. It does not copy values from another interface.

## Update and remove

```bash
omarchy plugin update rohirik.network-settings
omarchy plugin disable rohirik.network-settings
omarchy plugin enable omarchy.network
omarchy plugin remove rohirik.network-settings
```

If you added the optional menu entries, remove `setup.network.wifi` and `setup.network.ip` when uninstalling. The stock Network submenu can remain.

## Development

```bash
python3 -m unittest discover -s tests -v
omarchy plugin validate .
```

Tests mock NetworkManager and never modify a real connection.

## Attribution

The network panel and model derive from [Basecamp Omarchy](https://github.com/basecamp/omarchy), packaged version 4.0.3-1. This plugin adds the IPv4 editor, current-IP shortcut, and profile helper. Distributed under the MIT license; see [LICENSE](LICENSE).
