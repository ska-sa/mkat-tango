import logging
import time

MODULE_LOGGER = logging.getLogger(__name__)

class Model(object):
    def __init__(self, name, start_time=None, min_update_time=0.99,
                 time_func=time.time):
        self.name = name
        self.min_update_time = min_update_time
        self.time_func = time_func
        self.start_time = start_time or time_func()
        self.last_update_time = self.start_time
        self.sim_quantities = {}
        self._sim_state = {}
        self.setup_sim_quantities()
        # Making a public reference to _sim_state. Allows us to hook read-only views
        # or updates or whatever the future requires of this humble public attribute.
        self.quantity_state = self._sim_state


    def setup_sim_quantities(self):
        """Set up self.sim_quantities with simulated quantities

        Subclasses should implement this method. Should place simulated quantities in
        self.sim_quantities dict. Keyed by name of quantity, value must be instances
        satisfying the :class:`quantites.Quantity` interface.

        Notes
        =====

        - Must use self.start_time to set initial time values.
        - Must call super method after setting up `sim_quantities`

        """
        self._sim_state.update(
            {var: (quant.last_val, quant.last_update_time)
             for var, quant in self.sim_quantities.items()})

    def update(self):
        sim_time = self.time_func()
        dt = sim_time - self.last_update_time
        if dt < self.min_update_time:
            MODULE_LOGGER.debug(
                "Sim {} skipping update at {}, dt {} < {}"
                .format(self.name, sim_time, dt, self.min_update_time))
            return

        MODULE_LOGGER.info("Stepping at {}, dt: {}".format(sim_time, dt))
        self.last_update_time = sim_time
        try:
            for var, quant in self.sim_quantities.items():
                self._sim_state[var] = (quant.next_val(sim_time), sim_time)
        except Exception:
            MODULE_LOGGER.exception('Exception in update loop')
