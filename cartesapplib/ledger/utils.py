import logging

LOGGER = logging.getLogger(__name__)

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
