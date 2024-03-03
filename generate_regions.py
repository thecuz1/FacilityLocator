"""Script to generate region names and locations for use with the bot."""

import string
import asyncio

import aiohttp


overridden_names = {
    "OarbreakerHex": "Oarbreaker Isles",
    "MooringCountyHex": "The Moors",
    "FishermansRowHex": "Fisherman's Row",
    "LinnMercyHex": "The Linn of Mercy",
    "KingsCageHex": "King's Cage",
    "DeadLandsHex": "Deadlands",
    "LochMorHex": "Loch Mór",
    "ClahstraHex": "The Clahstra",
    "DrownedValeHex": "The Drowned Vale",
    "HeartlandsHex": "The Heartlands",
}


async def main() -> None:
    region_names: dict[str, list[str]] = {}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://war-service-live.foxholeservices.com/api/worldconquest/maps"  # noqa: E501
        ) as response:
            regions = await response.json()

        regions.sort()

        for region in regions:
            if region in overridden_names:
                region_name = overridden_names[region]
            else:
                region_name = region.replace("Hex", "")
                for index, char in enumerate(region_name[1:]):
                    index += 1
                    if char in string.ascii_uppercase:
                        region_name = region_name[:index] + " " + region_name[index:]  # noqa: E501

            async with session.get(
                f"https://war-service-live.foxholeservices.com/api/worldconquest/maps/{region}/static"  # noqa: E501
            ) as response:
                result = await response.json()
                for item in result["mapTextItems"]:
                    region_names.setdefault(region_name, []).append(item["text"])  # noqa: E501

    with open("region_output.txt", "w", encoding="utf-8") as f:
        f.write("REGIONS: dict[str, tuple[str, ...]] = {\n")
        for region, names in region_names.items():
            f.write(f'    "{region}": (\n')
            for name in names:
                f.write(f'        "{name}",\n')

            f.write("    ),\n")
        f.write("}")


asyncio.run(main())
