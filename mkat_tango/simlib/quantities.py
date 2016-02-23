import time
import abc

from random import gauss

inf = float('inf')
ninf = float('-inf')

class Quantity(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, start_value=None, start_time=None):
        """Subclasses must call this super __init__()

        Subclasses should also initialise the `last_val` attribute with the initial
        quantity value.

        """
        self.last_update_time = start_time or time.time()
        if start_value is not None:
            self.last_val = start_value


    @abc.abstractmethod
    def next_val(self, t):
        """Return the next simulated value for simulation time at t seconds

        Must update attributes `last_val` with the new value and `last_update_time` with
        the simulation time

        """
        pass

    def set_val(self, val, t):
        """Set a value to the quantity"""
        self.last_update_time = t
        self.last_val = val

class GaussianSlewLimited(Quantity):
    """A Gaussian random variable a slew-rate limit and clipping

    Parameters
    ==========

    mean : float
        Gaussian mean value
    std_dev : float
        Gaussian standard deviation
    max_slew_rate : float
        Maximum quantity slew rate in amount per second. Random values will be clipped to
        satisfy this condition.
    min_bound : float
        Minimum quantity value, random values will be clipped if needed.
    max_bound : float
        Maximum quantity value, random values will be clipped if needed.

    """

    def __init__(self, mean, std_dev,
                 max_slew_rate=inf,
                 min_bound=ninf, max_bound=inf,
                 start_value=None, start_time=None):
        start_value = start_value if start_value is not None else mean
        super(GaussianSlewLimited, self).__init__(start_value=start_value,
                                                  start_time=start_time)
        self.mean = mean
        self.std_dev = std_dev
        assert max_slew_rate > 0
        self.max_slew_rate = max_slew_rate
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.last_val = mean

    def next_val(self, t):
        dt = t - self.last_update_time
        max_slew = self.max_slew_rate*dt
        new_val = gauss(self.mean, self.std_dev)
        delta = new_val - self.last_val
        val = self.last_val + cmp(delta, 0) * min(abs(delta), max_slew)
        val = min(val, self.max_bound)
        val = max(val, self.min_bound)
        self.last_val = val
        return val

class ConstantQuantity(Quantity):
    """A quantity that does not change unless explicitly set"""

    def next_val(self, t):
        return self.last_val
