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
        "rules_url": "https://localhost:8010/rules?product=SystemAddons",
    },
    "production": {
        "server": "https://aus-api.mozilla.org",
        "verify_ssl": True,
        "release_url": "https://aus-api.mozilla.org/api/v1/releases/{release}",
        "rules_url": "https://aus-api.mozilla.org/api/v1/rules?product=SystemAddons",
    },
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
        if key in ("data_version", "update_type", "backgroundRate", "product"):
            continue
        if unexpanded_rule[key] is not None:
            expanded_rule[key] = unexpanded_rule[key]
    return expanded_rule


async def get_release(release_url, verify_ssl=True):
    async with aiohttp.ClientSession() as session:
        async with session.get(release_url, verify_ssl=verify_ssl) as response:
            return await response.json()


async def async_main(config):
    async with aiohttp.ClientSession() as session:
        async with session.get(
            config["rules_url"], verify_ssl=config["verify_ssl"]
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
    for channel in set([r["channel"] for r in sorted_rules]):
        with open(f"rules/{channel}.yml", "w") as fh:
            fh.write(
                yaml.dump(
                    [r for r in sorted_rules if r["channel"] == channel],
                    sort_keys=False,
                )
            )
    with open("mappings.yml", "w") as fh:
        fh.write(yaml.dump(mappings))


def main():
    # XXX argparse to allow for local vs staging vs prod?
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(SERVER_CONFIG["production"]))


__name__ == "__main__" and main()
