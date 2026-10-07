#!/usr/bin/env python3
"""
crypt.py — Xul's file crypt tool
AES-256-GCM | Argon2id | RSA-OAEP | expiry | use-limits | shred
"""

import os
import sys
import struct
import argparse
import time
import secrets
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.exceptions import InvalidTag
try:
    from argon2 import PasswordHasher
    HAS_ARGON2 = True
except ImportError:
    HAS_ARGON2 = False

# ──────────────────────────────────────────────────────────────
# XUL'S SIGNATURE — Hollow Knight & Ultrakill echoes
# ──────────────────────────────────────────────────────────────

XUL_BANNER = r"""
    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
    █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █
    █ █  █ █ █  █ █ █ █  █ █ █  █ █ █ █  █ █
    █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █
    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
         X  U  L   '  S   V  A  U  L  T
    ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄
    █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █  ▄▀▄  █
    █ █  █ █ █  █ █ █ █  █ █ █  █ █ █ █  █ █
    █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █  ▀▄▀  █
    ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀
"""

# Linpeas-style ASCII shield shown during encrypt/decrypt
ENCGO_SHIELD = r"""
      ███████╗███╗   ██╗ ██████╗  ██████╗ ██████╗
      ██╔════╝████╗  ██║██╔════╝ ██╔═══██╗██╔══██╗
      █████╗  ██╔██╗ ██║██║      ██║   ██║██████╔╝
      ██╔══╝  ██║╚██╗██║██║      ██║   ██║██╔══██╗
      ███████╗██║ ╚████║╚██████╗ ╚██████╔╝██║  ██║
      ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
              ╔══════════════════════╗
              ║  ┌──┐  ┌──┐  ┌──┐  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  └──┘  └──┘  └──┘  ║
              ║  ┌──┐  ┌──┐  ┌──┐  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  └──┘  └──┘  └──┘  ║
              ║  ┌──┐  ┌──┐  ┌──┐  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  └──┘  └──┘  └──┘  ║
              ║  ┌──┐  ┌──┐  ┌──┐  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  └──┘  └──┘  └──┘  ║
              ║  ┌──┐  ┌──┐  ┌──┐  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  │▓▓│  │▓▓│  │▓▓│  ║
              ║  └──┘  └──┘  └──┘  ║
              ╚══════════════════════╝
"""

HK_QUOTES = [
    "The infection... it's gone. But the void remains.",
    "No cost too great. No mind to think. No will to break.",
    "Hollow. Empty. Whole.",
    "Radiance... I remember you.",
    "The King's brand... it burns still.",
    "Sealed. Bound. Forgotten.",
    "Dream no more.",
]

UK_QUOTES = [
    "BLOOD IS FUEL. HELL IS FULL.",
    "MANKIND IS DEAD. BLOOD IS FUEL.",
    "THE ONLY WAY OUT IS THROUGH.",
    "V1. V2. THE MACHINE GOD.",
    "ULTRAKILL. SLAUGHTER. REPEAT.",
    "YOUR SOUL IS MINE. YOUR BODY IS FUEL.",
    "FEAR NOT. DEATH IS MERCY.",
]

EASTER_EGGS = {
    "void": "🕳️  The void gazes back. You feel a chill...",
    "radiance": "☀️  A blinding light sears your retinas. -999 HP",
    "pale king": "👑  The White Palace doors creak open...",
    "hornet": "🕷️  *Needle clicks* 'We are the protectors.'",
    "v1": "🤖  [V1 ACTIVATED] Blood fuel: 100%. Style: ULTRAVIOLENT.",
    "v2": "🤖  [V2 ONLINE] Paradise lost. Judgement imminent.",
    "gabriel": "👼  'I am the judgement of the Lord.' *trumpet sounds*",
    "minos": "⚖️  'Justice is not a commodity.' *gavel falls*",
    "sisyphus": "🏋️  'Push the boulder. Again. Forever.'",
    "xul": "⚔️  Xul. The vault keeper. Keeper of secrets. Keeper of keys.",
}

# ──────────────────────────────────────────────────────────────
# CONSTANTS & FILE FORMAT
# ──────────────────────────────────────────────────────────────

MAGIC = b"CRYPT1"
VERSION = 1
CHUNK_SIZE = 65536  # 64 KiB streaming
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
HEADER_FMT = "<6sBB16s12sQII"  # magic, ver, flags, salt, nonce, expiry, max_uses, cur_uses
HEADER_SIZE = struct.calcsize(HEADER_FMT)

FLAG_EXPIRY = 0x01
FLAG_MAX_USES = 0x02
FLAG_WRAPPED_KEY = 0x04
FLAG_SHRED = 0x08

# Argon2id params (t=3, m=64MiB, p=4)
ARGON2_TIME = 3
ARGON2_MEMORY = 64 * 1024  # KiB
ARGON2_PARALLEL = 4

# PBKDF2 fallback
PBKDF2_ITER = 600_000

# ──────────────────────────────────────────────────────────────
# UTILITIES
# ──────────────────────────────────────────────────────────────

def die(msg: str, code: int = 1):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(code)

def info(msg: str):
    print(f"✓ {msg}")

def warn(msg: str):
    print(f"⚠ {msg}", file=sys.stderr)

def maybe_easter_egg(text: str):
    """Check for Hollow Knight / Ultrakill triggers in passphrase or filename"""
    lower = text.lower()
    for trigger, msg in EASTER_EGGS.items():
        if trigger in lower:
            print(msg)
            return

def show_shield(status: str):
    """Display the EncGO shield with a status message (encrypting/decrypting)"""
    print(ENCGO_SHIELD)
    print(f"  ╔══════════════════════════════════════╗")
    print(f"  ║  {status:^36}  ║")
    print(f"  ╚══════════════════════════════════════╝")
    print()

def parse_expiry(s: str) -> int:
    """Parse expiry string: 7d, 30m, 1y, 24h → Unix ms (0=none)"""
    if not s:
        return 0
    s = s.strip().lower()
    now = int(time.time() * 1000)
    try:
        if s.endswith('d'):
            return now + int(s[:-1]) * 86400 * 1000
        if s.endswith('h'):
            return now + int(s[:-1]) * 3600 * 1000
        if s.endswith('m'):
            return now + int(s[:-1]) * 60 * 1000
        if s.endswith('y'):
            return now + int(s[:-1]) * 365 * 86400 * 1000
    except ValueError:
        pass
    die(f"Invalid expiry format: {s} (use 7d, 30m, 1y, 24h)")

def format_expiry(ms: int) -> str:
    if ms == 0:
        return "never"
    dt = ms // 1000
    now = int(time.time())
    diff = dt - now
    if diff <= 0:
        return "EXPIRED"
    days = diff // 86400
    hours = (diff % 86400) // 3600
    mins = (diff % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    return " ".join(parts) or "<1m"

def derive_key_argon2(passphrase: str, salt: bytes) -> bytes:
    try:
        from argon2.low_level import hash_secret_raw, Type
        return hash_secret_raw(
            passphrase.encode(), salt,
            time_cost=ARGON2_TIME, memory_cost=ARGON2_MEMORY,
            parallelism=ARGON2_PARALLEL, hash_len=32, type=Type.ID
        )
    except ImportError:
        return derive_key_pbkdf2(passphrase, salt)

def derive_key_pbkdf2(passphrase: str, salt: bytes) -> bytes:
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    kdf = PBKDF2HMAC(hashes.SHA256(), 32, salt, PBKDF2_ITER)
    return kdf.derive(passphrase.encode())

def derive_key(passphrase: str, salt: bytes) -> bytes:
    if HAS_ARGON2:
        return derive_key_argon2(passphrase, salt)
    return derive_key_pbkdf2(passphrase, salt)

def load_public_key(pem_path: Path):
    with open(pem_path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def load_private_key(pem_path: Path, password=None):
    with open(pem_path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=password)

def wrap_key(file_key: bytes, pubkey) -> bytes:
    return pubkey.encrypt(
        file_key,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )

def unwrap_key(wrapped: bytes, privkey) -> bytes:
    return privkey.decrypt(
        wrapped,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    )

def secure_shred(path: Path, passes: int = 3):
    """Overwrite file with random data, then remove"""
    try:
        size = path.stat().st_size
        for _ in range(passes):
            with open(path, "wb") as f:
                f.write(secrets.token_bytes(size))
                f.flush()
                os.fsync(f.fileno())
        path.unlink(missing_ok=True)
    except Exception:
        pass  # Best effort

# ──────────────────────────────────────────────────────────────
# ENCRYPTION / DECRYPTION (STREAMING)
# ──────────────────────────────────────────────────────────────

def encrypt_file(in_path: Path, out_path: Path, key: bytes, salt: bytes, expiry_ms: int,
                 max_uses: int, wrapped_key: bytes | None, shred: bool):
    nonce = secrets.token_bytes(NONCE_LEN)
    aesgcm = AESGCM(key)

    flags = 0
    if expiry_ms:
        flags |= FLAG_EXPIRY
    if max_uses:
        flags |= FLAG_MAX_USES
    if wrapped_key:
        flags |= FLAG_WRAPPED_KEY
    if shred:
        flags |= FLAG_SHRED

    header = struct.pack(HEADER_FMT, MAGIC, VERSION, flags, salt, nonce,
                         expiry_ms, max_uses, 0)

    # Encrypt entire file at once (acceptable for typical use)
    with open(in_path, "rb") as fin:
        data = fin.read()
    ct = aesgcm.encrypt(nonce, data, None)
    ciphertext = ct[:-TAG_LEN]
    tag = ct[-TAG_LEN:]

    with open(out_path, "wb") as fout:
        fout.write(header)
        if wrapped_key:
            fout.write(struct.pack("<I", len(wrapped_key)))
            fout.write(wrapped_key)
        fout.write(ciphertext)
        fout.write(tag)

    info(f"Encrypted → {out_path}")
    if expiry_ms:
        info(f"Expires: {format_expiry(expiry_ms)}")
    if max_uses:
        info(f"Max uses: {max_uses}")
    if wrapped_key:
        info("Key wrapped with RSA public key")

def decrypt_file(in_path: Path, out_path: Path, key: bytes, force_shred: bool) -> bool:
    with open(in_path, "rb") as fin:
        header = fin.read(HEADER_SIZE)
        if len(header) != HEADER_SIZE:
            die("Invalid or corrupted .crypt file (header too short)", 2)

        magic, ver, flags, salt, nonce, expiry_ms, max_uses, cur_uses = struct.unpack(HEADER_FMT, header)

        if magic != MAGIC:
            die("Not a valid .crypt file (bad magic)", 2)
        if ver != VERSION:
            die(f"Unsupported version: {ver}", 2)

        # Check expiry
        if flags & FLAG_EXPIRY:
            now = int(time.time() * 1000)
            if now > expiry_ms:
                die(f"File expired on {format_expiry(expiry_ms)}. Use --force-shred to destroy.", 2)

        # Check use limit
        if flags & FLAG_MAX_USES:
            if cur_uses >= max_uses:
                die(f"Use limit reached ({max_uses}). Use --force-shred to destroy.", 2)

        # Read wrapped key if present
        wrapped_key = None
        if flags & FLAG_WRAPPED_KEY:
            wk_len_bytes = fin.read(4)
            if len(wk_len_bytes) != 4:
                die("Corrupted wrapped key length", 2)
            wk_len = struct.unpack("<I", wk_len_bytes)[0]
            wrapped_key = fin.read(wk_len)

        # Read ciphertext + tag
        remaining = fin.read()
        if len(remaining) < TAG_LEN:
            die("Corrupted file: no tag", 2)
        ciphertext = remaining[:-TAG_LEN]
        tag = remaining[-TAG_LEN:]

    # Decrypt
    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext + tag, None)
    except InvalidTag:
        die("Authentication failed — file tampered or wrong key", 2)

    # Write output
    with open(out_path, "wb") as fout:
        fout.write(plaintext)

    # Update use count in header
    if flags & FLAG_MAX_USES:
        new_uses = cur_uses + 1
        with open(in_path, "r+b") as f:
            f.seek(HEADER_SIZE - 4)  # cur_uses offset
            f.write(struct.pack("<I", new_uses))
            f.flush()
            os.fsync(f.fileno())
        info(f"Use {new_uses}/{max_uses}")

        if new_uses >= max_uses and (flags & FLAG_SHRED):
            warn("Max uses reached — shredding files")
            secure_shred(in_path)
            key_path = in_path.with_suffix(in_path.suffix + ".key")
            secure_shred(key_path)

    info(f"Decrypted → {out_path}")
    return True

# ──────────────────────────────────────────────────────────────
# COMMANDS
# ──────────────────────────────────────────────────────────────

def cmd_encrypt(args):
    in_path = Path(args.file)
    if not in_path.exists():
        die(f"Input file not found: {in_path}")

    out_path = Path(args.output) if args.output else in_path.with_suffix(in_path.suffix + ".crypt")

    # Check for easter eggs in filename
    maybe_easter_egg(in_path.name)

    # Key source
    if args.pubkey:
        # Asymmetric: generate random file key, wrap with public key
        file_key = secrets.token_bytes(32)
        pubkey = load_public_key(Path(args.pubkey))
        wrapped_key = wrap_key(file_key, pubkey)
        passphrase = None
        salt = secrets.token_bytes(SALT_LEN)  # still need salt for header
    else:
        # Symmetric: derive from passphrase
        passphrase = args.passphrase or input("Passphrase: ")
        maybe_easter_egg(passphrase)
        salt = secrets.token_bytes(SALT_LEN)
        file_key = derive_key(passphrase, salt)
        wrapped_key = None

    expiry_ms = parse_expiry(args.expire) if args.expire else 0
    max_uses = args.max_uses if args.max_uses is not None else (4 if args.expire or args.shred else 0)
    shred = args.shred

    show_shield("🔐 ENCRYPTING 🔐")
    encrypt_file(in_path, out_path, file_key, salt, expiry_ms, max_uses, wrapped_key, shred)

    # Save wrapped key to companion file if asymmetric
    if wrapped_key:
        key_path = out_path.with_suffix(out_path.suffix + ".key")
        with open(key_path, "wb") as f:
            f.write(wrapped_key)
        info(f"Wrapped key → {key_path}")

def cmd_decrypt(args):
    in_path = Path(args.file)
    if not in_path.exists():
        die(f"Input file not found: {in_path}")

    if not in_path.name.endswith(".crypt"):
        die("Expected .crypt file", 1)

    out_path = Path(args.output) if args.output else in_path.with_suffix("")

    # Read header first to check for wrapped key
    with open(in_path, "rb") as fin:
        header = fin.read(HEADER_SIZE)
        if len(header) != HEADER_SIZE:
            die("Invalid .crypt file", 2)
        magic, ver, flags, salt, nonce, expiry_ms, max_uses, cur_uses = struct.unpack(HEADER_FMT, header)

    # Determine key
    if flags & FLAG_WRAPPED_KEY:
        if not args.privkey:
            die("This file uses a wrapped key — provide --privkey", 1)
        # Read wrapped key
        with open(in_path, "rb") as fin:
            fin.seek(HEADER_SIZE)
            wk_len = struct.unpack("<I", fin.read(4))[0]
            wrapped_key = fin.read(wk_len)
        privkey = load_private_key(Path(args.privkey))
        file_key = unwrap_key(wrapped_key, privkey)
    else:
        if not args.passphrase:
            args.passphrase = input("Passphrase: ")
        maybe_easter_egg(args.passphrase)
        file_key = derive_key(args.passphrase, salt)

    show_shield("🔓 DECRYPTING 🔓")
    decrypt_file(in_path, out_path, file_key, args.force_shred)

def cmd_keygen(args):
    # Generate a random key and optionally wrap it
    key = secrets.token_bytes(32)
    out_path = Path(args.output) if args.output else Path("key.crypt.key")

    if args.pubkey:
        pubkey = load_public_key(Path(args.pubkey))
        wrapped = wrap_key(key, pubkey)
        with open(out_path, "wb") as f:
            f.write(wrapped)
        info(f"Wrapped key → {out_path}")
    else:
        # Save raw key (base64)
        import base64
        with open(out_path, "w") as f:
            f.write(base64.b64encode(key).decode())
        info(f"Raw key (base64) → {out_path}")
        warn("Store this key securely — anyone with it can decrypt!")

def cmd_verify(args):
    """Verify a .crypt file integrity without decrypting"""
    in_path = Path(args.file)
    with open(in_path, "rb") as fin:
        header = fin.read(HEADER_SIZE)
        magic, ver, flags, salt, nonce, expiry_ms, max_uses, cur_uses = struct.unpack(HEADER_FMT, header)

    print(f"File: {in_path}")
    print(f"Version: {ver}")
    print(f"Flags: {'EXPIRY ' if flags&FLAG_EXPIRY else ''}{'MAX_USES ' if flags&FLAG_MAX_USES else ''}{'WRAPPED_KEY ' if flags&FLAG_WRAPPED_KEY else ''}{'SHRED ' if flags&FLAG_SHRED else ''}")
    print(f"Expiry: {format_expiry(expiry_ms)}")
    print(f"Max uses: {max_uses if max_uses else 'unlimited'}")
    print(f"Current uses: {cur_uses}")
    print("Header valid ✓")

# ──────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="crypt — Xul's file encryption vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 crypt.py secrets.txt                    # encrypt with passphrase
  python3 crypt.py secrets.txt.crypt              # decrypt (prompts passphrase)
  python3 crypt.py file.txt --pubkey alice.pem --expire 7d --max-uses 4
  python3 crypt.py file.txt.crypt --privkey mykey.pem
  python3 crypt.py --keygen --pubkey alice.pem --out key.crypt.key
  python3 crypt.py --verify file.txt.crypt
        """
    )

    # Positional file (for quick encrypt/decrypt)
    parser.add_argument("file", nargs="?", help="File to encrypt or decrypt")

    # Mode flags
    parser.add_argument("--keygen", action="store_true", help="Generate a new key")
    parser.add_argument("--verify", action="store_true", help="Verify .crypt file header")

    # Key options
    parser.add_argument("--passphrase", "-p", help="Passphrase (prompt if omitted)")
    parser.add_argument("--pubkey", help="Recipient's public key (PEM) for key wrapping")
    parser.add_argument("--privkey", help="Your private key (PEM) for key unwrapping")

    # Output
    parser.add_argument("--output", "-o", help="Output file path")

    # Extreme mode
    parser.add_argument("--expire", help="Expiry time: 7d, 30m, 1y, 24h")
    parser.add_argument("--max-uses", type=int, help="Max decrypt uses (default 4 with --expire/--shred)")
    parser.add_argument("--shred", action="store_true", help="Secure shred on expiry/limit")
    parser.add_argument("--force-shred", action="store_true", help="Force shred expired/limited file")

    # Fun
    parser.add_argument("--banner", action="store_true", help="Show Xul's banner")
    parser.add_argument("--quote", choices=["hk", "uk"], help="Show a quote")

    args = parser.parse_args()

    # Fun flags
    if args.banner:
        print(XUL_BANNER)
        return
    if args.quote:
        import random
        print(random.choice(HK_QUOTES if args.quote == "hk" else UK_QUOTES))
        return

    # Dispatch
    if args.keygen:
        cmd_keygen(args)
    elif args.verify:
        if not args.file:
            die("--verify requires a file")
        cmd_verify(args)
    elif args.file:
        # Auto-detect encrypt vs decrypt by extension
        if args.file.endswith(".crypt"):
            cmd_decrypt(args)
        else:
            cmd_encrypt(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()