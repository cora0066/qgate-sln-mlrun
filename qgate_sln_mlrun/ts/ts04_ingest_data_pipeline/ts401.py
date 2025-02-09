"""
  TS401: Ingest data & pipeline (Preview mode)
"""

from qgate_sln_mlrun.ts.tsbase import TSBase
from qgate_sln_mlrun.setup import Setup
import mlrun.feature_store as fstore
import mlrun.feature_store.steps as fsteps
import pandas as pd
import glob
import os


class TS401(TSBase):

    def __init__(self, solution):
        super().__init__(solution, self.__class__.__name__)

    @property
    def desc(self) -> str:
        return "Ingest data & pipeline (Preview mode)"

    @property
    def long_desc(self):
        return "Ingest data & pipeline (Preview mode) from DataFrame Source"

    def prj_exec(self, project_name):
        """Data ingest"""

        pipelines = None
        if self.test_setting.get('pipeline'):
            if self.test_setting_pipeline.get('featuresets'):
                pipelines = self.test_setting_pipeline['featuresets']

        if pipelines:
            for featureset_name in self.get_featuresets(self.project_specs.get(project_name)):
                # processing only feature sets with pipelines
                if featureset_name in pipelines:
                    # create possible file for load
                    source_file = os.path.join(os.getcwd(),
                                               self.setup.model_definition,
                                               "02-data",
                                               self.setup.dataset_name,
                                               f"*-{featureset_name}.csv.gz")

                    # check existing data set
                    for file in glob.glob(source_file):
                        self._ingest_data(f"{project_name}/{featureset_name}", project_name, featureset_name, file)

    @TSBase.handler_testcase
    def _ingest_data(self, testcase_name, project_name, featureset_name, file):
        # get existing feature set (feature set have to be created in previous test scenario)
        featureset = fstore.get_feature_set(f"{project_name}/{featureset_name}")

        # add pipelines
        setting=self.test_setting_pipeline['tests'][featureset_name]
        if setting:
            last_step=None
            # add steps
            if setting["imputer"]:
                last_step=featureset.graph.add_step(fsteps.Imputer(mapping=setting['imputer']),
                                         name="imputer",
                                         after=None if not last_step else last_step.name)

            if setting["onehotencoder"]:
                last_step = featureset.graph.add_step(fsteps.OneHotEncoder(mapping=setting['onehotencoder']),
                                                      name="onehotencoder",
                                                      after=None if not last_step else last_step.name)

            if setting["storey.filter"]:
                last_step=featureset.graph.add_step("storey.Filter",
                                     name="filter",
                                     after=None if not last_step else last_step.name,
                                     _fn=f"{setting['storey.filter']}")

            if setting["storey.extend"]:
                last_step=featureset.graph.add_step("storey.Extend",
                                         name="extend",
                                         after=None if not last_step else last_step.name,
                                         _fn=f"{setting['storey.extend']}")

        # https://docs.mlrun.org/en/latest/feature-store/transformations.html
        #ok - Imputer
        #DateExtractor
        #MapValues
        #ok - OneHotEncoder
        #DropFeatures
        #MLRunStep

        # https://docs.mlrun.org/en/latest/feature-store/transformations.html#supporting-multiple-engines

        #     if setting["extend"]:
        #         last_step=graph.add_step("storey.Extend",
        #                                  name="extend",
        #                                  after=None if not last_step else last_step.name,
        #                                  _fn=f"{setting['extend']}")


        featureset.save()

        # ingest data with bundl/chunk
        for data_frm in pd.read_csv(file,
                                    sep=self.setup.csv_separator,
                                    header="infer",
                                    decimal=self.setup.csv_decimal,
                                    compression="gzip",
                                    encoding="utf-8",
                                    chunksize=Setup.MIN_BUNDLE):
            featureset.preview(data_frm)

