"""
This script aims to test the barebones version of the KnowledgeBase db schema

To test that the schema is suitable, we will perform one full submission of an acutal dataset.
In parallel to testing the schema, this will also allow us to make sure that the input sheets (workbook)
are suitably formatted and contain all the required information.

I have tried to comment thoroughly so that you can read through the various sections to see how
the input excel columns relate to the db tables and columns.

Please see the models.py for the db schema. I hope that the table
and column names are self explanatory.

The walkthrough of the submission starts at the start method of the GSSchemaTest class.

Any questions or if I've forgotten something, please don't hestitate to get in touch:
benjamin[D0t]humeATuni-konstanz.de
"""

from sqlalchemy import create_engine
from sqlalchemy.orm.exc import NoResultFound
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
engine = create_engine(DATABASE_URI)
from models import Base, Campaign, CoralSpecies, HeatStressProfile, NCBIBioSample, SequencingEffortBarcode, SequencingEffortMetagnomic, SequencingEffortRNASeq, User, Site, EnvironmentRecord, Region, CBASSAssay, Dive, Assay, Colony, CBASSNucleicAcidFragment, CBASSAssayFragment, DiveTablePhoto, ColonyPhoto, CBASSFragmentPhoto
from datetime import datetime, tzinfo
import pytz

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
        self.submission_work_book_path = "/home/humebc/projects/GlobalSearch/20210813_input_template_bh/20210813_CBASS_submission_workbook_CBASS84_bh.xlsx"
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
            self.dive_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "dive_df.p"), read_method=self.read_in_dive_df)
            # COLONY df
            self.colony_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "colony_df.p"), read_method=self.read_in_colony_df)
            # SAMPLE df
            self.sample_df = self._check_cache_and_load(pickle_path=os.path.join(self.excel_cache_path, "sample_df.p"), read_method=self.read_in_sample_df)
        else:
            self.site_df = self.read_in_site_df()
            self.experiment_df = self.read_in_experiment_df()
            self.dive_df = self.read_in_dive_df()
            self.colony_df = self.read_in_colony_df()
            self.sample_df = self.read_in_sample_df()

        self.photo_dir = "/home/humebc/projects/GlobalSearch/20210811_input_template_excels_CBASS84/cbass_84_photos"
    
    def start(self):
        # We will progress from left to right in the work book I.e. SITE -> EXPERIMENT -> DIVE -> COLONY -> SAMPLE
        
        # NOTE: Throughout this script I am only aiming to successfuly 
        # get through a single submission from start to end.
        # If I try to run this script again after a successful submission
        # I will get lots of errors relating to violating unique constraints.
        # This is becuase I have not put checks in place to make sure that the
        # user is not trying to upload data that has already been uploaded.
        # The unique constraints that I have in place in the db schema (see models.py)
        # Are a good indication of how we can detect and report on attempts
        # of users trying to submit data that has already been submitted.

        #### User objects ####
        chris_user, carol_user = self._make_users()
        
        #### Campaign object ####
        self.campaign = self._make_campaign(lead_user=chris_user)

        # Associate users to campaign
        chris_user.campaigns.append(self.campaign)
        carol_user.campaigns.append(self.campaign)
        
        # Add the objects to the session
        # In general we will not commit the newly created objects
        # to the database, until the entire submission is completed.
        # If there is an error during the submission process the db will automatically
        # be rolled back to the state it was in before the user started the submission
        self.s.add(chris_user)
        self.s.add(carol_user)
        self.s.add(self.campaign)

        #### Site, EnvironmentRecord objects ####
        self._populate_sites_environment_records()
        
        #### Assay objects ####
        self._populate_cbass_assays()

        #### Dive objects ####
        self._populate_dives()

        #### Colony objects ####
        self._populate_colonies()

        #### Fragment, HeatStressProfile, SequencingEffor, NCBIBioSample objects (HeatStressProfiles)####
        self._populate_fragments()

        # Commit
        self.s.commit()

    def _populate_sites_environment_records(self):
        # From the SITE sheet we create the Site and EnvironmentRecord objects in that order.
        # EnvironmentRecord is related to Site.

        # You'll see that there is also a Region table in the models.py schema.
        # I need to catch up with Chris about whether we will still make use of this table is.
        # The problem with the region concept is: how do you define a region? and how 
        # do you control what submitting users consider a region?
        # For example there are some standardised lists of regions hosted by e.g. NATO
        # but this is probably not the resolution at which Chris envisaged us tracking regions.
        # So, for the time being I have not included the Region in this script, but I have fully
        # implemented the tables and relations in the models.py database so that it can be used
        # at a later date. We can likely control the use of Region in the excel submission
        # workbook by using a controlled vocab (i.e. drop down). You'll see that I have currently
        # removed Region from the submission work book. Please note: the 'sub-region' is not
        # relate to the Region table. This is something different.

        # CHECKS
        # CHECK to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        # I will not implement this check here, but I imagine it will need to be done for the full implementation
        # site_required_fields = ["record number", "site name", "site abbreviation", "timestamp", "time zone", "country", "country abbreviation", "latitude", "longitude", "env_broad_scale", "env_local_scale", "env_medium", "scientist that added this",	"record label"]
        # site_optional_fields = ["sub-region", "water temperature", "turbidity",	"chl a",	"salinity",	"pH",	"dissolved oxygen",	"maximum monthly mean",	"thermal stress anomaly frequency stdev",	"sea surface temperature stdev"]
        self.site_df.replace({"na": nan}, inplace=True)
        
        self.site_df.set_index("record number", inplace=True, drop=True)
        # We will create a convenience lookup dict of the site abbreviation
        # and label to the timezone string. This will be populated in
        # self._create_environment_record below
        self.time_zone_dict = {}
        for record, ser in self.site_df.iterrows():
            new_site = self._create_site(ser)
            new_environment_record = self._create_environment_record(ser, new_site)
            self.s.add(new_environment_record)

    def _populate_fragments(self):
        # In the database we refer to 'fragements'. Outside of the database, these will
        # generally be referred to as 'samples'.
        # Every row in the SAMPLES input sheet corresponds to a db Fragment object
        # (one of two possible subclasses CBASSAssayFragment or 
        # CBASSNucleicAcidFragment; see below).

        # Depending on what sequencing has been conducted we will also be defining a number
        # of instances of the SequencingEffort subclasses. These are:
        # SequencingEffortMetagnomic, SequencingEffortRNASeq, SequencingEffortBarcode
        # We will also be defining a number of NCBIBioSample objects. I will document the
        # logic for creating these after the Fragement objects have been created below.

        # CHECK to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        # There are a lot of optional fields because this input table has to account for two subclasses of Fragement.
        # 1 - CBASSAssayFragment and 2 - CBASSNucleicAcidFragment
        # The CBASSAssayFragment is a piece of coral that has been in an experimental aquaria
        # and challenged. It may also, optionally, have been prepared for sequencing.
        # The CBASSNucleicAcidFragment is a piece of coral that has not have been in an
        # experimental aquarium, and rather is prepared for sequencing only.
        # Beause it has not been in an aquarium it will not have any of the aquaria-derived fields completed.
        # The two subclasses of Fragment are differentiated explicitly in the input sheet
        # in the field 'sample type'. 'assay and optional sequencing' relates to the subclass of CBASSAssayFragment.
        # This will be the most common subclass. 'sequencing only' relates to the subclass of CBASSNucleicAcidFragment.
        # This will be less common.

        # Fragments that that are of class CBASSAssayFragment will be assocaited to a HeatStressProfile object.
        # I will document the logic for making these below.
        # sample_required_fields = ["sample number", "colony","sample type", "16S barcode sequencing", "18S barcode sequencing", "ITS2 barcode sequencing", "metagenomic sequencing", "RNA-seq", "sample label", "sample token label"]
        # sample_optional_fields = ["treatment temperature", "Fv/Fm 1", "Fv/Fm 1 time point", "Fv/Fm 2", "Fv/Fm 2 time point", "sampling time point",	"storage chemical",	"storage temperature", "storage container", "relative zoox loss", "zoox loss method", "16S barcode sequencing", "18S barcode sequencing", "ITS2 barcode sequencing", "metagenomic sequencing", "RNA-seq", "CBASS photo label"]
        
        self.sample_df.replace({"na": nan}, inplace=True)

        for fragment, ser in self.sample_df.iterrows():
            # As before make a parameters dictionary where parameters are set to None
            # if not provided
            fragment_optional_params_dict = self._check_optional_fragment_params(ser=ser)
            
            # First we create Fragment object implemented as one of two possible subclasses:
            colony_fragment = self.s.query(Colony).filter(Colony.label==ser["colony"]).one()
            if ser["sample type"] == "sequencing only":
                new_cbass_frag = self._create_cbass_nuc_frag(ser, fragment_optional_params_dict, colony_fragment)
            elif ser["sample type"] == "assay and optional sequencing":
                new_cbass_frag = self._create_cbass_assay_frag(ser, fragment_optional_params_dict, colony_fragment)
                heat_stress_profile_frag = self._identify_create_heat_stress_profile(fragment_optional_params_dict, colony_fragment)
                
                # Associate the HeatStressProfile to the CBASSAssayFragment
                new_cbass_frag.heat_stress_profile=heat_stress_profile_frag
            self.s.add(new_cbass_frag)

            self._make_seq_effort_and_biosample_objects(ser, new_cbass_frag)
        
            # Finally, check for photos
            # We first need to see if there is a photos to look for
            # (i.e. whether the user has included an entry in the
            # 'CBASS photo label' column)
            # Unlike for the DiveTablePhoto and ColonyPhoto
            # we need to check if the CBASSFragmentPhoto db object has aleady been
            # created as multiple fragments can be associated to the same CBASSFragmentPhoto
            if not pd.isna(ser["CBASS photo label"]):
                self._make_associate_cbass_fragment_photo(ser["CBASS photo label"], new_frag=new_cbass_frag)


    def _make_associate_cbass_fragment_photo(self, photo_label, new_frag):
        # First check to see if the CBASSFragmentPhoto object already exists
        try:
            # If the photo already exists, simply associate the new fragment
            existing_cbass_frag_photo = self.s.query(CBASSFragmentPhoto).filter(CBASSFragmentPhoto.name==photo_label + ".jpg").one()
            existing_cbass_frag_photo.fragments.append(new_frag)
        except: # TODO work out the proper Exception class
            # Photo did not already exist so create new photo        
            match_list = []
            for photo_file in os.listdir(self.photo_dir):
                if photo_label == photo_file.replace(".JPG", "").replace(".jpg", "").replace(".jpeg", "").replace(".JPEG", ""):
                    match_list.append(photo_file)
            if len(match_list) != 1:
                raise RuntimeError(f"Error finding photo {photo_label}")
            else:
                # We found the photo so now make the db object
                # This db object may well have more attributes added to it
                # for FIVE's purposes but for the time being we'll just populate
                # it with some very basic parameters.

                # CHECK
                # 1 - if the name doesn't already exactly match the value given
                # in the input sheet, change it to match.
                # 2 - standardise the extendsion to .jpg

                new_frag_photo = CBASSFragmentPhoto(
                        url=os.path.join(self.photo_dir, match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")),
                        name=match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")
                    )
                new_frag_photo.fragments.append(new_frag)
                self.s.add(new_frag_photo)

    def _identify_create_heat_stress_profile(self, fragment_optional_params_dict, colony_fragment):
        # Each CBASSAssayFragment instance will be associated with a HeatStressProfile
        # instance. A HeatStressProfile represents one or more aquaria
        # (but usually a single aquarium) in which all of
        # the experimental fragments, from the same one experiment(!), 
        # are being subjected to the same temperature challenge.
        # So, the HeatStressProfile that should be associated to the
        # CBASSAssayFragment in question should be associated to the same Assay as
        # the Colony from which the CBASSAssayFragment originated. It should also
        # have a relative_challenge_temperature equal to that given in the inputsheet
        # for the fragment. NB there may be multiple colonies (same or differnt species)
        # in a given HeatStressProfile.
        try:
            heat_stress_profile_frag = self.s.query(HeatStressProfile).filter(
                        HeatStressProfile.cbass_assay==colony_fragment.assay,
                        HeatStressProfile.relative_challenge_temperature==fragment_optional_params_dict["treatment temperature"]
                        ).one()
        except: #TODO identify the correct exception (not found in database/does exist)
                    # Then the HeatStressProfile object does not yet exist
                    # Create it
            heat_stress_profile_frag = HeatStressProfile(
                        cbass_assay=colony_fragment.assay,
                        relative_challenge_temperature=float(fragment_optional_params_dict["treatment temperature"])
                        )
            self.s.add(heat_stress_profile_frag)
        return heat_stress_profile_frag

    def _create_cbass_assay_frag(self, ser, fragment_optional_params_dict, colony_fragment):
        new_cbass_frag = CBASSAssayFragment(
                    fv_fm_measurement_one_value=fragment_optional_params_dict["Fv/Fm 1"],
                    fv_fm_measurement_two_value=fragment_optional_params_dict["Fv/Fm 2"],
                    fv_fm_measurement_one_time_point=fragment_optional_params_dict["Fv/Fm 1 time point"],
                    fv_fm_measurement_two_time_point=fragment_optional_params_dict["Fv/Fm 2 time point"],
                    relative_sampling_time=int(ser["sampling time point"]),
                    storage_chemical=fragment_optional_params_dict["storage chemical"],
                    storage_temperature=fragment_optional_params_dict["storage temperature"],
                    storage_container=fragment_optional_params_dict["storage container"],
                    relative_zoox_loss=fragment_optional_params_dict["relative zoox loss"],
                    zoox_loss_method=fragment_optional_params_dict["zoox loss method"],
                    label=ser["sample label"],
                    token_label=ser["sample token label"],
                    colony=colony_fragment, comments=fragment_optional_params_dict["comments"]
                )
        
        return new_cbass_frag

    def _create_cbass_nuc_frag(self, ser, fragment_optional_params_dict, colony_fragment):
        new_cbass_frag = CBASSNucleicAcidFragment(
                    label=ser["sample label"],
                    token_label=ser["sample token label"],
                    storage_chemical=fragment_optional_params_dict["storage chemical"],
                    storage_temperature=fragment_optional_params_dict["storage temperature"],
                    storage_container=fragment_optional_params_dict["storage container"],
                    colony=colony_fragment, comments=fragment_optional_params_dict["comments"]
                    )
        return new_cbass_frag

    def _make_seq_effort_and_biosample_objects(self, ser, new_cbass_frag):
        # Now identify the required SequencingEffort and NCBIBiosample objects
        # There will be 1 NCBIBiosample object per fragement that has some sequencing
        # being done. I.e. if any of the "16S barcode sequencing",
        # "18S barcode sequencing", "ITS2 barcode sequencing",
        # "metagenomic sequencing" or "RNA-seq" input fields is 'yes' then we need to create
        # an NCBIBiosample and associate this to any of the SequencingEffort objects
        # that will be created.
        # There will be 1 SequencingEffort per sequencing field (see above) that has a 'yes'
        # in it. The different subclasses of Sequencing effort (SequencingEffortMetagnomic, 
        # SequencingEffortRNASeq, SequencingEffortBarcode) relate to the different sequencing types.
        # Each of the created SequencingEffort objects created will be associated to the fragment in question.
        biosample_created = False
        new_biosample = None
        if ser["16S barcode sequencing"] == "yes":
            if not biosample_created:
                new_biosample = NCBIBioSample()
                biosample_created = True
            barcode_16_seq_effort = SequencingEffortBarcode(
                    # Associate to the NCBIBioSample
                    ncbi_biosample=new_biosample,
                    # Associate to the Fragment
                    fragment=new_cbass_frag,
                    barcode="16S")
            self.s.add(barcode_16_seq_effort)
        if ser["18S barcode sequencing"] == "yes":
            if not biosample_created:
                new_biosample = NCBIBioSample()
                biosample_created = True
            barcode_18_seq_effort = SequencingEffortBarcode(
                    ncbi_biosample=new_biosample,
                    fragment=new_cbass_frag,
                    barcode="18S")
            self.s.add(barcode_18_seq_effort)
        if ser["ITS2 barcode sequencing"] == "yes":
            if not biosample_created:
                new_biosample = NCBIBioSample()
                biosample_created = True
            barcode_its2_seq_effort = SequencingEffortBarcode(
                    ncbi_biosample=new_biosample,
                    fragment=new_cbass_frag,
                    barcode="ITS2")
            self.s.add(barcode_its2_seq_effort)
            # NB there is no barcode field for these two subclasses of SequencingEffort.
        if ser["metagenomic sequencing"] == "yes":
            if not biosample_created:
                new_biosample = NCBIBioSample()
                biosample_created = True
            barcode_metag_seq_effort = SequencingEffortMetagnomic(
                    ncbi_biosample=new_biosample,
                    fragment=new_cbass_frag)
            self.s.add(barcode_metag_seq_effort)
        if ser["RNA-seq"] == "yes":
            if not biosample_created:
                new_biosample = NCBIBioSample()
                biosample_created = True
            barcode_rna_seq_effort = SequencingEffortRNASeq(
                    ncbi_biosample=new_biosample,
                    fragment=new_cbass_frag)
            self.s.add(barcode_rna_seq_effort)

    def _check_optional_fragment_params(self, ser):
        params_dict = {}
        integer_params = ["Fv/Fm 1", "Fv/Fm 1 time point", "Fv/Fm 2", "Fv/Fm 2 time point", "sampling time point"]
        for param in integer_params:
            if pd.isna(ser[param]):
                params_dict[param] = None
            else:
                params_dict[param] = int(ser[param])
        
        string_params = ["storage chemical", "storage temperature", "storage container", "zoox loss method", "comments"]
        for param in string_params:
            if pd.isna(ser[param]):
                params_dict[param] = None
            else:
                # The zoox loss method has drop down options, one of which is 'not conducted'
                # If this is selected then this should be set to None
                if param == "zoox loss method":
                    if ser[param] == "not conducted":
                        params_dict[param] = None
                    else:
                        params_dict[param] = str(ser[param])
                else:
                    params_dict[param] = str(ser[param])
        
        float_params = ["treatment temperature", "relative zoox loss"]
        for param in float_params:
            if pd.isna(ser[param]):
                    params_dict[param] = None
            else:
                if param == "relative zoox loss":
                    # Check for proper format taking into account that the percent
                    # may have been entered as an integer i.e. 50% = 50 or as a 
                    # decimal i.e. 50% = 0.5
                    # We want decimal format
                    if float(ser["relative zoox loss"]) > 1:
                        params_dict[param] = float(ser["relative zoox loss"])/100
                    else:
                        params_dict[param] = float(ser["relative zoox loss"])
                else:
                    params_dict[param] = float(ser["relative zoox loss"])
        return params_dict
        

    def _populate_colonies(self):
        # Each row in the COLONY sheet will be a Colony db object
        # The species information is held in a separate table so we will need
        # to check to see if the species in question already has an entry in the 
        # database. If not, then create an entry, if so, create a new entry.
        # Then we assign the retrieved or created species information to the Colonly object.
        
        # CHECK to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        # I will not implement this check here, but I imagine it will need to be done for the full implementation
        # All input fields except for 'colony photo label' should be filled for COLONY.
        self.colony_df.replace({"na": nan}, inplace=True)

        for colony, ser in self.colony_df.iterrows():
            # First check whether a CoralSpecies entry exists.
            try:
                spis_coral_species = self.s.query(CoralSpecies).filter(CoralSpecies.species_binomial_tax==ser["coral species"]).one()
            # TODO find the correct exception class
            except NoResultFound:
                # The species does not exist so create a new CoralSpecies object
                # TODO Ideally we want to be able to assign an NCBI taxonomy ID to the species
                # This can be looked up here: https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi
                # For this testing we will enter the data manually, but the values I am entering are
                # taken directly from
                # the NCBI taxonomy browser result from searching "Stylophora pistillata".
                # As part of the real implementation this should be automated.
                if ser["coral species"] == "Stylophora pistillata":
                    spis_coral_species = CoralSpecies(
                        phylum_tax="Cnidaria",
                        class_tax="Anthozoa",
                        order_tax="Scleractinia",
                        family_tax="Pocilloporidae",
                        genus_tax="Stylophora",
                        species_monomial_tax="pistillata",
                        species_binomial_tax="Stylophora pistillata",
                        ncbi_tax_id=50429,
                        abbreviation=ser["coral species abbreviation"]
                        )
                    self.s.add(spis_coral_species)
                else:
                    raise NotImplementedError("We're only setup for Stylophora pistillata for testing")
            
            # Then create the Colony object
            # The associated Dive and Assay objects can be looked up directly by their labels
            # The Site object needs to be looked up via the Assay object
            dive_colony = self.s.query(Dive).filter(Dive.label==ser["dive"]).one()
            assay_colony = self.s.query(CBASSAssay).filter(CBASSAssay.label==ser["experiment"]).one()
            site_colony = assay_colony.site
            
            # Covert the 'time collected' into a proper timestamp.
            # Get the date and timezone offset from the associated dive
            time_collected_colony = datetime.fromisoformat(str(dive_colony.time_in.date()) + "T" + str(ser["time collected"]) + self.time_zone_dict[site_colony.name_abbreviation])
            new_colony = Colony(
                coral_species=spis_coral_species,
                dive=dive_colony,
                site=site_colony,
                time_collected=time_collected_colony,
                depth_collected=float(ser["depth collected"]),
                assay=assay_colony,
                label=ser["colony label"]
                )
            self.s.add(new_colony)

            # Finally, check for photos
            # We first need to see if there are any photos to look for
            # (i.e. whether the user has included any entries in the
            # 'colony photo label' column)
            # We then need to check that they are present and make
            # a ColonyPhoto object if they are.
            if not pd.isna(ser["colony photo label"]):
                self._make_colony_photo(ser["colony photo label"], new_colony=new_colony)


    def _make_colony_photo(self, photo_label, new_colony):
        # All of the colony photos should have unique names
        # Every colony (i.e. row of the input) should have a different photo (or none)
        # so we don't have to worry about a colony sharing a photo with another colony
        # like we will have to worry about with the CBASSFragmentPhoto objects.
        match_list = []
        for photo_file in os.listdir(self.photo_dir):
            if photo_label == photo_file.replace(".JPG", "").replace(".jpg", "").replace(".jpeg", "").replace(".JPEG", ""):
                match_list.append(photo_file)
        if len(match_list) != 1:
            raise RuntimeError(f"Error finding photo {photo_label}")
        else:
            # We found the photo so now make the db object
            # This db object may well have more attributes added to it
            # for FIVE's purposes but for the time being we'll just populate
            # it with some very basic parameters.

            # CHECK
            # 1 - if the name doesn't already exactly match the value given
            # in the input sheet, change it to match.
            # 2 - standardise the extension to .jpg

            self.s.add(
                ColonyPhoto(
                    colony=new_colony,
                    url=os.path.join(self.photo_dir, match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")),
                    name=match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")
                )
            )

    def _populate_dives(self):
        # CHECK to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        # I will not implement this check here, but I imagine it will need to be done for the full implementation.
        # We are currently not using the "scientist that added this" input column. Need to check with Chris Voolstra.
        # dive_required_fields = ["dive number", "site", "dive start timestamp", "dive end timestamp", "scientist that added this", "dive label"]
        # dive_optional_fields = ["water temperature", "max depth", "diver 1" , "diver 2", "purpose", "comments", "dive table photo label 1",	"dive table photo label 2",	"dive table photo label 3"]
        self.dive_df.replace({"na": nan}, inplace=True)

        for dive, ser in self.dive_df.iterrows():
            params_dict = self._check_optional_diver_params(ser)

            # Get the site to associate with the dive by looking up the site abbreviation
            site = self.s.query(Site).filter(Site.name_abbreviation==ser["site"]).one()

            new_dive = Dive(
                site=site,
                time_in=datetime.fromisoformat(ser["dive start timestamp"] + self.time_zone_dict[ser["site"]]),
                time_out=datetime.fromisoformat(ser["dive end timestamp"] + self.time_zone_dict[ser["site"]]),
                max_depth=params_dict["max depth"],
                purpose=params_dict["purpose"],
                comments=params_dict["comments"],
                water_temperature=params_dict["water temperature"],
                label=ser["dive label"]
                )

            self.s.add(new_dive)

            # Check whether users have been provided in the input
            self._add_user_to_dive(ser, "diver 1", new_dive)
            self._add_user_to_dive(ser, "diver 2", new_dive)

            # Finally, check for photos
            # We first need to see if there are any photos to look for
            # (i.e. whether the user has included any entries in the
            # 'dive table photo label X' columns)
            # We then need to check that they are present and make
            # a DiveTablePhoto object if they are.
            for dive_table_photo_field in ["dive table photo label 1", "dive table photo label 2", "dive table photo label 3"]:
                if not pd.isna(ser[dive_table_photo_field]):
                    self._make_dive_table_photo(ser[dive_table_photo_field], new_dive=new_dive)
            
    def _make_dive_table_photo(self, photo_label, new_dive):
        # NOTE this code will not be tested as there are no DiveTablePhotos provided
        # as part of the CBASS84 project.
        # All of the dive photos should have unique names
        # Every dive (i.e. row of the input) should have a different set of photos
        # so we don't have to worry about a dive sharing a photo with another dive
        # like we will have to worry about with the CBASSFragmentPhoto objects.
        match_list = []
        for photo_file in os.listdir(self.photo_dir):
            if photo_label in photo_file:
                match_list.append(photo_file)
        if len(match_list) != 1:
            raise RuntimeError(f"Error finding photo {photo_label}")
        else:
            # We found the photo so now make the db object
            # This db object may well have more attributes added to it
            # for FIVE's purposes but for the time being we'll just populate
            # it with some very basic parameters.

            # CHECK
            # 1 - if the name doesn't already exactly match the value given
            # in the input sheet, change it to match.

            self.s.add(
                DiveTablePhoto(
                    dive=new_dive,
                    url=os.path.join(self.photo_dir, match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")),
                    name=match_list[0].replace(".JPG", ".jpg").replace(".jpeg", ".jpg").replace(".JPEG", ".jpg")
                )
            )

    def _check_optional_diver_params(self, ser):
        # Check which of the optional parameters have been provied.
        # Set to None if they have not been provided.
        params_dict = {}
        if pd.isna(ser["max depth"]):
            params_dict["max depth"] = None
        else:
            try:
                params_dict["max depth"] = float(ser["max depth"])
            except ValueError:
                raise RuntimeError("error with max depth")
        if pd.isna(ser["water temperature"]):
            params_dict["water temperature"] = None
        else:
            try:
                params_dict["water temperature"] = float(ser["water temperature"])
            except ValueError:
                raise RuntimeError("error with water temp")

        if pd.isna(ser["purpose"]):
            params_dict["purpose"] = None
        else:
            params_dict["purpose"] = ser["purpose"]
        if pd.isna(ser["comments"]):
            params_dict["comments"] = None
        else:
            params_dict["comments"] = ser["comments"]
        return params_dict

    def _add_user_to_dive(self, ser, diver_string, new_dive):
        if not pd.isna(ser[diver_string]):
            # A user has been provided and we should associate the appropriate user
            # by adding to the nex_experiment object
            try:
                new_dive.divers.append(self.s.query(User).filter(User.first_name==ser[diver_string].split(" ")[0], User.last_name==ser[diver_string].split(" ")[-1]).one())
            # NOTE TODO these sorts of errors will need to be better handled in the actual implementation
            except:
                raise RuntimeError("Error identifying user in DIVE table")

    def _create_environment_record(self, ser, new_site):
        # Create the EnvironmentRecord and link it to the Site object just created
        # CHECK that the 'timestamp' and the 'time zone' provided by the user is in the correct format
        # CHECK that the env_broad_scale, env_local_scale and env_medium are valid terms from 
        # here: https://www.ebi.ac.uk/ols/index

        # To create the timestamp object we wil use the python3 datetime module
        timestamp = datetime.fromisoformat(ser["timestamp"] + ser["time zone"])
        self.time_zone_dict[ser["site abbreviation"]] = ser["time zone"]
        self.time_zone_dict[ser["record label"]] = ser["time zone"]

        # CHECK whether the optional parameters exist and set to None if not
        param_dict = self._check_site_optional_params_valid(ser)

        # NOTE for the time being we will ignore 'coral_cover'.
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
        # The headers here perfectly match those of the input excel file
        # so it should be clear which input column go to which db table column
        # I will use the exact excel input column headers throughout this script
        # so the relation between excel and db objects should be clear. 
        new_site = Site(
            name=ser["site name"],
            name_abbreviation=ser["site abbreviation"],
            latitude=ser["latitude"],
            longitude=ser["longitude"],
            country=ser["country"],
            country_abbreviation=ser["country abbreviation"],
            time_zone=ser["time zone"],
            sub_region=record_sub_region)

        self.s.add(new_site)
        return new_site

    def _make_campaign(self, lead_user):
        # We will enter the campagin manually, as this will have been created by an
        # admin in the back end before a user does a submission.
        # The uploading user will have access to a specific
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
        # create them manually here so that we can work with them for the testing.
        # The example we are working with works with 2 users:
        # Christian R Voolstra and Carol Buitrago-López
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
        # Each of the rows in EXPERIMENT will make 1 CBASSAssay object

        # CHECKS
        # 1 - General check to see that all required fields have been populated (after removing user entries like "na", "NA", "N/A").
        # experiment_required_fields = ["experiment number", "site record", "experiment type", "baseline temp", "experiment start timestamp", "experiment stop timestamp",	"scientist that added this", "experiment label"]
        # experiment_optional_fields = ["light level",	"flow rate", "tank volume",	"seawater source",	"scientist 1",	"scientist 2"]
        # I will not implement this check here, but I imagine it will need to be done for the full implementation
        self.experiment_df.replace({"na": nan}, inplace=True)
        self.experiment_df.set_index("experiment number", inplace=True, drop=True)

        # NOTE we currently don't make use of the 'scientist that added this'
        # I need to check with Chris Voolstra what the purpose of this field is 
        # but I think maybe they are not required in the database.

        for experiment, ser in self.experiment_df.iterrows(): # for each row of the excel sheet
            # CHECK whether the optional parameters exist and set to None if not
            params_dict = self._check_cbass_assay_optional_params_valid(ser)

            new_experiment = CBASSAssay(
                site=self.s.query(Site).filter(Site.name_abbreviation==ser["site record"].split("_")[-1]).one(),
                environment_record = self.s.query(EnvironmentRecord).filter(EnvironmentRecord.label==ser["site record"]).one(),
                campaign = self.campaign,
                label = ser["experiment label"],
                start_time=datetime.fromisoformat(ser["experiment start timestamp"] + self.time_zone_dict[ser["site record"]]),
                stop_time=datetime.fromisoformat(ser["experiment stop timestamp"] + self.time_zone_dict[ser["site record"]]),
                baseline_temp=float(ser["baseline temp"]),
                flow_rate=params_dict["flow rate"],
                light_level=params_dict["light level"], tank_volume=params_dict["tank volume"],
                seawater_source=params_dict["seawater source"]
                )

            # Associate users
            # We need to check whether the input inlcludes users to be associated to the CBASSAssay
            self._add_user_to_cbass_assay(ser, "scientist 1", new_experiment)
            self._add_user_to_cbass_assay(ser, "scientist 2", new_experiment)

            self.s.add(new_experiment)

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
                new_experiment.users.append(self.s.query(User).filter(User.first_name==ser[scientist_string].split(" ")[0], User.last_name==ser[scientist_string].split(" ")[-1]).one())
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

    schema_test = GSSchemaTest(s_scope=s, use_cache=True).start()
    
    foo = "bar"
    