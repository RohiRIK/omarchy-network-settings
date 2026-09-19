import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('settings', Path(__file__).resolve().parents[1] / 'settings.py')
settings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(settings)

class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.data = {'UUID': 'test', 'IP4.ADDRESS': '192.168.7.42/23',
                     'IP4.GATEWAY': '192.168.6.1', 'IP4.DNS': '192.168.6.1\n1.1.1.1'}
        self.calls = []
        self.nm_patch = patch.object(settings, 'nm', side_effect=self.nm)
        self.nm_patch.start()
        self.profile_patch = patch.object(settings, 'read_profile', return_value={'uuid': 'test', 'type': '802-3-ethernet'})
        self.profile_patch.start()
        self.addCleanup(self.nm_patch.stop)
        self.addCleanup(self.profile_patch.stop)

    def nm(self, *args):
        self.calls.append(args)
        return self.data.get(args[1], '') if args[0] == '-g' else ''

    def save(self, method='manual', address='192.168.7.42/23', gateway='192.168.6.1', dns='1.1.1.1'):
        with patch('sys.argv', ['settings.py', 'save', 'test', method, address, gateway, dns]):
            return settings.main()

    def test_current_preserves_actual_prefix_and_dns(self):
        data = settings.current_static('test')
        self.assertEqual(data['addresses'], '192.168.7.42/23')
        self.assertEqual(data['dns'], '192.168.6.1,1.1.1.1')
        self.assertIn('192.168.6.0/23', data['message'])
        self.assertEqual(data['method'], 'manual')
        self.assertTrue(all(c[0] == '-g' for c in self.calls))

    def test_current_rejects_inactive_profile(self):
        self.data['UUID'] = 'another-profile'
        with self.assertRaisesRegex(ValueError, 'Connect to this network'):
            settings.current_static('test')

    def test_current_rejects_missing_ipv4(self):
        self.data['IP4.ADDRESS'] = ''
        with self.assertRaisesRegex(ValueError, 'no current IPv4'):
            settings.current_static('test')

    def test_current_allows_no_gateway_or_dns(self):
        self.data.update({'IP4.GATEWAY': '', 'IP4.DNS': ''})
        data = settings.current_static('test')
        self.assertEqual((data['gateway'], data['dns']), ('', ''))

    def test_manual_updates_only_ipv4_without_activation(self):
        self.save()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0][:4], ('connection', 'modify', 'uuid', 'test'))
        self.assertNotIn('up', self.calls[0])
        self.assertNotIn('ipv6.method', self.calls[0])

    def test_dhcp_clears_static_address_and_dns_override(self):
        self.save('auto', 'old', 'old', '')
        values = dict(zip(self.calls[0][4::2], self.calls[0][5::2]))
        self.assertEqual(values['ipv4.addresses'], '')
        self.assertEqual(values['ipv4.gateway'], '')
        self.assertEqual(values['ipv4.ignore-auto-dns'], 'no')

    def test_invalid_addresses_never_write(self):
        for address in ('', '192.168.1.5', '999.1.1.1/24', '::1/64', '192.168.1.5/99'):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.save(address=address)
        self.assertEqual(self.calls, [])

    def test_invalid_gateway_dns_and_method_never_write(self):
        for kwargs in ({'gateway': 'invalid'}, {'dns': '::1'}, {'method': 'shared'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.save(**kwargs)
        self.assertEqual(self.calls, [])


class PublicIpTests(unittest.TestCase):
    def test_returns_valid_ipv4_with_timeout(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ip":"203.0.113.7"}'
        with patch.object(settings.urllib.request, 'urlopen', return_value=response) as request:
            self.assertEqual(settings.public_ip(), {'ip': '203.0.113.7'})
            self.assertEqual(request.call_args.kwargs['timeout'], 8)
            self.assertEqual(request.call_args.args[0].full_url, 'https://api.ipify.org?format=json')

    def test_rejects_invalid_response(self):
        from unittest.mock import MagicMock
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ip":"not-an-address"}'
        with patch.object(settings.urllib.request, 'urlopen', return_value=response):
            with self.assertRaises(ValueError):
                settings.public_ip()

    def test_offline_error_propagates_to_cli_error_handler(self):
        with patch.object(settings.urllib.request, 'urlopen', side_effect=TimeoutError('offline')):
            with self.assertRaises(TimeoutError):
                settings.public_ip()

if __name__ == '__main__':
    unittest.main()
