"""Offline verification only; never extracts ZIP paths or uploads private records."""

import argparse
import hashlib
import json
import zipfile


def verify(path, tsa_ca=None):
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > 100 or sum(i.file_size for i in infos) > 64 * 1024 * 1024:
            raise ValueError("Bundle exceeds limits")
        names = [i.filename for i in infos]
        if len(names) != len(set(names)) or any(
            n.startswith("/") or ".." in n.split("/") for n in names
        ):
            raise ValueError("Ambiguous/unsafe bundle paths")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("schema_version") != 1 or set(manifest["files"]) != set(
            names
        ) - {"manifest.json"}:
            raise ValueError("Manifest does not cover the exact bundle")
        for name, digest in manifest["files"].items():
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError("Digest mismatch: " + name)
        timestamp_verified = False
        if tsa_ca and manifest.get("external_timestamp"):
            from backend.app.services.platform.timestamps import (
                verify as verify_timestamp,
            )

            ts = manifest["external_timestamp"]
            timestamp_verified = verify_timestamp(
                archive.read(ts["target"]), archive.read(ts["receipt"]), tsa_ca
            )
    return {
        "external_timestamp_verified": timestamp_verified,
        "verified_files": len(manifest["files"]),
        "timestamp_kind": manifest["timestamp_kind"],
        "authorship_verified": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle")
    parser.add_argument("--tsa-ca")
    args = parser.parse_args()
    print(json.dumps(verify(args.bundle, args.tsa_ca)))
