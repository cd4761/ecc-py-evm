from typing import (
    Type,
)

from eth.rlp.blocks import BaseBlock
from eth.vm.forks.byzantium import (
    ByzantiumVM,
    get_uncle_reward,
)
from eth.vm.state import BaseState

from .blocks import PetersburgBlock
from .constants import EIP1234_BLOCK_REWARD
from .headers import (
    compute_petersburg_difficulty,
    configure_petersburg_header,
    create_petersburg_header_from_parent,
)
from .state import PetersburgState


class PetersburgVM(ByzantiumVM):
    # fork name
    fork = 'petersburg'

    # classes
    block_class: Type[BaseBlock] = PetersburgBlock
    _state_class: Type[BaseState] = PetersburgState

    # Methods
    create_header_from_parent = staticmethod(create_petersburg_header_from_parent)  # type: ignore
    compute_difficulty = staticmethod(compute_petersburg_difficulty)    # type: ignore
    configure_header = configure_petersburg_header
    get_uncle_reward = staticmethod(get_uncle_reward(EIP1234_BLOCK_REWARD))

    @staticmethod
    def get_block_reward() -> int:
        return EIP1234_BLOCK_REWARD
