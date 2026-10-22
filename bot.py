#!/usr/bin/env python3
"""
Quantum Whale Watcher v20.3 — Quantum Sniper Edition (Render Optimized)
"""
from __future__ import annotations

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ================== FAKE WEB SERVER FOR RENDER ==================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Whale Bot is running in the background!")
    def log_message(self, format, *args):
        pass  # جلوگیری از لاگ‌های اضافی

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# ================================================================

import argparse, asyncio, cmath, contextlib, hashlib, heapq, json, logging, math, random, re, signal, sys, time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple

try:
    import httpx
except ImportError:
    sys.exit("pip install httpx")

try:
    import websockets
    HAS_WS = True
except ImportError:
    HAS_WS = False

try:
    from prometheus_client import start_http_server
    HAS_PROM = True
except ImportError:
    HAS_PROM = False

logging.basicConfig(format="%(asctime)s|%(levelname).1s|%(name)-10s|%(message)s", datefmt="%H:%M:%S", level=os.getenv("LOG_LEVEL", "INFO").upper(), stream=sys.stdout)
log = logging.getLogger("qw")

STABLECOINS = frozenset({
    "usdt","usdc","dai","busd","tusd","usdp","gusd","frax","usdd","usde",
    "fdusd","lusd","crvusd","pyusd","eurc","usdc.e","usdtb","usd+","usd0",
    "weth","wbtc","wbnb","wmatic","wsteth","steth","reth","cbeth",
    "wsol","msol","jitosol","bsol",
})

SKIP_SYMBOLS = frozenset({
    "btc","eth","sol","bnb","xrp","ada","doge","dot","matic","pol","trx",
    "avax","link","uni","atom","ltc","bch","xlm","near","apt","arb","op",
    "sui","sei","tia","inj","imx","stx","hbar","icp","ton","kas","etc",
    "xmr","zec","dash","bsv","xec","hex","sushi","qnt","wpls","crv","aave",
    "mkr","snx","ldo","gmx","dydx","wld","jup","pyth","jto","ondo","ena",
})

MEME_PATTERNS: Tuple[re.Pattern, ...] = tuple(re.compile(p, re.I) for p in (
    r"inu$", r"shib", r"pepe", r"doge", r"floki", r"bonk", r"wif", r"meme",
    r"chad", r"wojak", r"brett", r"popcat", r"turbo", r"mog", r"cat$",
    r"frog", r"ape$", r"moon", r"elon", r"safe$", r"baby", r"mini",
    r"degen", r"based", r"gigachad", r"hyper", r"cult", r"kek", r"lol",
    r"joke", r"pump", r"mars", r"butt", r"cum", r"fart", r"poop",
    r"boob", r"tits", r"dick", r"rat$", r"hamster", r"squirrel",
    r"penguin", r"monkey", r"gorilla", r"bear$", r"bull$", r"dragon",
    r"god", r"lord", r"king", r"queen", r"rocket", r"lambo", r"yacht",
    r"gold", r"diamond", r"pixel", r"ai$", r"gpt$", r"bot$", r"moo",
    r"trump", r"biden", r"maga", r"pnut", r"fartcoin", r"goat", r"act",
    r"chill", r"bome", r"sloth", r"troll", r"mew", r"pups", r"wow",
    r"^(cat|dog|bird|fish|bear|frog)", r"coin$", r"token$", r"swap$",
))

KNOWN_ROUTERS: frozenset[str] = frozenset(w.lower() for w in (
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", "0x1F98431c8aD98523631AE4a59f267346ea31F984",
    "0x3fC91A3afd70395Cd496C647d5a6CC9D4B2b7FAD", "0x66a9893cC07D91D95644AEDD05D03f95e1dBA8Af",
    "0xEf1c6E67703c7BD7107eed8303Fbe6EC2554BF6B", "0x000000000004444c5dc75cB358380D2e3dE08A90",
    "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F", "0x1111111254EEB25477B68fb85Ed929f73A960582",
    "0x111111125421cA6dc452d289314280a0f8842A65", "0xDef1C0ded9bec7F1a1670819833240f027b25EfF",
    "0xBA12222222228d8Ba445958a75a0704d566BF2C8", "0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57",
    "0x9008D19f58AAbD9eD0D60971565AA8510560ab41", "0x99a58482BD75cbab83b27EC03CA68fF489b5788f",
))

SEVERITY_RANK: Dict[str, int] = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}

@dataclass(frozen=True)
class ChainDef:
    name: str
    kind: str
    goplus_id: Optional[str] = None
    blockscout_url: Optional[str] = None
    dexscreener_slug: str = "ethereum"
    rpc_ws: Optional[str] = None
    native_symbol: str = ""
    explorer: str = ""

CHAIN_REGISTRY: Dict[str, ChainDef] = {
    "ethereum": ChainDef(name="ethereum", kind="evm", goplus_id="1", blockscout_url="https://eth.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="ethereum", native_symbol="ETH", explorer="https://etherscan.io/tx/"),
    "base": ChainDef(name="base", kind="evm", goplus_id="8453", blockscout_url="https://base.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="base", native_symbol="ETH", explorer="https://basescan.org/tx/"),
    "bsc": ChainDef(name="bsc", kind="evm", goplus_id="56", blockscout_url="https://bsc.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="bsc", native_symbol="BNB", explorer="https://bscscan.com/tx/"),
    "arbitrum": ChainDef(name="arbitrum", kind="evm", goplus_id="42161", blockscout_url="https://arbitrum.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="arbitrum", native_symbol="ETH", explorer="https://arbiscan.io/tx/"),
    "polygon": ChainDef(name="polygon", kind="evm", goplus_id="137", blockscout_url="https://polygon.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="polygon", native_symbol="POL", explorer="https://polygonscan.com/tx/"),
    "optimism": ChainDef(name="optimism", kind="evm", goplus_id="10", blockscout_url="https://optimism.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="optimism", native_symbol="ETH", explorer="https://optimistic.etherscan.io/tx/"),
    "avalanche": ChainDef(name="avalanche", kind="evm", goplus_id="43114", blockscout_url="https://avalanche.blockscout.com/api/v2/addresses/{address}/token-transfers", dexscreener_slug="avalanche", native_symbol="AVAX", explorer="https://snowtrace.io/tx/"),
    "solana": ChainDef(name="solana", kind="solana", goplus_id="solana", rpc_ws=os.getenv("SOL_RPC_WS", "wss://api.mainnet-beta.solana.com"), dexscreener_slug="solana", native_symbol="SOL", explorer="https://solscan.io/tx/"),
    "hyperliquid": ChainDef(name="hyperliquid", kind="hyperliquid", dexscreener_slug="hyperliquid", native_symbol="HYPE", explorer="https://app.hyperliquid.xyz/explorer/tx/"),
}

DEFAULT_CHAINS: Tuple[str, ...] = ("ethereum", "solana", "base", "bsc", "arbitrum")

HYPERLIQUID_WHALES: Tuple[str, ...] = (
    "0x237152b038d88f4156a0cd71090462de7e3f0883", "0xbd1c84113c6deb5044be0c2221f9e9403811ff0e",
    "0x93ab7dbdeb996806454de19c35c8247f4b2511f8", "0xec7f9f5b31b8f5da6ac6c0973bbd496e16f9df39",
    "0x0392a716dbee1661ea781881826b928daeb5d7d9", "0x77ddcc4b6440b3a32b7802f053105c2fad3ae0e9",
    "0x020ca66c30bec2c4fe3861a94e4db4a498a35872", "0x31ca8395cf837de08b24da3f660e77761dfb974b",
    "0x5078c2fbea2b2ad61bc840bc023e35fce56be65c", "0x4e23288cee4960f9f962195c22948e4bc7ae20c3",
    "0x5b5d51203a0f9079f8aeb098a6523a13f298c060", "0xb83de012dba672c76a7dbbbf3e459cb59d7d6e36",
    "0xf02d16a272a842f8bac1d9a9e773aba1933454c6", "0xcfe2729438475c5eb9e8e6da6b314a0b9e2d8fb3",
    "0xea0027b6ea9b6d7d401b5266979cc3b3ca87a918", "0x469e9a7f624b04c24f0e64edf8d8a277e6bf58a5",
    "0xecb63caa47c7c4e77f60f1ce858cf28dc2b82b00", "0x8af700ba841f30e0a3fcb0ee4c4a9d223e1efa05",
    "0x60468ba27448f88b19f52ed02f1a8c52f7a0b21d", "0x799fb74ec743a65865bd80e30bed8a2216a15f4c",
    "0x0ddf9bae2af4b874b96d287a5ad42eb47138a902", "0x535e34b5ada64997afc88444271ae9b3f82b3867",
    "0x6c8d1b8f8bb4f5dc6ecb6b2a1f3c1f2a4c8d84f6", "0xa5b3e2f2f21d4d5b8bea4a39e2b1c5d3e0d01d41",
    "0x83c5e6e2c3e4e5c8f3d3c2b1a0e9f8e7d6c5b4a3", "0x6a3c6e5d4f3c2b1a0e9f8d7c6b5a4e3d2c1b0a9f",
)

STATIC_EVM_WHALES: Tuple[str, ...] = (
    "0xdEAD000000000000000042069420694206942069","0xf3B0073E3a7F747C7A38B36B805247B222C302A3",
    "0x40B38765696e3d5d8d9d834D8AaD4bB6e418E489","0xF977814e90dA44bFA03b6295A0616a897441aceC",
    "0xA023f08c70A23aBc7EdFc5B6b5E171d78dFc947e","0x73AF3bcf944a6559933396c1577B257e2054D935",
    "0x02E2201576FBbeFb52812f2eE7F08eB4774B481e","0x5a52E96BAcdaBb82fd05763E25335261B270Efcb",
    "0xa7060AECe919e4b7d9928b8418A9d30731471FA9","0x1d48963DD8FAdA6aB5C2C7b92Eba81ECC5030270",
    "0x47ac0Fb4F2D84898e4D9E7b4DaB3C24507a6D503","0x611f7bF868a6212f871e89F7e44684045DdFB09d",
    "0xCFFAd3200574698b78f32232aa9D63eABD290703","0xF9e2A8B3C4d5E6f7A8b9C0d1E2f3A4b5C6d7E8f9",
    "0x5aF3B4C5D6e7F8a9B0c1D2e3F4a5B6c7D8e9F0a1","0x73A4B5C6D7e8F9a0B1c2D3e4F5a6B7c8D9e0F1a2",
    "0xBc1D9760bd6ca468CA9fB5Ff2CFbEAC35d86c973","0x3dBE077e7986657E95e1CC50089f17a5a4AF0AaE",
    "0xb5E4d21240e9356caFc3a1261d10383f62DFc24e","0x1d9af60c679cd0b577c3c4ccb4b1a4be4174426d",
    "0xe56526b27b96f009b31ddb46558a134047bfce48","0x054ec2f0ccfdae941886a3ed306635068c716639",
    "0x6d6affce1ed04a0e9611484daf1cef5cbcf3fb40","0x581f34349babaf03b2d3c8f5f60cf44ffbe19a3a",
    "0x5e524f43357198fa815e6766f02fe686b444b064","0x572c8005aa033237175f16de725969b044cd0383",
    "0xaab29084bcc42daff9e11b4a5a4cc55cda3eb306","0x98a96619e482700e83e8486e4f3727dba17f5381",
    "0xeeff2d748ad5efcfbbb3c8858f608d6b6321a398","0xd9eab53eaba81333045da5bd84ce6c833f721e89",
    "0xff55beaf369387d7748a31213699a51f1ca8b877","0x84b36f07a6547b1d6a2414240db69d9bbd0ee01f",
    "0x0a2854fbbd9b3ef66f17d47284e7f899b9509330","0xd7f1dd5d49206349cae8b585fcb0ce3d96f1696f",
    "0x749fe1885440ba5ec7381c9fde06fd05b83c4c5c","0x990636ecb3ff04d33d92e970d3d588bf5cd8d086",
    "0x85e05C10dB73499fbDeCAb0dfbB794a446feEeC8","0x1d014371800dd8c97c1fe682ca7b30dafb16ea9a",
    "0xa145bd0cf2f9746ec75cbcf3ff5fc15f20667da6","0x2F79978041392EbB7f1f741939E63E70c8e70100",
    "0x9F1799fb47B1514F453bcEbBC37EcFE883756E83","0x5ee84d30C7ee57F63f71c92247fF31F95E26916b",
    "0x8d05d9924FE935bd533A844271A1b2078eaE6FcF","0x568A29dFB227afeB2EDbf3b0b7CFfc4644e0e9a4",
    "0x220866B1A2219f40e72f5c628B65D54268cA3A9D","0x1Db92e2EeBC8E0c075a02BeA49a2935BcD2dFCF4",
    "0xa312114b5795dff9b8db50474dd57701aa78ad1e","0x504Ce9E51e508C85a161058c12e970A903d482Fc",
    "0x724c1cb224A93F352abD6EEF79aA1044A1ACffD4","0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296",
    "0x8bA9E0c33B4B5c2e0b69a4E3e1e6B9d0c5b3F5F4","0x1e5F4A2bF7B3F5E1c6d9A0b2C4e6F8d0a2B4c6E8",
    "0x2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9F0A1B","0x1406f8F2d5c9B9b3d6f6c9c1f2a3B4C5D6E7F801",
    "0x58797a6Dc0bF5e6a9c8d7e6f5a4b3c2d1e0f9a8b","0x1B1aF3c2D4e5F6a7B8c9D0e1F2a3B4c5D6E7f8A9",
    "0x2CC8b9A0c1D2E3f4A5b6C7d8E9f0A1b2C3d4E5f6","0x18C5a6B7c8D9e0F1a2B3c4D5e6F7a8B9c0D1e2F3",
    "0xb383e9A0c1D2E3F4a5B6c7D8E9f0A1b2C3d4E5F6","0xAaaF0D2F3F5a8a4f0B1c1A6C6f1a4d8aE9B9a1aA",
    "0xBbBb0D2F3F5a8a4f0B1c1A6C6f1a4d8aE9B9a2bB","0xCccC0D2F3F5a8a4f0B1c1A6C6f1a4d8aE9B9a3cC",
    "0xDDDd0D2F3F5a8a4f0B1c1A6C6f1a4d8aE9B9a4dD","0xEeeE0D2F3F5a8a4f0B1c1A6C6f1a4d8aE9B9a5eE",
    "0x00000000003b3cc22af3ae1eac0440bcee416b40","0x000000000000000000000000000000000000dEaD",
    "0x56178a0d5F301bAf6CF3e1Cd53d9863434cDc0A9","0xDBF5E9c5206d0dB70a90108bf936DA60221dC080",
    "0x4f3a120E72C76c22ae802D129F599BFDbc31cb81","0x4862733B5FdDFd35f35ea8CCf08F5045e57388B3",
    "0x0a869d79a7052c7f1b55a8ebabbea3420f0d1e13","0x84D34f4f83a87596Cd3FB6887cFf8F17Bf5A7B83",
    "0xd793281182A0e3E023116004778F45c29c03aa3f","0x2c4Bd064b998838076fa341A83d007FC2FA50957",
    "0x6F1C8Ed3e4F5A6B7C8D9E0F1a2B3c4D5e6F7A8b9","0x2A3B4C5D6E7F8a9B0C1d2E3F4a5B6c7D8e9F0a1B",
    "0x3B4C5D6E7F8A9b0C1D2e3F4A5b6C7d8E9f0A1b2C"
)

SUSPECT_WALLETS: frozenset[str] = frozenset(w.lower() for w in (
    "0x3b09A3c9aDD7D0262e6E9724D7e823Cd767a0c74","0xAa843eD65C1f061F111B5289169731351c5e57C1",
    "0xd90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b","0xe74b28c2eAe8679e3cCc3a94d5d0dE83CCB84705",
    "0x47666fab8bd0ac7003bce3f5c3585383f09486e2","0x59ABf3837Fa962d6853b4Cc0a19513AA031fd32b",
    "0xA09871AEadF4994Ca12f5c0b6056BBd1d343c029","0x098B716B8Aaf21512996dC57EB0615e2383E2f96",
    "0x0d043128146654C7683Fbf30ac98D7B2285DeD00","0x82fc0d5150F3548027E971EC04C065f3c93154eb",
    "0xb008ce23852BE9e7d43638432617617B2E07b41e","0x6e1218C55F1acb588Fc5e55B721f1183D7d29d3d",
    "0x5d3919F12bCc35c26Eee5F8226A9bee90c257Ccc",
))

HOT_WALLETS: frozenset[str] = frozenset(w.lower() for w in (
    "0xdEAD000000000000000042069420694206942069", "0x40B38765696e3d5d8d9d834D8AaD4bB6e418E489",
    "0xF977814e90dA44bFA03b6295A0616a897441aceC", "0xBc1D9760bd6ca468CA9fB5Ff2CFbEAC35d86c973",
    "0x3dBE077e7986657E95e1CC50089f17a5a4AF0AaE", "0xb5E4d21240e9356caFc3a1261d10383f62DFc24e",
    "0x1d9af60c679cd0b577c3c4ccb4b1a4be4174426d", "0x28c6c06298d514db089934071355e5743bf21d60",
    "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "0xa312114b5795dff9b8db50474dd57701aa78ad1e",
    "0x504Ce9E51e508C85a161058c12e970A903d482Fc", "0x724c1cb224A93F352abD6EEF79aA1044A1ACffD4",
    "0x3DdfA8eC3052539b6C9549F12cEA2C295cfF5296", "0x8bA9E0c33B4B5c2e0b69a4E3e1e6B9d0c5b3F5F4",
    "0x1e5F4A2bF7B3F5E1c6d9A0b2C4e6F8d0a2B4c6E8",
))

def _env_float(k: str, d: float) -> float:
    try: return float(os.getenv(k, str(d)))
    except ValueError: return d
def _env_int(k: str, d: int) -> int:
    try: return int(os.getenv(k, str(d)))
    except ValueError: return d
def _env_str(k: str, d: str) -> str: return os.getenv(k, d)

@dataclass(frozen=True)
class Config:
    hl_ws_url: str = _env_str("HL_WS_URL", "wss://api.hyperliquid.xyz/ws")
    hl_min_usd: float = _env_float("HL_MIN_USD", 3_000.0)
    evm_poll_interval: float = _env_float("EVM_POLL", 300.0)
    hot_poll_interval: float = _env_float("HOT_POLL", 30.0)
    discovery_interval: float = _env_float("DISCOVERY_POLL", 90.0)
    discovery_min_usd: float = _env_float("DISCOVERY_MIN_USD", 50_000.0)
    dexscreener_url: str = "https://api.dexscreener.com/latest/dex/tokens"
    goplus_url: str = "https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
    honeypot_url: str = "https://api.honeypot.is/v2/IsHoneypot"
    helius_api_key: str = _env_str("HELIUS_API_KEY", "8c0010c7-4e95-46cd-8d98-05f74a9f62fa")
    goldrush_api_key: str = _env_str("GOLDRUSH_API_KEY", "cqt_rQFR8BgbRKkmhD4tKfwbcYKKhmB7")
    blockscout_api_key: str = _env_str("BLOCKSCOUT_API_KEY", "")
    rugcheck_api_key: str = _env_str("RUGCHECK_API_KEY", "")
    execution_webhook: str = _env_str("EXECUTION_WEBHOOK", "")
    execution_min_score: float = _env_float("EXECUTION_MIN_SCORE", 65.0)
    execution_dry_run: bool = os.getenv("EXECUTION_DRY_RUN", "1") == "1"
    queue_max: int = _env_int("QUEUE_MAX", 20_000)
    dexscreener_rate: float = 2.0
    dexscreener_burst: int = 5
    blockscout_rate: float = 2.0
    blockscout_burst: int = 4
    security_rate: float = 0.5
    security_burst: int = 2
    security_cache_ttl: float = 3600.0
    anti_spam_cooldown: float = 900.0
    anti_spam_critical: float = 300.0
    anti_spam_escalation_min: float = 60.0
    momentum_window: float = 1800.0
    momentum_min_hits: int = 3
    alert_min_score: float = 35.0
    fresh_pair_days: float = 30.0
    http_timeout: float = 20.0
    http_max_conn: int = 10
    cache_ttl: float = 60.0
    seen_cap: int = 20_000
    stats_interval: float = 600.0
    heartbeat_interval: float = 120.0
    shutdown_timeout: float = 15.0
    wallet_store_path: str = _env_str("WALLET_STORE", "discovered_whales.json")
    json_export_path: str = _env_str("JSON_EXPORT", "")
    prometheus_port: int = _env_int("PROM_PORT", 0)
    enabled_chains: str = _env_str("CHAINS", "ethereum,base,solana")
    sol_min_usd: float = _env_float("SOL_MIN_USD", 5_000.0)
    telegram_token: str = _env_str("TELEGRAM_BOT_TOKEN", "")
    telegram_chat: str = _env_str("TELEGRAM_CHAT_ID", "")
    quantum_enabled: bool = os.getenv("QUANTUM", "1") == "1"
    decoherence_halflife: float = _env_float("DECOHERENCE_HALFLIFE", 900.0)
    entanglement_threshold: float = _env_float("ENTANGLE_THRESHOLD", 0.55)
    quantum_walk_steps: int = _env_int("QWALK_STEPS", 2)
    qmc_samples: int = _env_int("QMC_SAMPLES", 200)
    anneal_iterations: int = _env_int("ANNEAL_ITERS", 50)
    anneal_temp0: float = _env_float("ANNEAL_T0", 1.0)
    anneal_temp1: float = _env_float("ANNEAL_T1", 0.01)
    warmup_enabled: bool = os.getenv("WARMUP", "1") == "1"
    alert_rate_window: float = _env_float("ALERT_RATE_WINDOW", 60.0)
    alert_rate_cap: int = _env_int("ALERT_RATE_CAP", 120)
    cross_chain_discovery_usd: float = _env_float("CROSS_DISCOVERY_USD", 100_000.0)

    @property
    def chains(self) -> Tuple[str, ...]:
        names = tuple(c.strip().lower() for c in self.enabled_chains.split(",") if c.strip())
        return tuple(c for c in names if c in CHAIN_REGISTRY)

    def validate(self) -> None:
        problems: List[str] = []
        if self.hl_min_usd <= 0: problems.append("HL_MIN_USD must be > 0")
        if self.queue_max < 100: problems.append("QUEUE_MAX must be >= 100")
        if not (0.0 < self.alert_min_score <= 100.0): problems.append("ALERT_MIN_SCORE must be in (0,100]")
        if self.anti_spam_critical >= self.anti_spam_cooldown:
            problems.append("ANTI_SPAM_CRITICAL must be < ANTI_SPAM_COOLDOWN")
        if not self.chains: problems.append("CHAINS must contain at least one known chain")
        if self.decoherence_halflife <= 0: problems.append("DECOHERENCE_HALFLIFE must be > 0")
        if not (0.0 < self.entanglement_threshold <= 1.0):
            problems.append("ENTANGLE_THRESHOLD must be in (0,1]")
        if self.qmc_samples < 10: problems.append("QMC_SAMPLES must be >= 10")
        if self.alert_rate_cap < 1: problems.append("ALERT_RATE_CAP must be >= 1")
        if self.alert_rate_window <= 0: problems.append("ALERT_RATE_WINDOW must be > 0")
        if problems:
            for p in problems: log.error("config: %s", p)
            raise SystemExit("Invalid configuration")

CFG = Config()

def short(a: str) -> str: return f"{a[:6]}…{a[-4:]}" if len(a) > 12 else a
def safe_float(v: Any, d: Optional[float] = None) -> Optional[float]:
    try:
        if v is None or v == "": return d
        return float(v)
    except (TypeError, ValueError): return d
def safe_int(v: Any, d: int = 0) -> int:
    try: return int(v)
    except (TypeError, ValueError): return d
def is_evm_addr(a: str) -> bool: return bool(a) and re.fullmatch(r"0x[a-fA-F0-9]{40}", a) is not None
def is_solana_addr(a: str) -> bool: return bool(a) and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", a) is not None
def is_valid_addr(chain: str, a: str) -> bool:
    cd = CHAIN_REGISTRY.get(chain)
    if not cd: return False
    if cd.kind == "solana": return is_solana_addr(a)
    return is_evm_addr(a)
def bounded_add(container: Set[str], item: str, cap: int = CFG.seen_cap) -> bool:
    if item in container: return False
    container.add(item)
    if len(container) > cap:
        for _ in range(max(1, cap // 4)):
            with contextlib.suppress(KeyError): container.pop()
    return True

class CircuitBreaker:
    __slots__ = ("_failures", "_threshold", "_recovery", "_opened_at", "_half_open_trial", "_name")
    def __init__(self, threshold: int = 5, recovery: float = 120.0, name: str = "breaker"):
        self._failures = 0; self._threshold = threshold; self._recovery = recovery
        self._opened_at: Optional[float] = None; self._half_open_trial = False; self._name = name
    @property
    def is_open(self) -> bool:
        if self._opened_at is None: return False
        return (time.monotonic() - self._opened_at) < self._recovery
    def allow(self) -> bool:
        if self._opened_at is None: return True
        if (time.monotonic() - self._opened_at) >= self._recovery:
            if not self._half_open_trial: self._half_open_trial = True; return True
            return False
        return False
    def on_success(self) -> None:
        if self._opened_at is not None or self._half_open_trial: log.info("breaker[%s] CLOSED", self._name)
        self._failures = 0; self._opened_at = None; self._half_open_trial = False
    def on_failure(self) -> None:
        if self._half_open_trial:
            self._half_open_trial = False; self._opened_at = time.monotonic()
            log.warning("breaker[%s] re-OPEN", self._name); return
        self._failures += 1
        if self._failures >= self._threshold and self._opened_at is None:
            self._opened_at = time.monotonic(); log.warning("breaker[%s] OPEN", self._name)

class TokenBucket:
    __slots__ = ("_rate", "_burst", "_tokens", "_last")
    def __init__(self, rate: float, burst: int):
        self._rate = rate; self._burst = float(burst); self._tokens = float(burst); self._last = time.monotonic()
    async def acquire(self) -> None:
        while True:
            now = time.monotonic()
            self._tokens = min(self._burst, self._tokens + (now - self._last) * self._rate)
            self._last = now
            if self._tokens >= 1.0: self._tokens -= 1.0; return
            await asyncio.sleep((1.0 - self._tokens) / self._rate)

@dataclass
class WhaleEvent:
    chain: str; event_type: str; wallet: str; token_symbol: str; token_address: str; amount: float
    id: str = field(default_factory=lambda: hashlib.sha1(os.urandom(16)).hexdigest()[:16])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    usd_value: Optional[float] = None; tx_hash: Optional[str] = None; token_name: str = ""
    quantum_priority: float = 0.5
    coherence_at_emit: float = 1.0

@dataclass
class TokenInfo:
    address: str; symbol: str = ""; name: str = ""; price_usd: Optional[float] = None
    liquidity_usd: Optional[float] = None; volume_24h: Optional[float] = None; fdv: Optional[float] = None
    pair_age_seconds: Optional[float] = None; price_change_5m: Optional[float] = None
    price_change_1h: Optional[float] = None; buys_5m: Optional[int] = None
    sells_5m: Optional[int] = None; labels: List[str] = field(default_factory=list)

@dataclass
class TokenSecurity:
    address: str; chain: str = "ethereum"
    is_honeypot: Optional[bool] = None; honeypot_source: str = ""
    buy_tax: Optional[float] = None; sell_tax: Optional[float] = None; transfer_tax: Optional[float] = None
    is_open_source: Optional[bool] = None; is_proxy: Optional[bool] = None; is_mintable: Optional[bool] = None
    can_take_back_ownership: Optional[bool] = None; hidden_owner: Optional[bool] = None; selfdestruct: Optional[bool] = None
    holder_count: Optional[int] = None; owner_percent: Optional[float] = None; creator_percent: Optional[float] = None
    top10_holder_percent: Optional[float] = None; lp_holder_count: Optional[int] = None
    lp_locked_percent: Optional[float] = None
    buy_simulation_ok: Optional[bool] = None; sell_simulation_ok: Optional[bool] = None
    risk_flags: List[str] = field(default_factory=list); fetched_at: float = 0.0
    raw: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Alert:
    severity: str; title: str; event: WhaleEvent; risk_score: float; reason: str
    price_usd: Optional[float] = None; momentum: int = 0; momentum_usd: float = 0.0
    security: Optional[TokenSecurity] = None
    quantum_state: str = ""
    quantum_confidence: float = 0.0
    entanglement_size: int = 0
    coherence: float = 1.0
    interference_bonus: float = 0.0

class WalletStore:
    def __init__(self, path: str):
        self._path = Path(path); self._wallets: Set[str] = set(); self._dirty = False; self._load()
    def _load(self) -> None:
        try:
            with self._path.open("r") as f: data = json.load(f)
            self._wallets = {w.lower() for w in data.get("wallets", []) if isinstance(w, str) and (is_evm_addr(w) or is_solana_addr(w))}
            log.info("💾 loaded %d wallets from %s", len(self._wallets), self._path)
        except FileNotFoundError: log.info("💾 no wallet store; starting fresh")
        except Exception as e: log.warning("wallet load failed: %s", e)
    def save(self) -> None:
        if not self._dirty: return
        try:
            if self._path.exists():
                with contextlib.suppress(Exception):
                    self._path.with_suffix(self._path.suffix + ".bak").write_bytes(self._path.read_bytes())
            tmp = self._path.with_suffix(self._path.suffix + ".tmp")
            with tmp.open("w") as f:
                json.dump({"wallets": sorted(self._wallets), "saved": datetime.now(timezone.utc).isoformat(), "count": len(self._wallets)}, f)
                f.flush()
                with contextlib.suppress(OSError): os.fsync(f.fileno())
            tmp.replace(self._path); self._dirty = False
            log.info("💾 saved %d wallets", len(self._wallets))
        except Exception as e: log.warning("wallet save failed: %s", e)
    def add(self, w: str) -> bool:
        if not (is_evm_addr(w) or is_solana_addr(w)): return False
        wl = w.lower()
        if wl in self._wallets: return False
        self._wallets.add(wl); self._dirty = True; return True
    def all_addresses(self) -> Set[str]: return set(self._wallets)
    def __contains__(self, w: str) -> bool: return w.lower() in self._wallets
    def __len__(self) -> int: return len(self._wallets)

class QuantumEventState:
    __slots__ = ("amplitudes", "_collapsed", "_collapsed_at", "_observed_at")
    BASIS: Tuple[str, ...] = ("whale_buy", "wash_trade", "manipulation", "organic_buy", "distressed_sell")
    RISK_WEIGHTS: Dict[str, float] = {"whale_buy": 15.0, "wash_trade": 65.0, "manipulation": 85.0, "organic_buy": 30.0, "distressed_sell": 55.0}

    def __init__(self) -> None:
        n = len(self.BASIS); amp = complex(1.0 / math.sqrt(n), 0.0)
        self.amplitudes: Dict[str, complex] = {b: amp for b in self.BASIS}
        self._collapsed = False; self._collapsed_at: Optional[str] = None
        self._observed_at: Optional[float] = None

    def interfere(self, basis: str, phase_shift: float, strength: float = 0.18) -> None:
        if basis not in self.amplitudes: return
        cur = self.amplitudes[basis]
        rot = cmath.exp(1j * phase_shift)
        self.amplitudes[basis] = cur * (1 - strength) + (cur * rot) * strength
        self._normalize()

    def _normalize(self) -> None:
        norm = math.sqrt(sum(abs(a) ** 2 for a in self.amplitudes.values())) or 1.0
        self.amplitudes = {k: v / norm for k, v in self.amplitudes.items()}

    def observe(self, threshold: float = 0.62) -> Tuple[str, float]:
        probs = {k: abs(a) ** 2 for k, a in self.amplitudes.items()}
        top_basis, top_p = max(probs.items(), key=lambda kv: kv[1])
        if top_p >= threshold and not self._collapsed:
            self._collapsed = True; self._collapsed_at = top_basis
            self._observed_at = time.monotonic()
        return top_basis, top_p

    def expected_risk(self) -> float:
        return sum(abs(a) ** 2 * self.RISK_WEIGHTS.get(b, 50.0) for b, a in self.amplitudes.items())

    def collapse_bias(self, event: WhaleEvent, sec: Optional[TokenSecurity], is_meme: bool, conf: float) -> None:
        usd = event.usd_value or 0.0
        if event.event_type == "buy":
            self.interfere("whale_buy", +0.9, strength=0.30)
            if is_meme and conf >= 0.6: self.interfere("organic_buy", +0.5, strength=0.20)
            if usd >= 500_000: self.interfere("whale_buy", +0.3, strength=0.15)
        else:
            self.interfere("distressed_sell", +0.7, strength=0.25)
        if sec:
            if sec.is_honeypot: self.interfere("manipulation", +1.4, strength=0.40)
            if sec.is_mintable or sec.hidden_owner: self.interfere("manipulation", +0.6, strength=0.20)
            if (sec.sell_tax or 0) > 0.10: self.interfere("wash_trade", +0.5, strength=0.15)
        if event.wallet.lower() in SUSPECT_WALLETS:
            self.interfere("wash_trade", +0.8, strength=0.25)
            self.interfere("manipulation", +0.4, strength=0.15)

class EntanglementGraph:
    def __init__(self, window: float = 300.0, threshold: float = 0.55, cap: int = 50_000):
        self._window = window; self._threshold = threshold; self._cap = cap
        self._history: Dict[str, Deque[Tuple[float, str]]] = defaultdict(deque)
        self._pair_co: Dict[Tuple[str, str], int] = defaultdict(int)
        self._wallet_total: Dict[str, int] = defaultdict(int)
        self._cluster_cache: Dict[str, Set[str]] = {}

    def record(self, token_key: str, wallet: str) -> None:
        w = wallet.lower(); now = time.monotonic()
        dq = self._history[token_key]; dq.append((now, w))
        cutoff = now - self._window
        while dq and dq[0][0] < cutoff: dq.popleft()
        self._wallet_total[w] += 1
        recent = list({x for _, x in dq})
        for i, w1 in enumerate(recent):
            for w2 in recent[i + 1:]:
                key = (w1, w2) if w1 < w2 else (w2, w1)
                self._pair_co[key] += 1
        if len(self._pair_co) > self._cap:
            for k in list(self._pair_co)[: self._cap // 4]: del self._pair_co[k]
        self._cluster_cache.clear()

    def strength(self, w1: str, w2: str) -> float:
        w1, w2 = w1.lower(), w2.lower()
        if w1 == w2: return 1.0
        key = (w1, w2) if w1 < w2 else (w2, w1)
        co = self._pair_co.get(key, 0)
        if co == 0: return 0.0
        t1 = max(1, self._wallet_total.get(w1, 1))
        t2 = max(1, self._wallet_total.get(w2, 1))
        return co / math.sqrt(t1 * t2)

    def cluster(self, wallet: str) -> Set[str]:
        w = wallet.lower()
        if w in self._cluster_cache: return self._cluster_cache[w]
        cluster = {w}
        for (w1, w2), _ in self._pair_co.items():
            if w1 == w or w2 == w:
                if self.strength(w1, w2) >= self._threshold:
                    cluster.add(w1); cluster.add(w2)
        self._cluster_cache[w] = cluster
        return cluster

    def cluster_bonus(self, wallet: str) -> Tuple[int, float]:
        c = self.cluster(wallet)
        n = len(c) - 1
        if n <= 0: return 0, 0.0
        return n, min(0.6, math.sqrt(n) * 0.18)

class DecoherenceTracker:
    def __init__(self, halflife: float):
        self._tau = max(1.0, halflife / math.log(2.0))
        self._emission: Dict[str, float] = {}

    def emit(self, event_id: str) -> None:
        self._emission[event_id] = time.monotonic()
        if len(self._emission) > 50_000:
            for k in list(self._emission)[: 12_500]: del self._emission[k]

    def coherence(self, event_id: str, now: Optional[float] = None) -> float:
        t0 = self._emission.get(event_id)
        if t0 is None: return 1.0
        dt = (now or time.monotonic()) - t0
        return math.exp(-dt / self._tau)

class InterferenceDetector:
    def __init__(self, window: float = 600.0):
        self._window = window
        self._events: Deque[Tuple[float, str, str, str, float]] = deque()
        self._cap = 10_000

    def record(self, chain: str, token: str, wallet: str, action: str, usd: float) -> None:
        now = time.monotonic()
        key = f"{chain}:{token.lower()}"
        self._events.append((now, key, wallet.lower(), action, usd))
        cutoff = now - self._window
        while self._events and self._events[0][0] < cutoff: self._events.popleft()
        while len(self._events) > self._cap: self._events.popleft()

    def compute(self, chain: str, token: str, wallet: str, action: str) -> float:
        key = f"{chain}:{token.lower()}"; now = time.monotonic()
        cutoff = now - self._window
        buys: Set[str] = set(); sells: Set[str] = set()
        buy_usd = 0.0; sell_usd = 0.0
        for t, k, w, a, u in self._events:
            if t < cutoff or k != key or w == wallet.lower(): continue
            if a == "buy": buys.add(w); buy_usd += u
            else: sells.add(w); sell_usd += u
        if action == "buy":
            constructive = min(0.6, len(buys) * 0.15 + math.log10(max(buy_usd, 1)) * 0.08)
            destructive = min(0.5, len(sells) * 0.10 + math.log10(max(sell_usd, 1)) * 0.06)
            return constructive - destructive
        else:
            return min(0.3, len(sells) * 0.08) - min(0.3, len(buys) * 0.05)

class QuantumAnnealer:
    def __init__(self, t0: float, t1: float, iters: int, param_bounds: Tuple[float, float]):
        self._t0 = t0; self._t1 = t1; self._iters = iters
        self._lo, self._hi = param_bounds
        self._current = (self._lo + self._hi) / 2.0
        self._best = self._current
        self._best_cost = float("inf")
        self._history: List[float] = []

    def step(self, observed_cost: float) -> float:
        if len(self._history) < 5:
            self._history.append(observed_cost); return self._current
        t_frac = min(1.0, len(self._history) / max(1, self._iters))
        temp = self._t0 * ((self._t1 / self._t0) ** t_frac)
        sigma = (self._hi - self._lo) * 0.1 * temp + 0.5
        proposal = max(self._lo, min(self._hi, self._current + random.gauss(0, sigma)))
        delta = observed_cost - self._best_cost
        if delta < 0 or random.random() < math.exp(-max(0.0, delta) / max(temp, 1e-6)):
            self._current = proposal
            if observed_cost < self._best_cost:
                self._best_cost = observed_cost; self._best = proposal
        self._history.append(observed_cost)
        if len(self._history) > self._iters: self._history.pop(0)
        return self._best

class QuantumMonteCarlo:
    @staticmethod
    def estimate(base_score: float, sigma: float, samples: int) -> Tuple[float, float]:
        sigma = max(0.5, sigma)
        vals = [base_score + random.gauss(0, sigma) for _ in range(max(10, samples))]
        vals.sort()
        mean = sum(vals) / len(vals)
        lo = vals[int(0.05 * len(vals))]
        hi = vals[int(0.95 * len(vals))]
        return mean, (hi - lo) / 2.0

class QuantumWalkDiscovery:
    def __init__(self, steps: int = 2, fanout: int = 3):
        self._steps = steps; self._fanout = fanout
        self._adj: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        self._seen: Set[str] = set()

    def learn(self, token_a: str, token_b: str, weight: float = 1.0) -> None:
        if not token_a or not token_b or token_a == token_b: return
        self._adj[token_a][token_b] += weight
        self._adj[token_b][token_a] += weight

    def walk(self, seeds: Iterable[str]) -> List[str]:
        frontier = list(dict.fromkeys(seeds)); out: List[str] = []
        for _ in range(self._steps):
            nxt: List[str] = []
            for node in frontier:
                neighbors = sorted(self._adj.get(node, {}).items(), key=lambda kv: kv[1], reverse=True)
                for nb, _w in neighbors[: self._fanout]:
                    if nb in self._seen: continue
                    self._seen.add(nb); nxt.append(nb); out.append(nb)
                    if len(self._seen) > CFG.seen_cap:
                        for _r in range(max(1, CFG.seen_cap // 8)):
                            with contextlib.suppress(KeyError):
                                self._seen.pop()
            frontier = nxt
            if not frontier: break
        return out

class PriceEnricher:
    def __init__(self, client: httpx.AsyncClient):
        self._client = client; self._cache: Dict[str, Tuple[TokenInfo, float]] = {}
        self._breaker = CircuitBreaker(threshold=3, recovery=120.0, name="dexscreener")
        self._bucket = TokenBucket(CFG.dexscreener_rate, CFG.dexscreener_burst)
    async def fetch(self, addr: str, chain: str = "ethereum") -> Optional[TokenInfo]:
        if not addr or not is_valid_addr(chain, addr): return None
        key = f"{chain}:{addr.lower()}"; now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[1] < CFG.cache_ttl: return cached[0]
        if not self._breaker.allow(): return cached[0] if cached else None
        await self._bucket.acquire()
        try:
            r = await self._client.get(f"{CFG.dexscreener_url}/{addr}", timeout=12.0, headers={"Accept": "application/json"})
            if r.status_code == 429: self._breaker.on_failure(); return cached[0] if cached else None
            if r.status_code != 200: self._breaker.on_failure(); return cached[0] if cached else None
            pairs = (r.json() or {}).get("pairs") or []
            if not pairs: self._breaker.on_success(); return None
            chain_slug = CHAIN_REGISTRY.get(chain, CHAIN_REGISTRY["ethereum"]).dexscreener_slug
            chain_pairs = [p for p in pairs if (p.get("chainId") or "").lower() == chain_slug]
            if not chain_pairs: chain_pairs = pairs
            best = max(chain_pairs, key=lambda p: safe_float((p.get("liquidity") or {}).get("usd"), 0.0) or 0.0)
            info = self._parse(best); self._cache[key] = (info, now)
            if len(self._cache) > 2_000:
                items = sorted(self._cache.items(), key=lambda kv: kv[1][1])
                for k, _ in items[: len(items) // 4]: del self._cache[k]
            self._breaker.on_success(); return info
        except (httpx.HTTPError, ValueError, KeyError) as e:
            log.debug("enrich fail %s: %s", short(addr), e); self._breaker.on_failure()
            return cached[0] if cached else None
    @staticmethod
    def _parse(p: Dict[str, Any]) -> TokenInfo:
        base = p.get("baseToken") or {}; liq = (p.get("liquidity") or {}).get("usd"); vol = (p.get("volume") or {}).get("h24")
        pc = p.get("priceChange") or {}; txns = (p.get("txns") or {}).get("m5") or {}
        created = p.get("pairCreatedAt"); age = (time.time() - created / 1000.0) if created else None
        return TokenInfo(
            address=base.get("address", "") or "", symbol=(base.get("symbol") or "").upper(),
            name=base.get("name") or "", price_usd=safe_float(p.get("priceUsd")),
            liquidity_usd=safe_float(liq), volume_24h=safe_float(vol), fdv=safe_float(p.get("fdv")),
            pair_age_seconds=age, price_change_5m=safe_float(pc.get("m5")), price_change_1h=safe_float(pc.get("h1")),
            buys_5m=safe_int(txns.get("buys")) if txns.get("buys") is not None else None,
            sells_5m=safe_int(txns.get("sells")) if txns.get("sells") is not None else None,
            labels=list(p.get("labels") or []),
        )

class MemeDetector:
    def quick(self, symbol: str, name: str = "") -> bool:
        s = (symbol or "").lower().strip()
        if not s or s in STABLECOINS or s in SKIP_SYMBOLS: return False
        for pat in MEME_PATTERNS:
            if pat.search(s) or (name and pat.search(name)): return True
        return bool(re.search(r"[a-z]{2,}\d{1,3}$", s))
    def deep(self, info: Optional[TokenInfo]) -> Tuple[bool, float]:
        if not info: return False, 0.0
        s = (info.symbol or "").lower(); n = (info.name or "").lower()
        if s in STABLECOINS or s in SKIP_SYMBOLS: return False, 0.0
        score = 0.0
        for pat in MEME_PATTERNS:
            if pat.search(s) or pat.search(n): score += 0.45; break
        age = info.pair_age_seconds
        if age is not None:
            days = age / 86400.0
            if days <= 1: score += 0.30
            elif days <= 7: score += 0.20
            elif days <= CFG.fresh_pair_days: score += 0.10
        liq, vol = info.liquidity_usd, info.volume_24h
        if liq is not None and vol is not None and liq > 0:
            ratio = vol / liq
            if ratio > 5: score += 0.15
            elif ratio > 2: score += 0.08
        if liq is not None and liq < 30_000 and (vol or 0) > 50_000: score += 0.15
        if info.buys_5m is not None and info.sells_5m is not None:
            total = info.buys_5m + info.sells_5m
            if total >= 10 and info.buys_5m / total > 0.7: score += 0.10
        if info.price_change_5m is not None and info.price_change_5m > 15: score += 0.10
        if info.price_change_1h is not None and info.price_change_1h > 50: score += 0.10
        return score >= 0.40, min(score, 1.0)

class SecurityEngine:
    RUGCHECK_SUMMARY = "https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
    def __init__(self, client: httpx.AsyncClient):
        self._client = client; self._cache: Dict[str, Tuple[TokenSecurity, float]] = {}
        self._goplus_breaker = CircuitBreaker(threshold=3, recovery=180.0, name="goplus")
        self._honeypot_breaker = CircuitBreaker(threshold=2, recovery=180.0, name="honeypot.is")
        self._rugcheck_breaker = CircuitBreaker(threshold=2, recovery=180.0, name="rugcheck")
        self._bucket = TokenBucket(CFG.security_rate, CFG.security_burst)
    async def audit(self, address: str, chain: str) -> Optional[TokenSecurity]:
        cd = CHAIN_REGISTRY.get(chain)
        if not cd or not is_valid_addr(chain, address): return None
        key = f"{chain}:{address.lower()}"; now = time.monotonic()
        cached = self._cache.get(key)
        if cached and now - cached[1] < CFG.security_cache_ttl: return cached[0]
        if cd.kind == "solana": sec = await self._audit_solana(address)
        else: sec = await self._audit_evm(address, chain)
        if sec:
            sec.fetched_at = now; self._cache[key] = (sec, now)
            if len(self._cache) > 1_000:
                items = sorted(self._cache.items(), key=lambda kv: kv[1][1])
                for k, _ in items[: len(items) // 4]: del self._cache[k]
        return sec
    async def _audit_evm(self, address: str, chain: str) -> Optional[TokenSecurity]:
        sec = TokenSecurity(address=address, chain=chain)
        goplus = await self._fetch_goplus(address, chain)
        if goplus:
            sec.is_honeypot = goplus.get("is_honeypot"); sec.honeypot_source = "goplus"
            sec.buy_tax = safe_float(goplus.get("buy_tax")); sec.sell_tax = safe_float(goplus.get("sell_tax"))
            sec.is_mintable = goplus.get("is_mintable"); sec.hidden_owner = goplus.get("hidden_owner")
            sec.is_proxy = goplus.get("is_proxy"); sec.holder_count = goplus.get("holder_count")
            sec.owner_percent = safe_float(goplus.get("owner_percent"))
            sec.lp_locked_percent = safe_float(goplus.get("lp_locked_percent"))
        hp = await self._fetch_honeypot_is(address, chain)
        if hp and hp.get("IsHoneypot") is not None:
            if sec.is_honeypot is None: sec.is_honeypot = hp["IsHoneypot"]; sec.honeypot_source = "honeypot.is"
            elif hp["IsHoneypot"]: sec.is_honeypot = True; sec.honeypot_source = "both"
            sec.sell_simulation_ok = not hp.get("IsHoneypot", False)
        self._synthesize_flags(sec); return sec
    async def _fetch_goplus(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        cd = CHAIN_REGISTRY.get(chain)
        if not cd or not cd.goplus_id or not self._goplus_breaker.allow(): return None
        await self._bucket.acquire()
        try:
            r = await self._client.get(CFG.goplus_url.format(chain_id=cd.goplus_id), params={"contract_addresses": address.lower()}, timeout=15.0)
            if r.status_code == 429: self._goplus_breaker.on_failure(); return None
            if r.status_code != 200: return None
            result = (r.json() or {}).get("result") or {}
            data = result.get(address.lower()) or {}
            if not data: self._goplus_breaker.on_success(); return None
            def _b(v: Any) -> Optional[bool]:
                if v is None: return None
                s = str(v).strip()
                return True if s == "1" else False if s == "0" else None
            self._goplus_breaker.on_success()
            return {
                "is_honeypot": _b(data.get("is_honeypot")), "is_mintable": _b(data.get("is_mintable")),
                "hidden_owner": _b(data.get("hidden_owner")), "is_proxy": _b(data.get("is_proxy")),
                "buy_tax": data.get("buy_tax"), "sell_tax": data.get("sell_tax"),
                "holder_count": safe_int(data.get("holder_count"), 0) or None,
                "owner_percent": data.get("owner_percent"),
                "lp_locked_percent": data.get("lp_locked_percent"),
            }
        except Exception: self._goplus_breaker.on_failure(); return None
    async def _fetch_honeypot_is(self, address: str, chain: str) -> Optional[Dict[str, Any]]:
        cd = CHAIN_REGISTRY.get(chain)
        if not cd or not cd.goplus_id or not self._honeypot_breaker.allow(): return None
        await self._bucket.acquire()
        try:
            r = await self._client.get(CFG.honeypot_url, params={"address": address, "chainID": cd.goplus_id}, timeout=15.0)
            if r.status_code == 429: self._honeypot_breaker.on_failure(); return None
            if r.status_code != 200: return None
            data = r.json()
            if not isinstance(data, dict): return None
            self._honeypot_breaker.on_success(); return data
        except Exception: self._honeypot_breaker.on_failure(); return None
    async def _audit_solana(self, mint: str) -> Optional[TokenSecurity]:
        if not self._rugcheck_breaker.allow(): return None
        await self._bucket.acquire()
        url = self.RUGCHECK_SUMMARY.format(mint=mint)
        headers = {"Authorization": f"Bearer {CFG.rugcheck_api_key}"} if CFG.rugcheck_api_key else {}
        try:
            r = await self._client.get(url, timeout=20.0, headers=headers)
            if r.status_code == 429: self._rugcheck_breaker.on_failure(); return None
            if r.status_code != 200: return None
            data = r.json() or {}
        except Exception: self._rugcheck_breaker.on_failure(); return None
        sec = TokenSecurity(address=mint, chain="solana")
        score_norm = safe_float(data.get("score_normalised"), 0.0) or 0.0
        if score_norm >= 60: sec.is_honeypot = True; sec.honeypot_source = "rugcheck"
        for item in (data.get("risks") or []):
            name = (item.get("name") or "").lower()
            if "mint" in name and "authority" in name: sec.is_mintable = True; sec.risk_flags.append("mint_authority")
            if "freeze" in name and "authority" in name: sec.risk_flags.append("freeze_authority")
        lp = data.get("lpLockedPct")
        if lp is not None: sec.lp_locked_percent = safe_float(lp, 0.0)
        holders = data.get("totalHolders")
        if holders is not None: sec.holder_count = safe_int(holders, 0) or None
        top10 = data.get("topHoldersPct")
        if top10 is not None: sec.top10_holder_percent = safe_float(top10)
        creator = data.get("creatorBalance")
        if creator is not None: sec.creator_percent = safe_float(creator)
        self._synthesize_flags(sec)
        self._rugcheck_breaker.on_success()
        return sec
    @staticmethod
    def _synthesize_flags(sec: TokenSecurity) -> None:
        if sec.is_honeypot: sec.risk_flags.append("HONEYPOT")
        if sec.sell_tax is not None and sec.sell_tax > 0.10: sec.risk_flags.append("high_sell_tax")
        if sec.is_mintable: sec.risk_flags.append("mintable")
        if sec.hidden_owner: sec.risk_flags.append("hidden_owner")
        if sec.owner_percent is not None and sec.owner_percent > 0.20: sec.risk_flags.append("owner_concentration")
        if sec.top10_holder_percent is not None and sec.top10_holder_percent > 0.50: sec.risk_flags.append("top10_concentration")
        if sec.lp_locked_percent is not None and sec.lp_locked_percent < 0.50: sec.risk_flags.append("low_lp_lock")

class HyperliquidListener:
    MAX_WALLETS_PER_SUB = 1_000
    def __init__(self, wallets: Iterable[str], queue: Any):
        self._wallets = tuple(w.lower() for w in wallets if is_evm_addr(w))
        self._queue = queue; self._stop = asyncio.Event(); self._seen_tx: Set[str] = set()
    async def run(self) -> None:
        if not HAS_WS: log.error("websockets not installed"); return
        if not self._wallets: log.warning("HL listener: no wallets"); return
        if not CFG.goldrush_api_key: log.error("HL v20 requires GOLDRUSH_API_KEY"); return
        chunks = [self._wallets[i:i+self.MAX_WALLETS_PER_SUB] for i in range(0, len(self._wallets), self.MAX_WALLETS_PER_SUB)]
        async def _run_chunk(chunk: List[str]) -> None:
            uri = f"wss://hypercore.goldrushdata.com/ws?key={CFG.goldrush_api_key}"
            attempt = 0
            while not self._stop.is_set():
                try:
                    async with websockets.connect(uri, ping_interval=30, ping_timeout=30, close_timeout=15) as ws:
                        attempt = 0; log.info("✅ HL GoldRush chunk connected (%d wallets)", len(chunk))
                        await ws.send(json.dumps({"method": "subscribe", "subscription": {"type": "userFills", "addresses": chunk}}))
                        async for raw in ws:
                            if self._stop.is_set(): break
                            try: msg = json.loads(raw)
                            except json.JSONDecodeError: continue
                            if msg.get("channel") == "userFills": self._handle(msg)
                except asyncio.CancelledError: raise
                except Exception as exc:
                    attempt += 1; delay = min(60.0, 2 ** attempt) + random.uniform(0, 1)
                    log.warning("HL GoldRush chunk drop: %s; retry %.1fs", exc, delay)
                    with contextlib.suppress(asyncio.TimeoutError): await asyncio.wait_for(self._stop.wait(), timeout=delay)
        await asyncio.gather(*(_run_chunk(c) for c in chunks), return_exceptions=True)
    def _handle(self, msg: Dict[str, Any]) -> None:
        fills = msg.get("fills") or []
        for item in fills:
            if not isinstance(item, (list, tuple)) or len(item) < 2: continue
            wallet, f = item[0], item[1]
            self._emit(wallet, f)
    def _emit(self, wallet: str, f: Dict[str, Any]) -> None:
        if not isinstance(f, dict) or f.get("isSnapshot"): return
        side = f.get("side")
        if side not in ("B", "A"): return
        event_type = "buy" if side == "B" else "sell"
        coin = (f.get("coin") or "").lower()
        if not coin or coin in SKIP_SYMBOLS or coin in STABLECOINS: return
        px = safe_float(f.get("px")); sz = safe_float(f.get("sz"))
        if not px or not sz: return
        usd = px * sz
        if usd < CFG.hl_min_usd: return
        tx = f.get("hash") or ""; wallet_l = wallet.lower()
        dedup_key = f"{tx}:{wallet_l}" if tx else ""
        if dedup_key and not bounded_add(self._seen_tx, dedup_key): return
        try: self._queue.put_nowait(WhaleEvent(chain="hyperliquid", event_type=event_type, wallet=wallet_l, token_symbol=coin.upper(), token_address="", amount=sz, usd_value=usd, tx_hash=tx))
        except asyncio.QueueFull: return
    def stop(self) -> None: self._stop.set()

class SolanaRpcListener:
    HISTORY_URL = "https://api.helius.xyz/v0/addresses/{address}/transactions"
    def __init__(self, wallets: Iterable[str], queue: Any):
        self._wallets = tuple(w for w in wallets if is_solana_addr(w))
        self._queue = queue; self._stop = asyncio.Event(); self._seen_tx: Set[str] = set()
        self._client: Optional[httpx.AsyncClient] = None; self._bucket = TokenBucket(2.0, 5)
    async def run(self) -> None:
        if not self._wallets: 
            log.warning("Solana listener: no wallets. Sleeping for 60s...")
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=60.0)
            return
        if not CFG.helius_api_key: log.error("Solana listener requires HELIUS_API_KEY"); return
        self._client = httpx.AsyncClient(timeout=15.0)
        attempt = 0
        while not self._stop.is_set():
            try: await self._poll_all(); attempt = 0
            except Exception as exc:
                attempt += 1; delay = min(60.0, 2 ** attempt) + random.uniform(0, 1)
                log.warning("Solana v0 error: %s; retry %.1fs", exc, delay)
                with contextlib.suppress(asyncio.TimeoutError): await asyncio.wait_for(self._stop.wait(), timeout=delay)
            else: await asyncio.sleep(20.0)
        if self._client: await self._client.aclose()
    async def _poll_all(self) -> None:
        for w in self._wallets:
            if self._stop.is_set(): return
            await self._poll_wallet(w); await asyncio.sleep(0.2)
    async def _poll_wallet(self, address: str) -> None:
        assert self._client is not None
        await self._bucket.acquire()
        try:
            url = self.HISTORY_URL.format(address=address)
            r = await self._client.get(url, params={"api-key": CFG.helius_api_key, "limit": 5}, timeout=12.0)
            if r.status_code != 200: return
            data = r.json(); txs = data if isinstance(data, list) else (data.get("transactions") or data.get("data") or [])
        except Exception: return
        for tx in txs:
            sig = tx.get("signature") or ""
            if not sig or not bounded_add(self._seen_tx, sig): continue
            self._parse_v0_tx(tx, address)
            if tx.get("events"): self._parse_parsed_event(tx, address)
    def _parse_v0_tx(self, tx: Dict[str, Any], wallet: str) -> None:
        wallet_l = wallet.lower(); sig = tx.get("signature") or ""
        for ev in (tx.get("tokenTransfers") or []):
            mint = ev.get("mint") or ""
            if not mint: continue
            amount = safe_float(ev.get("tokenAmount"), 0.0) or 0.0
            if amount <= 0: continue
            frm = (ev.get("fromUserAccount") or "").lower(); to = (ev.get("toUserAccount") or "").lower()
            event_type: Optional[str] = None
            if to == wallet_l: event_type = "buy"
            elif frm == wallet_l: event_type = "sell"
            if not event_type: continue
            try: self._queue.put_nowait(WhaleEvent(chain="solana", event_type=event_type, wallet=wallet_l, token_symbol="UNKNOWN", token_address=mint, amount=amount, tx_hash=sig))
            except asyncio.QueueFull: return
    def _parse_parsed_event(self, tx: Dict[str, Any], wallet: str) -> None:
        for ev in (tx.get("events") or []):
            if ev.get("type") not in ("transfer", "swap", "buy", "sell"): continue
            mint = ev.get("mint") or ev.get("tokenMint") or ""
            if not mint: continue
            symbol = (ev.get("tokenSymbol") or ev.get("symbol") or "UNKNOWN").upper()
            if symbol in SKIP_SYMBOLS or symbol in STABLECOINS: continue
            amount = safe_float(ev.get("amount"), 0.0) or 0.0
            if amount <= 0: continue
            frm = (ev.get("from") or "").lower(); to = (ev.get("to") or "").lower()
            wallet_l = wallet.lower(); event_type: Optional[str] = None
            if to == wallet_l: event_type = "buy"
            elif frm == wallet_l: event_type = "sell"
            if not event_type: continue
            try: self._queue.put_nowait(WhaleEvent(chain="solana", event_type=event_type, wallet=wallet_l, token_symbol=symbol, token_address=mint, amount=amount, tx_hash=tx.get("signature") or ""))
            except asyncio.QueueFull: return
    def stop(self) -> None: self._stop.set()

class EVMScanner:
    API_BASE = "https://api.blockscout.com"
    def __init__(self, client: httpx.AsyncClient, queue: Any, store: WalletStore, chain: str):
        self._client = client; self._queue = queue; self._store = store; self._chain = chain
        self._cd = CHAIN_REGISTRY[chain]; self._seen: Set[str] = set()
        self._breaker = CircuitBreaker(threshold=4, recovery=180.0, name=f"blockscout-{chain}")
        self._bucket = TokenBucket(CFG.blockscout_rate, CFG.blockscout_burst)
        self._stop_requested = False
    def _endpoint(self, address: str) -> str:
        if CFG.blockscout_api_key:
            chain_id = self._cd.goplus_id or "1"
            return f"{self.API_BASE}/{chain_id}/api/v2/addresses/{address}/token-transfers"
        return self._cd.blockscout_url.format(address=address)
    def _endpoint_fallback(self, address: str) -> Optional[str]:
        if not self._cd.blockscout_url or not CFG.blockscout_api_key: return None
        base = self._cd.blockscout_url.format(address=address)
        sep = "&" if "?" in base else "?"
        return f"{base}{sep}apikey={CFG.blockscout_api_key}"
    async def scan_all(self) -> None:
        if not self._breaker.allow(): return
        if not self._cd.blockscout_url and not CFG.blockscout_api_key: return
        wallets = set(STATIC_EVM_WHALES) | self._store.all_addresses()
        valid = [w for w in wallets if is_evm_addr(w)]
        if not valid: return
        for i in range(0, len(valid), 10):
            if self._stop_requested: return
            batch = valid[i:i+10]
            await asyncio.gather(*(self._scan(w) for w in batch), return_exceptions=True)
            await asyncio.sleep(1.0)
    async def scan_hot(self) -> None:
        if not self._breaker.allow(): return
        for w in HOT_WALLETS:
            if self._stop_requested: return
            await self._scan(w); await asyncio.sleep(0.2)
    async def _scan(self, address: str) -> None:
        await self._bucket.acquire()
        headers = {"Authorization": f"Bearer {CFG.blockscout_api_key}"} if CFG.blockscout_api_key else {}
        try:
            r = await self._client.get(self._endpoint(address), params={"items_count": 3}, headers=headers, timeout=10.0)
            if r.status_code in (403, 404):
                fb = self._endpoint_fallback(address)
                if fb:
                    r = await self._client.get(fb, params={"items_count": 3}, timeout=10.0)
            if r.status_code == 403: log.warning("Blockscout 403 on %s; backing off", self._chain); self._breaker.on_failure(); return
            if r.status_code != 200: return
            items = (r.json() or {}).get("items") or []
        except Exception: return
        addr_lower = address.lower()
        for tx in items:
            tx_hash = tx.get("transaction_hash") or tx.get("hash")
            if not tx_hash: continue
            dedup_key = f"{self._chain}:{tx_hash}:{addr_lower}"
            if not bounded_add(self._seen, dedup_key): continue
            to_addr = ((tx.get("to") or {}).get("hash") or "").lower()
            frm = ((tx.get("from") or {}).get("hash") or "").lower()
            token = tx.get("token") or {}; sym = (token.get("symbol") or "UNKNOWN").upper()
            if sym.lower() in SKIP_SYMBOLS or sym.lower() in STABLECOINS: continue
            decimals = safe_int(token.get("decimals"), 18) or 18
            raw_val = safe_float((tx.get("total") or {}).get("value"), 0.0) or 0.0
            amount = raw_val / (10 ** decimals)
            if amount <= 0: continue
            event_type: Optional[str] = None
            if to_addr == addr_lower and frm in KNOWN_ROUTERS: event_type = "buy"
            elif frm == addr_lower and to_addr in KNOWN_ROUTERS: event_type = "sell"
            if not event_type: continue
            try: self._queue.put_nowait(WhaleEvent(chain=self._chain, event_type=event_type, wallet=address, token_symbol=sym, token_address=token.get("address") or "", amount=amount, tx_hash=tx_hash, token_name=token.get("name") or ""))
            except asyncio.QueueFull: return
    def stop(self) -> None: self._stop_requested = True

class MomentumTracker:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[Tuple[float, float, str]]] = defaultdict(deque); self._last_cleanup = time.monotonic()
    def add(self, key: str, usd: float, wallet: str) -> None:
        now = time.monotonic(); dq = self._events[key]; dq.append((now, usd, wallet.lower())); cutoff = now - CFG.momentum_window
        while dq and dq[0][0] < cutoff: dq.popleft()
        if now - self._last_cleanup > 600.0: self._cleanup(now); self._last_cleanup = now
    def _cleanup(self, now: float) -> None:
        cutoff = now - CFG.momentum_window; empty: List[str] = []
        for k, dq in self._events.items():
            while dq and dq[0][0] < cutoff: dq.popleft()
            if not dq: empty.append(k)
        for k in empty: del self._events[k]
    def check(self, key: str) -> Tuple[int, float, Set[str]]:
        now = time.monotonic(); cutoff = now - CFG.momentum_window; dq = self._events.get(key)
        if not dq: return 0, 0.0, set()
        valid = [(t, u, w) for t, u, w in dq if t >= cutoff]
        return len(valid), sum(u for _, u, _ in valid), {w for _, _, w in valid}

class AntiSpam:
    def __init__(self) -> None:
        self._last: Dict[str, Tuple[float, str]] = {}
        self._last_critical: Dict[str, float] = {}
        self._last_cleanup = time.monotonic()

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < 3600.0: return
        self._last_cleanup = now
        cutoff = now - CFG.anti_spam_cooldown * 4
        self._last = {k: v for k, v in self._last.items() if v[0] >= cutoff}
        self._last_critical = {k: v for k, v in self._last_critical.items()
                               if now - v < CFG.anti_spam_critical * 4}

    def allow(self, key: str, severity: str) -> bool:
        now = time.monotonic()
        self._maybe_cleanup(now)
        rank = SEVERITY_RANK.get(severity, 0)
        if severity == "CRITICAL":
            if now - self._last_critical.get(key, 0.0) < CFG.anti_spam_critical: return False
            self._last_critical[key] = now; self._last[key] = (now, severity); return True
        last_time, last_sev = self._last.get(key, (0.0, "LOW"))
        last_rank = SEVERITY_RANK.get(last_sev, 0); elapsed = now - last_time
        if elapsed < CFG.anti_spam_cooldown:
            if rank > last_rank and elapsed >= CFG.anti_spam_escalation_min: self._last[key] = (now, severity); return True
            return False
        self._last[key] = (now, severity); return True

class RiskEngine:
    def __init__(self) -> None:
        self._success: Dict[str, int] = defaultdict(int); self._fail: Dict[str, int] = defaultdict(int)
    def score(self, ev: WhaleEvent, conf: float, m_count: int, m_usd: float, sec: Optional[TokenSecurity] = None, unique_wallets: Optional[Set[str]] = None) -> Tuple[float, str]:
        lr = 1.0; reasons: List[str] = []; usd = ev.usd_value or 0.0
        if ev.event_type == "buy":
            if m_count >= 5: lr *= 2.5; reasons.append(f"{m_count} whales")
            elif m_count >= 3: lr *= 1.8; reasons.append(f"{m_count} whales")
            if m_usd >= 500_000: lr *= 1.5
        if usd >= 500_000: lr *= 1.4
        elif usd >= 100_000: lr *= 1.2
        if conf >= 0.7: lr *= 1.3; reasons.append(f"meme {conf:.0%}")
        if sec:
            if sec.is_honeypot: lr *= 20.0; reasons.append("HONEYPOT")
            if sec.is_mintable: lr *= 3.0; reasons.append("mintable")
            if sec.hidden_owner: lr *= 4.0; reasons.append("hidden-owner")
            if sec.is_proxy: lr *= 2.0
            if sec.sell_tax and sec.sell_tax > 0.10: lr *= (1 + sec.sell_tax * 5); reasons.append(f"sell-tax {sec.sell_tax:.0%}")
            if sec.buy_tax and sec.buy_tax > 0.10: lr *= (1 + sec.buy_tax * 3)
            if sec.top10_holder_percent and sec.top10_holder_percent > 0.50: lr *= (1 + sec.top10_holder_percent * 2); reasons.append("top10>50%")
            if sec.lp_locked_percent is not None and sec.lp_locked_percent < 0.50: lr *= 2.0; reasons.append(f"LP-lock {sec.lp_locked_percent:.0%}")
            if sec.sell_simulation_ok is False: lr *= 3.0; reasons.append("sell-sim-fail")
        if ev.wallet.lower() in SUSPECT_WALLETS: lr *= 1.5; reasons.append("suspect")
        wins = self._success.get(ev.wallet, 0)
        if wins > 0: lr *= max(0.5, 1.0 - wins * 0.1)
        if ev.event_type == "buy" and unique_wallets:
            trusted = {w for w in unique_wallets if w.lower() not in SUSPECT_WALLETS}
            if len(trusted) >= 3: lr *= 2.0; reasons.append(f"{len(trusted)} trusted whales")
            elif len(trusted) >= 2: lr *= 1.8; reasons.append(f"{len(trusted)} trusted whales")
        risk_prob = lr / (1 + lr); score = risk_prob * 100.0
        return min(score, 100.0), " | ".join(reasons) or "base"
    def update(self, wallet: str, success: bool) -> None:
        key = wallet.lower()
        if success: self._success[key] += 1
        else: self._fail[key] += 1

class Notifier:
    def __init__(self) -> None:
        self._json_path = Path(CFG.json_export_path) if CFG.json_export_path else None
        self._exec_bucket = TokenBucket(1.0, 3)
        self._tg_bucket = TokenBucket(1.0, 5)
        
    def _format(self, a: Alert) -> str:
        ev = a.event
        usd = f"${ev.usd_value:,.0f}" if ev.usd_value else "نامشخص"
        price = f"${a.price_usd:.8f}" if a.price_usd else "نامشخص"
        
        # ترجمه پارامترها به فارسی
        severity_fa = {"CRITICAL": "بحرانی 🔴", "HIGH": "بالا 🟠", "MEDIUM": "متوسط 🟡", "LOW": "پایین 🟢"}.get(a.severity, a.severity)
        event_type_fa = "خرید 🟢" if ev.event_type == "buy" else "فروش 🔴"
        
        chain_fa = {
            "ethereum": "اتریوم", "solana": "سولانا", "base": "بیس", 
            "bsc": "بایننس اسمارت چین", "arbitrum": "آربیتروم", "hyperliquid": "هایپرلیکوئید"
        }.get(ev.chain.lower(), ev.chain.upper())

        explorer = CHAIN_REGISTRY.get(ev.chain, CHAIN_REGISTRY["ethereum"]).explorer
        
        lines = [
            f"🐋 <b>سیگنال {event_type_fa} - {ev.token_symbol}</b>",
            f"━━━━━━━━━━━━━━━━",
            f"⚠️ <b>وضعیت:</b> {severity_fa} ({a.risk_score:.0f}/100)",
            f"🌐 <b>شبکه:</b> {chain_fa}",
            f"👤 <b>کیف پول:</b> <a href='{explorer.replace('/tx/', '/address/')}{ev.wallet}'>{short(ev.wallet)}</a>",
            f"💰 <b>حجم معامله:</b> {usd}",
            f"💵 <b>قیمت ارز:</b> {price}",
            f"📊 <b>مومنتوم:</b> {a.momentum} نهنگ / ${a.momentum_usd:,.0f}",
            f"📝 <b>دلیل:</b> {a.reason}",
        ]
        
        if a.quantum_state:
            lines.append("── ⚛️ تحلیل کوانتوم ──")
            lines.append(f"وضعیت: {a.quantum_state} (اعتماد: {a.quantum_confidence:.0%})")
            lines.append(f"خوشه: {a.entanglement_size} کیف پول")
            
        if a.security:
            sec = a.security; lines.append("── 🛡️ امنیت قرارداد ──")
            if sec.is_honeypot is not None: lines.append(f"هانی پات: {'🚨 بله' if sec.is_honeypot else '✅ خیر'}")
            if sec.sell_tax is not None: lines.append(f"کارمزد فروش: {sec.sell_tax:.1%}")
            if sec.is_mintable: lines.append("⚠️ قابلیت چاپ (Mintable)")
            if sec.hidden_owner: lines.append("⚠️ مالک مخفی")
            
        if ev.tx_hash: lines.append(f"🔗 <a href='{explorer}{ev.tx_hash}'>مشاهده تراکنش در اکسپلورر</a>")
        if ev.token_address:
            slug = CHAIN_REGISTRY.get(ev.chain, CHAIN_REGISTRY["ethereum"]).dexscreener_slug
            lines.append(f"📈 <a href='https://dexscreener.com/{slug}/{ev.token_address}'>مشاهده چارت در DexScreener</a>")
            
        return "\n".join(lines)

    async def send(self, alert: Alert) -> None:
        text = self._format(alert)
        emoji = "🚨" if alert.severity in ("CRITICAL", "HIGH") else "🔔"
        log.info("%s [%s] %s", emoji, alert.severity, alert.title)
        log.info("   chain=%s wallet=%s usd=%s", alert.event.chain, short(alert.event.wallet), f"${alert.event.usd_value:,.0f}" if alert.event.usd_value else "?")
        log.info("   reason=%s", alert.reason)
        if alert.quantum_state:
            log.info("   ⚛️  state=%s conf=%.0f%% cluster=%d coherence=%.0f%% interf=%+.2f",
                     alert.quantum_state, alert.quantum_confidence*100, alert.entanglement_size, alert.coherence*100, alert.interference_bonus)
        if self._json_path:
            with contextlib.suppress(Exception):
                record = {
                    "ts": alert.event.timestamp.isoformat(), "severity": alert.severity, "title": alert.title,
                    "chain": alert.event.chain, "type": alert.event.event_type, "symbol": alert.event.token_symbol,
                    "token_address": alert.event.token_address, "wallet": alert.event.wallet,
                    "usd": alert.event.usd_value, "price_usd": alert.price_usd,
                    "momentum": alert.momentum, "momentum_usd": alert.momentum_usd,
                    "risk_score": alert.risk_score, "reason": alert.reason,
                    "security": asdict(alert.security) if alert.security else None,
                    "quantum": {"state": alert.quantum_state, "confidence": alert.quantum_confidence,
                                "cluster_size": alert.entanglement_size, "coherence": alert.coherence,
                                "interference": alert.interference_bonus},
                }
                with self._json_path.open("a") as f: f.write(json.dumps(record, default=str) + "\n")
        if CFG.telegram_token and CFG.telegram_chat:
            await self._tg_bucket.acquire()
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(f"https://api.telegram.org/bot{CFG.telegram_token}/sendMessage", json={"chat_id": CFG.telegram_chat, "text": text, "disable_web_page_preview": True, "parse_mode": "HTML"}, timeout=10.0)
            except Exception as e: log.debug("telegram fail: %s", e)
        if CFG.execution_webhook and alert.risk_score >= CFG.execution_min_score and alert.event.event_type == "buy":
            await self._exec_bucket.acquire()
            p = 1.0 - (alert.risk_score / 100.0); b = 2.0
            kelly = max(0.0, p - (1 - p) / b)
            position_pct = min(kelly * 100, 5.0)
            if CFG.execution_dry_run:
                est_size = (alert.event.usd_value or 0.0) * position_pct / 100.0
                log.info("   [DRY RUN] would fire score=%.0f kelly=%.2f%% pos=%.2f%% est_size=$%.2f",
                         alert.risk_score, kelly * 100, position_pct, est_size)
            else:
                try:
                    async with httpx.AsyncClient() as c:
                        await c.post(CFG.execution_webhook, json={
                            "chain": alert.event.chain, "token": alert.event.token_address, "symbol": alert.event.token_symbol,
                            "usd": alert.event.usd_value, "wallet": alert.event.wallet, "risk_score": alert.risk_score,
                            "severity": alert.severity, "position_size_pct": round(position_pct, 2),
                            "kelly_fraction": round(kelly, 4), "reason": alert.reason,
                            "quantum": {"state": alert.quantum_state, "cluster": alert.entanglement_size,
                                        "coherence": alert.coherence, "interference": alert.interference_bonus},
                        }, timeout=5.0)
                    log.info("   ✅ execution webhook fired (score=%.0f pos=%.2f%%)", alert.risk_score, position_pct)
                except Exception as e: log.warning("   execution webhook failed: %s", e)
    async def close(self) -> None: pass

async def supervisor(name: str, factory: Callable[[], Any], stop: asyncio.Event) -> None:
    backoff = 2.0; restarts = 0
    while not stop.is_set():
        try: await factory(); backoff = 2.0
        except asyncio.CancelledError: return
        except Exception as exc:
            restarts += 1; log.exception("supervisor[%s] crashed (#%d): %s", name, restarts, exc)
            with contextlib.suppress(asyncio.TimeoutError): await asyncio.wait_for(stop.wait(), timeout=backoff)
            backoff = min(backoff * 2.0, 120.0)

class Orchestrator:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[WhaleEvent] = asyncio.Queue(maxsize=CFG.queue_max)
        self.notifier = Notifier(); self.enricher: Optional[PriceEnricher] = None
        self.security_engine: Optional[SecurityEngine] = None
        self.meme = MemeDetector(); self.momentum = MomentumTracker(); self.anti_spam = AntiSpam(); self.risk = RiskEngine()
        self.store = WalletStore(CFG.wallet_store_path)
        self._http: Optional[httpx.AsyncClient] = None
        self._stop = asyncio.Event(); self._tasks: List[asyncio.Task] = []
        self._hl: Optional[HyperliquidListener] = None; self._sol: Optional[SolanaRpcListener] = None
        self._evm_scanners: List[EVMScanner] = []
        self.entangle = EntanglementGraph(window=300.0, threshold=CFG.entanglement_threshold)
        self.decohere = DecoherenceTracker(halflife=CFG.decoherence_halflife)
        self.interfere = InterferenceDetector(window=600.0)
        self.qwalk = QuantumWalkDiscovery(steps=CFG.quantum_walk_steps, fanout=3)
        self.annealer = QuantumAnnealer(CFG.anneal_temp0, CFG.anneal_temp1, CFG.anneal_iterations,
                                        (max(15.0, CFG.alert_min_score - 15.0), CFG.alert_min_score + 15.0))
        self._adaptive_threshold: float = CFG.alert_min_score
        self._alert_window: Deque[float] = deque(maxlen=max(CFG.alert_rate_cap * 4, 500))
        self._stats = {"processed": 0, "alerts": 0, "filtered": 0, "buys": 0, "sells": 0,
                       "security_audits": 0, "started": time.monotonic(),
                       "quantum_states": 0, "entangled_hits": 0, "interference_hits": 0,
                       "rate_limited": 0, "cross_discovered": 0}
    async def start(self) -> None:
        limits = httpx.Limits(max_connections=CFG.http_max_conn, max_keepalive_connections=CFG.http_max_conn // 2)
        self._http = httpx.AsyncClient(headers={"User-Agent": "qw/20.3"}, timeout=CFG.http_timeout, limits=limits, follow_redirects=True)
        self.enricher = PriceEnricher(self._http); self.security_engine = SecurityEngine(self._http)
        if HAS_PROM and CFG.prometheus_port > 0:
            start_http_server(CFG.prometheus_port); log.info("📈 Prometheus on :%d", CFG.prometheus_port)
        if CFG.warmup_enabled: await self._warmup()
        self._tasks = []
        self._tasks.append(asyncio.create_task(supervisor("proc", self._processor, self._stop), name="sup-proc"))
        if "hyperliquid" in CFG.chains:
            self._hl = HyperliquidListener(HYPERLIQUID_WHALES, self.queue)
            self._tasks.append(asyncio.create_task(supervisor("hl", self._hl.run, self._stop), name="sup-hl"))
        if "solana" in CFG.chains:
            sol_wallets = [w for w in self.store.all_addresses() if is_solana_addr(w)]
            self._sol = SolanaRpcListener(sol_wallets, self.queue)
            self._tasks.append(asyncio.create_task(supervisor("sol", self._sol.run, self._stop), name="sup-sol"))
        for chain in CFG.chains:
            if CHAIN_REGISTRY[chain].kind == "evm":
                evm = EVMScanner(self._http, self.queue, self.store, chain)
                self._evm_scanners.append(evm)
                self._tasks.append(asyncio.create_task(supervisor(f"evm-{chain}", lambda e=evm: self._poll(e.scan_all, CFG.evm_poll_interval), self._stop), name=f"sup-evm-{chain}"))
                self._tasks.append(asyncio.create_task(supervisor(f"evm-hot-{chain}", lambda e=evm: self._poll(e.scan_hot, CFG.hot_poll_interval), self._stop), name=f"sup-evm-hot-{chain}"))
        self._tasks += [
            asyncio.create_task(supervisor("stats", self._stats_loop, self._stop), name="sup-stats"),
            asyncio.create_task(supervisor("heartbeat", self._heartbeat_loop, self._stop), name="sup-heartbeat"),
            asyncio.create_task(supervisor("save", self._save_loop, self._stop), name="sup-save"),
            asyncio.create_task(supervisor("telegram-alive", self._telegram_heartbeat_loop, self._stop), name="sup-tg-alive"),
        ]
        log.info("🐋 Quantum Whale Watcher v20.3 (patched)")
        log.info("   Chains        : %s", ", ".join(CFG.chains))
        log.info("   HL whales     : %d", len([w for w in HYPERLIQUID_WHALES if is_evm_addr(w)]))
        log.info("   Static EVM    : %d", len([w for w in STATIC_EVM_WHALES if is_evm_addr(w)]))
        log.info("   Hot wallets   : %d", len(HOT_WALLETS))
        log.info("   Suspects      : %d", len(SUSPECT_WALLETS))
        log.info("   Discovered    : %d", len(self.store))
        log.info("   EVM poll      : %.0fs (hot: %.0fs)", CFG.evm_poll_interval, CFG.hot_poll_interval)
        log.info("   Solana        : Helius v0 address-transactions")
        log.info("   Execution     : %s (min score %.0f)", CFG.execution_webhook or "disabled", CFG.execution_min_score)
        log.info("   ⚛️  Quantum    : %s (τ½=%.0fs, θ_ent=%.2f, QMC=%d)",
                 "ON" if CFG.quantum_enabled else "OFF", CFG.decoherence_halflife, CFG.entanglement_threshold, CFG.qmc_samples)
        log.info("   Rate limit    : %d alerts / %.0fs", CFG.alert_rate_cap, CFG.alert_rate_window)
        await self._stop.wait(); await self._shutdown()

    async def _telegram_heartbeat_loop(self) -> None:
        await self._sleep(60) # در شروع کار ۱ دقیقه صبر میکنه بعد پیام میده
        while not self._stop.is_set():
            if CFG.telegram_token and CFG.telegram_chat:
                try:
                    async with httpx.AsyncClient() as client:
                        await client.post(
                            f"https://api.telegram.org/bot{CFG.telegram_token}/sendMessage",
                            json={"chat_id": CFG.telegram_chat, "text": "💚 <b>ربات نهنگ‌ها زنده است!</b>\nدر حال رصد بازار...", "parse_mode": "HTML"},
                            timeout=10.0
                        )
                except Exception as e:
                    log.warning("Telegram heartbeat failed: %s", e)
            # هر ۴ ساعت یکبار پیام میده (4 * 60 * 60 ثانیه)
            await self._sleep(4 * 60 * 60)

    async def _warmup(self) -> None:
        assert self.enricher is not None
        trending = [
            ("0x6982508145454ce325ddbe47a25d4ec3d2311933", "ethereum"), ("0xcf0c122c6b73ff809c693db761e7baebe62b6a2e", "ethereum"),
            ("0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce", "ethereum"), ("0x4ed4e862860bed51a9570b96d89af5e1b0efefed", "base"),
            ("0x532f27101965dd16442e59d40670faf5ebb142e4", "base"), ("DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263", "solana"),
        ]
        log.info("🔥 warming price cache (%d tokens)", len(trending))
        for addr, chain in trending:
            if chain not in CFG.chains and chain != "ethereum": continue
            with contextlib.suppress(Exception):
                await self.enricher.fetch(addr, chain); await asyncio.sleep(0.6)
        log.info("🔥 price cache warmed")
    async def _shutdown(self) -> None:
        log.info("⏳ shutting down…")
        if self._hl: self._hl.stop()
        if self._sol: self._sol.stop()
        for e in self._evm_scanners: e.stop()
        for t in self._tasks: t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        try: await asyncio.wait_for(self._drain(), timeout=5.0)
        except asyncio.TimeoutError: log.warning("drain timeout; %d left", self.queue.qsize())
        self.store.save(); await self.notifier.close()
        if self._http: await self._http.aclose()
        log.info("✅ shutdown complete")
    async def _drain(self) -> None:
        while not self.queue.empty():
            try: ev = self.queue.get_nowait()
            except asyncio.QueueEmpty: return
            try: await self._process(ev)
            except Exception: log.exception("drain error")
            finally: self.queue.task_done()
    def stop(self) -> None: self._stop.set()
    async def _poll(self, fn: Callable[[], Any], interval: float) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            try: await fn()
            except Exception as exc: log.debug("poll error: %s", exc)
            elapsed = time.monotonic() - t0
            await self._sleep(max(1.0, interval - elapsed + random.uniform(0, interval * 0.1)))
    async def _sleep(self, seconds: float) -> None:
        with contextlib.suppress(asyncio.TimeoutError): await asyncio.wait_for(self._stop.wait(), timeout=seconds)
    async def _stats_loop(self) -> None:
        while not self._stop.is_set():
            await self._sleep(CFG.stats_interval); up = int(time.monotonic() - self._stats["started"])
            log.info("📊 proc=%d alerts=%d filt=%d rl=%d buys=%d sells=%d audits=%d xchain=%d q=%d up=%ds",
                     self._stats["processed"], self._stats["alerts"], self._stats["filtered"],
                     self._stats["rate_limited"], self._stats["buys"], self._stats["sells"],
                     self._stats["security_audits"], self._stats["cross_discovered"],
                     self.queue.qsize(), up)
            if CFG.quantum_enabled:
                log.info("   ⚛️  states=%d entangled=%d interfere=%d adaptive_th=%.1f",
                         self._stats["quantum_states"], self._stats["entangled_hits"],
                         self._stats["interference_hits"], self._adaptive_threshold)
    async def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            await self._sleep(CFG.heartbeat_interval); log.debug("💓 q=%d wallets=%d", self.queue.qsize(), len(self.store))
    async def _save_loop(self) -> None:
        while not self._stop.is_set():
            await self._sleep(300.0); self.store.save()
    async def _processor(self) -> None:
        while not self._stop.is_set():
            try: ev = await asyncio.wait_for(self.queue.get(), timeout=2.0)
            except asyncio.TimeoutError: continue
            except asyncio.CancelledError: return
            try: await self._process(ev)
            except asyncio.CancelledError: self.queue.task_done(); raise
            except Exception: log.exception("process error")
            finally: self.queue.task_done(); self._stats["processed"] += 1
    async def _enrich_event(self, ev: WhaleEvent) -> Optional[TokenInfo]:
        if not ev.token_address: return None
        assert self.enricher is not None
        info = await self.enricher.fetch(ev.token_address, ev.chain)
        if info:
            if not ev.usd_value and info.price_usd is not None and ev.amount > 0: ev.usd_value = ev.amount * info.price_usd
            if not ev.token_name and info.name: ev.token_name = info.name
            if not ev.token_symbol or ev.token_symbol == "UNKNOWN": ev.token_symbol = info.symbol or ev.token_symbol
        return info
    async def _audit_security(self, ev: WhaleEvent) -> Optional[TokenSecurity]:
        if not ev.token_address or not self.security_engine: return None
        sec = await self.security_engine.audit(ev.token_address, ev.chain)
        if sec: self._stats["security_audits"] += 1
        return sec
    async def _process(self, ev: WhaleEvent) -> None:
        has_addr = bool(ev.token_address); sym_unknown = (not ev.token_symbol) or ev.token_symbol == "UNKNOWN"
        if not (has_addr and sym_unknown):
            if not self.meme.quick(ev.token_symbol, ev.token_name):
                self._stats["filtered"] += 1; return
        info = await self._enrich_event(ev)
        is_meme, conf = self.meme.deep(info)
        if not is_meme:
            if has_addr and not self.meme.quick(ev.token_symbol, ev.token_name):
                self._stats["filtered"] += 1; return
            elif not has_addr: is_meme, conf = True, 0.45
            else: self._stats["filtered"] += 1; return
        sec = await self._audit_security(ev)
        qs = QuantumEventState()
        qs.collapse_bias(ev, sec, is_meme, conf)
        q_state, q_conf = qs.observe()
        expected_risk = qs.expected_risk()
        self._stats["quantum_states"] += 1
        token_key = f"{ev.chain}:{ev.token_address.lower() if ev.token_address else ev.token_symbol.upper()}"
        self.entangle.record(token_key, ev.wallet)
        cluster_size, ent_bonus = self.entangle.cluster_bonus(ev.wallet)
        if ent_bonus > 0: self._stats["entangled_hits"] += 1
        self.interfere.record(ev.chain, ev.token_address or ev.token_symbol, ev.wallet, ev.event_type, ev.usd_value or 0.0)
        interf = self.interfere.compute(ev.chain, ev.token_address or ev.token_symbol, ev.wallet, ev.event_type)
        if abs(interf) > 0.05: self._stats["interference_hits"] += 1
        if ev.event_type == "buy":
            self.momentum.add(token_key, ev.usd_value or 0.0, ev.wallet); m_count, m_usd, wallets_set = self.momentum.check(token_key); self._stats["buys"] += 1
        else: m_count, m_usd, wallets_set = 0, 0.0, set(); self._stats["sells"] += 1
        self.decohere.emit(ev.id)
        coherence = self.decohere.coherence(ev.id)
        base_score, reason = self.risk.score(ev, conf, m_count, m_usd, sec, unique_wallets=wallets_set)
        if CFG.quantum_enabled: blended = 0.7 * base_score + 0.3 * expected_risk
        else: blended = base_score
        qmc_mean, qmc_ci = QuantumMonteCarlo.estimate(blended, sigma=5.0 + 15.0 * (1 - q_conf), samples=CFG.qmc_samples)
        adjusted = qmc_mean * (1.0 + ent_bonus + interf) * coherence
        adjusted = max(0.0, min(100.0, adjusted))
        if CFG.quantum_enabled:
            target = max(CFG.alert_min_score - 10.0, min(CFG.alert_min_score + 15.0, adjusted))
            self._adaptive_threshold = 0.95 * self._adaptive_threshold + 0.05 * target
            self._adaptive_threshold = max(CFG.alert_min_score * 0.85, self._adaptive_threshold)
            cost = abs(target - adjusted) * 0.05 + (1 - q_conf) * 2.0
            annealed_th = self.annealer.step(cost)
            if math.isfinite(annealed_th) and 0.0 < annealed_th < 100.0:
                threshold = 0.7 * self._adaptive_threshold + 0.3 * annealed_th
            else:
                threshold = self._adaptive_threshold
        else:
            threshold = CFG.alert_min_score
        if adjusted < threshold: self._stats["filtered"] += 1; return

        # ==========================================
        # فیلتر کردن تراکنش‌های اسپم و بی‌ارزش
        # ==========================================
        if not ev.usd_value or ev.usd_value < 10000: 
            self._stats["filtered"] += 1; return
        if ev.wallet.lower() == "0x000000000000000000000000000000000000dead":
            self._stats["filtered"] += 1; return

        severity = ("CRITICAL" if adjusted >= 80 else "HIGH" if adjusted >= 60 else "MEDIUM" if adjusted >= 45 else "LOW")
        if not self.anti_spam.allow(token_key, severity): return
        if ev.token_address: self.qwalk.learn(token_key, f"{ev.chain}:{ev.token_symbol.upper()}", weight=math.log10(max(ev.usd_value or 1, 1)))
        price = info.price_usd if (info and info.price_usd is not None) else ((ev.usd_value / ev.amount) if (ev.usd_value and ev.amount > 0) else None)
        if ev.event_type == "sell": title = f"📉 {ev.chain.upper()} SELL — {ev.token_symbol}"
        elif sec and sec.is_honeypot: title = f"🚨 HONEYPOT BUY — {ev.token_symbol}"
        elif m_count >= CFG.momentum_min_hits: title = f"🔥 MOMENTUM {ev.token_symbol} — {m_count} whales"
        elif cluster_size >= 2: title = f"🕸️ ENTANGLED BUY — {ev.token_symbol} (cluster {cluster_size})"
        else: title = f"🐋 {ev.chain.upper()} BUY — {ev.token_symbol}"
        q_reasons = []
        if ent_bonus > 0: q_reasons.append(f"entangled+{ent_bonus:.2f}")
        if abs(interf) > 0.05: q_reasons.append(f"interf{interf:+.2f}")
        if coherence < 0.5: q_reasons.append(f"decoher{coherence:.0%}")
        full_reason = reason + (" | " + " ".join(q_reasons) if q_reasons else "")
        alert = Alert(severity=severity, title=title, event=ev, risk_score=adjusted, reason=full_reason, price_usd=price, momentum=m_count, momentum_usd=m_usd, security=sec, quantum_state=q_state, quantum_confidence=q_conf, entanglement_size=cluster_size, coherence=coherence, interference_bonus=interf)
        now_t = time.monotonic()
        while self._alert_window and now_t - self._alert_window[0] > CFG.alert_rate_window:
            self._alert_window.popleft()
        if len(self._alert_window) >= CFG.alert_rate_cap:
            self._stats["rate_limited"] += 1
            log.debug("alert rate-limited: %s", title)
            return
        self._alert_window.append(now_t)
        await self.notifier.send(alert); self._stats["alerts"] += 1
        if (ev.usd_value or 0) > 100_000: self.risk.update(ev.wallet, success=True)
        if ev.chain == "hyperliquid" and (ev.usd_value or 0.0) >= CFG.cross_chain_discovery_usd and is_evm_addr(ev.wallet):
            if self.store.add(ev.wallet):
                self._stats["cross_discovered"] += 1
                log.info("🧬 cross-chain whale discovered: %s ($%.0f)", short(ev.wallet), ev.usd_value or 0.0)

def _check_wallets() -> int:
    def _report(name: str, addrs: Iterable[str]) -> int:
        items = list(addrs)
        seen_evm: Set[str] = set(); seen_sol: Set[str] = set(); bad: List[str] = []
        for a in items:
            if is_evm_addr(a):      seen_evm.add(a.lower())
            elif is_solana_addr(a): seen_sol.add(a.lower())
            else:                    bad.append(a)
        log.info("%-20s total=%d evm=%d sol=%d invalid=%d", name, len(items), len(seen_evm), len(seen_sol), len(bad))
        for b in bad[:5]: log.warning("  invalid: %s", b)
        return len(bad)
    bad = 0
    bad += _report("HYPERLIQUID_WHALES", HYPERLIQUID_WHALES)
    bad += _report("STATIC_EVM_WHALES", STATIC_EVM_WHALES)
    bad += _report("SUSPECT_WALLETS", SUSPECT_WALLETS)
    bad += _report("HOT_WALLETS", HOT_WALLETS)
    return 1 if bad else 0

async def amain() -> None:
    CFG.validate(); orch = Orchestrator(); loop = asyncio.get_running_loop()
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(NotImplementedError, AttributeError, ValueError): loop.add_signal_handler(sig, orch.stop)
    except Exception:
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(Exception): signal.signal(sig, lambda *_: orch.stop())
    try: await orch.start()
    except Exception: log.exception("fatal")

def main() -> None:
    global CFG
    parser = argparse.ArgumentParser(description="Quantum Whale Watcher v20.3 Patched Quantum Sniper")
    parser.add_argument("--check-wallets", action="store_true", help="Validate wallet lists and exit")
    parser.add_argument("--no-quantum", action="store_true", help="Disable quantum layer (classic mode)")
    parser.add_argument("--quantum", action="store_true", help="Force-enable quantum layer")
    parser.add_argument("--no-warmup", action="store_true", help="Skip price-cache warmup")
    args = parser.parse_args()

    if args.check_wallets:
        sys.exit(_check_wallets())

    overrides: Dict[str, Any] = {}
    if args.no_quantum: overrides["quantum_enabled"] = False
    if args.quantum:    overrides["quantum_enabled"] = True
    if args.no_warmup:  overrides["warmup_enabled"] = False
    if overrides:
        CFG = replace(CFG, **overrides)
        log.info("⚙️  CLI overrides applied: %s", overrides)

    try: asyncio.run(amain())
    except KeyboardInterrupt: log.info("interrupted")

if __name__ == "__main__":
    main()
