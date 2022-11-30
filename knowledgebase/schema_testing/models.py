"""Quick setup: https://www.learndatasci.com/tutorials/using-databases-python-postgres-sqlalchemy-and-alembic/"""

from decimal import Decimal
from re import I
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey, Numeric, TIMESTAMP
from sqlalchemy.orm import relation, relationship
from sqlalchemy.sql.expression import null
from sqlalchemy.sql.selectable import FromClause
from sqlalchemy.sql.sqltypes import Time

Base = declarative_base()

# many_to_many join tables
campaign_user = Table('campaign_user', Base.metadata,
    Column('campaign_id', ForeignKey('campaign.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key=True)
)

dive_user = Table('dive_user', Base.metadata,
    Column('dive_id', ForeignKey('dive.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key=True)
)

assay_user = Table('assay_user', Base.metadata,
    Column('assay_id', ForeignKey('assay.id'), primary_key=True),
    Column('user_id', ForeignKey('user.id'), primary_key=True)
)

# DONE
class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    # TODO will come from a controlled vocab.
    role = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    username = Column(String, nullable=False, unique=True)
    registration_date = Column(TIMESTAMP(timezone=True), nullable=False)
    led_campaigns = relationship("Campaign", back_populates="lead_user", cascade="all, delete", passive_deletes=True)
    campaigns = relationship("Campaign", secondary=campaign_user, back_populates="users")
    dives = relationship("Dive", secondary=dive_user, back_populates="divers")
    assays = relationship("Assay", secondary=assay_user, back_populates="users")
    def __repr__(self):
        return f"<User(id='{self.id}', role='{self.role}', email={self.email}, user_name={self.user_name})>"


# DONE
class Campaign(Base):
    __tablename__ = "campaign"
    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    lead_user = relationship("User", back_populates="led_campaigns")
    assays = relationship("Assay", back_populates="campaign", cascade="all, delete", passive_deletes=True)
    users = relationship("User", secondary=campaign_user, back_populates="campaigns")
    name = Column(String(100), nullable=False, unique=True)
    start_date = Column(TIMESTAMP(timezone=True), nullable=False)
    end_date = Column(TIMESTAMP(timezone=True), nullable=False)
    
    # Having this as nullable=False will enforce that the lead_user
    # creates an NCBI BioProject object (https://www.ncbi.nlm.nih.gov/bioproject?cmd=Retrieve)
    ncbi_bio_project_accession = Column(String(10), nullable=False, unique=True)
    


# DONE
class Site(Base):
    __tablename__ = "site"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dives = relationship("Dive", back_populates="site", cascade="all, delete", passive_deletes=True)
    environment_records = relationship("EnvironmentRecord", back_populates="site", cascade="all, delete", passive_deletes=True)
    latitude = Column(Numeric(precision=7, scale=5), nullable=False)
    longitude = Column(Numeric(precision=8, scale=5), nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    name_abbreviation = Column(String(10), unique=True, nullable=False)
    region_id = Column(Integer, ForeignKey("region.id", ondelete="CASCADE"), nullable=True)
    region = relationship("Region", back_populates="sites")
    time_zone = Column(String(6), nullable=False)
    country = Column(String(100), nullable=False)
    country_abbreviation = Column(String(2), nullable=True)
    # This is free form text that will be combined with the above country
    # value in order to create the entry for the file geo_loc_name
    # in the NCBI submission sheet.
    sub_region = Column(String(200), nullable=True)
    colonies = relationship("Colony", back_populates="site", cascade="all, delete", passive_deletes=True)
    assays = relationship("Assay", back_populates="site", cascade="all, delete", passive_deletes=True)

class EnvironmentRecord(Base):
    __tablename__ = "environment_record"
    id = Column(Integer, primary_key=True, autoincrement=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    site = relationship("Site", back_populates="environment_records")
    assays = relationship("Assay", back_populates="environment_record", cascade="all, delete", passive_deletes=True)
    record_timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    env_broad_scale = Column(String(100), nullable=False)
    env_local_scale = Column(String(100), nullable=False)
    env_medium = Column(String(100), nullable=False)
    # TODO determine format for turbidity
    turbidity = Column(Numeric(precision=6, scale=3), nullable=True)
    sea_surface_temperature = Column(Numeric(precision=4, scale=2), nullable=True)
    sea_surface_temperature_stdev = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine format for chlorophyl a
    chlorophyll_a = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine format for salinity
    salinity = Column(Numeric(precision=4, scale=2), nullable=True)
    ph = Column(Numeric(precision=4, scale=2), nullable=True)
    dissolved_oxygen = Column(Numeric(precision=5, scale=2), nullable=True)
    maximum_monthy_mean = Column(Numeric(precision=4, scale=2), nullable=True)
    thermall_stress_anomaly_frequency_stdev = Column(Numeric(precision=4, scale=2), nullable=True)
    # TODO determine the units and format of coral_cover
    coral_cover = Column(Numeric(precision=4, scale=2), nullable=True)
    label = Column(String(200), nullable=False, unique=True)

# DONE
class Region(Base):
    __tablename__ = "region"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100))
    # TODO check to see if this needs to be linked to a controlled vocab from NCBI
    abbreviation = Column(String(3), nullable=False)
    sites = relationship("Site", back_populates="region", cascade="all, delete", passive_deletes=True)

# DONE
class Dive(Base):
    __tablename__ = "dive"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colonies = relationship("Colony", back_populates="dive", cascade="all, delete", passive_deletes=True)
    dive_table_photos = relationship("DiveTablePhoto", back_populates="dive", cascade="all, delete", passive_deletes=True)
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"))
    site = relationship("Site", back_populates="dives")
    divers = relationship("User", secondary=dive_user, back_populates="dives")
    time_in = Column(TIMESTAMP(timezone=True), nullable=False)
    time_out = Column(TIMESTAMP(timezone=True), nullable=False)
    # Depth in meters with 2 decimal places.
    max_depth = Column(Numeric(precision=5, scale=2), nullable=True)
    # Probably best if this is a controlled vocabulary
    # TODO constraint: specifiy the vocab; Have an 'other' category.
    purpose = Column(String(100), nullable=True)
    # Freehand value for additional information
    comments = Column(String(1000), nullable=True)
    # deg C of the water logged by the users dive computer
    water_temperature = Column(Numeric(precision=4, scale=2))
    label = Column(String(200), nullable=False, unique=True)

# DONE
class CoralSpecies(Base):
    __tablename__ = "coral_species"
    id = Column(Integer, primary_key=True, autoincrement=True)
    phylum_tax = Column(String(50))
    class_tax = Column(String(50))
    order_tax = Column(String(50))
    family_tax = Column(String(50))
    genus_tax = Column(String(50))
    species_monomial_tax = Column(String(50))
    species_binomial_tax = Column(String(100), unique=True, nullable=False)
    # TODO Build in a check to make sure that this is a valid ID
    # in the NCBI taxonomy database (https://www.ncbi.nlm.nih.gov/taxonomy)
    ncbi_tax_id = Column(Integer, nullable=False, unique=True)
    abbreviation = Column(String(10), nullable=False, unique=True)
    colonies = relationship("Colony", back_populates="coral_species", cascade="all, delete", passive_deletes=True)

# DONE
class Colony(Base):
    __tablename__ = "colony"
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Many to one relationship to coral_species
    coral_species_id = Column(Integer, ForeignKey('coral_species.id', ondelete="CASCADE"), nullable=False)
    coral_species = relationship("CoralSpecies", back_populates="colonies")
    # Many to one relationship to dive
    dive_id = Column(Integer, ForeignKey('dive.id', ondelete="CASCADE"), nullable=False)
    dive = relationship("Dive", back_populates="colonies")
    # Many to one relationship to site
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    site = relationship("Site", back_populates="colonies")
    time_collected = Column(TIMESTAMP(timezone=True), nullable=False)
    
    depth_collected = Column(Numeric(precision=5, scale=2), nullable=False)
    colony_photo = relationship("ColonyPhoto", back_populates="colony", cascade="all, delete", passive_deletes=True)
    fragments = relationship("Fragment", back_populates="colony", cascade="all, delete", passive_deletes=True)
    # Relate Colony to Assay
    assay_id = Column(Integer, ForeignKey("assay.id", ondelete="CASCADE"), nullable=False)
    assay = relationship("Assay", back_populates="colonies")
    label = Column(String(200), nullable=False)

# DONE
class ColonyPhoto(Base):    
    __tablename__ = "colony_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colony_id = Column(Integer, ForeignKey(column="colony.id", ondelete="CASCADE"), nullable=False)
    colony = relationship("Colony", back_populates="colony_photo")
    name = Column(String(100), nullable=False, unique=True)
    url = Column(String(1000), nullable=True, unique=True)

# DONE
class DiveTablePhoto(Base):
    __tablename__ = "diver_table_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    dive_id = Column(Integer, ForeignKey("dive.id", ondelete="CASCADE"), nullable=False)
    dive = relationship("Dive", back_populates="dive_table_photos")
    url = Column(String(1000), nullable=True, unique=True)
    name = Column(String(100), nullable=False, unique=True)


class Fragment(Base):
    __tablename__ = "fragment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    colony_id = Column(Integer, ForeignKey("colony.id", ondelete="CASCADE"), nullable=False)
    colony = relationship("Colony", back_populates="fragments")
    sequencing_efforts = relationship("SequencingEffort", back_populates="fragment", cascade="all, delete", passive_deletes=True)
    type = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity':'fragment',
        'polymorphic_on':type
    }


class CBASSFragmentPhoto(Base):
    __tablename__ = "cbass_fragment_photo"
    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(1000), nullable=True, unique=True)
    name = Column(String(100), nullable=False, unique=True)
    fragments = relationship("CBASSAssayFragment", back_populates="cbass_fragment_photo", cascade="all, delete", passive_deletes=True)


class CBASSNucleicAcidFragment(Fragment):
    __tablename__ = "cbass_nucleic_acid_fragment"
    id = Column(ForeignKey("fragment.id"), primary_key=True)
    label = Column(String(200), nullable=False, unique=True)
    token_label = Column(String(200), nullable=False, unique=False)
    storage_chemical = Column(String(100), nullable=True)
    storage_temperature = Column(String(20), nullable=True)
    storage_container = Column(String(100), nullable=True)
    comments = Column(String(1000), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'cbass_nucleic_acid_fragment',
    }


class CBASSAssayFragment(Fragment):
    __tablename__ = "cbass_assay_fragment"
    id = Column(ForeignKey("fragment.id"), primary_key=True)
    heat_stress_profile_id = Column(Integer, ForeignKey("heat_stress_profile.id", ondelete="CASCADE"))
    heat_stress_profile = relationship("HeatStressProfile", back_populates="cbass_assay_fragments")
    fv_fm_measurement_one_value = Column(Numeric(precision=6, scale=3), nullable=True)
    # time in minutes
    fv_fm_measurement_one_time_point = Column(Integer, nullable=True)
    fv_fm_measurement_two_value = Column(Numeric(precision=6, scale=3), nullable=True)
    # time in minutes
    fv_fm_measurement_two_time_point = Column(Integer, nullable=True)
    # Time in minutes
    relative_sampling_time = Column(Integer, nullable=False)
    cbass_fragment_photo_id = Column(Integer, ForeignKey("cbass_fragment_photo.id", ondelete="CASCADE"))
    cbass_fragment_photo = relationship("CBASSFragmentPhoto", back_populates="fragments")
    label = Column(String(200), nullable=False, unique=True)
    token_label = Column(String(200), nullable=False, unique=False)
    relative_zoox_loss = Column(Numeric(precision=4, scale=4), nullable=True)
    zoox_loss_method = Column(String(30), nullable=True)
    storage_chemical = Column(String(100), nullable=True)
    storage_temperature = Column(String(20), nullable=True)
    storage_container = Column(String(100), nullable=True)
    comments = Column(String(1000), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'cbass_assay_fragment',
    }


class HeatStressProfile(Base):
    __tablename__ = "heat_stress_profile"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cbass_assay_fragments = relationship("CBASSAssayFragment", back_populates="heat_stress_profile", cascade="all, delete", passive_deletes=True)
    cbass_assay_id = Column(Integer, ForeignKey("cbass_assay.id"))
    cbass_assay = relationship("CBASSAssay", back_populates="heat_stress_profiles")
    relative_challenge_temperature = Column(Numeric(precision=2, scale=1), nullable=False)


class Assay(Base):
    __tablename__ = "assay"
    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50))
    environment_record_id = Column(Integer, ForeignKey("environment_record.id", ondelete="CASCADE"), nullable=False)
    environment_record = relationship("EnvironmentRecord", back_populates="assays")
    campaign_id = Column(Integer, ForeignKey("campaign.id", ondelete="CASCADE"), nullable=False)
    campaign = relationship("Campaign", back_populates="assays")
    label = Column(String(200), nullable=False)
    users = relationship("User", secondary=assay_user, back_populates="assays")
    site_id = Column(Integer, ForeignKey("site.id", ondelete="CASCADE"), nullable=False)
    site = relationship("Site", back_populates="assays")
    colonies = relationship("Colony", back_populates="assay", cascade="all, delete", passive_deletes=True)

    __mapper_args__ = {
        'polymorphic_identity':'assay',
        'polymorphic_on':type
    }


class CBASSAssay(Assay):
    __tablename__ = "cbass_assay"
    id = Column(Integer, ForeignKey("assay.id"), primary_key=True)
    heat_stress_profiles = relationship("HeatStressProfile", back_populates="cbass_assay")
    start_time = Column(TIMESTAMP(timezone=True), nullable=False)
    stop_time = Column(TIMESTAMP(timezone=True), nullable=False)
    baseline_temp = Column(Numeric(precision=4, scale=2), nullable=False)
    # in liters per hour
    flow_rate = Column(Numeric(precision=6, scale=2), nullable=True)
    # TODO confirm units
    light_level = Column(Numeric(precision=6, scale=3), nullable=True)
    tank_volume = Column(Integer, nullable=True)
    seawater_source = Column(String(50), nullable=True)

    __mapper_args__ = {
        'polymorphic_identity':'cbass_assay',
    }

# This table has no direct practical application currently
# I have put it here to act as a place holder and to show that
# there will be different subclasses of Assay.
class CalcificationAssay(Assay):
    __tablename__ = "calcification_assay"
    id = Column(Integer, ForeignKey("assay.id"), primary_key=True)

    __mapper_args__ = {
        'polymorphic_identity':'calcification_assay',
    }

class NCBIBioSample(Base):
    __tablename__ = "ncbi_biosample"
    id = Column(Integer, primary_key=True, autoincrement=True)
    accession = Column(String(50), nullable=True)
    sequencing_efforts = relationship("SequencingEffort", back_populates="ncbi_biosample", cascade="all, delete", passive_deletes=True)

class SequencingEffort(Base):
    __tablename__ = "sequencing_effort"
    id = Column(Integer, primary_key=True, autoincrement=True)
    fragment_id = Column(Integer, ForeignKey("fragment.id", ondelete="CASCADE"), nullable=False)
    fragment = relationship("Fragment", back_populates="sequencing_efforts")
    ncbi_biosample_id = Column(Integer, ForeignKey("ncbi_biosample.id", ondelete="CASCADE"), nullable=True)
    ncbi_biosample = relationship("NCBIBioSample", back_populates="sequencing_efforts")
    type = Column(String(50))

    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort',
        'polymorphic_on':type
    }

class SequencingEffortMetagnomic(SequencingEffort):
    __tablename__ = "sequencing_effort_metagenomic"
    id = Column(ForeignKey("sequencing_effort.id"), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_metagenomic',
    }

class SequencingEffortRNASeq(SequencingEffort):
    __tablename__ = "sequencing_effort_rna_seq"
    id = Column(ForeignKey("sequencing_effort.id"), primary_key=True)
    
    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_rna_seq',
    }

class SequencingEffortBarcode(SequencingEffort):
    __tablename__ = "sequencing_effort_barcode"
    id = Column(ForeignKey("sequencing_effort.id"), primary_key=True)
    barcode = Column(String(50), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity':'sequencing_effort_barcode',
    }
