from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
engine = create_engine(DATABASE_URI)
from models import Base, User, Site, EnvironmentRecord, Region

import pandas as pd
import os
import pickle
from numpy import nan

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

from contextlib import contextmanager

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def recreate_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


class GSSchemaTest:
    def __init__(self, s_scope, use_cache=True):
        self.submission_work_book_path = "/home/humebc/projects/GlobalSearch/20210813_input_template_bh/20210813_CBASS_submission_workbook_bh.xlsx"
        # Why is read_excel so Fing slow!!
        # I will implement a quick cache so that we don't have to read these in multiple times
        self.s = s_scope
        self.excel_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel_cache")
        if not os.path.exists(self.excel_cache_path):
            os.makedirs(self.excel_cache_path)
        if use_cache:
            # SITE df
            self.site_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "site_df.p"), read_method=self.read_in_site_df)
            # EXPERIMENT df
            self.experiment_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "experiment_df.p"), read_method=self.read_in_experiment_df)
            # DIVE df
            self.dive_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "dive_df.p"), read_method=self.read_in_experiment_df)
            # COLONY df
            self.colony_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "colony_df.p"), read_method=self.read_in_experiment_df)
            # SAMPLE df
            self.sample_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "sample_df.p"), read_method=self.read_in_experiment_df)
        else:
            self.read_in_site_df()
            self.read_in_experiment_df()
            self.read_in_dive_df()
            self.read_in_colony_df()
            self.read_in_sample_df()
    
    def start(self):
        # We will progress from left to right in the work book I.e. SITE -> EXPERIMENT -> DIVE -> COLONY -> SAMPLE
        
        #### SITE ####
        # From the SITE sheet we create the Site and EnvironmentRecord objects in that order.
        # EnvironmentRecord is related to Site.

        # CHECKS
        # 1 - General check to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        #   Required fields are:
        site_required_fields = ["record number", "site name", "site abbreviation", "timestamp", "time zone", "country", "country abbreviation", "latitude", "longitude", "env_broad_scale", "env_local_scale", "env_medium", "scientist that added this",	"record label"]
        site_optional_fields = ["sub-region", "water temperature", "turbitidy",	"chl a",	"salinity",	"pH",	"dissolved oxygen",	"maximum monthly mean",	"thermal stress anomaly frequency stdev",	"sea surface temperature stdev"]
        self.site_df.replace({"na": nan}, inplace=True)
        self.site_df.set_index("record number", inplace=True, drop=True)
        for record, ser in self.site_df.iterrows():
            # CHECK to see if sub-region has been provided. Set to NULL if not.
            if pd.isna(ser["sub-region"]):
                record_sub_region = None
            else:
                record_sub_region = ser["sub-region"]

            self.s.add(Site(
                name=ser["site name"],
                name_abbreviation=ser["site abbreviation"],
                latitude=ser["latitude"],
                longitude=ser["longitude"],
                country=ser["country"],
                country_abbreviation=ser["country abbreviation"],
                time_zone=ser["time zone"],
                sub_region=record_sub_region))

            foo = "bar"



    def _check_cache_and_load(self, pickle_path, read_method):
        if os.path.exists(pickle_path):
            return pickle.load(open(pickle_path, 'rb'))
        else:
            df = read_method()
            pickle.dump(df, open(pickle_path, 'wb'))
            return df

    def read_in_sample_df(self):
        df = pd.read_excel(self.submission_work_book_path, sheet_name="SAMPLE", skiprows=[0,2,3])
        return df

    def read_in_colony_df(self):
        df = pd.read_excel(self.submission_work_book_path, sheet_name="COLONY", skiprows=[1])
        return df

    def read_in_dive_df(self):
        df = pd.read_excel(self.submission_work_book_path, sheet_name="DIVE", skiprows=[1,2])
        return df

    def read_in_experiment_df(self):
        df = pd.read_excel(self.submission_work_book_path, sheet_name="EXPERIMENT", skiprows=[1,2])
        return df

    def read_in_site_df(self):
        df = pd.read_excel("/home/humebc/projects/GlobalSearch/20210813_input_template_bh/20210813_CBASS_submission_workbook_bh.xlsx", sheet_name="SITE", skiprows=[1])
        return df

with session_scope() as s:
    # TODO this is where we need to read in the input excel workbooks and coerse them into
    # proper database objects.

    schema_test = GSSchemaTest(s_scope=s).start()
    user = s.query(User).all()
    foo = "bar"
    