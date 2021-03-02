# -*- coding: utf-8 -*-

import pytest

from ansto_radon_monitor.main import fib

__author__ = "Alan Griffiths"
__copyright__ = "Alan Griffiths"
__license__ = "mit"


def test_fib():
    assert fib(1) == 1
    assert fib(2) == 1
    assert fib(7) == 13
    with pytest.raises(AssertionError):
        fib(-10)
