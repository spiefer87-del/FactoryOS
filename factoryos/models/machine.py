"""
Kompatibilitätsimport für ältere FactoryOS-Module.

Das zentrale Maschinenmodell befindet sich jetzt unter:
factoryos.modules.masterdata.machines.models
"""

from factoryos.modules.masterdata.machines.models import (
    Machine,
    InjectionMoldingData,
)

__all__ = [
    "Machine",
    "InjectionMoldingData",
]
