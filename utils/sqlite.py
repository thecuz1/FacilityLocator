from typing import List, Dict, Iterable
from collections import UserList
import sqlite3
import logging
import aiosqlite
from discord import Guild, TextChannel
from facility import Facility

logger = logging.getLogger(__name__)


class Messages(UserList):
    @staticmethod
    def adapt(messages: list[int]):
        return ";".join(str(message) for message in messages)

    @classmethod
    def convert(cls, messages: str):
        return cls(map(int, messages.split(b";")))


class Database:
    def __init__(self, bot, db_file) -> None:
        self.bot = bot
        self.db_file = db_file
        aiosqlite.register_adapter(Messages, Messages.adapt)
        aiosqlite.register_converter("messages", Messages.convert)

    async def create(self):
        async with aiosqlite.connect(self.db_file) as db:
            cur = await db.execute(
                """
                CREATE TABLE "facilities" (
                    "id_"	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    "name"	TEXT,
                    "description"	TEXT,
                    "region"	TEXT,
                    "coordinates"	TEXT,
                    "marker"	INTEGER,
                    "maintainer"	TEXT,
                    "author"	INTEGER,
                    "item_services"	INTEGER,
                    "vehicle_services"	INTEGER,
                    "creation_time"	INTEGER,
                    "guild_id"	INTEGER
                );
                """
            )
            await cur.execute(
                """
                CREATE TABLE "roles" (
	                "id"	INTEGER UNIQUE,
	                "guild_id"	INTEGER,
	                PRIMARY KEY("id")
                );
                """
            )
            await db.commit()
            logger.info("Created database %r", str(self.db_file))

    async def get_all_facilities(self) -> List[Facility]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            results = await db.execute("SELECT * FROM facilities")
            rows = await results.fetchall()
            return [Facility(**row) for row in rows]

    async def add_facility(self, facility: Facility) -> int:
        async with aiosqlite.connect(self.db_file) as db:
            values = (
                facility.name,
                facility.description,
                facility.region,
                facility.coordinates,
                facility.marker,
                facility.maintainer,
                facility.author,
                facility.item_services,
                facility.vehicle_services,
                facility.creation_time,
                facility.guild_id,
            )
            cur = await db.execute(
                "INSERT INTO facilities (name, description, region, coordinates, marker, maintainer, author, item_services, vehicle_services, creation_time, guild_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                values,
            )
            await db.commit()
            return cur.lastrowid

    async def get_facilities(self, search_dict: Dict[str, str | int]) -> List[Facility]:
        if not search_dict:
            return await self.get_all_facilities()
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            sql = "SELECT * FROM facilities WHERE "
            sql += "AND".join(search_dict.keys())

            result = await db.execute(sql, tuple(search_dict.values()))
            fetched_results = await result.fetchall()
            return [Facility(**row) for row in fetched_results]

    async def get_facility_ids(self, ids) -> List[Facility]:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            facility_list = []
            for lookup_id in ids:
                res = await db.execute(
                    "SELECT * FROM facilities WHERE id_ == ?", (lookup_id,)
                )
                fetched_result = await res.fetchone()
                if not fetched_result:
                    continue
                facility = Facility(**fetched_result)
                facility_list.append(facility)
            return facility_list

    async def get_facility_id(self, id_: int) -> Facility | None:
        async with aiosqlite.connect(self.db_file) as db:
            db.row_factory = aiosqlite.Row
            res = await db.execute("SELECT * FROM facilities WHERE id_ == ?", (id_,))
            fetched_result = await res.fetchone()
            if not fetched_result:
                return None
            return Facility(**fetched_result)

    async def remove_facilities(self, facilities) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            ids = [(facility.id_,) for facility in facilities]
            await db.executemany("DELETE FROM facilities WHERE id_ == ?", ids)
            await db.commit()

    async def update_facility(self, facility) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            values = (
                facility.name,
                facility.description,
                facility.maintainer,
                facility.item_services,
                facility.vehicle_services,
                facility.id_,
            )
            await db.execute(
                "UPDATE facilities SET name = ?, description = ?, maintainer = ?, item_services = ?, vehicle_services = ? WHERE id_ == ?",
                values,
            )
            await db.commit()

    async def reset(self) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute("DELETE FROM facilities")
            await db.execute(
                "UPDATE sqlite_sequence SET seq = 0 WHERE name == 'facilities'"
            )
            await db.commit()
            await db.execute("VACUUM")
            await db.commit()
        logger.info("Removed all entries from facilities and executed VACUUM")

    async def set_roles(self, role_ids: list[int], guild_id: int) -> None:
        async with aiosqlite.connect(self.db_file) as db:
            cur = await db.execute(
                "DELETE FROM roles WHERE guild_id == ?",
                (guild_id,),
            )
            for role_id in role_ids:
                await cur.execute(
                    """INSERT INTO roles (id, guild_id) VALUES(?, ?)""",
                    (role_id, guild_id),
                )
            await db.commit()

    async def get_roles(self, guild_id: int) -> list[int]:
        async with aiosqlite.connect(self.db_file) as db:
            cur = await db.execute(
                """SELECT * FROM roles WHERE guild_id == ?""", (guild_id,)
            )
            res = await cur.fetchall()
            return [row[0] for row in res]

    async def set_list(
        self,
        guild: Guild,
        channel: TextChannel,
        messages: list[int],
    ):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                """INSERT OR REPLACE INTO list (guild_id, channel_id, messages) VALUES (?, ?, ?)""",
                (guild.id, channel.id, Messages(messages)),
            )
            await db.commit()

    async def remove_list(
        self,
        guild: Guild,
    ):
        async with aiosqlite.connect(self.db_file) as db:
            await db.execute(
                """DELETE FROM list WHERE guild_id == ?""",
                (guild.id,),
            )
            await db.commit()

    async def get_list(self, guild: Guild):
        async with aiosqlite.connect(
            self.db_file,
            detect_types=sqlite3.PARSE_DECLTYPES,
        ) as db:
            cur = await db.execute(
                """SELECT channel_id, messages FROM list WHERE guild_id == ?""",
                (guild.id,),
            )
            return await cur.fetchone()
