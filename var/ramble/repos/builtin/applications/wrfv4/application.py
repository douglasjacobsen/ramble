# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import os
from ramble.appkit import *
from ramble.expander import Expander


class Wrfv4(ExecutableApplication):
    """Define Wrf version 4 application"""

    name = "wrfv4"

    maintainers("douglasjacobsen")

    tags("nwp", "weather")

    define_compiler("gcc9", pkg_spec="gcc@9.3.0", package_manager="spack*")

    software_spec(
        "intel-mpi",
        pkg_spec="intel-mpi@2018.4.274",
        compiler="gcc9",
        package_manager="spack*",
    )

    software_spec(
        "wrfv4",
        pkg_spec="wrf@4.2 build_type=dm+sm compile_type=em_real nesting=basic ~chem ~pnetcdf",
        compiler="gcc9",
        package_manager="spack*",
    )

    required_package("wrf", package_manager="spack*")

    input_file(
        "CONUS_2p5km",
        url="https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus2.5km.tar.gz",
        sha256="dcae9965d1873c1c1e34e21ad653179783302b9a13528ac10fab092b998578f6",
        description="2.5 km resolution mesh of the continental United States.",
    )

    input_file(
        "CONUS_12km",
        url="https://www2.mmm.ucar.edu/wrf/users/benchmark/v422/v42_bench_conus12km.tar.gz",
        sha256="6a0e87e3401efddc50539e71e5437fd7a5af9228b64cd4837e739737c3706fc3",
        description="12 km resolution mesh of the continental United States.",
    )

    executable(
        "cleanup",
        "rm -f rsl.* wrfout*",
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable(
        "copy",
        template=[
            "cp -R {input_path}/* {experiment_run_dir}/.",
            "ln -s {wrf_path}/run/* {experiment_run_dir}/.",
        ],
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable(
        "fix_12km",
        template=[
            "sed -i -e 's/ start_hour.*/ start_hour                          = 23,/g' namelist.input",
            "sed -i -e 's/ restart .*/ restart                             = .true.,/g' namelist.input",
        ],
        use_mpi=False,
        output_capture=OUTPUT_CAPTURE.ALL,
    )
    executable("execute", "wrf.exe", use_mpi=True)

    workload(
        "CONUS_2p5km",
        executables=["cleanup", "copy", "execute"],
        input="CONUS_2p5km",
    )

    workload(
        "CONUS_12km",
        executables=["cleanup", "copy", "fix_12km", "execute"],
        input="CONUS_12km",
    )

    workload_variable(
        "input_path",
        default="{CONUS_12km}",
        description="Path for CONUS 12km inputs.",
        workloads=["CONUS_12km"],
    )

    workload_variable(
        "input_path",
        default="{CONUS_2p5km}",
        description="Path for CONUS 2.5km inputs.",
        workloads=["CONUS_2p5km"],
    )

    log_str = os.path.join(
        Expander.expansion_str("experiment_run_dir"), "stats.out"
    )

    figure_of_merit(
        "Average Timestep Time",
        log_file=log_str,
        fom_regex=r"Average time:\s+(?P<avg_time>[0-9]+\.[0-9]*).*",
        group_name="avg_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Cumulative Timestep Time",
        log_file=log_str,
        fom_regex=r"Cumulative time:\s+(?P<total_time>[0-9]+\.[0-9]*).*",
        group_name="total_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Minimum Timestep Time",
        log_file=log_str,
        fom_regex=r"Min time:\s+(?P<min_time>[0-9]+\.[0-9]*).*",
        group_name="min_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Maximum Timestep Time",
        log_file=log_str,
        fom_regex=r"Max time:\s+(?P<max_time>[0-9]+\.[0-9]*).*",
        group_name="max_time",
        units="s",
        fom_type=FomType.TIME,
    )

    figure_of_merit(
        "Number of timesteps",
        log_file=log_str,
        fom_regex=r"Number of times:\s+(?P<count>[0-9]+)",
        group_name="count",
        units="",
        fom_type=FomType.MEASURE,
    )

    figure_of_merit(
        "Avg. Max Ratio Time",
        log_file=log_str,
        fom_regex=r"Avg time / Max time:\s+(?P<avg_max_ratio>[0-9]+\.[0-9]*).*",
        group_name="avg_max_ratio",
        units="",
        fom_type=FomType.MEASURE,
    )

    success_criteria(
        "Complete",
        mode="string",
        match=r".*wrf: SUCCESS COMPLETE WRF.*",
        file="{experiment_run_dir}/rsl.out.0000",
    )

    archive_pattern("{experiment_run_dir}/rsl.out.*")
    archive_pattern("{experiment_run_dir}/rsl.error.*")

    def _analyze_experiments(self, workspace, app_inst=None):
        import glob
        import re

        # Generate stats file

        file_list = glob.glob(
            os.path.join(
                self.expander.expand_var_name("experiment_run_dir"),
                "rsl.out.*",
            )
        )

        if file_list:
            timing_regex = re.compile(
                r"Timing for main.*:\s+(?P<main_time>[0-9]+\.[0-9]*).*"
            )
            avg_time = 0.0
            min_time = float("inf")
            max_time = float("-inf")
            sum_time = 0.0
            count = 0
            for out_file in file_list:
                with open(out_file) as f:
                    for line in f.readlines():
                        m = timing_regex.match(line)
                        if m:
                            time = float(m.group("main_time"))
                            count += 1
                            sum_time += time
                            min_time = min(min_time, time)
                            max_time = max(max_time, time)

            avg_time = sum_time / max(count, 1)

            stats_path = os.path.join(
                self.expander.expand_var_name("experiment_run_dir"),
                "stats.out",
            )
            with open(stats_path, "w+") as f:
                f.write("Average time: %s s\n" % (avg_time))
                f.write("Cumulative time: %s s\n" % (sum_time))
                f.write("Min time: %s s\n" % (min_time))
                f.write("Max time: %s s\n" % (max_time))
                f.write(
                    "Avg time / Max time: %s s\n"
                    % (avg_time / max(max_time, float(1.0)))
                )
                f.write("Number of times: %s\n" % (count))

        super()._analyze_experiments(workspace)
