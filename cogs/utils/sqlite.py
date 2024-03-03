from __future__ import annotations

from enum import Enum, auto
from typing import List, Dict, Iterable, TYPE_CHECKING
from contextlib import asynccontextmanager
import sqlite3
import logging
import aiosqlite
from aiosqlite import Row

from .facility import Facility
from .flags import ItemServiceFlags, VehicleServiceFlags


if TYPE_CHECKING:
    from discord import Guild, TextChannel

    from bot import FacilityBot


logger = logging.getLogger(__name__)


class FetchMethod(Enum):
    NONE = auto()
    ONE = auto()
    ALL = auto()


class AdaptableList(list):
    @staticmethod
    def adapt(messages: list[int]):
        return ";".join(str(message) for message in messages)

    @classmethod
    def convert(cls, messages: str):
        return cls(map(int, messages.split(b";")))


def adapt_bool(b: bool):
    return int(b)


def convert_int(i: bytes):
    return bool(int(i))


class Database:
    def __init__(self, bot: FacilityBot, db_file) -> None:
        self.bot: FacilityBot = bot
        self.db_file = db_file
        aiosqlite.register_adapter(AdaptableList, AdaptableList.adapt)
        aiosqlite.register_converter("messages", AdaptableList.convert)
        aiosqlite.register_adapter(AdaptableList, AdaptableList.adapt)
        aiosqlite.register_converter("CHANNEL_IDS", AdaptableList.convert)
        aiosqlite.register_adapter(ItemServiceFlags, ItemServiceFlags.adapt)
        aiosqlite.register_converter("ITEM_SERVICES", ItemServiceFlags._from_value)
        aiosqlite.register_adapter(VehicleServiceFlags, VehicleServiceFlags.adapt)
        aiosqlite.register_converter(
            "VEHICLE_SERVICES", VehicleServiceFlags._from_value
        )
        aiosqlite.register_adapter(bool, adapt_bool)
        aiosqlite.register_converter("BOOL", convert_int)

    @asynccontextmanager
    async def _connect(self):
        conn = await aiosqlite.connect(
            self.db_file, detect_types=sqlite3.PARSE_DECLTYPES
        )
        try:
            yield conn
        finally:
            await conn.close()

    async def _execute_query(
        self,
        query: str,
        params: tuple | list[tuple] | None = None,
        fetch_method: FetchMethod = FetchMethod.NONE,
    ) -> Iterable[Row] | Row | None:
        async with self._connect() as db:
            db.row_factory = Row
            if ";" in query:
                logger.debug("Running executescript statement %r", query)
                cur = await db.executescript(query)

            elif isinstance(params, list):
                logger.debug(
                    "Running executemany statement %s with parameters %r", query, params
                )
                cur = await db.executemany(query, params)

            else:
                logger.debug(
                    "Running execute statement %r with parameters %r", query, params
                )
                cur = await db.execute(query, params)

            match fetch_method:
                case FetchMethod.ONE:
                    result = await cur.fetchone()
                    if result:
                        logger.debug("Fetched row with first column %r", result[0])
                    else:
                        logger.debug("Fetched row with no result")
                    return result
                case FetchMethod.ALL:
                    result = await cur.fetchall()
                    if result:
                        logger.debug(
                            "Fetched multiple rows with first column's %r",
                            [row[0] for row in result],
                        )
                    else:
                        logger.debug("Fetched multiple rows with no result")
                    return result
                case _:
                    await db.commit()
                    logger.debug("Committed changes to DB, lastrowid %r", cur.lastrowid)
                    return cur.lastrowid

    async def fetch(
        self,
        query: str,
        *params,
    ) -> Iterable[Row]:
        async with self._connect() as db:
            logger.debug(
                "Running fetchall statement %r with parameters %r",
                query,
                params,
            )
            result = await db.execute_fetchall(query, params)

            if result:
                logger.debug(
                    "Fetched multiple rows with first column's %r",
                    [row[0] for row in result],
                )
            else:
                logger.debug("Fetched multiple rows with no result")
            return result or []

    async def fetch_one(
        self,
        query: str,
        *params,
    ) -> Row | None:
        async with self._connect() as db:
            logger.debug(
                "Running fetch statement %r with parameters %r",
                query,
                params,
            )
            cur = await db.execute(query, params)
            result = await cur.fetchone()

            if result:
                logger.debug(
                    "Fetched row with first column %r",
                    result[0],
                )
            else:
                logger.debug("Fetched row with no result")
            return result

    async def execute(
        self,
        query: str,
        *params,
    ) -> int:
        async with self._connect() as db:
            logger.debug(
                "Running execute statement %r with parameters %r", query, params
            )
            cur = await db.execute(query, params)
            await db.commit()
            logger.debug("Committed changes to database")

            return cur.lastrowid

    async def executemultiple(self, query: str):
        async with self._connect() as db:
            await db.executescript(query)
            await db.commit()

    async def create(self):
        sql = """
                CREATE TABLE "facilities" (
                    "id_"	INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
                    "name"	TEXT,
                    "description"	TEXT,
                    "region"	TEXT,
                    "coordinates"	TEXT,
                    "marker"	INTEGER,
                    "maintainer"	TEXT,
                    "author"	INTEGER,
                    "item_services"	ITEM_SERVICES,
                    "vehicle_services"	VEHICLE_SERVICES,
                    "creation_time"	INTEGER,
                    "guild_id"	INTEGER,
                    "image_url"	TEXT,
                    "thread_id"	INTEGER,
                );
                CREATE TABLE "blacklist" (
                    "object_id"	INTEGER UNIQUE,
                    "reason"	TEXT,
                    PRIMARY KEY("object_id")
                );
                CREATE TABLE "list" (
                    "guild_id"	INTEGER UNIQUE,
                    "channel_id"	INTEGER,
                    "messages"	messages,
                    PRIMARY KEY("guild_id")
                );
                CREATE TABLE "command_stats" (
                    "name"	TEXT NOT NULL,
                    "run_count"	INTEGER NOT NULL,
                    "guild_id"	INTEGER NOT NULL
                );
                CREATE UNIQUE INDEX "command_index" ON "command_stats" (
                    "name",
                    "guild_id"
                );
                CREATE TABLE "response" (
                    "guild_id"	INTEGER UNIQUE,
                    "channel_ids"	CHANNEL_IDS,
                    PRIMARY KEY("guild_id")
                );
                CREATE TABLE "user_options" (
                    "user_id"	INTEGER,
                    "ephemeral"	BOOL,
                    PRIMARY KEY("user_id")
                );
                CREATE TABLE "guild_options" (
                    "guild_id"	INTEGER,
                    "forum_id"	INTEGER,
                    PRIMARY KEY("guild_id")
                );
            """
        await self.executemultiple(sql)
        logger.info("Created database %r", str(self.db_file))

    async def ephemeral_preference(self, user_id: int) -> bool | None:
        query = """SELECT ephemeral FROM user_options WHERE user_id = ?"""
        current_choice_row = await self.fetch_one(query, user_id)
        if current_choice_row:
            return current_choice_row[0]

        query = """INSERT OR REPLACE INTO user_options VALUES (?,?)"""
        current_choice_row = await self.bot.db.execute(query, user_id, False)

        return None

    async def get_all_facilities(self) -> List[Facility]:
        async with self._connect() as db:
            db.row_factory = Row
            results = await db.execute_fetchall("SELECT * FROM facilities")
            return [Facility(**row) for row in results]

    async def add_facility(self, facility: Facility) -> int:
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
            facility.image_url,
        )
        lastrowid = await self._execute_query(
            """INSERT INTO facilities (name, description, region, coordinates, marker, maintainer, author, item_services, vehicle_services, creation_time, guild_id, image_url) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        return lastrowid

    async def get_facilities(
        self, search_dict: Dict[str, str | int] | None = None
    ) -> List[Facility]:
        if not search_dict:
            return await self.get_all_facilities()
        sql = "SELECT * FROM facilities WHERE "
        sql += "AND".join(search_dict)
        rows = await self._execute_query(
            sql, tuple(search_dict.values()), FetchMethod.ALL
        )

        return [Facility(**row) for row in rows]

    async def get_facility_ids(
        self, ids: list[int], guild_id: int | None = None
    ) -> List[Facility]:
        sql = """SELECT * FROM facilities WHERE id_ == ?"""
        if guild_id:
            sql += """AND guild_id == ?"""
        facility_list = []
        for lookup_id in ids:
            values = [lookup_id]
            if guild_id:
                values.append(guild_id)
            row = await self._execute_query(
                sql,
                tuple(values),
                FetchMethod.ONE,
            )
            if not row:
                continue
            facility = Facility(**row)
            facility_list.append(facility)
        return facility_list

    async def get_facility_id(self, id_: int) -> Facility | None:
        row = await self._execute_query(
            """SELECT * FROM facilities WHERE id_ == ?""", (id_,), FetchMethod.ONE
        )
        if not row:
            return None
        return Facility(**row)

    async def remove_facilities(self, facilities: list[Facility]) -> None:
        ids = [(facility.id_,) for facility in facilities]
        await self._execute_query("""DELETE FROM facilities WHERE id_ == ?""", ids)

    async def update_facility(self, facility: Facility) -> None:
        values = (
            facility.name,
            facility.description,
            facility.maintainer,
            facility.item_services,
            facility.vehicle_services,
            facility.image_url,
            facility.thread_id,
            facility.id_,
        )
        await self._execute_query(
            """UPDATE facilities SET name = ?, description = ?, maintainer = ?, item_services = ?, vehicle_services = ?, image_url = ?, thread_id = ? WHERE id_ == ?""",
            values,
        )

    async def reset(self) -> None:
        sql = """
            DELETE FROM facilities;
            UPDATE sqlite_sequence SET seq = 0 WHERE name == 'facilities';
            VACUUM;
        """
        await self._execute_query(sql)
        logger.info("Removed all entries from facilities and executed VACUUM")

    async def set_roles(self, role_ids: list[int], guild_id: int) -> None:
        await self._execute_query(
            """DELETE FROM roles WHERE guild_id == ?""",
            (guild_id,),
        )
        for role_id in role_ids:
            await self._execute_query(
                """INSERT INTO roles (id, guild_id) VALUES(?, ?)""",
                (role_id, guild_id),
            )

    async def get_roles(self, guild_id: int) -> list[int]:
        rows: Iterable[Row] = await self._execute_query(
            """SELECT * FROM roles WHERE guild_id == ?""",
            (guild_id,),
            FetchMethod.ALL,
        )
        return [row[0] for row in rows]

    async def set_list(
        self,
        guild: Guild,
        channel: TextChannel,
        messages: list[int],
    ) -> None:
        await self._execute_query(
            """INSERT OR REPLACE INTO list (guild_id, channel_id, messages) VALUES (?, ?, ?)""",
            (guild.id, channel.id, AdaptableList(messages)),
        )

    async def remove_list(
        self,
        guild: Guild,
    ) -> None:
        await self._execute_query(
            """DELETE FROM list WHERE guild_id == ?""",
            (guild.id,),
        )

    async def get_list(self, guild: Guild) -> Row | None:
        return await self._execute_query(
            """SELECT channel_id, messages FROM list WHERE guild_id == ?""",
            (guild.id,),
            FetchMethod.ONE,
        )
