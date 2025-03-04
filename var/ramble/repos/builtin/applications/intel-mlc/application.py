# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.appkit import *


class IntelMlc(ExecutableApplication):
    """"""

    name = "intel-mlc"

    maintainers("douglasjacobsen")

    tags("benchmark-app", "mini-app", "benchmark")

    required_package("intel-mlc")

    executable(
        "execute_bw",
        "{intel-mlc_path}/{exec_name} --max_bandwidth {isa_flag} -k{cpu_list} -b{buffer_size} {additional_args}",
    )

    workload("max_bandwidth", executables=["execute_bw"])

    workload_group("all_workloads", workloads=["max_bandwidth"])

    workload_variable(
        "exec_name",
        default="mlc",
        values=["mlc", "mlc.exe"],
        description="Name of executable to use for Intel MLC",
        workload_group="all_workloads",
    )

    workload_variable(
        "cpu_list",
        default="",
        description="Comma delimited list of CPUs to run tests with. Defined by application if omitted from an experiment definition.",
        workload_group="all_workloads",
    )

    workload_variable(
        "additional_args",
        default="",
        description="Additional command line arguments for the mlc binary",
        workload_group="all_workloads",
    )

    workload_variable(
        "cores_per_node",
        default="{processes_per_node}",
        description="Maximum number of cores to use per node when generating cpu_list",
        workload_group="all_workloads",
    )

    workload_variable(
        "thread_distribution",
        default="spread",
        values=["spread", "compact"],
        description="Thread distribution method when generating cpu_list",
        workload_group="all_workloads",
    )

    workload_variable(
        "isa_flag",
        default="-Z",
        values=["-Y", "-Z"],
        description="Flag for controlling the vector instructions used.",
        workload_group="all_workloads",
    )

    workload_variable(
        "buffer_size",
        default="1g",
        description="Size of buffer per thread",
        workload_group="all_workloads",
    )

    workload_variable(
        "spread_divisions",
        default="2",
        description="Number of blocks to spread threads over",
        workload_group="all_workloads",
    )

    figure_of_merit(
        "All Read Bandwidth",
        fom_regex=r"ALL Reads\s*:\s+(?P<bw>[0-9\.]+)",
        group_name="bw",
        units="MB/s",
    )

    figure_of_merit(
        "3:1 Reads-Write Bandwidth",
        fom_regex=r"3:1 Reads-Writes\s*:\s+(?P<bw>[0-9\.]+)",
        group_name="bw",
        units="MB/s",
    )

    figure_of_merit(
        "2:1 Reads-Write Bandwidth",
        fom_regex=r"2:1 Reads-Writes\s*:\s+(?P<bw>[0-9\.]+)",
        group_name="bw",
        units="MB/s",
    )

    figure_of_merit(
        "1:1 Reads-Write Bandwidth",
        fom_regex=r"1:1 Reads-Writes\s*:\s+(?P<bw>[0-9\.]+)",
        group_name="bw",
        units="MB/s",
    )

    figure_of_merit(
        "Triad Bandwidth",
        fom_regex=r"Stream-triad like\s*:\s+(?P<bw>[0-9\.]+)",
        group_name="bw",
        units="MB/s",
    )

    def _compact_thread_indices(self, n_threads, max_thread, spread_divisions):
        if n_threads > max_thread:
            logger.die(
                f"Error creating compact threads. {n_threads} requested, but max thread id is {max_thread}"
            )

        threads = []
        for i in range(0, n_threads):
            threads.append(str(i))
        return threads

    def _spread_thread_indices(self, n_threads, max_thread, spread_divisions):
        if n_threads > max_thread:
            logger.die(
                f"Error creating spread threads. {n_threads} requested, but max thread id is {max_thread}"
            )

        threads = []
        cur_indices = []
        numa_index = 0
        for i in range(0, spread_divisions):
            cur_indices.append(numa_index)
            numa_index += max_thread // spread_divisions

        defined_threads = 0
        cur_node = 0
        while defined_threads < n_threads:
            threads.append(str(cur_indices[cur_node]))
            cur_indices[cur_node] += 1
            defined_threads += 1

            cur_node = (cur_node + 1) % spread_divisions
        return threads

    def add_expand_vars(self, workspace):
        if not self._vars_are_expanded:
            self._generate_input_file(workspace, self)
            super().add_expand_vars(workspace)

    def _generate_input_file(self, workspace, app_inst=None):
        workload = app_inst.workloads[app_inst.expander.workload_name]

        thread_dist = app_inst.expander.expand_var_name("thread_distribution")
        if thread_dist == "{thread_distribution}":
            thread_dist = workload.variables["thread_distribution"].default

        ppn = int(app_inst.expander.expand_var_name("processes_per_node"))
        n_threads = int(app_inst.expander.expand_var_name("n_threads"))

        spread_divisions = app_inst.expander.expand_var_name(
            "spread_divisions"
        )
        if spread_divisions == "{spread_divisions}":
            spread_divisions = workload.variables["spread_divisions"].default

        try:
            spread_divisions = int(spread_divisions)
        except ValueError:
            logger.die(f" Spread divisions was: {spread_divisions}")
        n_nodes = int(app_inst.expander.expand_var_name("n_nodes"))
        cpu_list = app_inst.expander.expand_var_name("cpu_list")

        if cpu_list != "{cpu_list}":
            return

        if n_nodes > 1:
            logger.warn(
                f"The {self.name} application is intended to be used on a single "
                f"node, but is configured with n_nodes = {n_nodes}"
            )

        if thread_dist == "compact":
            thread_list = self._compact_thread_indices(
                n_threads, ppn, spread_divisions
            )
        elif thread_dist == "spread":
            thread_list = self._spread_thread_indices(
                n_threads, ppn, spread_divisions
            )
        else:
            logger.die(
                "Unsupported thread distribution method requested. Options are 'spread' and 'compact'"
            )

        thread_str = ",".join(thread_list)
        app_inst.define_variable("cpu_list", thread_str)
