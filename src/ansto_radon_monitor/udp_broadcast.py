from .configuration import DetectorConfig
from .openrvdas_udp.udp_writer import UDPWriter

from typing import List, Any, Dict
import json
import logging


_logger = logging.getLogger()

def udp_broadcast(data: List[Dict[str,Any]], config: DetectorConfig):
    if len(data) == 0 or config.udp_destination is None:
        return  

    
    # JSON-encode each record before sending to the writer
    encoded_data = [json.dumps(itm, default=str) for itm in data]
    writer = UDPWriter(destination=config.udp_destination, port=config.udp_port, 
                       mc_interface=config.udp_multicast_interface)
    writer.write(encoded_data)    
    n = len(data)
    _logger.info(f"Sent {n} JSON-encoded record(s) to {config.udp_destination}:{config.udp_port}")