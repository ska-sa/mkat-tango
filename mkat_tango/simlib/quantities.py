import time

from random import gauss

inf = float('inf')
ninf = float('-inf')

class GaussianSlewLimited(object):
    def __init__(self, mean, std_dev,
                 max_slew_rate=inf,
                 min_bound=ninf, max_bound=inf,
                 start_time=None):
        self.mean = mean
        self.std_dev = std_dev
        assert max_slew_rate > 0
        self.max_slew_rate = max_slew_rate
        self.min_bound = min_bound
        self.max_bound = max_bound
        self.last_val = mean
        self.last_update_time = start_time or time.time()

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
