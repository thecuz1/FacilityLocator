from typing import (
    Self,
    overload,
    Callable,
    Any,
    Type,
    TypeVar,
    Iterator,
    ClassVar,
)
from discord import SelectOption

from .ansi import Colour, ANSIColour

FF = TypeVar("FF", bound="FacilityFlags")


class flag:
    def __init__(self, *, display_name: str = "") -> None:
        self.display_name: str = display_name
        self.flag_value: int = 0

    def __set_name__(self, owner: Type[FF], name: str) -> None:
        self.display_name = self.display_name or name

    def __call__(self, func: Callable[[Any], int]) -> Self:
        self.flag_value: int = func(None)
        return self

    @overload
    def __get__(self, instance: None, owner: Type[FF]) -> Self:
        ...

    @overload
    def __get__(self, instance: FF, owner: Type[FF]) -> bool:
        ...

    def __get__(self, instance: FF | None, owner: Type[FF]) -> Any:
        if instance is None:
            return self
        return instance._has_flag(self.flag_value)

    def __set__(self, instance: FF, value: bool) -> None:
        instance._set_flag(self.flag_value, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} flag_value={self.flag_value!r}>"


class vehicle_flag(flag):
    def __init__(
        self,
        *,
        display_name: str = "",
        produces: tuple[str, ...] = tuple(),
        ansi: ANSIColour = ANSIColour(),
    ) -> None:
        super().__init__(display_name=display_name)
        self.produces: tuple[str, ...] = produces
        self.ansi: ANSIColour = ansi


class FlagsMeta(Type):
    def __new__(
        cls: Type[FF], name: str, bases: tuple[type, ...], namespace: dict[str, Any]
    ):
        namespace["MAPPED_FLAGS"] = {
            var_name: value
            for var_name, value in namespace.items()
            if isinstance(value, flag)
        }

        return super().__new__(cls, name, bases, namespace)

    def __len__(cls: Type[FF]) -> int:
        return len(cls.MAPPED_FLAGS)

    def __getitem__(cls: Type[FF], index_or_slice):
        if not isinstance(index_or_slice, slice):
            raise TypeError("Only supports slices")

        start, stop, step = index_or_slice.indices(len(cls))
        return list(cls.MAPPED_FLAGS)[start:stop:step]


class FacilityFlags(metaclass=FlagsMeta):
    MAPPED_FLAGS: ClassVar[dict[str, flag]]

    __slots__ = ("value",)

    def __init__(self, value: int = 0, **kwargs: bool) -> None:
        self.value: int = int(value)
        for key, set_value in kwargs.items():
            if key not in self.MAPPED_FLAGS:
                raise TypeError(f"{key!r} is not a valid flag")
            setattr(self, key, set_value)

    def __iter__(self) -> Iterator[tuple[str, bool]]:
        for value in self.MAPPED_FLAGS.values():
            if isinstance(value, flag):
                yield (value.display_name, self._has_flag(value.flag_value))

    def __len__(self) -> int:
        return len(self.MAPPED_FLAGS)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} value={self.value}>"

    def __bool__(self) -> bool:
        return self.value != 0

    @classmethod
    def _from_value(cls, value: int) -> Self:
        return cls(value)

    @classmethod
    def from_menu(cls, *args: str) -> Self:
        kwargs = {name: True for name in args}
        return cls(**kwargs)

    def _has_flag(self, flag_value: int) -> bool:
        return (self.value & flag_value) == flag_value

    def _set_flag(self, flag_value: int, toggle: bool) -> None:
        if toggle is True:
            self.value |= flag_value
        elif toggle is False:
            self.value &= ~flag_value
        else:
            raise TypeError("Value must be bool")

    def select_options(self) -> list[SelectOption]:
        return [
            SelectOption(
                label=flag_descriptor.display_name,
                value=name,
                default=getattr(self, name),
            )
            for name, flag_descriptor in self.MAPPED_FLAGS.items()
        ]

    def adapt(self) -> int:
        return self.value


class ItemServiceFlags(FacilityFlags):
    __slots__ = ()

    @flag(display_name="CMats")
    def bcons(self):
        return 1  # 1 << 0

    @flag(display_name="PCons & Pipes")
    def pcons_pipes(self):
        return 2  # 1 << 1

    @flag(display_name="SCons")
    def scons(self):
        return 4  # 1 << 2

    @flag(display_name="Oil & Petrol")
    def oil_petrol(self):
        return 8  # 1 << 3

    @flag(display_name="Heavy Oil")
    def heavy_oil(self):
        return 16  # 1 << 4

    @flag(display_name="Enriched Oil")
    def enriched_oil(self):
        return 32  # 1 << 5

    @flag(display_name="Components")
    def components(self):
        return 64  # 1 << 6

    @flag(display_name="Coke")
    def coke(self):
        return 128  # 1 << 7

    @flag(display_name="Amats 1-2 (Cams & Pams)")
    def cams_pams(self):
        return 256  # 1 << 8

    @flag(display_name="Amats 3-4 (Sams & Hams)")
    def sams_hams(self):
        return 512  # 1 << 9

    @flag(display_name="Amats 5 (Nams)")
    def nams(self):
        return 1024  # 1 << 10

    @flag(display_name="Concrete")
    def concrete(self):
        return 2048  # 1 << 11

    @flag(display_name="Metal Beams")
    def metal_beams(self):
        return 4096  # 1 << 12

    @flag(display_name="Barbed Wire")
    def barbed_wire(self):
        return 8192  # 1 << 13

    @flag(display_name="Sandbags")
    def sandbags(self):
        return 16384  # 1 << 14

    @flag(display_name="Lamentum")
    def lamentum(self):
        return 16777216  # 1 << 24

    @flag(display_name="Daucus ISG")
    def isg(self):
        return 33554432  #  1 << 25

    @flag(display_name="Fissura")
    def fissura(self):
        return 67108864  #  1 << 26

    @flag(display_name="Typhon")
    def typhon(self):
        return 134217728  #  1 << 27

    @flag(display_name="Tripod")
    def tripod(self):
        return 268435456  #  1 << 28

    @flag(display_name="MSups")
    def msups(self):
        return 536870912  #  1 << 29

    @flag(display_name="Flame Barrel")
    def flame_barrel(self):
        return 32768  # 1 << 15

    @flag(display_name="Rocket")
    def rocket(self):
        return 65536  # 1 << 16

    # @flag(display_name="Incendiary Rocket") # warden
    # def incendiary_rocket(self):
    #    return 131072  # 1 << 17

    @flag(display_name="300mm")
    def mm300(self):
        return 262144  # 1 << 18

    @flag(display_name="250mm")
    def mm250(self):
        return 524288  # 1 << 19

    @flag(display_name="150mm")
    def mm150(self):
        return 1048576  # 1 << 20

    @flag(display_name="120mm")
    def mm120(self):
        return 2097152  # 1 << 21

    @flag(display_name="94.5mm")
    def mm94_5(self):
        return 4194304  # 1 << 22

    @flag(display_name="75mm")
    def mm75(self):
        return 8388608  # 1 << 23


class VehicleServiceFlags(FacilityFlags):
    MAPPED_FLAGS: ClassVar[dict[str, vehicle_flag]]

    __slots__ = ()

    @classmethod
    def all_vehicles(cls) -> Iterator[tuple[str, vehicle_flag]]:
        for flag_descriptor in cls.MAPPED_FLAGS.values():
            for vehicle in flag_descriptor.produces:
                yield (vehicle, flag_descriptor)

    @vehicle_flag(display_name="Modification Center")
    def modification_center(self):
        return 1  # 1 << 0

    @vehicle_flag(
        display_name="Small Assembly (Base)",
        produces=(
            '00MS "Stinger" (Motorcycle)',
            'R-9 "Speartip" Escort',
            'R-5b "Sisyphus" Hauler',
            # "Dunne Landrunner 12c", # warden vehicles
            # "Dunne Leatherback 2a",
            "Material Pallet",
            'BMS "Mineseeker" (Small Train)',
            'BMS "Railtruck" (Small Container Car)',
            'BMS "Linerunner" (Small Flatbed Car)',
            'BMS "Tinder Box" (Small Liquid Car)',
        ),
        ansi=ANSIColour(text_colour=Colour.YELLOW),
    )
    def light_assembly(self):
        return 2  # 1 << 1

    @vehicle_flag(
        display_name="Motor Pool (Small Assembly)",
        produces=(
            'T5 "Percutio" (AT-AC)',
            'T8 "Gemini" (RPG-AC)',
            'T20 "Ixion" (30mm Tankette)',
            'T14 "Vesta" (Flame Tankette)',
            'UV-05c "Odyssey" (LUV)',
            'UV-24 "Icarus" (RPG LUV)',
            # "O'Brien V.113 "Gravekeeper" (AC)",
            # "O'Brien V.121 "Highlander" (AC)",
            # "O'Brien V.130 "Wild Jack" (AC)",
            # "O'Brien V.101 "Freeman" (AC)",
            # "Drummond 100a (LUV)",
        ),
        ansi=ANSIColour(text_colour=Colour.CYAN),
    )
    def motor_pool(self):
        return 4  # 1 << 2

    @vehicle_flag(
        display_name="Rocket Factory (Small Assembly)",
        produces=(
            'R-17 "Retiarius" (Rocket Truck)',
            'T13 "Deioneus" (Rocket Tankette)',
            'DAE 3b-2 "Hades Net" (Emplaced Rocket Artillery)',
            'HH-b "Hoplite" (Half-Track)',
            'HH-d "Peltast" (Mortar Half-Track)',
            # 'Rycker 4/3-F "Wasp Nest"',
            # 'Niska-Rycker Mk. IX "Skycaller"'
            # 'Niska Mk. II "Blinder"',
            # 'King Jester - Mk. I-1'
        ),
        ansi=ANSIColour(text_colour=Colour.PINK),
    )
    def rocket_factory(self):
        return 8  # 1 << 3

    @vehicle_flag(
        display_name="Field Station (Small Assembly)",
        produces=(
            'HC-2 "Scorpion" (Infantry Support Tank)',
            'AB-11 "Doru" (APC)',
            '40-45 "Smelter" (HV40mm)',
            # "Balfour Rampart 68mm (HV68mm)",
            # 'King Gallant Mk. II (Scout Tank)',
            'BMS "Scrap Hauler" (Harvester)',
            'BMS "Fabricator" (ACV)',
        ),
        ansi=ANSIColour(text_colour=Colour.GREY),
    )
    def field_station(self):
        return 16  # 1 << 4

    @vehicle_flag(
        display_name="Tank Factory (Small Assembly)",
        produces=(
            'H-19 "Vulcan" (Light Tank)',
            'H-10 "Pelekys" (Light Tank)',
            'H-5 "Kranesca" (Light Tank)',
            '85K-a "Spatha" (Assault Tank)',
            '86K-c "Ranseur" (Assault Tank)',
            'DAE 2a-1 "Raptura" (HV75mm Cannon)',
            # "Silverhand Chieftain - Mk. VI (Assault Tank)",
            # "Gallagher Highwayman Mk. III (Cruiser Tank)",
            # "Noble Firebrand Mk. XVII (Tank Destroyer)",
            # "Devitt Ironhide Mk. IV (Light Tank)",
            # "Devitt-Caine Mk. IV MMR (Light Tank)",
            # "Huber Starbreaker 94.5mm (HV94.5 EAT)",
        ),
        ansi=ANSIColour(text_colour=Colour.RED),
    )
    def tank_factory(self):
        return 32  # 1 << 5

    @vehicle_flag(
        display_name="Weapons Platform (Small Assembly)",
        produces=(
            '945g "Stygian Bolt" (94.5mm FAT)',
            '85V-g "Talos" (Assault Tank)',
            # "Gallagher Thornfall Mk. VI (Cruiser Tank)",
            # "Balfour Stockade 75mm (Field Gun)",
        ),
        ansi=ANSIColour(text_colour=Colour.WHITE),
    )
    def weapons_platform(self):
        return 64  # 1 << 6

    @vehicle_flag(
        display_name="Large Assembly (Base)",
        produces=(
            'BMS "Black Bolt" (Locomotive)',
            'BMS "Rockhold" (Container Car)',
            'BMS "Holdout" (Infantry Car)',
            'BMS "Longrider" (Flatbed Car)',
            'BMS "Roadhouse" (Caboose)',
        ),
        ansi=ANSIColour(
            background_colour=Colour.BACKGROUND_FIREFLY_DARK_BLUE,
            text_colour=Colour.RED,
        ),
    )
    def large_assembly(self):
        return 128  # 1 << 7

    @vehicle_flag(
        display_name="Train (Large Assembly)",
        produces=(
            "Aegis Steelbreaker K5a (Combat Car)",
            "Tempest Cannon RA-2 (Artillery Car)",
        ),
        ansi=ANSIColour(
            background_colour=Colour.BACKGROUND_FIREFLY_DARK_BLUE,
            text_colour=Colour.YELLOW,
        ),
    )
    def train(self):
        return 256  # 1 << 8

    @vehicle_flag(
        display_name="Heavy Tank (Large Assembly)",
        produces=(
            '0-75b "Ares" (Super Tank)',
            "Lance-36 (Battle Tank)",
            # "Flood Mk. I (Battle Tank)",
            # "Cullen Predator Mk. III (Super Tank)",
        ),
        ansi=ANSIColour(
            background_colour=Colour.BACKGROUND_FIREFLY_DARK_BLUE,
            text_colour=Colour.PINK,
        ),
    )
    def heavy_tank(self):
        return 512  # 1 << 9
