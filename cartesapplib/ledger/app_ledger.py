from pydantic import BaseModel
from typing import Optional, List
import logging

from cartesi.abi import Address, UInt256, Bytes, Bytes32

from cartesapp.output import contract_call

LOGGER = logging.getLogger(__name__)


# Function Selectors (libcma input discriminators)

WITHDRAW_ETHER = b'\x8c\xf7\x0f\x0b'
WITHDRAW_ERC20 = b'O\x94\xd3B'
WITHDRAW_ERC721 = b'3\xac\xf2\x93'
WITHDRAW_ERC1155_SINGLE = b'\x8b\xb0\xa8\x11'
WITHDRAW_ERC1155_BATCH = b'P\xc8\x00\x19'
TRANSFER_ETHER = b'\xffg\xc9\x03'
TRANSFER_ERC20 = b'\x03\xd6\x1d\xcd'
TRANSFER_ERC721 = b'\xafaZZ'
TRANSFER_ERC1155_SINGLE = b'\xe1\xc9\x13\xed'
TRANSFER_ERC1155_BATCH = b'c\x8a\xc6\xf9'


# Portal addresses (defaults; can be overridden via LEDGER_CONFIG)

ETHER_PORTAL_ADDRESS = "0xA632c5c05812c6a6149B7af5C56117d1D2603828"
ERC20_PORTAL_ADDRESS = "0xACA6586A0Cf05bD831f2501E7B4aea550dA6562D"
ERC721_PORTAL_ADDRESS = "0x9E8851dadb2b77103928518846c4678d48b5e371"
ERC1155_SINGLE_PORTAL_ADDRESS = "0x18558398Dd1a8cE20956287a4Da7B76aE7A96662"
ERC1155_BATCH_PORTAL_ADDRESS = "0xe246Abb974B307490d9C6932F48EbE79de72338A"


# Settings

def get_settings_module():
    import types
    module_name = "ledger.settings"
    mod = types.ModuleType(module_name)
    mod.NOTICE_FORMAT = "header_abi"
    return mod


# Input payload models (kept for frontend encoding/codegen; backend uses decode_advance / decode_*_deposit)

class DepositEtherPayload(BaseModel):
    sender: Address
    amount: UInt256
    exec_layer_data: Bytes

class DepositErc20Payload(BaseModel):
    token: Address
    sender: Address
    amount: UInt256
    exec_layer_data: Bytes

class DepositErc721Payload(BaseModel):
    token: Address
    sender: Address
    token_id: UInt256
    data_bytes: Bytes

class DataBytes(BaseModel):
    base_layer_data: Bytes
    exec_layer_data: Bytes

class DepositErc1155SinglePayload(BaseModel):
    token: Address
    sender: Address
    token_id: UInt256
    amount: UInt256
    data_bytes: Bytes

class DepositErc1155BatchPayload(BaseModel):
    token: Address
    sender: Address
    batch_bytes: Bytes

class BatchBytes(BaseModel):
    token_ids: List[UInt256]
    amounts: List[UInt256]
    base_layer_data: Bytes
    exec_layer_data: Bytes

class WithdrawEtherPayload(BaseModel):
    amount: UInt256
    exec_layer_data: Bytes

class WithdrawErc20Payload(BaseModel):
    token: Address
    amount: UInt256
    exec_layer_data: Bytes

class WithdrawErc721Payload(BaseModel):
    token: Address
    token_id: UInt256
    exec_layer_data: Bytes

class WithdrawErc1155SinglePayload(BaseModel):
    token: Address
    token_id: UInt256
    amount: UInt256
    exec_layer_data: Bytes

class WithdrawErc1155BatchPayload(BaseModel):
    token: Address
    token_ids: List[UInt256]
    amounts: List[UInt256]
    exec_layer_data: Bytes

class TransferEtherPayload(BaseModel):
    receiver: Bytes32
    amount: UInt256
    exec_layer_data: Bytes

class TransferErc20Payload(BaseModel):
    token: Address
    receiver: Bytes32
    amount: UInt256
    exec_layer_data: Bytes

class TransferErc721Payload(BaseModel):
    token: Address
    receiver: Bytes32
    token_id: UInt256
    exec_layer_data: Bytes

class TransferErc1155SinglePayload(BaseModel):
    token: Address
    receiver: Bytes32
    token_id: UInt256
    amount: UInt256
    exec_layer_data: Bytes

class TransferErc1155BatchPayload(BaseModel):
    token: Address
    receiver: Bytes32
    token_ids: List[UInt256]
    amounts: List[UInt256]
    exec_layer_data: Bytes

class BalancePayload(BaseModel):
    account: str
    token: Optional[str] = None
    token_id: Optional[str] = None
    exec_layer_data: Optional[str] = None

class SupplyPayload(BaseModel):
    token: Optional[str] = None
    token_id: Optional[str] = None
    exec_layer_data: Optional[str] = None


# Voucher models (ABI-encoded calldata for submit_contract_call)

@contract_call(module_name='ledger', no_module_header=True)
class Erc20Voucher(BaseModel):
    receiver:   Address
    amount:     UInt256

@contract_call(module_name='ledger', no_module_header=True)
class Erc721Voucher(BaseModel):
    sender:     Address
    receiver:   Address
    token_id:   UInt256

@contract_call(module_name='ledger', no_module_header=True)
class Erc1155SingleVoucher(BaseModel):
    sender:     Address
    receiver:   Address
    token_id:   UInt256
    amount:     UInt256
    data:       Bytes

@contract_call(module_name='ledger', no_module_header=True)
class Erc1155BatchVoucher(BaseModel):
    sender:     Address
    receiver:   Address
    token_ids:  List[UInt256]
    amounts:    List[UInt256]
    data:       Bytes

# Memory-file initializer (run once, out of band, to allocate the libcma backing file)

def initialize_ledger(config):
    from pathlib import Path
    from pycma import Ledger
    mem_file = config.get("mem_file")
    if not isinstance(mem_file, str):
        raise Exception("ledger app config mem_file not valid")
    if config.get('memory_size') is None or config.get('max_accounts') is None or \
            config.get('max_assets') is None or config.get('max_balances') is None:
        raise Exception("ledger app config mem configuration not valid")

    ledger_offset = config.get('offset') or 0
    file_path = Path(mem_file)
    if file_path.is_file():
        LOGGER.debug(f"State file {mem_file} found")
        if file_path.stat().st_size < ledger_offset + config.get('memory_size'):
            raise Exception("ledger file size  mem configuration not valid")
    else:
        LOGGER.debug(f"Creating state file {mem_file} with {ledger_offset + config.get('memory_size')} bytes")
        with open(mem_file, "wb") as f:
            f.truncate(ledger_offset + config.get('memory_size'))

    ledger = Ledger(
        memory_filename=mem_file,
        offset=ledger_offset,
        mem_length=config.get('memory_size'),
        n_accounts=config.get('max_accounts'),
        n_assets=config.get('max_assets'),
        n_balances=config.get('max_balances'),
        initialize_memory=True,
    )
    LOGGER.debug("Ledger created")
    asset_info = ledger.retrieve_asset(base_token = True)
    LOGGER.debug(f"Created base asset with id = {asset_info['asset_id']}")


def initialize(config):
    from pycma import Ledger, decode_advance, decode_ether_deposit, decode_erc20_deposit, \
        decode_erc721_deposit, decode_erc1155_single_deposit, decode_erc1155_batch_deposit

    from cartesapp.input import mutation, query
    from cartesapp.output import add_output, submit_contract_call
    from cartesapp.context import Context, get_metadata, get_low_level_rollup, get_ledger

    ether_portal_address = config.get('ether_portal_address') or ETHER_PORTAL_ADDRESS
    erc20_portal_address = config.get('erc20_portal_address') or ERC20_PORTAL_ADDRESS
    erc721_portal_address = config.get('erc721_portal_address') or ERC721_PORTAL_ADDRESS
    erc1155_single_portal_address = config.get('erc1155_single_portal_address') or ERC1155_SINGLE_PORTAL_ADDRESS
    erc1155_batch_portal_address = config.get('erc1155_batch_portal_address') or ERC1155_BATCH_PORTAL_ADDRESS

    # Helpers

    class EtherId:
        ether_id = None
        def __new__(cls):
            return cls
        @classmethod
        def set(cls, val):
            cls.ether_id = val
        @classmethod
        def get(cls):
            return cls.ether_id

    def check_remove_account(ledger, account_id):
        account_info = ledger.retrieve_account(account_id=account_id)
        if account_info["n_balances"] == 0:
            ledger.retrieve_account(account_id=account_id, remove=True)

    def check_remove_asset(ledger, asset_id):
        if asset_id == EtherId.get():
            return
        asset_info = ledger.retrieve_asset(asset_id=asset_id)
        if asset_info["total_supply"] == 0:
            ledger.retrieve_asset(asset_id=asset_id, remove=True)

    def check_asset_enabled(config, asset):
        assets_enabled = config.get('assets_enabled')
        assets_disabled = config.get('assets_disabled')
        if assets_enabled is not None:
            if not isinstance(assets_enabled, list):
                raise Exception("ledger app config assets_enabled is not a list")
            return asset in assets_enabled
        if assets_disabled is not None:
            if not isinstance(assets_disabled, list):
                raise Exception("ledger app config assets_disabled is not a list")
            return asset not in assets_disabled
        return True

    def _normalize_receiver(b: bytes) -> str:
        # Bytes32 receiver: 20-byte address left-padded with 12 zero bytes, or a raw 32-byte internal id.
        return f"0x{b[12:].hex()}" if b.startswith(b'\0' * 12) else f"0x{b.hex()}"

    def _to_uint(s):
        if s is None:
            return None
        return int(s, 16) if s.startswith('0x') else int(s)


    mem_file = config.get("mem_file")
    if mem_file is not None:
        if not isinstance(mem_file, str):
            raise Exception("ledger app config mem_file not valid")
        if config.get('memory_size') is None or config.get('max_accounts') is None or \
                config.get('max_assets') is None or config.get('max_balances') is None:
            raise Exception("ledger app config mem configuration not valid")

        Context().ledger = Ledger(
            memory_filename=mem_file,
            offset=config.get('offset') or 0,
            mem_length=config.get('memory_size'),
            n_accounts=config.get('max_accounts'),
            n_assets=config.get('max_assets'),
            n_balances=config.get('max_balances'),
            initialize_memory=False,
        )
    else:
        Context().ledger = Ledger()

    asset_info = get_ledger().retrieve_asset(base_token=True, force_find=True)
    EtherId.set(asset_info['asset_id'])

    ###
    # Mutations

    # --- Ether ---

    @mutation(
        module_name='ledger', no_module_header=True,
        msg_sender=ether_portal_address,
        no_header=True,
        packed=True,
        specialized_template=False,
    )
    def deposit_ether() -> bool:
        advance = get_low_level_rollup().read_advance_state()
        deposit = decode_ether_deposit(advance)
        ledger = get_ledger()
        account_info = ledger.retrieve_account(account=deposit['sender'])
        ledger.deposit(EtherId.get(), account_info['account_id'], deposit['amount'])
        LOGGER.debug(f"{account_info['account']} deposited {deposit['amount']} ether (wei)")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=WITHDRAW_ETHER)
    def WithdrawEther(payload: WithdrawEtherPayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        account_info = ledger.retrieve_account(account=metadata.msg_sender)
        ledger.withdraw(EtherId.get(), account_info['account_id'], decoded['amount'])
        check_remove_account(ledger, account_info['account_id'])

        submit_contract_call(
            account_info['account'], decoded['amount'],
            tags=["ledger", "ether", "withdrawal", account_info['account']],
        )

        LOGGER.debug(f"{account_info['account']} withdrew {decoded['amount']} ether (wei)")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=TRANSFER_ETHER)
    def TransferEther(payload: TransferEtherPayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        from_acc = ledger.retrieve_account(account=metadata.msg_sender)
        to_acc = ledger.retrieve_account(account=decoded['receiver'])
        ledger.transfer(EtherId.get(), from_acc['account_id'], to_acc['account_id'], decoded['amount'])
        check_remove_account(ledger, from_acc['account_id'])

        LOGGER.debug(f"{from_acc['account']} transfered {decoded['amount']} ether (wei) to {to_acc['account']}")
        return True

    # --- ERC20 ---

    @mutation(
        module_name='ledger', no_module_header=True,
        msg_sender=erc20_portal_address,
        no_header=True,
        packed=True,
        specialized_template=False,
    )
    def deposit_erc20() -> bool:
        advance = get_low_level_rollup().read_advance_state()
        deposit = decode_erc20_deposit(advance)
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=deposit['token'])
        account_info = ledger.retrieve_account(account=deposit['sender'])
        ledger.deposit(asset_info['asset_id'], account_info['account_id'], deposit['amount'])
        LOGGER.debug(f"{deposit['sender']} deposited {deposit['amount']} of {deposit['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=WITHDRAW_ERC20)
    def WithdrawErc20(payload: WithdrawErc20Payload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=decoded['token'])
        account_info = ledger.retrieve_account(account=metadata.msg_sender)
        ledger.withdraw(asset_info['asset_id'], account_info['account_id'], decoded['amount'])
        check_remove_account(ledger, account_info['account_id'])
        check_remove_asset(ledger, asset_info['asset_id'])

        voucher = Erc20Voucher(receiver=metadata.msg_sender, amount=decoded['amount'])
        submit_contract_call(
            decoded['token'], "transfer", voucher,
            tags=["ledger", "erc20", "withdrawal", decoded['token'], account_info['account']],
        )

        LOGGER.debug(f"{account_info['account']} withdrew {decoded['amount']} of {decoded['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=TRANSFER_ERC20)
    def TransferErc20(payload: TransferErc20Payload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=decoded['token'])
        from_acc = ledger.retrieve_account(account=metadata.msg_sender)
        to_acc = ledger.retrieve_account(account=decoded['receiver'])
        ledger.transfer(asset_info['asset_id'], from_acc['account_id'], to_acc['account_id'], decoded['amount'])
        check_remove_account(ledger, from_acc['account_id'])

        LOGGER.debug(f"{from_acc['account']} transfered {decoded['amount']} of {decoded['token']} to {to_acc['account']}")
        return True

    # --- ERC721 ---

    @mutation(
        module_name='ledger', no_module_header=True,
        msg_sender=erc721_portal_address,
        no_header=True,
        packed=True,
        specialized_template=False,
    )
    def deposit_erc721() -> bool:
        advance = get_low_level_rollup().read_advance_state()
        deposit = decode_erc721_deposit(advance)
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=deposit['token'], token_id=deposit['token_id'])
        account_info = ledger.retrieve_account(account=deposit['sender'])
        ledger.deposit(asset_info['asset_id'], account_info['account_id'], 1)
        LOGGER.debug(f"{deposit['sender']} deposited id {deposit['token_id']} of {deposit['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=WITHDRAW_ERC721)
    def WithdrawErc721(payload: WithdrawErc721Payload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=decoded['token'], token_id=decoded['token_id'])
        account_info = ledger.retrieve_account(account=metadata.msg_sender)
        ledger.withdraw(asset_info['asset_id'], account_info['account_id'], 1)
        check_remove_account(ledger, account_info['account_id'])
        check_remove_asset(ledger, asset_info['asset_id'])

        voucher = Erc721Voucher(
            sender=metadata.app_contract,
            receiver=metadata.msg_sender,
            token_id=decoded['token_id'],
        )
        submit_contract_call(
            decoded['token'], "safeTransferFrom", voucher,
            tags=["ledger", "erc721", "withdrawal", decoded['token'], account_info['account']],
        )

        LOGGER.debug(f"{account_info['account']} withdrew id {decoded['token_id']} of {decoded['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=TRANSFER_ERC721)
    def TransferErc721(payload: TransferErc721Payload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(token=decoded['token'], token_id=decoded['token_id'])
        from_acc = ledger.retrieve_account(account=metadata.msg_sender)
        to_acc = ledger.retrieve_account(account=decoded['receiver'])
        ledger.transfer(asset_info['asset_id'], from_acc['account_id'], to_acc['account_id'], 1)
        check_remove_account(ledger, from_acc['account_id'])

        LOGGER.debug(f"{from_acc['account']} transfered id {decoded['token_id']} of {decoded['token']} to {to_acc['account']}")
        return True

    # --- ERC1155 single ---

    @mutation(
        module_name='ledger', no_module_header=True,
        msg_sender=erc1155_single_portal_address,
        no_header=True,
        packed=True,
        specialized_template=False,
    )
    def deposit_erc1155_single() -> bool:
        advance = get_low_level_rollup().read_advance_state()
        deposit = decode_erc1155_single_deposit(advance)
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(
            token=deposit['token'], token_id=deposit['token_id'], token_id_with_amount=True,
        )
        account_info = ledger.retrieve_account(account=deposit['sender'])
        ledger.deposit(asset_info['asset_id'], account_info['account_id'], deposit['amount'])
        LOGGER.debug(f"{deposit['sender']} deposited {deposit['amount']} of id {deposit['token_id']} from {deposit['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=WITHDRAW_ERC1155_SINGLE)
    def WithdrawErc1155Single(payload: WithdrawErc1155SinglePayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(
            token=decoded['token'], token_id=decoded['token_id'], token_id_with_amount=True,
        )
        account_info = ledger.retrieve_account(account=metadata.msg_sender)
        ledger.withdraw(asset_info['asset_id'], account_info['account_id'], decoded['amount'])
        check_remove_account(ledger, account_info['account_id'])
        check_remove_asset(ledger, asset_info['asset_id'])

        voucher = Erc1155SingleVoucher(
            sender=metadata.app_contract,
            receiver=metadata.msg_sender,
            token_id=decoded['token_id'],
            amount=decoded['amount'],
            data=b'',
        )
        submit_contract_call(
            decoded['token'], "safeTransferFrom", voucher,
            tags=["ledger", "erc1155", "withdrawal", decoded['token'], decoded['token_id'], account_info['account']],
        )

        LOGGER.debug(f"{account_info['account']} withdrew {decoded['amount']} of id {decoded['token_id']} from {decoded['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=TRANSFER_ERC1155_SINGLE)
    def TransferErc1155Single(payload: TransferErc1155SinglePayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        asset_info = ledger.retrieve_asset(
            token=decoded['token'], token_id=decoded['token_id'], token_id_with_amount=True,
        )
        from_acc = ledger.retrieve_account(account=metadata.msg_sender)
        to_acc = ledger.retrieve_account(account=decoded['receiver'])
        ledger.transfer(asset_info['asset_id'], from_acc['account_id'], to_acc['account_id'], decoded['amount'])
        check_remove_account(ledger, from_acc['account_id'])

        LOGGER.debug(f"{from_acc['account']} transfered {decoded['amount']} of id {decoded['token_id']} from {decoded['token']} to {to_acc['account']}")
        return True

    # --- ERC1155 batch ---

    @mutation(
        module_name='ledger', no_module_header=True,
        msg_sender=erc1155_batch_portal_address,
        no_header=True,
        packed=True,
        specialized_template=False,
    )
    def deposit_erc1155_batch() -> bool:
        advance = get_low_level_rollup().read_advance_state()
        deposit = decode_erc1155_batch_deposit(advance)
        ledger = get_ledger()
        account_info = ledger.retrieve_account(account=deposit['sender'])
        for token_id, amount in zip(deposit['token_ids'], deposit['amounts']):
            asset_info = ledger.retrieve_asset(
                token=deposit['token'], token_id=token_id, token_id_with_amount=True,
            )
            ledger.deposit(asset_info['asset_id'], account_info['account_id'], amount)
        LOGGER.debug(f"{deposit['sender']} deposited {deposit['amounts']} of ids {deposit['token_ids']} from {deposit['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=WITHDRAW_ERC1155_BATCH)
    def WithdrawErc1155Batch(payload: WithdrawErc1155BatchPayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        account_info = ledger.retrieve_account(account=metadata.msg_sender)
        for token_id, amount in zip(decoded['token_ids'], decoded['amounts']):
            asset_info = ledger.retrieve_asset(
                token=decoded['token'], token_id=token_id, token_id_with_amount=True,
            )
            ledger.withdraw(asset_info['asset_id'], account_info['account_id'], amount)
            check_remove_asset(ledger, asset_info['asset_id'])
        check_remove_account(ledger, account_info['account_id'])

        voucher = Erc1155BatchVoucher(
            sender=metadata.app_contract,
            receiver=metadata.msg_sender,
            token_ids=decoded['token_ids'],
            amounts=decoded['amounts'],
            data=b'',
        )
        tags = ["ledger", "erc1155", "withdrawal", decoded['token'], account_info['account']]
        tags.extend(decoded['token_ids'])
        submit_contract_call(decoded['token'], "safeBatchTransferFrom", voucher, tags=tags)

        LOGGER.debug(f"{account_info['account']} withdrew {decoded['amounts']} of ids {decoded['token_ids']} from {decoded['token']}")
        return True

    @mutation(module_name='ledger', no_module_header=True, fixed_header=TRANSFER_ERC1155_BATCH)
    def TransferErc1155Batch(payload: TransferErc1155BatchPayload) -> bool:
        metadata = get_metadata()
        decoded = decode_advance(get_low_level_rollup().read_advance_state())
        ledger = get_ledger()
        from_acc = ledger.retrieve_account(account=metadata.msg_sender)
        to_acc = ledger.retrieve_account(account=decoded['receiver'])
        for token_id, amount in zip(decoded['token_ids'], decoded['amounts']):
            asset_info = ledger.retrieve_asset(
                token=decoded['token'], token_id=token_id, token_id_with_amount=True,
            )
            ledger.transfer(asset_info['asset_id'], from_acc['account_id'], to_acc['account_id'], amount)
        check_remove_account(ledger, from_acc['account_id'])

        LOGGER.debug(f"{from_acc['account']} transfered {decoded['amounts']} of ids {decoded['token_ids']} from {decoded['token']} to {to_acc['account']}")
        return True

    ###
    # Queries

    # TODO: pycma.Ledger.retrieve_account has no FIND-only mode, so an inspect that
    # names an unknown account currently creates it. Mirror behavior in .template/ledger_app.py.

    @query(module_name='ledger')
    def getBalance(payload: BalancePayload) -> bool:
        ledger = get_ledger()
        asset_id = EtherId.get()
        if payload.token is not None:
            token_id = _to_uint(payload.token_id)
            asset_info = ledger.retrieve_asset(
                token=payload.token, token_id=token_id,
                token_id_with_amount=token_id is not None,
                force_find=True,
            )
            asset_id = asset_info['asset_id']
        account_info = ledger.retrieve_account(account=payload.account)
        current_balance = ledger.balance(asset_id, account_info['account_id'])
        add_output(current_balance.to_bytes(32, 'big'))
        LOGGER.debug(f"{payload.account} balance is {current_balance}")
        return True

    @query(module_name='ledger')
    def getSupply(payload: SupplyPayload) -> bool:
        ledger = get_ledger()
        asset_id = EtherId.get()
        if payload.token is not None:
            token_id = _to_uint(payload.token_id)
            asset_info = ledger.retrieve_asset(
                token=payload.token, token_id=token_id,
                token_id_with_amount=token_id is not None,
                force_find=True,
            )
            asset_id = asset_info['asset_id']
        current_supply = ledger.supply(asset_id)
        add_output(current_supply.to_bytes(32, 'big'))
        LOGGER.debug(f"asset {asset_id} supply is {current_supply}")
        return True
