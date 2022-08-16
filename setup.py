"""
   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at
       http://www.apache.org/licenses/LICENSE-2.0
   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import argparse
import sys
import os
import shutil
import logging
import numpy as np
import time

from data.schemas.instacart import gen_instacart_schema
from data.preparation.prepare_single_tables import prepare_all_tables

np.random.seed(1)

if __name__ == '__main__':

    #
    # ARGS - command-line options
    #      - should match the REST API, Knative interface
    #
    parser = argparse.ArgumentParser()

    # ARGS.REST 
    # - location of the main file
    parser.add_argument('--rest_dir', default='interface/dev/', 
                        help='location of the fastapi main file')

    # - name of the main file
    parser.add_argument('--rest_main', default='main', 
                        help='name of the fastapi main file. *.py')

    # - ip of the interface
    parser.add_argument('--rest_host', default='0.0.0.0', 
                        help='IP address of the interface')

    # - port of the interface
    parser.add_argument('--rest_port', default='8000', 
                        help='port of the interface')

    # ARGS.DATA PREPARATION
    # - dataset to be used
    parser.add_argument('--dataset', default='instacart', 
                        help='dataset to be learned')

    # - path and separator for csv file
    parser.add_argument('--csv_path', default='data/files/instacart/csv/orders.csv', 
                        help='csv path for the dataset specified')
    parser.add_argument('--csv_seperator', default=',') # for tpc-ds, use '|'

    # - path for hdf file
    parser.add_argument('--hdf_path', default='data/files/instacart/hdf', 
                        help='csv path for the dataset specified')

    parser.add_argument('--max_rows_per_hdf_file', type=int, default=20000000)
    parser.add_argument('--hdf_sample_size', type=int, default=1000000)


    # - prepares data : generate the hdf from the dataset(.csv)
    parser.add_argument('--generate_hdf', action='store_true', 
                        help='prepares hdf5 files for single tables')

    # ARGS.LEARN
    # - learn tables to create rspn ensemble, new or update
    parser.add_argument('--train', action='store_true', 
                        help='train rspns on the given dataset')

    # ARGS.INFERENCE
    # - estimate an approximate value for the given aggregation query
    parser.add_argument('--estimate', help='query to be approximated')

    # ARGS.CONFIGURATION
    # - set log level
    parser.add_argument('--log_level', type=int, default=logging.DEBUG)

    # ARGS: parse arguments
    args = parser.parse_args()

    #
    # CONF - configurations for traindb-ml
    #
    # CONF.Logging 
    # - copied from deepdb's maqp.py
    #
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=args.log_level,
        # [%(threadName)-12.12s]
        format="%(asctime)s [%(levelname)-5.5s]  %(message)s",
        handlers=[
            logging.FileHandler(
                "logs/{}_{}.log".format(
                    args.dataset, time.strftime("%Y%m%d-%H%M%S"))),
            logging.StreamHandler()
        ])
    logger = logging.getLogger(__name__)

    #
    # TODO: separate this as an option
    # CONF.Data_Preparation
    #  - SEE: deepdb/maqp.py, schema.py
    #     prepare_all_tables(...), prepare_sample_hdf(...)
    #
    #
    # CONF.Data_Preparation.Setup_Directories
    #
    logger.info( "Data Preparation: Setup Directories")
    dataset_path = "data/files/" + args.dataset
    dataset_csv_path = dataset_path + "/csv/"
    dataset_hdf_path = dataset_path + "/hdf/"
    logger.info( " - Setup Directories: " )
    """
              + f" input_csv_path: {args.csv_path}"
              + f" dataset_path: {dataset_path}"
              + f" dataset_csv_path: {dataset_csv_path}"
              + f" dataset_hdf_path: {dataset_hdf_path}")
    """

    #  - create csv directory
    logger.info(f" - Making csv path {dataset_csv_path}")
    os.makedirs(dataset_csv_path, exist_ok=True)

    #  - extract the filename from the csv_path and make a target path
    #  - copy the input csv file into the target path (overwrite if already exists)
    csv_target_filename = os.path.basename(args.csv_path)
    csv_target_path = dataset_csv_path + csv_target_filename

    # TODO remove if exist? just like the 'hdf'?
    logger.info(f"  (Overwrite? {os.path.exists(csv_target_path)})")
    if (args.csv_path != csv_target_path) and not os.path.exists(csv_target_path):
        shutil.copy(args.csv_path, csv_target_path) 

    # CONF.Data Preparation.Create_SchemaGraph
    #  - make a SchemaGraph from the csv
    logger.info( "Data Preparation: Create SchemaGraph")
    logger.info(f" - Making SchemaGraphs from {dataset_csv_path}")
    table_csv_path = dataset_csv_path + '{}.csv'
    if args.dataset == 'instacart':
        schema = gen_instacart_schema(table_csv_path)
    else:
        raise ValueError('Unknown dataset')

    #  - test
    logger.info(f" - Result")
    table = schema.table_dictionary['orders']
    logger.info(f"   orders object: {table}")
    logger.info(f"   orders.table_name: {table.table_name}")
    logger.info(f"   orders.table_size: {table.table_size}")
    logger.info(f"   orders.primary_key: {table.primary_key}")
    logger.info(f"   orders.csv_file_location: {table.csv_file_location}")
    logger.info(f"   orders.attributes: {table.attributes}")
    logger.info(f"   orders.sample_rate: {table.sample_rate}")

    #
    # CONF.Data_Preparation.Generate_HDF
    #  - make a hdf from the csv
    #  - requires: pip install tables
    logger.info( "Data Preparation: Generate HDF")
    logger.info(f" - Generate hdf files for the given csv and save into {dataset_hdf_path}")

    #  - create hdf directory
    if os.path.exists(dataset_hdf_path):
        logger.info(f" - Removing the old {dataset_hdf_path}")
        shutil.rmtree(dataset_hdf_path)
    logger.info(f" - Making new {dataset_hdf_path}")
    os.makedirs(dataset_hdf_path)

    # - prepare all tables
    logger.info(f" - Prepare all tables")
    prepare_all_tables(schema, dataset_hdf_path, args.csv_seperator, max_table_data = args.max_rows_per_hdf_file)

    logger.info(f"Bookmark")
    
    # TRAIN RSPNs - NEW or UPDATE
    # TODO


    # ESTIMATE
    # TODO

    #
    # CONF.RESTAPI
    #
    # launch the fast_api (/interface/dev/main.py)
    # prerequisite: pip install fastapi uvicorn
    # testing: launch browser with "http://0.0.0.0:8000" then see hello message
    #
    #os.system('uvicorn main:app --app-dir interface/dev/ --reload --host=0.0.0.0 --port=8000')
    os.system(f"uvicorn {args.rest_main}:app --app-dir {args.rest_dir} --reload --host={args.rest_host} --port={args.rest_port}")
    sys.exit("Shutting down, bye bye!")

