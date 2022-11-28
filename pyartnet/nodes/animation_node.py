from typing import Union, Optional, TypeVar

from .base_node import BaseNode

TYPE_ANIMATION_NODE = TypeVar('TYPE_ANIMATION_NODE', bound='AnimationNode')


class AnimationNode(BaseNode):
    def __init__(self, ip: str, port: int,
                 refresh_every: Union[int, float] = 2, sequence_counter=True,
                 source_ip: Optional[str] = None, source_port: Optional[int] = None):
        super().__init__(ip, port,
                         refresh_every=refresh_every, sequence_counter=sequence_counter,
                         source_ip=source_ip, source_port=source_port)

        a = self._socket

