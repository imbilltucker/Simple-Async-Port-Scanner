#!/usr/bin/env python3
# https://github.com/EONRaider/Simple-Async-Port-Scanner

__author__ = 'EONRaider @ keybase.io/eonraider'

import asyncio
import contextlib
import time
from typing import Iterable, Iterator, Tuple


class AsyncTCPScanner(object):
    def __init__(self, target_addresses: Iterable[str], ports: Iterable[int]):
        self.target_addresses = target_addresses
        self.ports = ports
        self.start_time = None
        self.end_time = None
        self.scan_results = None
        self.__observers = list()

    def register(self, observer):
        self.__observers.append(observer)

    def __notify_all(self):
        for observer in self.__observers:
            observer.update(self.target_addresses,
                            self.ports,
                            self.scan_results,
                            self.start_time,
                            self.end_time)

    def execute(self):
        self.start_time = time.time()
        self.scan_results: tuple = asyncio.run(self.__scan_targets())
        self.end_time = time.time()
        self.__notify_all()

    async def __scan_targets(self) -> tuple:
        loop = asyncio.get_event_loop()
        scans = (asyncio.create_task(self.__tcp_connection(loop, address, port))
                 for port in self.ports for address in self.target_addresses)
        return await asyncio.gather(*scans)

    @staticmethod
    async def __tcp_connection(loop: asyncio.AbstractEventLoop,
                               ip_address: str,
                               port: int) -> Tuple[str, int, str]:
        with contextlib.suppress(ConnectionRefusedError, asyncio.TimeoutError,
                                 OSError):
            port_state = 'closed'
            await asyncio.wait_for(
                asyncio.open_connection(ip_address, port, loop=loop),
                timeout=3.0)
            port_state = 'open'
        return ip_address, port, port_state


class ScanToScreen(object):
    def __init__(self, subject):
        subject.register(self)

    @staticmethod
    def update(target_addresses, ports, scan_results, start_time, end_time):
        targets = ' | '.join(target_addresses)
        num_ports = len(ports) * len(target_addresses)
        elapsed_time = end_time - start_time

        print(f'Starting Async Port Scanner at {time.ctime(start_time)}')
        print(f'Scan report for {targets}\n')

        for result in scan_results:
            print('{0: >7} {1}:{2} --> {3}'.format('[+]', *result))

        print(f"\nAsync TCP Connect scan of {num_ports} ports for {targets} "
              f"completed in {elapsed_time:.3f} seconds")


if __name__ == '__main__':
    import argparse


    def parse_ports(ports) -> Iterator[int]:
        """
        Yields an iterator with integers extracted from a string
        consisting of mixed port numbers and/or ranged intervals.
        Ex: From '20-25,53,80,111' to (21,22,25,26,27,28,29,30,53,80)
        """
        for port in ports.split(','):
            try:
                yield int(port)
            except ValueError:
                start, end = (int(port) for port in port.split('-'))
                yield from range(start, end + 1)


    usage = ('Usage examples:\n'
             '1. python3 simple_async_scan.py google.com -p 80,443\n'
             '2. python3 simple_async_scan.py '
             '45.33.32.156,demo.testfire.net,18.192.172.30 '
             '-p 20-25,53,80,111,135,139,443,3306,5900')

    parser = argparse.ArgumentParser(
        description='Simple asynchronous TCP Connect port scanner',
        epilog=usage,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('targets', type=str, metavar='IP_ADDRESSES',
                        help="A comma-separated sequence of IP addresses "
                             "and/or domain names to scan, e.g., "
                             "'45.33.32.156,65.61.137.117,"
                             "testphp.vulnweb.com'.")
    parser.add_argument('-p', '--ports', type=str, required=True,
                        help="A comma-separated sequence of port numbers "
                             "and/or port ranges to scan on each target "
                             "specified, e.g., '20-25,53,80,443'.")
    args = parser.parse_args()

    target_sequence: list = args.targets.split(',')
    port_sequence = parse_ports(args.ports)

    asyncio.run(scanner(target_addresses=target_sequence, ports=port_sequence))
