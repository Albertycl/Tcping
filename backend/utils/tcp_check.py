from utils import probe_sim


def is_port_open(ip, port, timeout=2, retries=3, delay=1):
    """Probes are simulated, so the SSH pre-check asks the simulator."""
    return probe_sim.probe_is_up(ip)
