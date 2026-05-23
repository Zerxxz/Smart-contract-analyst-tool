"""Fetch verified contract source from block explorers (Etherscan-compatible)."""
import httpx
from typing import Tuple
from app.core.config import settings


CHAIN_CONFIG = {
    "eth": {
        "url": "https://api.etherscan.io/api",
        "key_attr": "etherscan_api_key",
    },
    "bsc": {
        "url": "https://api.bscscan.com/api",
        "key_attr": "bscscan_api_key",
    },
    "polygon": {
        "url": "https://api.polygonscan.com/api",
        "key_attr": "polygonscan_api_key",
    },
    "arbitrum": {
        "url": "https://api.arbiscan.io/api",
        "key_attr": "arbiscan_api_key",
    },
}


async def fetch_source(address: str, chain: str = "eth") -> Tuple[str, str]:
    """
    Returns (concatenated_source, contract_name).
    Raises ValueError if the contract is not verified.
    """
    cfg = CHAIN_CONFIG.get(chain)
    if not cfg:
        raise ValueError(f"Unsupported chain: {chain}")
    api_key = getattr(settings, cfg["key_attr"], "")

    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key,
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(cfg["url"], params=params)
        r.raise_for_status()
        data = r.json()

    if data.get("status") != "1":
        raise ValueError(f"Explorer error: {data.get('message')} "
                         f"{data.get('result')}")

    result = data["result"][0]
    name = result.get("ContractName") or "Unknown"
    source = result.get("SourceCode") or ""
    if not source:
        raise ValueError("Contract source is not verified on explorer.")

    # Etherscan may wrap multi-file sources in {{ ... }} JSON
    if source.startswith("{{") and source.endswith("}}"):
        import json
        try:
            parsed = json.loads(source[1:-1])
            sources = parsed.get("sources", {})
            source = "\n\n".join(
                f"// === {fname} ===\n{fdata.get('content', '')}"
                for fname, fdata in sources.items()
            )
        except json.JSONDecodeError:
            pass
    elif source.startswith("{") and source.endswith("}"):
        import json
        try:
            parsed = json.loads(source)
            if isinstance(parsed, dict) and "sources" in parsed:
                source = "\n\n".join(
                    f"// === {fname} ===\n{fdata.get('content', '')}"
                    for fname, fdata in parsed["sources"].items()
                )
        except json.JSONDecodeError:
            pass

    return source, name
