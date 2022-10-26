from enum import Enum


class Service(Enum):
    BCONS = (1 << 0, 'Bcons')
    PCONS_PIPES = (1 << 1, 'Pcons & Pipes')
    SCONS = (1 << 2, 'Scons')
    OIL_PETROL = (1 << 3, 'Oil & Petrol')
    HEAVY_OIL = (1 << 4, 'Heavy Oil')
    ENRICHED_OIL = (1 << 5, 'Enriched Oil')
    CAMS_PAMS = (1 << 6, 'Cams & Pams')
    SAMS_HAMS = (1 << 7, 'Sams & Hams')
    NAMS = (1 << 8, 'Nams')
    LIGHT_ASSEMBLY = (1 << 9, 'Light Assembly')
    LIGHT_ASSEMBLY_MP = (1 << 10, 'Light Assembly (Motor Pool)')
    LIGHT_ASSEMBLY_RF = (1 << 11, 'Light Assembly (Rocket Factory)')
    LIGHT_ASSEMBLY_FS = (1 << 12, 'Light Assembly (Field Station)')
    LIGHT_ASSEMBLY_TF = (1 << 13, 'Light Assembly (Tank Factory)')
    LIGHT_ASSEMBLY_WP = (1 << 14, 'Light Assembly (Weapons Platform)')
    MODIFICATION_CENTER = (1 << 15, 'Modification Center')
    AMMO_FACTORY = (1 << 16, 'Ammo Factory')
    AMMO_FACTORY_RT = (1 << 17, 'Ammo Factory (Rocket)')
    AMMO_FACTORY_LS = (1 << 18, 'Ammo Factory (Large Shell)')
    LARGE_ASSEMBLY = (1 << 19, 'Large Assembly')
    LARGE_ASSEMBLY_T = (1 << 20, 'Large Assembly (Train)')
    LARGE_ASSEMBLY_HT = (1 << 21, 'Large Assembly (Heavy Tank)')


class Region(Enum):
    KALOKAI = 'Kalokai'
    RED_RIVER = 'Red River'
    ACRITHIA = 'Acrithia'
    ASH_FIELDS = 'Ash Fields'
    TERMINUS = 'Terminus'
    ORIGIN = 'Origin'
    THE_FINGERS = 'The Fingers'
    GREAT_MARCH = 'Great March'
    THE_HEARTLANDS = 'The Heartlands'
    SHACKLED_CHASM = 'Shackled Chasm'
    WESTGATE = 'Westgate'
    ALLODS_BIGHT = 'Allods Bight'
    FISHERMANS_ROW = 'Fishermans Row'
    TEMPEST_ISLAND = 'Tempest Island'
    UMBRAL_WILDWOOD = 'Umbral Wildwood'
    LOCH_MOR = 'Loch Mór'
    THE_DROWNED_VALE = 'The Drowned Vale'
    FARRANAC_COAST = 'Farranac Coast'
    ENDLESS_SHORE = 'Endless Shore'
    THE_OARBREAKER_ISLES = 'The Oarbreaker Isles'
    GODCROFTS = 'Godcrofts'
    DEADLANDS = 'DeadLands'
    THE_LINN_OF_MERCY = 'The Linn of Mercy'
    MARBAN_HOLLOW = 'Marban Hollow'
    STONECRADLE = 'Stonecradle'
    WEATHERED_EXPANSE = 'Weathered Expanse'
    NEVISH_LINE = 'Nevish Line'
    MORGENS_CROSSING = 'Morgens Crossing'
    CALLAHANS_PASSAGE = 'Callahans Passage'
    THE_MOORS = 'The Moors'
    VIPER_PIT = 'Viper Pit'
    CALLUMS_CAPE = 'Callums Cape'
    CLANSHEAD_VALLEY = 'Clanshead Valley'
    REACHING_TRAIL = 'Reaching Trail'
    SPEAKING_WOODS = 'Speaking Woods'
    HOWL_COUNTY = 'Howl County'
    BASIN_SIONNACH = 'Basin Sionnach'
