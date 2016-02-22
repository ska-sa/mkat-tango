import sys
import logging
import threading

from PyTango.server import server_run

def simulator_main(sim_class):
    """Main function for a simulator with class sim_class

    sim_class is a tango.server.Device subclass

    """
    run_ipython = '--ipython' in sys.argv
    if run_ipython:
        import IPython
        sys.argv.remove('--ipython')
        def run_ipython(sim_class):
            IPython.embed()
        t = threading.Thread(target=run_ipython, args=(sim_class,) )
        t.setDaemon(True)
        t.start()

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - '
        '%(pathname)s : %(lineno)d - %(message)s',
        level=logging.INFO)

    server_run([sim_class])
