from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
engine = create_engine(DATABASE_URI)
from models import Base, Campaign, User, Site, EnvironmentRecord, Region, CBASSAssay
from datetime import datetime, timedelta, timezone, time

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
            self.site_df = self.read_in_site_df()
            self.experiment_df = self.read_in_experiment_df()
            self.dive_df = self.read_in_dive_df()
            self.colony_df = self.read_in_colony_df()
            self.sample_df = self.read_in_sample_df()
    
    def start(self):
        # We will progress from left to right in the work book I.e. SITE -> EXPERIMENT -> DIVE -> COLONY -> SAMPLE
        
        #### USER ####
        chris_user, carol_user = self._make_users()
        
        #### CAMPAIGN ####
        self.campaign = self._make_campaign(lead_user=chris_user)

        #### CAMPAIGN_USER ####
        # Join table for many to many relationship
        chris_user.campaigns.append(self.campaign)
        carol_user.campaigns.append(self.campaign)
        
        self.s.add(chris_user)
        self.s.add(carol_user)
        self.s.add(self.campaign)

        #### SITE ####
        # From the SITE sheet we create the Site and EnvironmentRecord objects in that order.
        # EnvironmentRecord is related to Site.

        # CHECKS
        # 1 - General check to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        #   Required fields are:
        # I will not implement this check here, but I imagine it will need to be done for the full implementation
        site_required_fields = ["record number", "site name", "site abbreviation", "timestamp", "time zone", "country", "country abbreviation", "latitude", "longitude", "env_broad_scale", "env_local_scale", "env_medium", "scientist that added this",	"record label"]
        site_optional_fields = ["sub-region", "water temperature", "turbidity",	"chl a",	"salinity",	"pH",	"dissolved oxygen",	"maximum monthly mean",	"thermal stress anomaly frequency stdev",	"sea surface temperature stdev"]
        self.site_df.replace({"na": nan}, inplace=True)
        
        self.site_df.set_index("record number", inplace=True, drop=True)
        for record, ser in self.site_df.iterrows():
            new_site = self._create_site(ser)

            new_environment_record = self._create_environment_record(ser, new_site)
            self.s.add(new_environment_record)
        
        # At this point we have the Site and EnvironmentRecord objects populated
        
        #### CBASS ASSAYS ####
        self._populate_cbass_assays()

    def _create_environment_record(self, ser, new_site):
        # Create the EnvironmentRecord and link it to the Site object just created
        # CHECK that the 'timestamp' and the 'time zone' provided by the user is in the correct format
        # CHECK that the env_broad_scale, env_local_scale and env_medium are valid terms from 
        # here: https://www.ebi.ac.uk/ols/index

        # To create the timestamp object we wil use the python3 datetime module
        timestamp = datetime.fromisoformat(ser["timestamp"] + ser["time zone"])

        # CHECK whether the optional parameters exist and set to None if not
        param_dict = self._check_site_optional_params_valid(ser)

        # NB for the time being we will ignore 'coral_cover'.
        new_environment_record = EnvironmentRecord(
            site=new_site, record_timestamp=timestamp, env_broad_scale=ser["env_broad_scale"],
            env_local_scale=ser["env_local_scale"], env_medium=ser["env_medium"],
            sea_surface_temperature=param_dict["water temperature"], turbidity=param_dict["turbidity"],
            chlorophyll_a=param_dict["chl a"], salinity=param_dict["salinity"],
            ph=param_dict["pH"], dissolved_oxygen=param_dict["dissolved oxygen"],
            maximum_monthy_mean=param_dict["maximum monthly mean"],
            thermall_stress_anomaly_frequency_stdev=param_dict["thermal stress anomaly frequency stdev"],
            sea_surface_temperature_stdev=param_dict["sea surface temperature stdev"],
            label=ser["record label"]
            )
        return new_environment_record

    def _create_site(self, ser):
        # CHECK to see if sub-region has been provided. Set to NULL if not.
        # sub-region is optional and will be used only for the purpose of making the NCBI submission sheet.
        if pd.isna(ser["sub-region"]):
            record_sub_region = None
        else:
            record_sub_region = ser["sub-region"]

        # Create a Site object using the values from the excel row
        # NOTE for FIVE. The headers here perfectly match those of the input excel file
        # so it should be clear which input column go to which db table column
        new_site = Site(
            name=ser["site name"],
            name_abbreviation=ser["site abbreviation"],
            latitude=ser["latitude"],
            longitude=ser["longitude"],
            country=ser["country"],
            country_abbreviation=ser["country abbreviation"],
            time_zone="foo",
            sub_region=record_sub_region)

        self.s.add(new_site)
        return new_site

    def _make_campaign(self, lead_user):
        # We will enter the campagin manually, as this will have been created by an
        # admin in the back end. The uploading user will have access to a specific
        # Campaign.

        campaign = Campaign(
            lead_user=lead_user,
            name="CBASS84",
            start_date=datetime.fromisoformat("2018-08-07T12:00+03:00"),
            end_date=datetime.fromisoformat("2018-08-16T08:00+03:00"),
            ncbi_bio_project_accession = "SUB8645303"
            )

        return campaign

    def _make_users(self):
        # User objects will have been created manually by an admin. So we will
        # create them manually here.
        # The example we are working with works with 2 users:
        # Christian R Voolstra and Carol Buitrago-López
        
        # Because the import sheet has the name listed as the 'full name'
        # but the full name is not stored in the user object,
        # we will keep a dict that is full name to user object
        # so that we can easily look this up when the full name is given in the 
        # later sheets
        chris_user = User(
            role="admin", email="foo.bar@foobar.com",
            first_name="Christian", last_name="Voolstra",
            registration_date=datetime.now(), username='cvoolstra'
            )

        carol_user = User(
            role="power_user", email="bar.foo@foobar.com",
            first_name="Carol", last_name="Buitrago-López",
            registration_date=datetime.now(), username="clopez"
            )
        return chris_user, carol_user

    def _populate_cbass_assays(self):
        # each of the rows in EXPERIMENT will make 1 CBASSAssay object

        # CHECKS
        # 1 - General check to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        #   Required fields are:
        # I will not implement this check here, but I imagine it will need to be done for the full implementation
        self.experiment_df.replace({"na": nan}, inplace=True)
        self.experiment_df.set_index("experiment number", inplace=True, drop=True)

        # NOTE we currently don't make use of the ''scientist that added this'
        # I need to check with Chris Voolstra what the purpose of this field is 
        # but I think maybe they are not required in the database.
        # experiment_required_fields = ["experiment number", "site record", "experiment type", "baseline temp", "experiment start timestamp", "experiment stop timestamp",	"scientist that added this", "experiment label"]
        # experiment_optional_fields = ["light level",	"flow rate", "tank volume",	"seawater source",	"scientist 1",	"scientist 2"]

        for experiment, ser in self.site_df.iterrows(): 

            # CHECK whether the optional parameters exist and set to None if not
            params_dict = self._check_cbass_assay_optional_params_valid(ser)

            new_experiment = CBASSAssay(
                type=ser["experiment type"],
                site=self.s.query(Site).filter(Site.site_abbreviation==ser["site record"].split("_")[0]).one(),
                environment_record = self.s.query(EnvironmentRecord).filter(EnvironmentRecord.label==ser["site record"]).one(),
                campaign = self.campaign,
                label = ser["experiment label"],
                start_time=datetime.fromisoformat(ser["experiment start timestamp"]),
                start_time=datetime.fromisoformat(ser["experiment stop timestamp"]),
                baseline_temp=float(ser["baseline temp"]),
                flow_rate_liters_per_hour=params_dict["flow rate"],
                light_level=params_dict["light level"], tank_volumne_liter=params_dict["tank volume"],
                seawater_source=params_dict["seawater source"]
                )

            # Associate users
            # We need to check whether the input inlcludes users to be associated to the CBASSAssay
            self._add_user_to_cbass_assay(ser, "scientist 1", new_experiment)
            self._add_user_to_cbass_assay(ser, "scientist 2", new_experiment)

    
    def _check_cbass_assay_optional_params_valid(self, ser):
        param_dict = {}
        for optional_parameter in [
            "light level",	"flow rate", "tank volume",	"seawater source"
            ]:
            if pd.isna(ser[optional_parameter]):
                param_dict[optional_parameter] = None
            else:
                if optional_parameter != "seawater source":
                    try:
                        param_dict[optional_parameter] = float(ser[optional_parameter])
                    except ValueError:
                        raise RuntimeError(f"Problem with format of {optional_parameter}")
                else:
                    # The seawater source is a free form string
                    param_dict[optional_parameter] = ser[optional_parameter]
        
        return param_dict
    
    def _add_user_to_cbass_assay(self, ser, scientist_string, new_experiment):
        if not pd.isna(ser[scientist_string]):
            # A user has been provided and we should associate the appropriate user
            # by adding to the nex_experiment object
            try:
                new_experiment.users.append(self.s.query(User).filter(first_name=ser[scientist_string].split(" ")[0], last_name=ser[scientist_string].split(" ")[-1]).one())
            # NOTE TODO these sorts of errors will need to be better handled in the actual implementation
            except:
                raise RuntimeError("Error identifying user in EXPERIMENT table")

            



    def _check_site_optional_params_valid(self, ser):
        param_dict = {}
        for optional_parameter in [
            "water temperature", "turbidity",	"chl a",	"salinity",	"pH",
            "dissolved oxygen",	"maximum monthly mean",
            "thermal stress anomaly frequency stdev",	"sea surface temperature stdev"
            ]:
            if pd.isna(ser[optional_parameter]):
                param_dict[optional_parameter] = None
            else:
                try:
                    param_dict[optional_parameter] = float(ser[optional_parameter])
                except ValueError:
                    raise RuntimeError(f"Problem with format of {optional_parameter}")
        return param_dict



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

    schema_test = GSSchemaTest(s_scope=s, use_cache=True).start()
    user = s.query(User).all()
    foo = "bar"
    