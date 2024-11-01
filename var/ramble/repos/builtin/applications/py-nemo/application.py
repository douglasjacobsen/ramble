# Copyright 2022-2024 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.


import os
import re
from ramble.appkit import *

import ruamel.yaml as yaml

import ramble.util.yaml_generation


class PyNemo(ExecutableApplication):
    """A scalable generative AI framework built for researchers and
    developers working on Large Language Models, Multimodal, and
    Speech AI (Automatic Speech Recognition and Text-to-Speech)"""

    name = "py-nemo"

    maintainers("douglasjacobsen")

    tags("ml-framework", "machine-learning")

    executable(
        "setup_transformer_cache",
        'bash -c "python3 -c \'from transformers import AutoTokenizer; AutoTokenizer.from_pretrained(\\"gpt2\\")\'"',
        use_mpi=True,
    )

    executable(
        "pretraining_exec",
        'bash -c "cd /opt/NeMo; git rev-parse HEAD; export PYTHONPATH=/opt/NeMo:\${PYTHONPATH}; '
        "CUDA_VISIBLE_DEVICES={cuda_visible_devices} "
        "python3 -u /opt/NeMo/examples/nlp/language_modeling/megatron_gpt_pretraining.py "
        '--config-path={nemo_generated_config_path} --config-name={nemo_generated_config_name}"',
        use_mpi=True,
    )

    executable(
        "create_logs", "mkdir {exp_manager.explicit_log_dir}", use_mpi=False
    )

    input_file(
        "nemo_fetched_config",
        url="https://raw.githubusercontent.com/NVIDIA/NeMo-Framework-Launcher/refs/tags/{nemo_launcher_tag}/launcher_scripts/conf/{nemo_stage}/{nemo_model}/{nemo_config_name}.yaml",
        expand=False,
        target_dir="{model_inputs}",
        description="Base config for NeMo experiments",
    )

    workload(
        "pretraining",
        executables=[
            "create_logs",
            "setup_transformer_cache",
            "pretraining_exec",
        ],
        inputs=["nemo_fetched_config"],
    )

    default_config_string = "{default_config_value}"

    workload_group("all_workloads", workloads=["pretraining"])
    workload_group("pretraining", workloads=["pretraining"])
    all_workloads = ["pretraining"]

    workload_variable(
        "model_inputs",
        default="{workload_input_dir}/{nemo_stage}/{nemo_model}",
        description="NeMo model input directory",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_container_version",
        default="24.07",
        description="Version for NeMo container",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_launcher_tag",
        default="24.07",
        description="Tag of NeMo-Framework-Launcher repo to extract inputs from",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_stage",
        default="training",
        description="Stage to run in NeMo",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_model",
        default="gpt3",
        description="Model to run in NeMo",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_config_name",
        default="5b",
        description="Configuration name to run in NeMo. This is the name of the input "
        + "yaml file without the extension. e.g. 5b.yaml -> 5b, while "
        + "mixtral_8x22b.yaml -> mixtral_8x22b",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_base_config",
        default="{nemo_fetched_config}",
        description="Path to base config used for generating experiments. "
        + "Defaults to the fetched input, but can refer to a provided input.",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_generated_config_name",
        default="nemo.yaml",
        description="Name of nemo config file",
        workload_group="all_workloads",
    )

    workload_variable(
        "nemo_generated_config_path",
        default="{experiment_run_dir}",
        description="Path where nemo config file is contained",
        workload_group="all_workloads",
    )

    workload_variable(
        "cuda_visible_devices",
        default="0,1,2,3,4,5,6,7",
        description="Comma delimited list of CUDA device IDs.",
        workload_group="all_workloads",
    )
    environment_variable(
        "CUDA_VISIBLE_DEVICES",
        value="{cuda_visible_devices}",
        description="Comma delimited list of CUDA device IDs",
        workloads=all_workloads,
    )

    workload_variable(
        "transformers_offline",
        default="0",
        description="Whether transformers are offline (0) or not (1)",
        workload_group="all_workloads",
    )
    environment_variable(
        "TRANSFORMERS_OFFLINE",
        value="{transformers_offline}",
        description="Whether transformers are offline (0) or not (1)",
        workloads=all_workloads,
    )

    workload_variable(
        "torch_nccl_avoid_record_streams",
        default="1",
        description="Avoid (1) recording streams for Torch NCCL, or not (0)",
        workload_group="all_workloads",
    )
    environment_variable(
        "TORCH_NCCL_AVOID_RECORD_STREAMS",
        value="{torch_nccl_avoid_record_streams}",
        description="Avoid (1) recording streams for Torch NCCL, or not (0)",
        workloads=all_workloads,
    )

    workload_variable(
        "nccl_nvls_enable",
        default="0",
        description="Enable (1) NCCL NVLS or not (0)",
        workload_group="all_workloads",
    )
    environment_variable(
        "NCCL_NVLS_ENABLE",
        value="{nccl_nvls_enable}",
        description="Enable (1) NCCL NVLS or not (0)",
        workloads=all_workloads,
    )

    workload_variable(
        "results_mount",
        default="{experiment_run_dir}:{experiment_run_dir}",
        description="Container mount for results data",
        workload_group="all_workloads",
    )
    workload_variable(
        "logs_mount",
        default="{exp_manager.explicit_log_dir}:{exp_manager.explicit_log_dir}",
        description="Container mount for results data",
        workload_group="all_workloads",
    )
    environment_variable(
        "NEMO_CONTAINER_MOUNTS",
        value="{logs_mount},{results_mount}",
        description="All container mounts in an environment variable",
        workloads=all_workloads,
    )
    workload_variable(
        "container_mounts",
        default="{logs_mount},{results_mount}",
        description="All container mounts in a ramble variable",
        workload_group="all_workloads",
    )

    environment_variable(
        "NEMO_HOST_VARS",
        value="TRANSFORMERS_OFFLINE,TORCH_NCCL_AVOID_RECORD_STREAMS,NCCL_NVLS_ENABLE,CUDA_VISIBLE_DEVICES",
        description="Host variables for NeMo",
        workloads=all_workloads,
    )

    # Hydra parameters
    workload_variable(
        "hydra.searchpath",
        default=default_config_string,
        description="Hydra search paths",
        workload_group="all_workloads",
    )

    # Run parameters
    workload_variable(
        "run.name",
        default="{nemo_model}_{nemo_config_name}",
        description="Name of run",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.results_dir",
        default="{experiment_run_dir}",
        description="Experiment results directory",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.time_limit",
        default="6-00:00:00",
        description="Experiment time limit",
        workload_group="all_workloads",
    )
    workload_variable(
        "run.dependency",
        default="singleton",
        description="Experiment dependency type",
        workload_group="all_workloads",
    )

    # Trainer parameters
    workload_variable(
        "trainer.num_nodes",
        default="{n_nodes}",
        description="Number of nodes",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.devices",
        default="{gpus_per_node}",
        description="Number of devices per node",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.accelerator",
        default="gpu",
        description="Accelerator to use as device",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.precision",
        default=default_config_string,
        description="Precision for trainer",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.logger",
        default=False,
        description="Whether logger is enabled or not",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.enable_checkpointing",
        default=False,
        description="Whether checkpointing is enabled or not",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.use_distributed_sampler",
        default=False,
        description="Whether distributed sampler is used or not",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.max_epochs",
        default=default_config_string,
        description="Max number of epochs in run",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.max_steps",
        default=default_config_string,
        description="Max number of steps",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.max_time",
        default=default_config_string,
        description="Max time of run",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.log_every_n_steps",
        default=default_config_string,
        description="Frequency of logging",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.val_check_interval",
        default=default_config_string,
        description="Value checking interval",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.limit_val_batches",
        default=default_config_string,
        description="Val batch limit",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.limit_test_batches",
        default=default_config_string,
        description="Test batch limit",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.accumulate_grad_batches",
        default=default_config_string,
        description="Batch size for accumulating gradients",
        workload_group="pretraining",
    )
    workload_variable(
        "trainer.gradient_clip_val",
        default=default_config_string,
        description="Clipping value for gradients",
        workload_group="pretraining",
    )

    # Exp manager parameters
    workload_variable(
        "exp_manager.explicit_log_dir",
        default="{experiment_run_dir}/nemo_logs",
        description="Log directory for exp manager",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.exp_dir",
        default=None,
        description="Experiment directory for exp manager",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.name",
        default="{nemo_stage}_{nemo_model}_{nemo_config_name}",
        description="Exp manager name",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.create_wandb_logger",
        default=False,
        description="Whether to create wandb logger or not",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.wandb_logger_kwargs.project",
        default="nemo_{nemo_model}",
        description="wandb logger project",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.wandb_logger_kwargs.name",
        default="{nemo_model}_{nemo_config_name}",
        description="wandb logger name",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.resume_if_exists",
        default=False,
        description="Whether to resume if a checkpoint exists already",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.resume_ignore_no_checkpoint",
        default=True,
        description="Whether to ignore resume if a checkpoint does not exist",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.create_checkpoint_callback",
        default=default_config_string,
        description="Whether to create a checkpoint callback or not",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.monitor",
        default=default_config_string,
        description="Variable to monitor for checkpoint callback",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.save_top_k",
        default=default_config_string,
        description="Top k saved of monitor values",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.mode",
        default="min",
        description="Mode for callback checkpoint",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.always_save_nemo",
        default=False,
        description="Whether nemo is always saved or not",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.save_nemo_on_train_end",
        default=False,
        description="Whether nemo is saved at end of training",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.filename",
        default="megatron_gpt--\{val_loss:.2f\}-\{step\}-\{consumed_samples\}",
        description="Filename for checkpoint params",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.checkpoint_callback_params.model_parallel_size",
        default="{model.tensor_model_parallel_size}*{model.pipeline_model_parallel_size}",
        description="Parallel size",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.log_step_timing",
        default=True,
        description="Timing of logging",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.step_timing_kwargs.sync_cuda",
        default=True,
        description="Whether CUDA is synced or not",
        workload_group="pretraining",
    )
    workload_variable(
        "exp_manager.step_timing_kwargs.buffer_size",
        default=default_config_string,
        description="Size of buffer",
        workload_group="pretraining",
    )

    # Model parameters
    workload_variable(
        "model.micro_batch_size",
        default=default_config_string,
        description="Size of micro batches",
        workload_group="pretraining",
    )
    workload_variable(
        "model.global_batch_size",
        default=default_config_string,
        description="Global batch size",
        workload_group="pretraining",
    )
    workload_variable(
        "model.rampup_batch_size",
        default=default_config_string,
        description="Rampup batch size",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tensor_model_parallel_size",
        default=default_config_string,
        description="Parallel size of tensor model",
        workload_group="pretraining",
    )
    workload_variable(
        "model.pipeline_model_parallel_size",
        default=default_config_string,
        description="Parallel size of pipeline model",
        workload_group="pretraining",
    )
    workload_variable(
        "model.virtual_pipeline_model_parallel_size",
        default=default_config_string,
        description="Parallel size of Virtual Pipeline model",
        workload_group="pretraining",
    )
    workload_variable(
        "model.resume_from_checkpoint",
        default=default_config_string,
        description="",
        workload_group="pretraining",
    )
    workload_variable(
        "model.encoder_seq_length",
        default=default_config_string,
        description="Sequence length for encoder",
        workload_group="pretraining",
    )
    workload_variable(
        "model.max_position_embeddings",
        default=default_config_string,
        description="Max position embeddings",
        workload_group="pretraining",
    )
    workload_variable(
        "model.num_layers",
        default=default_config_string,
        description="Number of layers",
        workload_group="pretraining",
    )
    workload_variable(
        "model.hidden_size",
        default=default_config_string,
        description="Hidden size",
        workload_group="pretraining",
    )
    workload_variable(
        "model.ffn_hidden_size",
        default="{4*{model.hidden_size}}",
        description="FFN Hidden Size",
        workload_group="pretraining",
    )
    workload_variable(
        "model.num_attention_heads",
        default=default_config_string,
        description="Number of attention heads",
        workload_group="pretraining",
    )
    workload_variable(
        "model.init_method_std",
        default=default_config_string,
        description="Init Method Std",
        workload_group="pretraining",
    )
    workload_variable(
        "model.hidden_dropout",
        default=default_config_string,
        description="Hidden dropout",
        workload_group="pretraining",
    )
    workload_variable(
        "model.attention_dropout",
        default=default_config_string,
        description="Attention dropout",
        workload_group="pretraining",
    )
    workload_variable(
        "model.kv_channels",
        default=default_config_string,
        description="KV Channels",
        workload_group="pretraining",
    )
    workload_variable(
        "model.apply_query_key_layer_scaling",
        default=default_config_string,
        description="Whether to apply query key layer scaling or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.layernorm_epsilon",
        default=default_config_string,
        description="Epislon for Layer Normalization",
        workload_group="pretraining",
    )
    workload_variable(
        "model.make_vocab_size_divisible_by",
        default=default_config_string,
        description="Ensure vocab size is divisible by this",
        workload_group="pretraining",
    )
    workload_variable(
        "model.pre_process",
        default=default_config_string,
        description="Whether to pre-process or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.post_process",
        default=default_config_string,
        description="Whether to post-process or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.persist_layer_norm",
        default=default_config_string,
        description="Whether layer norms persist or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.gradient_as_bucket_view",
        default=default_config_string,
        description="Gradient as bucket view",
        workload_group="pretraining",
    )
    workload_variable(
        "model.grad_div_ar_fusion",
        default=default_config_string,
        description="Gradient div ar fusion",
        workload_group="pretraining",
    )
    workload_variable(
        "model.gradient_accumulation_fusion",
        default=default_config_string,
        description="Gradient accumulation fusion",
        workload_group="pretraining",
    )
    workload_variable(
        "model.bias_activation_fusion",
        default=default_config_string,
        description="Bias activation fusion",
        workload_group="pretraining",
    )
    workload_variable(
        "model.bias_dropout_add_fusion",
        default=default_config_string,
        description="Bias Dropout add fusion",
        workload_group="pretraining",
    )
    workload_variable(
        "model.masked_softmax_fusion",
        default=default_config_string,
        description="Masked Softmax Fusion",
        workload_group="pretraining",
    )
    workload_variable(
        "model.activations_checkpoint_granularity",
        default=default_config_string,
        description="Granularity of checkpoint activations",
        workload_group="pretraining",
    )
    workload_variable(
        "model.activations_checkpoint_method",
        default=default_config_string,
        description="Method of checkpoint activations",
        workload_group="pretraining",
    )
    workload_variable(
        "model.activations_checkpoint_num_layers",
        default=default_config_string,
        description="Number of layers for checkpoitn activation",
        workload_group="pretraining",
    )
    workload_variable(
        "model.num_micro_batches_with_partial_activation_checkpoints",
        default=default_config_string,
        description="Number of micro batches with partial activation checkpoints",
        workload_group="pretraining",
    )
    workload_variable(
        "model.activations_checkpoint_layers_per_pipeline",
        default=default_config_string,
        description="Activations checkpoint layer per pipeline",
        workload_group="pretraining",
    )
    workload_variable(
        "model.sequence_parallel",
        default=default_config_string,
        description="Whether to sequence in parallel or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.overlap_p2p_comm",
        default=default_config_string,
        description="Whether to overlap P2P Comms",
        workload_group="pretraining",
    )
    workload_variable(
        "model.batch_p2p_comm",
        default=default_config_string,
        description="Whether to batch P2P Comms",
        workload_group="pretraining",
    )
    workload_variable(
        "model.num_query_groups",
        default=default_config_string,
        description="Number of query groups",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tokenizer.library",
        default=default_config_string,
        description="Tokenizer library",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tokenizer.type",
        default=default_config_string,
        description="Tokenizer Type",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tokenizer.model",
        default=default_config_string,
        description="Tokenizer Model",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tokenizer.delimiter",
        default=default_config_string,
        description="Tokenizer Delimiter",
        workload_group="pretraining",
    )
    workload_variable(
        "model.native_amp_init_scale",
        default=default_config_string,
        description="Scale for initial native applification",
        workload_group="pretraining",
    )
    workload_variable(
        "model.native_amp_growth_interval",
        default=default_config_string,
        description="Growth intervale for native aplification",
        workload_group="pretraining",
    )
    workload_variable(
        "model.hysteresis",
        default=default_config_string,
        description="Hysteresis",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp32_residual_connection",
        default=default_config_string,
        description="FP32 Residual Connection",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp16_lm_cross_entropy",
        default=default_config_string,
        description="FP16 LM Cross Entropy",
        workload_group="pretraining",
    )
    workload_variable(
        "model.megatron_amp_O2",
        default=default_config_string,
        description="Megatron Apm O2",
        workload_group="pretraining",
    )
    workload_variable(
        "model.grad_allreduce_chunk_size_mb",
        default=default_config_string,
        description="Chunk Size (MB) for gradient all reduce",
        workload_group="pretraining",
    )
    workload_variable(
        "model.mcore_gpt",
        default=default_config_string,
        description="MCore GPT",
        workload_group="pretraining",
    )
    workload_variable(
        "model.transformer_engine",
        default=default_config_string,
        description="Transformer Engine",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8",
        default=default_config_string,
        description="FP8",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_e4m3",
        default=default_config_string,
        description="FP8 E4M3",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_hybrid",
        default=default_config_string,
        description="FP8 Hybrid",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_margin",
        default=default_config_string,
        description="FP8 Margin",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_interval",
        default=default_config_string,
        description="FP8 Interval",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_amax_history_len",
        default=default_config_string,
        description="FP8 Max History Length",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_amax_compute_algo",
        default=default_config_string,
        description="FP8 Max Compute Algorithm",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fp8_wgrad",
        default=default_config_string,
        description="FP8 Wgrad",
        workload_group="pretraining",
    )
    workload_variable(
        "model.ub_tp_comm_overlap",
        default=default_config_string,
        description="UB TP Comm Overlap",
        workload_group="pretraining",
    )
    workload_variable(
        "model.seed",
        default=default_config_string,
        description="Model Seed",
        workload_group="pretraining",
    )
    workload_variable(
        "model.sync_batch_comm",
        default=default_config_string,
        description="Whether to sync batch comms or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.use_cpu_initialization",
        default=default_config_string,
        description="Whether to use CPU for init or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.onnx_safe",
        default=default_config_string,
        description="Onnx Safe",
        workload_group="pretraining",
    )
    workload_variable(
        "model.apex_transformer_log_level",
        default=default_config_string,
        description="Apex Transformer Log Level",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.enabled",
        default=False,
        description="Whether nsys is enabled to profile",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.start_step",
        default=default_config_string,
        description="Step to start profiling at",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.end_step",
        default=default_config_string,
        description="Step to end profiling at",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.gen_shape",
        default=default_config_string,
        description="Shape generation for profiling",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.trace",
        default=default_config_string,
        description="Nsys profile trace options",
        workload_group="pretraining",
    )
    workload_variable(
        "model.nsys_profile.ranks",
        default=default_config_string,
        description="Ranks to profile with Nsys",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.name",
        default=default_config_string,
        description="Name of model optim",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.betas",
        default=default_config_string,
        description="Model optimization betas",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.bucket_cap_mb",
        default=default_config_string,
        description="Bucket capacity in MB",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.grad_sync_dtype",
        default=default_config_string,
        description="Gradient sync dtype",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.overlap_grad_sync",
        default=default_config_string,
        description="Gradient sync overlapping",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.overlap_param_sync",
        default=default_config_string,
        description="Param sync overlapping",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.contiguous_grad_buffer",
        default=default_config_string,
        description="Continuous gradient buffer",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.contiguous_param_buffer",
        default=default_config_string,
        description="Model optimization contiguous param buffer",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.lr",
        default=default_config_string,
        description="LR",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.weight_decay",
        default=default_config_string,
        description="Weight Decay",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.sched.name",
        default=default_config_string,
        description="Scheduler Name",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.sched.warmup_steps",
        default=default_config_string,
        description="Optim Scheduler warmup steps",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.sched.constant_steps",
        default=default_config_string,
        description="Optim Scheduler constant steps",
        workload_group="pretraining",
    )
    workload_variable(
        "model.optim.sched.min_lr",
        default=default_config_string,
        description="Minimum LR",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.data_impl",
        default=default_config_string,
        description="Data Implementation",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.data_prefix",
        default=default_config_string,
        description="Weighted data prefixes to use",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.splits_string",
        default=default_config_string,
        description="Splits String for Data",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.seq_length",
        default=default_config_string,
        description="Sequence Length",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.skip_warmup",
        default=default_config_string,
        description="Whether to skip warmup or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.num_workers",
        default=default_config_string,
        description="Number of data workers",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.dataloader_type",
        default=default_config_string,
        description="Dataloader type",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.reset_position_ids",
        default=default_config_string,
        description="Whether to reset position IDs or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.reset_attention_mask",
        default=default_config_string,
        description="Whether to reset attention mask or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.eod_mask_loss",
        default=default_config_string,
        description="EOD Mask loss",
        workload_group="pretraining",
    )
    workload_variable(
        "model.data.index_mapping_dir",
        default=default_config_string,
        description="Index Mapping Dir",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tp_comm_atomic_rs",
        default=default_config_string,
        description="Whether to enable TP comm atomic RS or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.tp_comm_atomic_ag",
        default=default_config_string,
        description="Whether to enable TP comm atomic AG or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.context_parallel_size",
        default=default_config_string,
        description="Context parallel size",
        workload_group="pretraining",
    )
    workload_variable(
        "model.sharp",
        default=default_config_string,
        description="Whether to enable sharp or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fsdp",
        default=default_config_string,
        description="Whether to enable fsdp or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fsdp_grad_reduce_dtype",
        default=default_config_string,
        description="Data type for gradient reduction in fsdp",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fsdp_sharded_checkpoint",
        default=default_config_string,
        description="Whether FSDP should use a sharded checkpoint or not",
        workload_group="pretraining",
    )
    workload_variable(
        "model.fsdp_sharding_strategy",
        default=default_config_string,
        description="Sharding strategy for fsdp",
        workload_group="pretraining",
    )

    processed_log_name = "{experiment_run_dir}/processed_{experiment_name}.out"

    final_epoch_regex = (
        r"Epoch (?P<epoch_id>[0-9]+):\s+:\s+(?P<pct_complete>[0-9]+)%.*\s+"
        + r"(?P<step_idx>[0-9]+)\/(?P<max_itr>[0-9]+) \[(?P<elapsed_time>[0-9]+:[0-9]+)<"
        + r"(?P<remaining_time>[0-9]+:[0-9]+),(\s+v_num=(?P<v_num>.*),)* reduced_train_loss="
        + r"(?P<reduced_train_loss>[0-9]+\.[0-9]+), global_step=(?P<global_step>[0-9]+\.[0-9]+), "
        + r"consumed_samples=(?P<consumed_samples>[0-9]+\.[0-9]+), train_step_timing in s="
        + r"(?P<train_step_timing>[0-9]+\.[0-9]+)(, val_loss=(?P<val_loss>[0-9]+\.[0-9]+))*\]"
    )

    figure_of_merit(
        "Final Epoch ID",
        fom_regex=final_epoch_regex,
        group_name="epoch_id",
        log_file=processed_log_name,
    )
    figure_of_merit(
        "Final Step ID",
        fom_regex=final_epoch_regex,
        group_name="step_idx",
        log_file=processed_log_name,
    )
    figure_of_merit(
        "Final Elapsed Time",
        fom_regex=final_epoch_regex,
        group_name="elapsed_time",
        log_file=processed_log_name,
    )
    figure_of_merit(
        "Final Elapsed Seconds",
        fom_regex=r"Elapsed seconds: (?P<seconds>[0-9]+)",
        group_name="seconds",
        log_file="{experiment_run_dir}/elapsed_seconds",
    )
    figure_of_merit(
        "Final Remaining Time",
        fom_regex=final_epoch_regex,
        group_name="remaining_time",
        log_file=processed_log_name,
    )
    figure_of_merit(
        "Final Step Timing",
        fom_regex=final_epoch_regex,
        group_name="train_step_timing",
        log_file=processed_log_name,
    )

    per_epoch_regex = (
        r"Epoch (?P<epoch_id>[0-9]+):\s+:\s+(?P<pct_complete>[0-9]+)%.*\s+"
        + r"(?P<step_idx>[0-9]+)/(?P<max_itr>[0-9]+) \[(?P<elapsed_time>[0-9:]+)<"
        + r"(?P<remaining_time>[0-9:]+).*"
    )

    epoch_context_name = "Epoch ID - Step ID"
    figure_of_merit_context(
        epoch_context_name,
        regex=per_epoch_regex,
        output_format="{epoch_id}-{step_idx}/{max_itr}",
    )
    figure_of_merit(
        "Epoch ID",
        fom_regex=per_epoch_regex,
        group_name="epoch_id",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Percent Complete",
        fom_regex=per_epoch_regex,
        group_name="pct_complete",
        units="%",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Step ID",
        fom_regex=per_epoch_regex,
        group_name="step_idx",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Elapsed Time",
        fom_regex=per_epoch_regex,
        group_name="elapsed_time",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "Remaining Time",
        fom_regex=per_epoch_regex,
        group_name="remaining_time",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "v_num",
        fom_regex=r"Epoch.*v_num=(?P<v_num>\S+)[,\]]",
        group_name="v_num",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "reduced_train_loss",
        fom_regex=r"Epoch.*reduced_train_loss=(?P<reduced_train_loss>[0-9\.]+)[,\]]",
        group_name="reduced_train_loss",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "global_step",
        fom_regex=r"Epoch.*global_step=(?P<global_step>[0-9\.]+)[,\]]",
        group_name="global_step",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "consumed_samples",
        fom_regex=r"Epoch.*consumed_samples=(?P<consumed_samples>[0-9\.]+)[,\]]",
        group_name="consumed_samples",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )
    figure_of_merit(
        "train_step_timing",
        fom_regex=r"Epoch.*train_step_timing in s=(?P<train_step_time>[0-9\.]+)[,\]]",
        group_name="train_step_time",
        units="s",
        log_file=processed_log_name,
        contexts=[epoch_context_name],
    )

    register_phase(
        "detect_unknown_configs",
        pipeline="setup",
        run_before=["write_config"],
        run_after=["make_experiments"],
    )

    def _detect_unknown_configs(self, workspace, app_inst):
        base_config = get_file_path(
            os.path.abspath(
                os.path.expandvars(
                    os.path.expanduser(
                        self.expander.expand_var_name("nemo_base_config")
                    )
                )
            ),
            workspace,
        )

        # Avoid problems with missing base config files
        if not os.path.exists(base_config):
            return

        workload = self.workloads[self.expander.workload_name]

        config_data = ramble.util.yaml_generation.read_config_file(base_config)

        known_config_options = set()

        for config in workload.variables:
            if len(config.split(".")) > 1:
                known_config_options.add(config)

        detected_config_options = (
            ramble.util.yaml_generation.all_config_options(config_data)
        )

        missing_configs = detected_config_options - known_config_options
        unneeded_configs = known_config_options - detected_config_options

        if missing_configs or unneeded_configs:

            config_warnings = os.path.join(
                self.expander.expand_var_name("experiment_run_dir"),
                "config_warnings.out",
            )

            logger.warn(
                "Detected configuration differences relative to base config."
            )
            logger.warn(f"See {config_warnings} for more details.")
            with open(config_warnings, "w+") as f:
                if missing_configs:
                    f.write(
                        "Configuration options in base config that are not workload_variables:\n"
                    )
                    for config in missing_configs:
                        f.write(f"    - {config}\n")

                if unneeded_configs:
                    f.write(
                        "Configuration options in that are workload_variables but are not in the base config:\n"
                    )
                    for config in unneeded_configs:
                        f.write(f"    - {config}\n")

    register_phase(
        "write_config", pipeline="setup", run_after=["make_experiments"]
    )

    def _write_config(self, workspace, app_inst):
        base_config = get_file_path(
            os.path.abspath(
                os.path.expandvars(
                    os.path.expanduser(
                        self.expander.expand_var_name("nemo_base_config")
                    )
                )
            ),
            workspace,
        )

        # Avoid errors for missing base config files
        if not os.path.exists(base_config):
            return

        config_data = ramble.util.yaml_generation.read_config_file(base_config)

        ramble.util.yaml_generation.apply_default_config_values(
            config_data, self, self.default_config_string
        )

        # Set config options in config_data
        for var_name in self.variables:
            if "." in var_name and len(var_name.split(".")) > 1:
                var_val = self.expander.expand_var(
                    self.expander.expansion_str(var_name), typed=True
                )

                # Convert any invalid tuples back to their default strings.
                if isinstance(var_val, tuple):
                    var_val = self.expander.expand_var(
                        self.expander.expansion_str(var_name)
                    )
                elif isinstance(var_val, list):
                    for i in range(0, len(var_val)):
                        var_val[i] = self.expander.expand_var(
                            var_val[i], typed=True
                        )

                ramble.util.yaml_generation.set_config_value(
                    config_data, var_name, var_val, force=True
                )

        config_path = os.path.join(
            self.expander.expand_var("{nemo_generated_config_path}"),
            self.expander.expand_var("{nemo_generated_config_name}"),
        )

        # Ensure all instances of ${data_dir} are replaced correctly
        config_str = yaml.dump(config_data, default_flow_style=False)
        config_str = config_str.replace(
            "${data_dir}",
            self.expander.expand_var("{workload_input_dir}/data"),
        )
        with open(config_path, "w+") as f:
            f.write(config_str)

    register_phase(
        "preprocess_log",
        pipeline="analyze",
        run_before=["analyze_experiments"],
    )

    def _preprocess_log(self, workspace, app_inst):
        log_file = get_file_path(
            os.path.abspath(self.expander.expand_var_name("log_file")),
            workspace,
        )

        elapsed_s = 0

        final_regex = re.compile(self.final_epoch_regex)

        with open(log_file, "r", encoding="ISO-8859-1") as f:
            data = f.read()

        with open(log_file, "r", encoding="ISO-8859-1") as f:
            for line in f.readlines():
                m = final_regex.match(line)

                if m:
                    timestamp = m.group("elapsed_time")

                    time_parts = timestamp.split(":")

                    part_s = 0
                    mult = 1
                    for part in reversed(time_parts):
                        part_s += int(part) * mult
                        mult = mult * 60
                    elapsed_s += part_s

        processed_log = self.expander.expand_var(
            "{experiment_run_dir}/processed_{experiment_name}.out"
        )

        with open(processed_log, "w+") as f:
            f.write(
                data.replace("\x13", "\n")
                .replace("\x96\x88", "")
                .replace("â", "")
            )

        sec_file_path = self.expander.expand_var(
            "{experiment_run_dir}/elapsed_seconds"
        )
        with open(sec_file_path, "w+") as f:
            f.write(f"Elapsed seconds: {elapsed_s}")
