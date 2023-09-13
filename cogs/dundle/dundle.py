from abc import abstractmethod
from dataclasses import dataclass
import math
from statistics import median
from typing import Any, Dict, Type

from attr import field
import discord

@dataclass(frozen=True)
class Career():
    title: str

@dataclass
class Asset():
    demand_key: str
    supply_key: str

    @property
    @abstractmethod
    def quality(self) -> int:
        return self._quality if self._quality else 1

    @staticmethod
    def get_value(asset: "Asset", region: "Region") -> int:
        supply: int = Asset.get_supply(asset, region)
        demand: float = Asset.get_categorical_performance(asset, region) * region.population

        estimated_consumption_ratio: float = supply * demand

        return estimated_consumption_ratio * asset.base_value

    @staticmethod
    def get_supply(asset: "Asset", region: "Region") -> int:
        asset_supply_key: str = f"{type(asset)}s"
        return region[asset_supply_key]

    @staticmethod
    def get_categorical_performance(asset: "Asset", region: "Region") -> float:
        asset_supply_key: str = f"{type(asset)}s"
        region_assets: list[Region] = region[asset_supply_key]

        return asset.quality / median([region_asset.quality for region_asset in region_assets])

@dataclass(frozen=True)
class InternCard():
    name: str
    image: str = None
    competence: int
    experience: int
    obedience: int
    pride: int
    creativity: int

@dataclass
class Intern(InternCard, Asset):
    passion: Career
    
    _is_motivated: bool = False

@dataclass
class Employee(Intern):
    job: Career

@dataclass
class Establishment():
    _reputation: int

class Plot(Asset):
    pass

@dataclass
class Machine(Asset):
    efficiency: int = 1

    @Asset.quality.getter
    def get_quality(self) -> int:
        return self.efficiency

@dataclass
class Region():
    local_intern_cards: list[InternCard]
    population: int

@dataclass
class World():
    regions: list[Region] = []
    establishments: list[Establishment] = []

class Player(discord.User):
    def __init__(self, bankruptcies: int = 0, initial_balance: float = 0.0) -> None:
        self.bankruptcies: int = bankruptcies
        self.balance: float = initial_balance
        self.plots: list[Plot] = []
    
    def buy(asset: Asset) -> None:
        pass

    def sell(asset: Asset, customer: "Player" = None            weqrt9) -> None:
        pass

    def owns(asset: Asset) -> bool:
        return False

class Dundle():
    _establishments: list[Establishment] = []
