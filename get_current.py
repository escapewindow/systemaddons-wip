#!/usr/bin/env python
"""
"""
# TODO: retries

import aiohttp
import asyncio
import yaml

SERVER_CONFIG = {
    "local": {
        "server": "https://localhost:8010",
        "verify_ssl": False,
        "release_url": "https://localhost:8010/releases/{release}",
        "rules_url": "https://localhost:8010/rules?product={product}",
    },
    "production": {
        "server": "https://aus-api.mozilla.org",
        "verify_ssl": True,
        "release_url": "https://aus-api.mozilla.org/api/v1/releases/{release}",
        "rules_url": "https://aus-api.mozilla.org/api/v1/rules?product={product}",
    },
}

PRODUCT_CONFIG = {
    "SystemAddons": {
        "single_rules_file": False,
    },
    "Widevine": {
        "single_rules_file": True,
    }
}


def expand_rule(config, mappings, unexpanded_rule):
    expanded_rule = {}
    for key in ("priority", "rule_id", "channel", "mapping", "version"):
        val = unexpanded_rule.pop(key, None)
        if val is not None:
            expanded_rule[key] = val
    if "blobs" in mappings[expanded_rule["mapping"]]:
        expanded_rule["blobs"] = mappings[expanded_rule["mapping"]]["blobs"][:]
    for key in sorted(unexpanded_rule.keys()):
        if (
            (key == "backgroundRate" and unexpanded_rule[key] == 100)
            or (key == "update_type" and unexpanded_rule[key] == "minor")
            or key in ("product", "data_version")
        ):
            continue
        if unexpanded_rule[key] is not None:
            expanded_rule[key] = unexpanded_rule[key]
    return expanded_rule


async def get_release(release_url, verify_ssl=True):
    async with aiohttp.ClientSession() as session:
        async with session.get(release_url, verify_ssl=verify_ssl) as response:
            return await response.json()


async def populate_product(config, product):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            config["rules_url"].format(product=product), verify_ssl=config["verify_ssl"]
        ) as response:
            rules = await response.json()
    futures = []
    mappings = {}
    for mapping in set([r["mapping"] for r in rules["rules"]]):
        release_url = config["release_url"].format(release=mapping)
        futures.append(
            asyncio.create_task(
                get_release(release_url, verify_ssl=config["verify_ssl"])
            )
        )
    await asyncio.gather(*futures)
    for resp in futures:
        result = resp.result()
        name = result["name"]
        mappings[name] = result
    sorted_rules = []
    for rule in sorted(
        rules["rules"],
        key=lambda x: f"{x['priority']:010}-{x['rule_id']:010}",
        reverse=True,
    ):
        sorted_rules.append(expand_rule(config, mappings, rule))
    dump_rules(product, sorted_rules)
    for release in sorted(mappings):
        with open(f"existing/{product}/releases/{release}.yml", "w") as fh:
            fh.write(yaml.dump(mappings[release]))


def dump_rules(product, sorted_rules):
    if PRODUCT_CONFIG[product]["single_rules_file"]:
        with open(f"existing/{product}/rules.yml", "w") as fh:
            fh.write(
                yaml.dump([r for r in sorted_rules], sort_keys=False)
            )
    else:
        for channel in set([r["channel"] for r in sorted_rules]):
            with open(f"existing/{product}/rules/{channel}.yml", "w") as fh:
                fh.write(
                    yaml.dump(
                        [r for r in sorted_rules if r["channel"] == channel],
                        sort_keys=False,
                    )
                )


async def async_main(config, products):
    tasks = []
    for product in products:
        tasks.append(populate_product(config, product))
    await asyncio.gather(*tasks)


def main():
    # XXX argparse to allow for local vs staging vs prod?
    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        async_main(SERVER_CONFIG["production"], PRODUCT_CONFIG.keys())
    )


__name__ == "__main__" and main()
