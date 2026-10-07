window.RAMBLE_TUTORIAL_DATA = {
  "tutorials": {
    "hello_world": {
      "title": "Hello World",
      "url": "tutorials/1_hello_world.html",
      "level": "Beginner",
      "duration": "10 min",
      "description": "Learn how to create a workspace, configure a basic experiment, and execute it.",
      "order_rank": 10
    },
    "gromacs_simple": {
      "title": "Running a Simple GROMACS Experiment",
      "url": "tutorials/2_running_a_simple_gromacs_experiment.html",
      "level": "Beginner",
      "duration": "15 min",
      "description": "Execute a real scientific application, manage input files, and analyze figures of merit.",
      "order_rank": 20
    },
    "gromacs_modify": {
      "title": "Modifying a GROMACS Experiment",
      "url": "tutorials/3_modifying_a_gromacs_experiment.html",
      "level": "Beginner",
      "duration": "15 min",
      "description": "Override workload variables, customize commands, and adjust experiment configurations.",
      "order_rank": 30
    },
    "vectors_matrices": {
      "title": "Using Vectors and Matrices",
      "url": "tutorials/4_using_vectors_and_matrices.html",
      "level": "Intermediate",
      "duration": "20 min",
      "description": "Explore parameter spaces and generate combinatorial experiments with vectors and matrices.",
      "order_rank": 40
    },
    "software_stack": {
      "title": "Changing Your Software Stack",
      "url": "tutorials/5_changing_your_software_stack.html",
      "level": "Intermediate",
      "duration": "20 min",
      "description": "Configure Spack software stacks, customize compilers, and manage package variants.",
      "order_rank": 50
    },
    "scaling_study": {
      "title": "Configuring a Scaling Study",
      "url": "tutorials/6_configuring_a_scaling_study.html",
      "level": "Intermediate",
      "duration": "25 min",
      "description": "Set up scaling experiments across nodes, MPI processes, and OpenMP threads with WRF.",
      "order_rank": 60
    },
    "zips_matrices": {
      "title": "Using Zips and Matrices",
      "url": "tutorials/7_using_zips_and_matrices.html",
      "level": "Advanced",
      "duration": "20 min",
      "description": "Coordinate coupled parameters across multi-dimensional grids without full Cartesian explosion.",
      "order_rank": 70
    },
    "var_expansion": {
      "title": "Variable Expansion, Indirection & Stack Parameterization",
      "url": "tutorials/8_var_expansion_indirection_and_stack_parameterization.html",
      "level": "Advanced",
      "duration": "20 min",
      "description": "Leverage dynamic variable evaluation, double-indirection, and stack parameterizations.",
      "order_rank": 80
    },
    "success_criteria": {
      "title": "Success Criteria",
      "url": "tutorials/9_success_criteria.html",
      "level": "Intermediate",
      "duration": "15 min",
      "description": "Define automated pass/fail validation rules and ensure benchmark data integrity.",
      "order_rank": 90
    },
    "modifiers": {
      "title": "Using Modifiers",
      "url": "tutorials/10_using_modifiers.html",
      "level": "Intermediate",
      "duration": "25 min",
      "description": "Inject profilers (perf, Caliper), monitors, and execution hooks across experiments.",
      "order_rank": 100
    },
    "internals": {
      "title": "Using Internals",
      "url": "tutorials/11_using_internals.html",
      "level": "Advanced",
      "duration": "15 min",
      "description": "Access Ramble's internal variables and inject custom shell scripts and hooks.",
      "order_rank": 110
    },
    "mirrors": {
      "title": "Managing Mirrors",
      "url": "tutorials/mirrors.html",
      "level": "Intermediate",
      "duration": "15 min",
      "description": "Create and manage offline mirrors for software tarballs and experiment input files.",
      "order_rank": 120
    },
    "eessi": {
      "title": "EESSI Package Manager",
      "url": "tutorials/EESSI_package_manager.html",
      "level": "Intermediate",
      "duration": "15 min",
      "description": "Leverage pre-optimized scientific software from the EESSI repository in your workspaces.",
      "order_rank": 130
    },
    "workspace_config_cmd": {
      "title": "Workspace Config Command",
      "url": "tutorials/Workspace_config_command.html",
      "level": "Beginner",
      "duration": "10 min",
      "description": "Inspect, view, and modify workspace configuration files directly from the command line.",
      "order_rank": 140
    },
    "workspace_manage_cmd": {
      "title": "Workspace Manage Experiments Command",
      "url": "tutorials/Workspace_manage_experiments_command.html",
      "level": "Intermediate",
      "duration": "15 min",
      "description": "Add, modify, and manage experiments across workloads using the CLI.",
      "order_rank": 150
    },
    "dev_basic_app": {
      "title": "Basic Application Definition",
      "url": "dev_guides/1_basic_application_definition_tutorial.html",
      "level": "Developer",
      "duration": "30 min",
      "description": "Author new Python application definitions using Ramble directives, executables, and workloads.",
      "order_rank": 200
    },
    "dev_hpl_app": {
      "title": "HPL Application Definition",
      "url": "dev_guides/2_hpl_application_definition_tutorial.html",
      "level": "Developer",
      "duration": "30 min",
      "description": "Develop complex definitions featuring template generation, FOM extractors, and software specs.",
      "order_rank": 210
    },
    "dev_utility": {
      "title": "Utility Definition Tutorial",
      "url": "dev_guides/3_utility_definition_tutorial.html",
      "level": "Developer",
      "duration": "20 min",
      "description": "Build reusable utility objects to share execution logic across applications.",
      "order_rank": 220
    },
    "dev_system_platform": {
      "title": "System and Platform Definitions",
      "url": "dev_guides/system_and_platform_definition_tutorial.html",
      "level": "Developer",
      "duration": "25 min",
      "description": "Define system topologies and platform specifications for multi-architecture deployments.",
      "order_rank": 230
    }
  },
  "goals": {
    "scaling_study": {
      "title": "Perform a Scaling Study",
      "icon": "\ud83d\udcc8",
      "description": "Scale applications across nodes, MPI ranks, and OpenMP threads using vectors and matrices.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "gromacs_modify",
        "vectors_matrices",
        "scaling_study",
        "zips_matrices"
      ]
    },
    "profiling_modifiers": {
      "title": "Profile & Instrument Benchmarks",
      "icon": "\u23f1\ufe0f",
      "description": "Inject profilers (Caliper, perf, etc.), monitors, and execution hooks via modifiers without modifying applications.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "gromacs_modify",
        "modifiers"
      ]
    },
    "software_management": {
      "title": "Customize Software Stacks & Package Managers",
      "icon": "\ud83d\udce6",
      "description": "Manage Spack specs, compiler matrices, software stacks, and alternate managers like EESSI.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "software_stack",
        "eessi"
      ]
    },
    "metrics_validation": {
      "title": "Validate Runs & Define Success Criteria",
      "icon": "\ud83c\udfaf",
      "description": "Automate benchmark validation, assert exit criteria, and verify figure-of-merit thresholds.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "success_criteria"
      ]
    },
    "parameter_sweeps": {
      "title": "Advanced Parameter Sweeps & Variable Expansion",
      "icon": "\ud83c\udf9b\ufe0f",
      "description": "Master multi-dimensional matrices, parameter zips, dynamic variable indirection, and shell internals.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "vectors_matrices",
        "zips_matrices",
        "var_expansion",
        "internals"
      ]
    },
    "cli_automation": {
      "title": "Automate Workspaces via the CLI",
      "icon": "\ud83d\udcbb",
      "description": "Use CLI manage commands to script experiment generation, workload filtering, and configuration updates.",
      "tutorials": [
        "hello_world",
        "workspace_config_cmd",
        "workspace_manage_cmd"
      ]
    },
    "offline_mirrors": {
      "title": "Manage Offline & Air-Gapped Mirrors",
      "icon": "\ud83e\ude9e",
      "description": "Cache software source tarballs and input datasets to run experiments without internet access.",
      "tutorials": [
        "hello_world",
        "mirrors"
      ]
    },
    "author_applications": {
      "title": "Author New Application Definitions",
      "icon": "\ud83d\udee0\ufe0f",
      "description": "Extend Ramble by writing custom application classes, defining executables, workloads, and FOMs.",
      "tutorials": [
        "hello_world",
        "gromacs_simple",
        "dev_basic_app",
        "dev_hpl_app"
      ]
    },
    "author_infrastructure": {
      "title": "Extend Utilities, Systems & Platforms",
      "icon": "\u2699\ufe0f",
      "description": "Write reusable utilities, system topology definitions, and platform managers.",
      "tutorials": [
        "hello_world",
        "dev_utility",
        "dev_system_platform"
      ]
    }
  }
};
