# -*- coding: UTF-8 -*-
import threading


class ThreadWithReturnValue(threading.Thread):
    """Simple implementation of a thread that returns a value."""
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs=None, Verbose=None): # pylint:disable=unused-argument
        if kwargs is None:
            kwargs = {}
        threading.Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        return self._return
