# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Pivot functions main module."""
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Type

import pkg_resources

from .._version import VERSION
from ..common.timespan import TimeSpan
from ..data import QueryProvider
from ..nbtools.nbwidgets import QueryTime
from ..sectools import TILookup
from .pivot_data_queries import add_data_queries_to_entities
from .pivot_register_reader import register_pivots
from .pivot_ti_provider import add_ioc_queries_to_entities

__version__ = VERSION
__author__ = "Ian Hellen"

_DEF_PIVOT_REG_FILE = "resources/mp_pivot_reg.yaml"


class Pivot:
    """Pivot environment loader."""

    def __init__(
        self,
        namespace: Dict[str, Any] = None,
        providers: Iterable[Any] = None,
        timespan: Optional[TimeSpan] = None,
    ):
        """
        Instantiate a Pivot environment.

        Parameters
        ----------
        namespace : Dict[str, Any], optional
            To search for and use any current providers, specify
            `namespace=globals()`, by default None
        providers : Iterable[Any], optional
            A list of query providers, TILookup or other providers to
            use (these will override providers of the same type read
            from `namespace`), by default None
        timespan : Optional[TimeSpan], optional
            The default timespan used by providers that require
            start and end times, by default the time range used is
            24 hours prio
        """
        self._query_time: QueryTime
        if timespan is not None:
            self.timespan = timespan
        else:
            self._set_default_query_time("day", 1)
        # acquire current providers
        self._providers: Dict[str, Any] = {}
        self._get_all_providers(namespace, providers)

        # create QueryTimes object

        # load and assign functions for data queries
        data_provs = (
            prov for prov in self._providers.values() if isinstance(prov, QueryProvider)
        )
        for prov in data_provs:
            add_data_queries_to_entities(prov, self._get_timespan)

        # load TI functions
        add_ioc_queries_to_entities(self.get_provider("TILookup"), container="ti")

        # Add pivots from config registry
        register_pivots(
            file_path=self._get_def_pivot_reg(), container="other", namespace=namespace
        )

    def _get_all_providers(
        self,
        namespace: Dict[str, Any] = None,
        providers: Iterable[Any] = None,
    ):
        self._get_query_providers(namespace=namespace, providers=providers)
        self._providers["TILookup"] = (
            self._get_provider_by_type(
                namespace=namespace, providers=providers, provider_type=TILookup
            )
            or TILookup()
        )

    def _get_query_providers(
        self,
        namespace: Dict[str, Any] = None,
        providers: Iterable[Any] = None,
    ):
        """Update the current list of loaded providers."""
        if namespace:
            # return just one provider for each data env.
            # Use the last one in the namespace
            self._providers.update(
                {
                    prov.environment: prov
                    for prov in namespace.values()
                    if isinstance(prov, QueryProvider)
                }
            )
        if providers:
            self._providers.update(
                {
                    prov.environment: prov
                    for prov in providers
                    if isinstance(prov, QueryProvider)
                }
            )

    @staticmethod
    def _get_provider_by_type(
        provider_type: Type,
        namespace: Dict[str, Any] = None,
        providers: Iterable[Any] = None,
    ) -> Any:
        if providers:
            ti_provs = [prov for prov in providers if isinstance(prov, provider_type)]
            if ti_provs:
                return ti_provs[0]
        if namespace:
            ns_providers = [
                prov for prov in namespace.values() if isinstance(prov, provider_type)
            ]
            if ns_providers:
                return ns_providers[-1]
        return None

    @staticmethod
    def _get_def_pivot_reg():
        return pkg_resources.resource_filename("msticpy", _DEF_PIVOT_REG_FILE)

    @property
    def providers(self) -> Dict[str, Any]:
        """
        Return the current set of loaded providers.

        Returns
        -------
        Dict[str, Any]
            provider_name, provider_instance

        """
        return self._providers

    def get_provider(self, name: str) -> Any:
        """
        Get a provider by type name.

        Parameters
        ----------
        name : str
            The name of the provider type.

        Returns
        -------
        Any
            An instance of the provider or None
            if the Pivot environment does not have one.
        """
        return self._providers.get(name)

    def edit_query_time(self, units: str = "day", timespan: Optional[TimeSpan] = None):
        """Display a QueryTime widget to get the timespan."""
        if self._query_time is None or self._query_time.units != units:
            self._set_default_query_time(units, 1)
        if timespan is not None:
            self._query_time = QueryTime(
                timespan=timespan,
                label="Set time range for pivot functions.",
            )
        self._query_time.display()

    def _set_default_query_time(self, units: str = "day", before: int = 1):
        self._query_time = QueryTime(
            origin_time=datetime.utcnow(),
            before=before,
            after=0,
            label="Set time range for pivot functions.",
            units=units,
        )

    @property
    def start(self):
        """Return current start time for queries."""
        return self._query_time.start

    @property
    def end(self):
        """Return current end time for queries."""
        return self._query_time.end

    @property
    def timespan(self):
        """Return the timespan as a TimeSpan object."""
        return TimeSpan(start=self.start, end=self.end)

    @timespan.setter
    def timespan(self, timespan: TimeSpan):
        """Set the current timespan for pivot queries."""
        self._query_time = QueryTime(
            timespan=timespan,
            label="Set time range for pivot functions.",
        )

    def _get_timespan(self):
        """Return the timespan as a TimeSpan object."""
        return TimeSpan(start=self.start, end=self.end)

    @staticmethod
    def register_pivot_providers(
        pivot_reg_path: str,
        namespace: Dict[str, Any] = None,
        def_container: str = "custom",
        force_container: bool = False,
    ):
        """
        Register pivot functions from configuration file.

        Parameters
        ----------
        file_path : str
            Path to config yaml file
        namespace : Dict[str, Any], optional
            Namespace to search for existing instances of classes, by default None
        container : str, optional
            Container name to use for entity pivot functions, by default "other"
        force_container : bool, optional
            Force `container` value to be used even if entity definitions have
            specific setting for a container name, by default False

        Raises
        ------
        ValueError
            An entity specified in the config file is not recognized.

        """
        register_pivots(
            pivot_reg_path,
            def_container=def_container,
            force_container=force_container,
            namespace=namespace,
        )