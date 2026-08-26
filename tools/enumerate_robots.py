"""Enumerate NVIDIA's Isaac robot asset library straight from S3.

The bucket is public HTTP, so the whole catalogue can be mapped without a GPU,
without Isaac Sim, and without spending any Kaggle quota. Only the actual
load-and-simulate test needs hardware.
"""
import json, re, sys, urllib.request

BUCKET = "https://omniverse-content-production.s3-us-west-2.amazonaws.com"
PREFIX = "Assets/Isaac/6.0/Isaac/Robots/"


def get(url):
    with urllib.request.urlopen(url, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def list_prefix(prefix, delimiter="/"):
    """S3 list-objects-v2 with continuation-token paging."""
    keys, prefixes, token = [], [], None
    while True:
        u = f"{BUCKET}/?list-type=2&prefix={prefix}"
        if delimiter:
            u += f"&delimiter={delimiter}"
        if token:
            u += f"&continuation-token={urllib.parse.quote(token, safe='')}"
        x = get(u)
        keys += re.findall(r"<Key>(.*?)</Key>", x)
        prefixes += re.findall(r"<Prefix>(.*?)</Prefix>", x)
        m = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", x)
        if not m:
            break
        token = m.group(1)
    return keys, prefixes


def main():
    import urllib.parse  # noqa: needed by list_prefix
    _, vendor_prefixes = list_prefix(PREFIX)
    vendors = [p[len(PREFIX):].strip("/") for p in vendor_prefixes]
    vendors = [v for v in vendors if v]
    print(f"{len(vendors)} vendors", file=sys.stderr)

    catalogue = []
    for i, v in enumerate(vendors, 1):
        keys, _ = list_prefix(PREFIX + v + "/", delimiter="")
        # USD ships in several serialisations. Filtering on ".usd" alone
        # misses ".usda" (ASCII) entirely -- and some vendors' canonical robot
        # is a .usda, so that filter silently reports working robots as absent.
        USD_EXT = (".usd", ".usda", ".usdc", ".usdz")
        usds = [k for k in keys if k.endswith(USD_EXT)
                and "/.thumbs/" not in k
                and "/configuration/" not in k
                and "/Props/" not in k]
        # FILTER FIRST, THEN TRUNCATE. Doing it the other way round means the
        # quality filter never sees the good file: Idealworks lists a dozen
        # HighResProps parts alphabetically before iw_hub.usd, so a naive
        # top-4 slice contains only cardboard boxes and wheels.
        JUNK = ("/payloads/", "/props/", "/highresprops/", "/configuration/",
                "/.thumbs/", "/materials/", "/meshes/", "/parts/", "/textures/")
        clean = [u for u in usds if not any(j in u.lower() for j in JUNK)]
        primary = [u for u in (clean or usds) if "instanceable" not in u.lower()]
        # shallowest paths first -- the canonical robot sits at the top level
        primary = sorted(primary, key=lambda u: (u.count("/"), len(u)))
        catalogue.append({
            "vendor": v,
            "n_usd": len(usds),
            "candidates": [u.replace("Assets/Isaac/6.0/", "") for u in
                           (primary or usds)[:6]],
        })
        print(f"  [{i:>2}/{len(vendors)}] {v:<24} {len(usds):>3} usd", file=sys.stderr)

    total = sum(c["n_usd"] for c in catalogue)
    out = {"source": BUCKET + "/" + PREFIX, "isaac_version": "6.0",
           "n_vendors": len(vendors), "n_robot_usd": total, "extensions_counted": [".usd",".usda",".usdc",".usdz"],
           "vendors": catalogue}
    json.dump(out, open("out/robot_catalogue.json", "w"), indent=2)
    print(f"\n{len(vendors)} vendors, {total} robot USD files"
          f" -> out/robot_catalogue.json", file=sys.stderr)


if __name__ == "__main__":
    import urllib.parse
    main()
