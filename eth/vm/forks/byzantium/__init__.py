from typing import (
    Type,
)

from eth_utils.toolz import (
    curry,
)
from eth_bloom import (
    BloomFilter,
)
from eth_utils import (
    encode_hex,
    ValidationError,
)

from eth.constants import (
    MAX_UNCLE_DEPTH,
)
from eth.rlp.blocks import BaseBlock
from eth.rlp.headers import BlockHeader
from eth.rlp.receipts import Receipt
from eth.rlp.transactions import BaseTransaction
from eth.validation import (
    validate_lte,
)
from eth.vm.forks.spurious_dragon import SpuriousDragonVM
from eth.vm.forks.frontier import make_frontier_receipt
from eth.vm.computation import BaseComputation
from eth.vm.state import BaseState

from .blocks import ByzantiumBlock
from .constants import (
    EIP649_BLOCK_REWARD,
    EIP658_TRANSACTION_STATUS_CODE_FAILURE,
    EIP658_TRANSACTION_STATUS_CODE_SUCCESS,
)
from .headers import (
    create_byzantium_header_from_parent,
    configure_byzantium_header,
    compute_byzantium_difficulty,
)
from .state import ByzantiumState


@curry
def get_uncle_reward(block_reward: int, block_number: int, uncle: BaseBlock) -> int:
    block_number_delta = block_number - uncle.block_number
    validate_lte(block_number_delta, MAX_UNCLE_DEPTH)
    return (8 - block_number_delta) * block_reward // 8


EIP658_STATUS_CODES = {
    EIP658_TRANSACTION_STATUS_CODE_SUCCESS,
    EIP658_TRANSACTION_STATUS_CODE_FAILURE,
}


class ByzantiumVM(SpuriousDragonVM):
    # fork name
    fork = 'byzantium'

    # classes
    block_class: Type[BaseBlock] = ByzantiumBlock
    _state_class: Type[BaseState] = ByzantiumState

    # Methods
    create_header_from_parent = staticmethod(create_byzantium_header_from_parent)   # type: ignore
    compute_difficulty = staticmethod(compute_byzantium_difficulty)     # type: ignore
    configure_header = configure_byzantium_header
    # Separated into two steps due to mypy bug of staticmethod.
    # https://github.com/python/mypy/issues/5530
    get_uncle_reward = get_uncle_reward(EIP649_BLOCK_REWARD)
    get_uncle_reward = staticmethod(get_uncle_reward)

    @classmethod
    def validate_receipt(cls, receipt: Receipt) -> None:
        super().validate_receipt(receipt)
        if receipt.state_root not in EIP658_STATUS_CODES:
            raise ValidationError(
                "The receipt's `state_root` must be one of [{0}, {1}].  Got: "
                "{2}".format(
                    encode_hex(EIP658_TRANSACTION_STATUS_CODE_SUCCESS),
                    encode_hex(EIP658_TRANSACTION_STATUS_CODE_FAILURE),
                    encode_hex(receipt.state_root),
                )
            )

    @staticmethod
    def get_block_reward() -> int:
        return EIP649_BLOCK_REWARD

    def add_receipt_to_header(self, old_header: BlockHeader, receipt: Receipt) -> BlockHeader:
        # Skip merkelizing the account data and persisting it to disk on every transaction.
        # Starting in Byzantium, this is no longer necessary, because the state root isn't
        # in the receipt anymore.
        return old_header.copy(
            bloom=int(BloomFilter(old_header.bloom) | receipt.bloom),
            gas_used=receipt.gas_used,
        )

    @staticmethod
    def make_receipt(
            base_header: BlockHeader,
            transaction: BaseTransaction,
            computation: BaseComputation,
            state: BaseState) -> Receipt:

        receipt_without_state_root = make_frontier_receipt(base_header, transaction, computation)

        if computation.is_error:
            status_code = EIP658_TRANSACTION_STATUS_CODE_FAILURE
        else:
            status_code = EIP658_TRANSACTION_STATUS_CODE_SUCCESS

        return receipt_without_state_root.copy(state_root=status_code)
