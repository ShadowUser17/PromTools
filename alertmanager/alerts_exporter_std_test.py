#!/usr/bin/env python3
from ast import arg
from urllib import request
import subprocess as sproc
import threading
import os


class TestAlertManagerExporter:
    def __init__(self) -> None:
        target = 'http://127.0.0.1:49152/'
        self.request = request.Request(target, method='GET')
        self.request_count = 0
        self.request_error = 0

        command = os.path.join(os.getcwd(), 'alerts_exporter_std.py')
        self.exporter = sproc.Popen([command], shell=True)
        print('Start:', command, self.exporter.pid)


    def __call__(self) -> None:
        worker_list = list()

        for test_id in range(0, 9):
            test = threading.Timer(2.0, self.test_parallel_get, args=(test_id,))
            worker_list.append(test)

        for test in worker_list:
            test.start()

        for test in worker_list:
            test.join()


    def __del__(self) -> None:
        self.exporter.terminate()
        print('Count:', self.request_count)
        print('Error:', self.request_error)


    def test_parallel_get(self, *args, **kwargs) -> None:
        try:
            self.request_count += 1
            with request.urlopen(self.request) as req:
                data_size = len(req.read())
                print('Test-{}: {}'.format(args[0], data_size))

        except Exception:
            self.request_error += 1


if __name__ == '__main__':
    testing = TestAlertManagerExporter()
    testing()
    del testing
