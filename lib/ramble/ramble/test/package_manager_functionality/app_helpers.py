# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


def config_for_app(app_name, pkg_man_name="None"):
    import ramble.repository

    app_inst = ramble.repository.get(app_name)

    base_config = """ramble:
  variables:
    mpi_command: 'mpirun -n {n_ranks}'
    batch_submit: '{execute_experiment}'
  applications:\n"""

    base_config += f"""    {app_name}:
      workloads:\n"""

    for workload in app_inst.workloads:
        base_config += f"""        {workload.strip()}:
          experiments:
            test_experiment:
              variables:
                n_ranks: '1'
                n_nodes: '1'
                processes_per_node: '1'\n"""
        if pkg_man_name == "None":
            for pkg in app_inst.required_packages.keys():
                base_config += f"                {pkg}_path: '/not/real/path'\n"

    base_config += """  software:
    packages: {}
    environments: {}\n"""

    base_config += f"""  variants:
    package_manager: {pkg_man_name}\n"""

    return base_config


def dryrun_app_workloads(app_name, pkg_man_name):
    import os
    import ramble.filters
    import ramble.pipeline

    setup_type = ramble.pipeline.pipelines.setup
    analyze_type = ramble.pipeline.pipelines.analyze
    archive_type = ramble.pipeline.pipelines.archive
    setup_cls = ramble.pipeline.pipeline_class(setup_type)
    analyze_cls = ramble.pipeline.pipeline_class(analyze_type)
    archive_cls = ramble.pipeline.pipeline_class(archive_type)
    filters = ramble.filters.Filters()

    ws_name = f"test_app_{app_name}_pkgman_{pkg_man_name}"

    with ramble.workspace.create(ws_name) as ws:
        ws.write()
        config_path = os.path.join(ws.config_dir, ramble.workspace.config_file_name)

        with open(config_path, "w+") as f:
            f.write(config_for_app(app_name, pkg_man_name))

        ws._re_read()
        ws.concretize()
        ws._re_read()
        ws.dry_run = True
        setup_pipeline = setup_cls(ws, filters)
        setup_pipeline.run()
        analyze_pipeline = analyze_cls(ws, filters)
        analyze_pipeline.run()
        archive_pipeline = archive_cls(ws, filters, create_tar=True)
        archive_pipeline.run()
