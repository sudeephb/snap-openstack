# Copyright (c) 2023 Canonical Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging

import click
from packaging.version import Version
from rich.console import Console

from sunbeam.commands.hypervisor import ReapplyHypervisorTerraformPlanStep
from sunbeam.commands.terraform import TerraformHelper, TerraformInitStep
from sunbeam.jobs.common import run_plan
from sunbeam.jobs.juju import JujuHelper
from sunbeam.plugins.interface.v1.openstack import (
    DisableOpenStackApplicationStep,
    EnableOpenStackApplicationStep,
    OpenStackControlPlanePlugin,
    TerraformPlanLocation,
)

LOG = logging.getLogger(__name__)
console = Console()


class TelemetryPlugin(OpenStackControlPlanePlugin):
    version = Version("0.0.1")

    def __init__(self) -> None:
        super().__init__(
            name="telemetry",
            tf_plan_location=TerraformPlanLocation.SUNBEAM_TERRAFORM_REPO,
        )

    def run_enable_plans(self) -> None:
        """Run plans to enable plugin."""
        data_location = self.snap.paths.user_data
        tfhelper = TerraformHelper(
            path=self.snap.paths.user_common / "etc" / f"deploy-{self.tfplan}",
            plan=self._get_plan_name(),
            backend="http",
            data_location=data_location,
        )
        tfhelper_hypervisor_deploy = TerraformHelper(
            path=self.snap.paths.user_common / "etc" / "deploy-openstack-hypervisor",
            plan="hypervisor-plan",
            backend="http",
            data_location=data_location,
        )
        jhelper = JujuHelper(data_location)
        plan = [
            TerraformInitStep(tfhelper),
            EnableOpenStackApplicationStep(tfhelper, jhelper, self),
            # No need to pass any extra terraform vars for this plugin
            ReapplyHypervisorTerraformPlanStep(tfhelper_hypervisor_deploy, jhelper),
        ]

        run_plan(plan, console)
        click.echo(f"OpenStack {self.name} application enabled.")

    def run_disable_plans(self) -> None:
        """Run plans to disable the plugin."""
        data_location = self.snap.paths.user_data
        tfhelper = TerraformHelper(
            path=self.snap.paths.user_common / "etc" / f"deploy-{self.tfplan}",
            plan=self._get_plan_name(),
            backend="http",
            data_location=data_location,
        )
        tfhelper_hypervisor_deploy = TerraformHelper(
            path=self.snap.paths.user_common / "etc" / "deploy-openstack-hypervisor",
            plan="hypervisor-plan",
            backend="http",
            data_location=data_location,
        )
        jhelper = JujuHelper(data_location)
        plan = [
            TerraformInitStep(tfhelper),
            DisableOpenStackApplicationStep(tfhelper, jhelper, self),
            ReapplyHypervisorTerraformPlanStep(tfhelper_hypervisor_deploy, jhelper),
        ]

        run_plan(plan, console)
        click.echo(f"OpenStack {self.name} application disabled.")

    def set_application_names(self) -> list:
        """Application names handled by the terraform plan."""
        database_topology = self.get_database_topology()

        apps = ["aodh", "aodh-mysql-router"]
        if database_topology == "multi":
            apps.append("aodh-mysql")

        if self.client.cluster.list_nodes_by_role("storage"):
            apps.extend(["ceilometer", "gnocchi", "gnocchi-mysql-router"])
            if database_topology == "multi":
                apps.append("gnocchi-mysql")

        return apps

    def set_tfvars_on_enable(self) -> dict:
        """Set terraform variables to enable the application."""
        return {
            "telemetry-channel": "2023.2/edge",
            "enable-telemetry": True,
        }

    def set_tfvars_on_disable(self) -> dict:
        """Set terraform variables to disable the application."""
        return {"enable-telemetry": False}

    def set_tfvars_on_resize(self) -> dict:
        """Set terraform variables to resize the application."""
        return {}

    @click.command()
    def enable_plugin(self) -> None:
        """Enable OpenStack Telemetry applications."""
        super().enable_plugin()

    @click.command()
    def disable_plugin(self) -> None:
        """Disable OpenStack Telemetry applications."""
        super().disable_plugin()
