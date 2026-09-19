import ipaddress
import json
import subprocess
import sys
import urllib.request

def nm(*args):
    p = subprocess.run(['nmcli', '--escape', 'no', *args], capture_output=True, text=True, timeout=20)
    if p.returncode:
        raise ValueError(p.stderr.strip() or 'NetworkManager request failed')
    return p.stdout.strip()

def read_profile(uuid):
    values = nm('-g', 'connection.id,connection.type,ipv4.method,ipv4.addresses,ipv4.gateway,ipv4.dns', 'connection', 'show', 'uuid', uuid).split('\n')
    values += [''] * (6-len(values))
    return dict(zip(['name', 'type', 'method', 'addresses', 'gateway', 'dns'], values), uuid=uuid)

def current_static(uuid):
    profile = read_profile(uuid)
    if profile['type'] not in ('802-3-ethernet', '802-11-wireless'):
        raise ValueError('Select a Wi-Fi or Ethernet connection')
    active = nm('-g', 'UUID', 'connection', 'show', '--active').splitlines()
    if uuid not in active:
        raise ValueError('Connect to this network first to use its current subnet')
    def live(field):
        return nm('-g', field, 'connection', 'show', 'uuid', uuid).splitlines()
    addresses = live('IP4.ADDRESS')
    if not addresses:
        raise ValueError('This connection has no current IPv4 address')
    parsed = [ipaddress.IPv4Interface(value) for value in addresses]
    gateway = live('IP4.GATEWAY')
    dns = live('IP4.DNS')
    profile.update(method='manual', addresses=','.join(str(value) for value in parsed),
                   gateway=gateway[0] if gateway else '', dns=','.join(dns),
                   message='Filled from current subnet ' + str(parsed[0].network) + '. Review, then save.')
    return profile

def public_ip():
    request = urllib.request.Request('https://api.ipify.org?format=json',
                                     headers={'User-Agent': 'Omarchy-Network-Settings/0.2.0'})
    with urllib.request.urlopen(request, timeout=8) as response:
        data = json.loads(response.read(1024))
    return {'ip': str(ipaddress.IPv4Address(data['ip']))}

def main():
    action = sys.argv[1]
    if action == 'public':
        return public_ip()
    if action == 'list':
        profiles = []
        for uuid in nm('-g', 'UUID', 'connection', 'show').splitlines():
            p = read_profile(uuid)
            if p['type'] in ('802-3-ethernet', '802-11-wireless'):
                profiles.append({'value': uuid, 'label': p['name']})
        active = nm('-g', 'UUID', 'connection', 'show', '--active').splitlines()
        selected = next((p['value'] for p in profiles if p['value'] in active), profiles[0]['value'] if profiles else '')
        return {'profiles': profiles, 'selected': read_profile(selected) if selected else None}
    if action == 'read':
        return read_profile(sys.argv[2])
    if action == 'current':
        return current_static(sys.argv[2])
    if action == 'save':
        uuid, method, addresses, gateway, dns = sys.argv[2:]
        previous = read_profile(uuid)
        if previous['type'] not in ('802-3-ethernet', '802-11-wireless'):
            raise ValueError('Select a Wi-Fi or Ethernet connection')
        if method not in ('auto', 'manual'):
            raise ValueError('Select DHCP or Static')
        addresses = addresses.strip()
        gateway = gateway.strip()
        dns = dns.strip()
        if method == 'manual':
            if not addresses:
                raise ValueError('Enter an IPv4 address with prefix, such as 192.168.1.50/24')
            for value in addresses.split(','):
                if '/' not in value or ipaddress.ip_interface(value.strip()).version != 4:
                    raise ValueError('Use IPv4 addresses with a prefix, such as 192.168.1.50/24')
            if gateway and ipaddress.ip_address(gateway).version != 4:
                raise ValueError('Gateway must be an IPv4 address')
        else:
            addresses = gateway = ''
        for value in dns.split(',') if dns else []:
            if ipaddress.ip_address(value.strip()).version != 4:
                raise ValueError('Use IPv4 DNS addresses separated by commas')
        nm('connection', 'modify', 'uuid', uuid, 'ipv4.method', method,
           'ipv4.addresses', addresses, 'ipv4.gateway', gateway,
           'ipv4.dns', dns, 'ipv4.ignore-auto-dns', 'yes' if dns else 'no')
        return {'message': 'Saved. Changes take effect when this connection reconnects.'}
    raise ValueError('Unknown action')

if __name__ == '__main__':
    try:
        print(json.dumps(main()))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)
