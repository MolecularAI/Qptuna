import argparse
import json
import logging
import os
import pathlib
from typing import Union

from apischema import deserialize, serialize

from optunaz.config.buildconfig import BuildConfig
from optunaz.config.optconfig import OptimizationConfig
from optunaz.model_writer import ModelPersistenceMode
from optunaz.three_step_opt_build_merge import (
    optimize,
    buildconfig_best,
    build_best,
    build_merged,
)

logger = logging.getLogger(__name__)


def main():

    parser = argparse.ArgumentParser(
        description="optbuild: Optimize hyper-parameters and build (train) the best model."
    )
    requiredNamed = parser.add_argument_group("required named arguments")
    requiredNamed.add_argument(
        "--config",
        type=pathlib.Path,
        required=True,
        help="Path to input configuration file (JSON): "
        "either Optimization configuration, "
        "or Build (training) configuration.",
    )
    parser.add_argument(
        "--best-buildconfig-outpath",
        help="Path where to write Json of the best build configuration.",
        type=pathlib.Path,
        default=None,
    )
    parser.add_argument(
        "--best-model-outpath",
        help="Path where to write (persist) the best model.",
        type=pathlib.Path,
        default=None,
    )
    parser.add_argument(
        "--merged-model-outpath",
        help="Path where to write (persist) the model trained on merged train+test data.",
        type=pathlib.Path,
        default=None,
    )
    parser.add_argument(
        "--model-persistence-mode",
        help="Model persistence mode: "
        "plain scikit-learn model, "
        "model with OptunaAZ, "
        "or AZ PIP "
        "(default: %(default)s).",
        type=ModelPersistenceMode,
        choices=[e.value for e in ModelPersistenceMode],
        default=ModelPersistenceMode.SKLEARN_WITH_OPTUNAZ.value,
    )
    args = parser.parse_args()

    AnyConfig = Union[OptimizationConfig, BuildConfig]
    with open(args.config, "rt") as fp:
        config = deserialize(AnyConfig, json.load(fp), additional_properties=True)

    if isinstance(config, OptimizationConfig):
        study_name = str(pathlib.Path(args.config).absolute())
        study = optimize(config, study_name=study_name)
        buildconfig = buildconfig_best(study)
    elif isinstance(config, BuildConfig):
        buildconfig = config
    else:
        raise ValueError(f"Unrecognized config type: {type(config)}.")

    if args.best_buildconfig_outpath:
        os.makedirs(os.path.dirname(args.best_buildconfig_outpath), exist_ok=True)
        with open(args.best_buildconfig_outpath, "wt") as fp:
            json.dump(serialize(buildconfig), fp, indent="  ")
    if args.best_model_outpath:
        build_best(buildconfig, args.best_model_outpath, args.model_persistence_mode)
    if args.merged_model_outpath:
        build_merged(
            buildconfig, args.merged_model_outpath, args.model_persistence_mode
        )
